# src/services/chat_service.py
from src.assistant.assistant_client import send_message_to_assistant, generate_structured_quiz, stream_structured_quiz
from src.assistant.image_handler import format_image_urls_for_openai
from src.storage.conversations_table import save_conversation
from src.storage.messages_table import save_message, get_recent_messages
from src.config.page_vectorstores import get_stores_for_page
from src.utils.logging_utils import log_event
from src.services.quiz_service import QuizService
from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal
import json
import re
import logging

logger = logging.getLogger(__name__)

def _normalize_email_for_storage(val):
    if val is None: return None
    if isinstance(val, str) and val.strip() == "": return None
    return val

def _normalize_page(val: str | None) -> str:
    if not val or (isinstance(val, str) and val.strip() == ""):
        return "/"
    return val

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def _build_history_list(conversation_id: str, max_user: int = 3, max_assistant: int = 3) -> List[Dict[str, Any]]:
    try:
        msgs = get_recent_messages(conversation_id=conversation_id, limit=20, ascending=True)
        if not msgs: return []

        user_msgs = [m for m in msgs if m.get("Role") == "user"][-max_user:]
        asst_msgs = [m for m in msgs if m.get("Role") == "assistant"][-max_assistant:]
        merged = sorted(user_msgs + asst_msgs, key=lambda m: m["Timestamp"])

        history_list = []
        for m in merged:
            role = m.get("Role", "user")
            text_content = m.get("MessageText", "")
            
            # Inject hidden context if this was a quiz response
            metadata = m.get("Metadata") or m.get("Meta")
            if role == "assistant" and metadata:
                try:
                    metadata_str = json.dumps(metadata, default=decimal_default)
                    hidden_context = (
                        f"\n\n[SYSTEM CONTEXT: User cannot see this. "
                        f"I previously generated this interactive quiz: {metadata_str}. "
                        f"I must use this data to answer follow-up questions about the quiz.]"
                    )
                    text_content += hidden_context
                except Exception:
                    pass

            content = [{"type": "input_text" if role == "user" else "output_text", "text": text_content}]
            history_list.append({"role": role, "content": content})
        
        return history_list
    except Exception as e:
        log_event("history_fetch_failed", {"conversation_id": conversation_id}, level="warning", error=e)
        return []

