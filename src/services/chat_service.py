from src.assistant.assistant_client import send_message_to_assistant
from src.assistant.thread_manager import get_or_create_thread
from src.assistant.audio_transcriber import transcribe_audio_url
from src.assistant.image_handler import format_image_urls_for_openai
from src.storage.conversations_table import save_conversation
from src.storage.messages_table import save_message

def get_ai_response(message, user_id, name, email, page, thread_id=None, image_urls=None, audio_url=None):
    """
    Handles user input (text, images, or audio) and returns AI response.
    """

    # Step 1: Ensure we have a valid thread
    thread_id = get_or_create_thread(user_id, thread_id)

    # Step 2: Save conversation metadata
    conversation_data = save_conversation(
        user_id=user_id,
        name=name,
        email=email,
        title=(message or "[Sin texto]")[:40],
        page=page,
        thread_id=thread_id
    )
    conversation_id = conversation_data["ConversationId"]

    # Step 3: Transcribe audio if provided
    audio_text = None
    if audio_url:
        try:
            audio_text = transcribe_audio_url(audio_url)
        except Exception as e:
            audio_text = "[Error al transcribir el audio]"

    # Step 4: Format image blocks
    image_blocks = format_image_urls_for_openai(image_urls or [])

    # Step 5: Build content_parts
    content_parts = []
    if message:
        content_parts.append({ "type": "text", "text": message })

    if audio_text:
        content_parts.append({ "type": "text", "text": f"Transcripción del audio: {audio_text}" })

    content_parts += image_blocks

    # Step 6: Send to assistant
    assistant_reply = send_message_to_assistant(
        content_parts=content_parts,
        thread_id=thread_id,
        user_id=user_id,
        page=page
    )

    # Step 7: Log messages
    if message:
        save_message(conversation_id, role="user", message_text=message)
    if audio_text:
        save_message(conversation_id, role="user", message_text=f"[Audio transcrito] {audio_text}")
    for img in image_urls or []:
        save_message(conversation_id, role="user", message_text=f"[Imagen]: {img}")

    save_message(conversation_id, role="assistant", message_text=assistant_reply)

    return assistant_reply, thread_id, conversation_id
