# src/services/chat_service.py
from src.assistant.assistant_client import send_message_to_assistant
from src.assistant.image_handler import format_image_urls_for_openai
from src.storage.conversations_table import save_conversation
from src.storage.messages_table import save_message, get_recent_messages
from src.config.page_vectorstores import get_stores_for_page
from src.utils.logging_utils import log_event
from src.services.quiz_service import QuizService  # <--- NEW IMPORT
from typing import List, Dict, Any, Tuple

# ... [Keep helper functions: _normalize_email_for_storage, _normalize_page, _build_history_list UNCHANGED] ...
# (I am omitting them here to save space, but ensure they remain in the file)

def _normalize_email_for_storage(val):
    if val is None: return None
    if isinstance(val, str) and val.strip() == "": return None
    return val

def _normalize_page(val: str | None) -> str:
    if not val or (isinstance(val, str) and val.strip() == ""):
        return "/"
    return val

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
            content = [{"type": "input_text" if role == "user" else "output_text", "text": m.get("MessageText", "")}]
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
) -> Tuple[str, str, str, Dict | None]: # <--- RETURNS 4 VALUES NOW
    """
    Returns: (assistant_reply_text, conversation_id, assistant_timestamp, quiz_data_json)
    """
    page = _normalize_page(page)

    # Step 1: Find-or-create conversation
    try:
        if not conversation_id:
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

    # 🔹 SRP: Delegate prompt injection to QuizService
    if intent == "quiz":
        conversation_input.append(QuizService.get_system_instruction())

    # Step 4: Send to model
    try:
        raw_response = send_message_to_assistant(
            conversation_input=conversation_input,
            user_id=user_id,
            page=page,
            name=(name or None),
            email=_normalize_email_for_storage(email),
            mode=mode 
        )
    except Exception as e:
        raise RuntimeError(f"❌ OpenAI Responses API failed: {e}")

    if not raw_response or "No assistant response" in raw_response:
        raise ValueError("❌ Assistant returned an empty or invalid response.")

    # 🔹 SRP: Delegate parsing to QuizService
    final_reply_text = raw_response
    quiz_data = None

    if intent == "quiz":
        extracted_data = QuizService.extract_quiz_data(raw_response)
        if extracted_data:
            quiz_data = extracted_data
            # Use the cleaner text intended for the chat bubble
            final_reply_text = extracted_data.get("reply_text", "Here is your question.")
        else:
            log_event("quiz_extraction_failed", {"raw": raw_response}, level="error")
            # Fallback: text is just raw response

    # Step 5: Persist (Save only the TEXT to DB, the JSON goes to frontend ephemeral)
    try:
        if message:
            save_message(conversation_id, role="user", message_text=message)
        for img in image_urls or []:
            save_message(conversation_id, role="user", message_text=f"[Imagen] {img}")
        
        assistant_message_item = save_message(
            conversation_id, 
            role="assistant", 
            message_text=final_reply_text
        )
        assistant_timestamp = assistant_message_item.get("Timestamp")
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save messages to DynamoDB: {e}")

    return final_reply_text, conversation_id, assistant_timestamp, quiz_data