def get_ai_response(
    message: str | None,
    user_id: str | None,
    name: str | None,
    email: str | None,
    page: str | None,
    conversation_id: str | None = None,
    image_urls: list[str] | None = None,
    mode: str = "omega",
    intent: str = "chat",
    stream_manager: Any | None = None # 🟢 Optional StreamManager
) -> Tuple[str, str, str, Dict | None]: 
    
    page = _normalize_page(page)

    # Step 1: Find-or-create conversation
    try:
        if conversation_id:
            log_event("conversation_reused", {"conversation_id": conversation_id})
        else:
            sanitized_email = _normalize_email_for_storage(email)
            conversation_data = save_conversation(
                user_id=user_id, name=name or "", email=sanitized_email,
                title=(message or "[Sin texto]")[:40], page=page,
            )
            conversation_id = conversation_data["ConversationId"]
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save/reuse conversation: {e}")

    # Step 2: Build Input
    conversation_input = _build_history_list(conversation_id)
    
    current_user_content = []
    if message:
        current_user_content.append({"type": "input_text", "text": message})
    current_user_content.extend(format_image_urls_for_openai(image_urls or []))

    if current_user_content:
        conversation_input.append({"role": "user", "content": current_user_content})

    # ------------------------------------------------------------------
    # 🟢 BRANCH: QUIZ (Structured) vs CHAT (Standard)
    # ------------------------------------------------------------------
    quiz_data = None
    final_reply_text = ""
    
    if intent == "quiz":
        # A. Setup Quiz Instructions
        topic_hint = message if message else "General Knowledge"
        num_questions = 5
        if message:
            match = re.search(r'\b(\d+)\b', message)
            if match:
                parsed_num = int(match.group(1))
                if 1 <= parsed_num <= 10: 
                    num_questions = parsed_num

        conversation_input.append(QuizService.get_system_instruction(topic=topic_hint, num_questions=num_questions))

        # B. Call API (Streaming or Batch)
        try:
            # 🟢 STREAMING PATH
            if stream_manager:
                log_event("quiz_streaming_started", {"user_id": user_id, "mode": mode})
                
                stream_gen = stream_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id,
                    page=page,
                    name=(name or None),
                    email=_normalize_email_for_storage(email),
                    mode=mode 
                )
                
                # Internal accumulators
                seen_indices = set()
                accumulated_questions = []
                final_reply_text = "Aquí tienes tu simulacro." # Default backup

                # Iterate over generator events
                for event in stream_gen:
                    evt_type = event.get("type")
                    
                    if evt_type == "intro":
                        text = event.get("text", "")
                        logger.info(f"ChatService: Intro received: {text[:30]}...")
                        final_reply_text = text
                        
                    elif evt_type == "question":
                        q_data = event.get("data") # Pydantic model
                        q_dict = q_data.dict()     # Convert to dict
                        idx = event.get("index", 0)
                        
                        # 🚀 Send to WebSocket immediately
                        stream_manager.send_quiz_item(question_data=q_dict, index=idx)
                        logger.info(f"ChatService: Pushed Question {idx} to client.")
                        
                        # Accumulate locally (safely)
                        if idx not in seen_indices:
                            accumulated_questions.append(q_dict)
                            seen_indices.add(idx)
                        
                    elif evt_type == "done":
                        # 🟢 CRITICAL FIX: Use the SDK's final validated object
                        # This ensures we save the COMPLETE list to DynamoDB
                        final_model = event.get("full_response")
                        if final_model:
                            logger.info(f"ChatService: Stream Done. SDK reports {len(final_model.questions)} questions.")
                            final_reply_text = final_model.intro_message
                            # Overwrite local accumulation with the perfect list
                            accumulated_questions = [q.dict() for q in final_model.questions]
                        
                    elif evt_type == "error":
                        error_msg = event.get("error", "Unknown stream error")
                        log_event("quiz_stream_error", {"error": error_msg}, level="error")
                        stream_manager.send_error(error_msg)

                # Final Data Construction
                quiz_data = {
                    "quiz_mode": "batch", 
                    "questions": accumulated_questions
                }
                log_event("quiz_streaming_completed", {"count": len(accumulated_questions)})

            # 🟢 BATCH PATH (Fallback)
            else:
                quiz_model = generate_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id,
                    page=page,
                    name=(name or None),
                    email=_normalize_email_for_storage(email),
                    mode=mode 
                )
                
                quiz_data = {
                    "quiz_mode": "batch", 
                    "questions": [q.dict() for q in quiz_model.questions]
                }
                final_reply_text = quiz_model.intro_message

        except Exception as e:
            log_event("quiz_generation_failed", {"error": str(e)}, level="error")
            final_reply_text = (
                "⚠️ **Error de Generación**: No pudimos generar el simulacro. "
                "Por favor intenta de nuevo."
            )
            quiz_data = None

    else:
        # Standard Chat Mode
        try:
            final_reply_text = send_message_to_assistant(
                conversation_input=conversation_input,
                user_id=user_id,
                page=page,
                name=(name or None),
                email=_normalize_email_for_storage(email),
                mode=mode 
            )
        except Exception as e:
            raise RuntimeError(f"❌ OpenAI Chat API failed: {e}")

    # Step 7: Persist
    assistant_timestamp = ""
    try:
        if message:
            save_message(conversation_id, role="user", message_text=message)
        for img in image_urls or []:
            save_message(conversation_id, role="user", message_text=f"[Imagen] {img}")
        
        # Save the FINAL, complete data
        saved_item = save_message(
            conversation_id, 
            role="assistant", 
            message_text=final_reply_text,
            metadata=quiz_data 
        )
        if saved_item and isinstance(saved_item, dict):
            assistant_timestamp = saved_item.get("Timestamp", "")

    except Exception as e:
        raise RuntimeError(f"❌ Failed to save messages: {e}")

    return final_reply_text, conversation_id, assistant_timestamp, quiz_data