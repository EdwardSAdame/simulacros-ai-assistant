# src/services/chat_service.py
from src.assistant.assistant_client import send_message_to_assistant
from src.assistant.image_handler import format_image_urls_for_openai
from src.storage.conversations_table import save_conversation
from src.storage.messages_table import save_message, get_recent_messages
from src.config.page_vectorstores import get_stores_for_page
from src.utils.logging_utils import log_event
from src.services.quiz_service import QuizService
from typing import List, Dict, Any, Tuple
from decimal import Decimal
import json
import re

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
    intent: str = "chat"
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

    # Step 3: Add current message
    current_user_content = []
    if message:
        current_user_content.append({"type": "input_text", "text": message})
    current_user_content.extend(format_image_urls_for_openai(image_urls or []))

    if current_user_content:
        conversation_input.append({"role": "user", "content": current_user_content})

    # 4. Inject Quiz Instructions (Using High Token Count from Omega Profile)
    if intent == "quiz":
        topic_hint = message if message else "General Knowledge"
        num_questions = 5 # Safe now with Omega's high token limit
        conversation_input.append(QuizService.get_system_instruction(topic=topic_hint, num_questions=num_questions))

    # Step 5: Send to model (Passing Mode)
    try:
        assistant_reply = send_message_to_assistant(
            conversation_input=conversation_input,
            user_id=user_id,
            page=page,
            name=(name or None),
            email=_normalize_email_for_storage(email),
            mode=mode # 🟢 Pass the mode to select the profile
        )
    except Exception as e:
        raise RuntimeError(f"❌ OpenAI Responses API failed: {e}")

    if not assistant_reply or "No assistant response" in assistant_reply:
        raise ValueError("❌ Assistant returned an empty or invalid response.")

    # 6. Extract & Clean Quiz Data
    quiz_data = None
    final_reply_text = assistant_reply

    if intent == "quiz":
        extracted_data = QuizService.extract_quiz_data(assistant_reply)
        if extracted_data:
            quiz_data = extracted_data
            cleaned = QuizService.clean_response_text(assistant_reply)
            final_reply_text = cleaned if cleaned else "Aquí tienes el simulacro."
        else:
            log_event("quiz_extraction_failed", {"preview": assistant_reply[:50]}, level="error")
            final_reply_text = (
                "⚠️ **Error de Generación**: El simulacro no se pudo procesar correctamente (respuesta incompleta). "
                "Intenta usar el modo 'Omega' o pedir menos preguntas."
            )
            quiz_data = None

    # Step 7: Persist
    try:
        if message:
            save_message(conversation_id, role="user", message_text=message)
        for img in image_urls or []:
            save_message(conversation_id, role="user", message_text=f"[Imagen] {img}")
        
        assistant_message_item = save_message(
            conversation_id, 
            role="assistant", 
            message_text=final_reply_text,
            metadata=quiz_data 
        )
        assistant_timestamp = assistant_message_item.get("Timestamp")
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save messages: {e}")

    return final_reply_text, conversation_id, assistant_timestamp, quiz_data