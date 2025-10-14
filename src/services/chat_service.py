# src/services/chat_service.py
from src.assistant.assistant_client import send_message_to_assistant
from src.assistant.image_handler import format_image_urls_for_openai
from src.storage.conversations_table import save_conversation
from src.storage.messages_table import save_message, get_recent_messages
from src.config.page_vectorstores import get_stores_for_page
from src.utils.logging_utils import log_event
from typing import List, Dict, Any

def _normalize_email_for_storage(val):
    """Return None for empty strings/whitespace so DynamoDB never gets an empty Email."""
    if val is None:
        return None
    if isinstance(val, str) and val.strip() == "":
        return None
    return val


def _normalize_page(val: str | None) -> str:
    """Default to '/' if empty; pass full URL or path through (assistant_client resolves)."""
    if not val or (isinstance(val, str) and val.strip() == ""):
        return "/"
    return val


def _build_history_list(conversation_id: str, max_user: int = 3, max_assistant: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch recent messages and return them as a structured list for the API.
    """
    try:
        msgs = get_recent_messages(conversation_id=conversation_id, limit=20, ascending=True)
        if not msgs:
            return []

        user_msgs = [m for m in msgs if m.get("Role") == "user"][-max_user:]
        asst_msgs = [m for m in msgs if m.get("Role") == "assistant"][-max_assistant:]

        merged = sorted(user_msgs + asst_msgs, key=lambda m: m["Timestamp"])

        history_list = []
        for m in merged:
            role = m.get("Role", "user")
            # Format to match the structure expected by the OpenAI Responses API
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
):
    """
    Handles user input (text + images) and returns AI response using the Responses API.
    """
    page = _normalize_page(page)

    # Step 1: Find-or-create conversation
    try:
        if conversation_id:
            log_event("conversation_reused", {
                "conversation_id": conversation_id, "user_id": user_id, "page": page,
                "vector_stores": get_stores_for_page(page),
            })
        else:
            sanitized_email = _normalize_email_for_storage(email)
            conversation_data = save_conversation(
                user_id=user_id, name=name or "", email=sanitized_email,
                title=(message or "[Sin texto]")[:40], page=page,
            )
            conversation_id = conversation_data["ConversationId"]
            log_event("conversation_created", {
                "conversation_id": conversation_id, "user_id": user_id, "page": page,
                "vector_stores": get_stores_for_page(page),
            })
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save/reuse conversation: {e}")

    # Step 2: Build the full conversation input for the API
    # This now starts with the structured history list
    conversation_input = _build_history_list(conversation_id)

    # Step 3: Add the current user message and images as a new, separate turn
    current_user_content = []
    if message:
        current_user_content.append({"type": "input_text", "text": message})
    
    image_blocks = format_image_urls_for_openai(image_urls or [])
    current_user_content.extend(image_blocks)

    if current_user_content:
        conversation_input.append({"role": "user", "content": current_user_content})

    # Step 4: Send to model
    try:
        log_event("openai_request_sent", {
            "user_id": user_id, "page": page,
            "conversation_length": len(conversation_input),
            "vector_stores": get_stores_for_page(page),
        })
        assistant_reply = send_message_to_assistant(
            conversation_input=conversation_input,
            user_id=user_id,
            page=page,
            name=(name or None),
            email=_normalize_email_for_storage(email),
        )
    except Exception as e:
        raise RuntimeError(f"❌ OpenAI Responses API failed: {e}")

    if not assistant_reply or "No assistant response" in assistant_reply:
        raise ValueError("❌ Assistant returned an empty or invalid response.")

    log_event("openai_response_received", {
        "conversation_id": conversation_id, "reply_snippet": assistant_reply[:100],
    })

    # Step 5: Persist messages
    try:
        if message:
            save_message(conversation_id, role="user", message_text=message)
        for img in image_urls or []:
            save_message(conversation_id, role="user", message_text=f"[Imagen] {img}")
        save_message(conversation_id, role="assistant", message_text=assistant_reply)
        log_event("messages_saved", {"conversation_id": conversation_id, "user_id": user_id})
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save messages to DynamoDB: {e}")

    return assistant_reply, conversation_id