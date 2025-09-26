# src/services/chat_service.py
from src.assistant.assistant_client import send_message_to_assistant
from src.assistant.image_handler import format_image_urls_for_openai
from src.storage.conversations_table import save_conversation
from src.storage.messages_table import save_message, get_recent_messages
from src.config.page_vectorstores import get_stores_for_page  # ✅ visibility/debug
from src.utils.logging_utils import log_event  # ✅ structured logger


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


def _build_history_block(conversation_id: str, max_turns: int = 8, max_chars_per_msg: int = 600) -> str | None:
    """
    Fetch last N messages and return a compact Spanish transcript.
    Oldest→newest order to preserve coherence. Truncates long messages.
    """
    try:
        msgs = get_recent_messages(conversation_id=conversation_id, limit=max_turns * 2, ascending=True)
        if not msgs:
            return None

        lines = ["[HISTORIAL RECIENTE]"]
        for m in msgs:
            role = m.get("Role", "user")
            text = m.get("MessageText", "")
            if max_chars_per_msg and len(text) > max_chars_per_msg:
                text = text[:max_chars_per_msg] + "…"
            speaker = "Usuario" if role == "user" else "Roma"
            lines.append(f"{speaker}: {text}")
        return "\n".join(lines)
    except Exception as e:
        # Don't fail the request if history fetch fails; just skip history
        log_event("history_fetch_failed", {"conversation_id": conversation_id}, level="warning", error=e)
        return None


def get_ai_response(
    message: str | None,
    user_id: str | None,
    name: str | None,
    email: str | None,
    page: str | None,
    conversation_id: str | None = None,   # ✅ reuse if provided
    image_urls: list[str] | None = None,
):
    """
    Handles user input (text + images) and returns AI response using the Responses API.
    No threads/runs are used. Raises exceptions for DLQ-friendly retries.
    Returns: (assistant_reply: str, conversation_id: str)
    """
    page = _normalize_page(page)

    # Step 1: Find-or-create conversation (REUSE if conversation_id provided)
    try:
        if conversation_id:
            log_event("conversation_reused", {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "page": page,
                "vector_stores": get_stores_for_page(page),  # ✅ visibility
            })
        else:
            sanitized_email = _normalize_email_for_storage(email)
            conversation_data = save_conversation(
                user_id=user_id,
                name=name or "",
                email=sanitized_email,
                title=(message or "[Sin texto]")[:40],
                page=page,
            )
            conversation_id = conversation_data["ConversationId"]
            log_event("conversation_created", {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "page": page,
                "vector_stores": get_stores_for_page(page),  # ✅ visibility
            })
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save/reuse conversation: {e}")

    # Step 2: Format image blocks
    try:
        image_blocks = format_image_urls_for_openai(image_urls or [])
        log_event("image_blocks_formatted", {
            "image_count": len(image_blocks),
            "user_id": user_id
        })
    except Exception as e:
        raise RuntimeError(f"❌ Failed to format image URLs: {e}")

    # Step 3: Build content_parts (include recent history as first block)
    content_parts = []

    history_block = _build_history_block(conversation_id, max_turns=8, max_chars_per_msg=600)
    if history_block:
        content_parts.append({"type": "text", "text": history_block})

    if message:
        content_parts.append({"type": "text", "text": message})

    content_parts += image_blocks

    # Step 4: Send to model
    try:
        log_event("openai_request_sent", {
            "user_id": user_id,
            "page": page,
            "content_parts_count": len(content_parts),
            "vector_stores": get_stores_for_page(page),  # ✅ visibility
        })
        assistant_reply = send_message_to_assistant(
            content_parts=content_parts,
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
        "conversation_id": conversation_id,
        "reply_snippet": assistant_reply[:100],
    })

    # Step 5: Persist messages
    try:
        if message:
            save_message(conversation_id, role="user", message_text=message)
        for img in image_urls or []:
            save_message(conversation_id, role="user", message_text=f"[Imagen] {img}")
        save_message(conversation_id, role="assistant", message_text=assistant_reply)

        log_event("messages_saved", {
            "conversation_id": conversation_id,
            "user_id": user_id,
        })
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save messages to DynamoDB: {e}")

    return assistant_reply, conversation_id
