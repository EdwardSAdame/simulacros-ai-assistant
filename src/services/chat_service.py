from src.assistant.assistant_client import send_message_to_assistant
from src.assistant.thread_manager import get_or_create_thread
from src.storage.conversations_table import save_conversation
from src.storage.messages_table import save_message  # This must exist

def get_ai_response(message, file_url, user_id, name, email, page, thread_id=None):
    """
    Minimal version: handles message and assistant reply only.
    """

    # Step 1: Ensure we have a valid thread_id
    thread_id = get_or_create_thread(user_id, thread_id)

    # Step 2: Save conversation metadata
    conversation_data = save_conversation(
        user_id=user_id,
        name=name,
        email=email,
        title=message[:40],
        page=page,
        thread_id=thread_id
    )

    # Step 3: Send message to OpenAI Assistant
    assistant_reply = send_message_to_assistant(
        message=message,
        thread_id=thread_id,
        file_ids=[],  # empty for now
        user_id=user_id,
        page=page
    )

    # Step 4: Log both messages
    conversation_id = conversation_data["ConversationId"]
    save_message(conversation_id, role="user", message_text=message)
    save_message(conversation_id, role="assistant", message_text=assistant_reply)

    return assistant_reply, thread_id, conversation_id
