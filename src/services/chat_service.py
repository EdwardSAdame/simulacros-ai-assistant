# src/services/chat_service.py
import json
import re
import logging
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional

# 🟢 CONFIG & UTILS
from src.config.settings import get_openai_client, get_vector_search_max_results
# 🔴 REMOVED: get_search_model_name
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.config.page_vectorstores import get_stores_for_page
from src.config.web_search_config import get_search_filters 
from src.utils.logging_utils import log_event

# 🟢 NEW: Import the Context Builder
from src.services.context_builder import build_runtime_context

# 🟢 STORAGE
from src.storage.conversations_table import save_conversation, _find_conversation_timestamp
from src.storage.messages_table import save_message, get_recent_messages

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

# 🟢 NEW LOGIC: Context Resolution Engine
def determine_exam_context(page_url: str, message_text: str | None = None) -> str:
    """
    Decides the Exam Context (UNAL vs ICFES vs GENERAL).
    """
    if page_url:
        url_lower = page_url.lower()
        if "unal" in url_lower: return "UNAL"
        if "icfes" in url_lower: return "ICFES"
    
    if message_text:
        msg_lower = message_text.lower()
        if any(x in msg_lower for x in ["unal", "nacional", "universidad nacional"]):
            return "UNAL"
        if any(x in msg_lower for x in ["icfes", "saber 11", "saber pro", "estado"]):
            return "ICFES"
            
    return "GENERAL" 

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
            
            metadata = m.get("Metadata") or m.get("Meta")
            if role == "assistant" and metadata:
                try:
                    metadata_str = json.dumps(metadata, default=decimal_default)
                    hidden_context = (
                        f"\n\n[SYSTEM CONTEXT: User cannot see this. "
                        f"I previously generated this interactive content: {metadata_str}. "
                        f"I must use this data to answer follow-up questions.]"
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

# ------------------------------------------------------------------
# MAIN FUNCTION
# ------------------------------------------------------------------
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
    requires_visuals: bool = False,
    stream_manager: Any | None = None 
) -> Tuple[str, str, str, Dict | None]: 
    
    # 🟢 LAZY IMPORTS
    from src.assistant.assistant_client import send_message_to_assistant, generate_structured_quiz, stream_structured_quiz
    from src.assistant.image_handler import format_image_urls_for_openai
    from src.services.quiz_service import QuizService

    page = _normalize_page(page)

    # 🟢 1. INTELLIGENCE LAYER
    exam_context = determine_exam_context(page, message)
    selected_vector_stores = get_stores_for_page(page)

    # 🟢 2. DETERMINE WEB SEARCH CONFIG
    # Get filters based on context (ICFES -> icfes.gov.co, etc.)
    web_search_config = get_search_filters(exam_context)
    
    # Is search ENABLED as a tool? Yes, if we have a config.
    is_web_search_active = (web_search_config is not None)
    
    # 🔴 CLEARED: We no longer check for model overrides here.
    # The active mode (Alpha/Omega) will handle the tools.

    log_event("context_resolution", {
        "user_id": user_id,
        "input_url": page,
        "derived_exam": exam_context, 
        "web_search_active": is_web_search_active,
        "trigger_message": message[:50] if message else "None"
    })

    # Step 2: Find-or-create conversation
    actual_conversation_id = conversation_id
    should_create_new = True

    if conversation_id and user_id:
        exists_timestamp = _find_conversation_timestamp(user_id, conversation_id)
        if exists_timestamp:
            should_create_new = False
        else:
            actual_conversation_id = None 

    try:
        if should_create_new:
            sanitized_email = _normalize_email_for_storage(email)
            conversation_data = save_conversation(
                user_id=user_id, name=name or "", email=sanitized_email,
                title=(message or "[Sin texto]")[:40], page=page,
            )
            actual_conversation_id = conversation_data["ConversationId"]
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save/reuse conversation: {e}")

    # Step 3: Build Input
    conversation_input = _build_history_list(actual_conversation_id)
    
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
    generated_assets = [] 
    sources_data = [] 
    
    if intent == "quiz":
        topic_hint = message if message else "General Knowledge"
        num_questions = 5
        if message:
            match = re.search(r'\b(\d+)\b', message)
            if match:
                parsed_num = int(match.group(1))
                if 1 <= parsed_num <= 10: 
                    num_questions = parsed_num

        conversation_input.append(QuizService.get_system_instruction(topic=topic_hint, num_questions=num_questions))

        try:
            if stream_manager:
                stream_gen = stream_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id,
                    page=page,
                    name=(name or None),
                    email=_normalize_email_for_storage(email),
                    mode=mode,
                    exam_context=exam_context 
                )
                
                seen_indices = set()
                accumulated_questions = []
                final_reply_text = "Aquí tienes tu simulacro."
                ai_generated_title = "Simulacro Generado" 

                for event in stream_gen:
                    evt_type = event.get("type")
                    if evt_type == "intro":
                        final_reply_text = event.get("text", "")
                    elif evt_type == "question":
                        q_data = event.get("data")
                        q_dict = q_data.dict()
                        idx = event.get("index", 0)
                        stream_manager.send_quiz_item(question_data=q_dict, index=idx)
                        if idx not in seen_indices:
                            accumulated_questions.append(q_dict)
                            seen_indices.add(idx)
                    elif evt_type == "done":
                        final_obj = event.get("full_response")
                        parsed_response = None
                        if hasattr(final_obj, 'questions'): parsed_response = final_obj
                        elif hasattr(final_obj, 'parsed') and hasattr(final_obj.parsed, 'questions'): parsed_response = final_obj.parsed
                        elif hasattr(final_obj, 'output_parsed') and hasattr(final_obj.output_parsed, 'questions'): parsed_response = final_obj.output_parsed
                        
                        if parsed_response:
                            final_reply_text = parsed_response.intro_message
                            accumulated_questions = [q.dict() for q in parsed_response.questions]
                            if hasattr(parsed_response, 'title') and parsed_response.title:
                                ai_generated_title = parsed_response.title

                    elif evt_type == "error":
                        error_msg = event.get("error", "Unknown stream error")
                        stream_manager.send_error(error_msg)

                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": ai_generated_title,
                    "questions": accumulated_questions
                }

            else:
                # Batch Mode
                quiz_model = generate_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id,
                    page=page,
                    name=(name or None),
                    email=_normalize_email_for_storage(email),
                    mode=mode,
                    exam_context=exam_context 
                )
                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": quiz_model.title,
                    "questions": [q.dict() for q in quiz_model.questions]
                }
                final_reply_text = quiz_model.intro_message

        except Exception as e:
            logger.error(f"Quiz Generation Error: {e}")
            log_event("quiz_generation_failed", {"error": str(e)}, level="error")
            final_reply_text = "**Error**: No pudimos generar el simulacro."
            quiz_data = None

    else:
        # 🟢 STANDARD CHAT MODE
        try:
            runtime_signals = build_runtime_context(
                page=page,
                user_id=user_id,
                name=name,
                email=email,
                requires_visuals=requires_visuals 
            )

            system_prompt = build_system_instructions(
                extras=runtime_signals,
                exam_context=exam_context,
                requires_visuals=requires_visuals,
                web_search_active=is_web_search_active 
            )

            # 🟢 UPDATED: Removed 'model_override' parameter
            response_tuple = send_message_to_assistant(
                conversation_input=conversation_input,
                user_id=user_id,
                page=page,
                name=(name or None),
                email=_normalize_email_for_storage(email),
                mode=mode,
                system_instruction=system_prompt,
                vector_store_ids=selected_vector_stores,
                requires_visuals=requires_visuals,
                web_search_config=web_search_config
            )
            
            final_reply_text = response_tuple[0]
            generated_assets = response_tuple[1]
            sources_data = response_tuple[2] if len(response_tuple) > 2 else []

        except Exception as e:
            raise RuntimeError(f"OpenAI Chat API failed: {e}")

    # Step 7: Persist
    assistant_timestamp = ""
    try:
        if message:
            save_message(actual_conversation_id, role="user", message_text=message)
        for img in image_urls or []:
            save_message(actual_conversation_id, role="user", message_text=f"[Imagen] {img}")
        
        meta_payload = quiz_data
        
        if not meta_payload:
            meta_payload = {}
            
        if generated_assets:
            meta_payload["type"] = "rich_chat"
            meta_payload["assets"] = [{"type": "image", "url": url, "alt": "Generated Visualization"} for url in generated_assets]
            
        if sources_data:
            meta_payload["sources"] = sources_data

        if not meta_payload: meta_payload = None

        saved_item = save_message(
            actual_conversation_id, 
            role="assistant", 
            message_text=final_reply_text,
            metadata=meta_payload
        )
        if saved_item and isinstance(saved_item, dict):
            assistant_timestamp = saved_item.get("Timestamp", "")

    except Exception as e:
        raise RuntimeError(f" Failed to save messages: {e}")

    return final_reply_text, actual_conversation_id, assistant_timestamp, meta_payload