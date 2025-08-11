# src/services/chat_service.py
from src.assistant.assistant_client import send_message_to_assistant
from src.assistant.thread_manager import get_or_create_thread
from src.assistant.audio_transcriber import transcribe_audio_url
from src.assistant.image_handler import format_image_urls_for_openai
from src.storage.conversations_table import save_conversation
from src.storage.messages_table import save_message
from src.utils.logging_utils import log_event  # ✅ structured logger

def get_ai_response(
    message,
    user_id,
    name,
    email,
    page,
    thread_id=None,
    conversation_id=None,   # ✅ NEW: allow reuse
    image_urls=None,
    audio_url=None
):
    """
    Handles user input (text, images, or audio) and returns AI response.
    Raises exceptions if any key step fails, to support DLQ-based retries.
    """

    # Step 1: Ensure we have a valid thread (reuse if provided)
    try:
        thread_id = get_or_create_thread(user_id, thread_id)
        log_event("thread_ready", {"user_id": user_id, "thread_id": thread_id})
    except Exception as e:
        raise RuntimeError(f"❌ Failed to create or fetch thread: {e}")

    # Step 2: Find-or-create conversation (REUSE if conversation_id provided)
    try:
        if conversation_id:
            # Reuse existing conversation for this thread
            log_event("conversation_reused", {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "page": page,
                "thread_id": thread_id
            })
        else:
            # First turn → create a new conversation row
            conversation_data = save_conversation(
                user_id=user_id,
                name=name,
                email=email,
                title=(message or "[Sin texto]")[:40],
                page=page,
                thread_id=thread_id
            )
            conversation_id = conversation_data["ConversationId"]
            log_event("conversation_created", {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "page": page,
                "thread_id": thread_id
            })
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save/reuse conversation: {e}")

    # Step 3: Transcribe audio if provided
    audio_text = None
    if audio_url:
        try:
            audio_text = transcribe_audio_url(audio_url)
            log_event("audio_transcribed", {
                "user_id": user_id,
                "audio_snippet": (audio_text or "")[:100]
            })
        except Exception as e:
            raise RuntimeError(f"❌ Failed to transcribe audio: {e}")

    # Step 4: Format image blocks
    try:
        image_blocks = format_image_urls_for_openai(image_urls or [])
        log_event("image_blocks_formatted", {
            "image_count": len(image_blocks),
            "user_id": user_id
        })
    except Exception as e:
        raise RuntimeError(f"❌ Failed to format image URLs: {e}")

    # Step 5: Build content_parts
    content_parts = []
    if message:
        content_parts.append({"type": "text", "text": message})
    if audio_text:
        content_parts.append({"type": "text", "text": f"Transcripción del audio: {audio_text}"})
    content_parts += image_blocks

    # Step 6: Send to assistant (same thread)
    try:
        log_event("openai_request_sent", {
            "user_id": user_id,
            "page": page,
            "thread_id": thread_id,
            "content_parts_count": len(content_parts)
        })
        assistant_reply = send_message_to_assistant(
            content_parts=content_parts,
            thread_id=thread_id,
            user_id=user_id,
            page=page
        )
    except Exception as e:
        raise RuntimeError(f"❌ OpenAI Assistant failed: {e}")

    if not assistant_reply or "No assistant response" in assistant_reply:
        raise ValueError("❌ Assistant returned an empty or invalid response.")

    log_event("openai_response_received", {
        "conversation_id": conversation_id,
        "reply_snippet": assistant_reply[:100]
    })

    # Step 7: Log messages (now include thread_id in each message item)
    try:
        if message:
            save_message(conversation_id, role="user",      message_text=message,            thread_id=thread_id)
        if audio_text:
            save_message(conversation_id, role="user",      message_text=f"[Audio] {audio_text}", thread_id=thread_id)
        for img in image_urls or []:
            save_message(conversation_id, role="user",      message_text=f"[Imagen] {img}",  thread_id=thread_id)
        save_message(conversation_id,     role="assistant", message_text=assistant_reply,     thread_id=thread_id)

        log_event("messages_saved", {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "thread_id": thread_id
        })
    except Exception as e:
        raise RuntimeError(f"❌ Failed to save messages to DynamoDB: {e}")

    return assistant_reply, thread_id, conversation_id
