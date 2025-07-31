from src.assistant.assistant_client import send_message_to_assistant
from src.assistant.thread_manager import get_or_create_thread
from src.assistant.file_uploader import upload_file_if_needed
from src.storage.conversations_table import save_conversation  # ✅ Import new module

def get_ai_response(message, file_url, user_id, name, email, page, thread_id=None):
    """
    Main pipeline: handles user input and returns assistant reply.
    """

    # Step 1: Ensure we have a valid thread_id for this user
    thread_id = get_or_create_thread(user_id, thread_id)

    # Step 2: Save the conversation (first message) to DynamoDB
    conversation_data = save_conversation(
        user_id=user_id,
        name=name,
        email=email,
        title=message[:40],  # Preview/title
        page=page,
        thread_id=thread_id
    )

    # Step 3: Upload file (image/audio) if present
    file_ids = []
    if file_url:
        file_id = upload_file_if_needed(file_url)
        if file_id:
            file_ids.append(file_id)

    # Step 4: Send message and file to OpenAI Assistant
    assistant_reply = send_message_to_assistant(
        message=message,
        thread_id=thread_id,
        file_ids=file_ids,
        user_id=user_id,
        page=page
    )

    # Step 5: Return reply, thread ID, and conversation ID
    return assistant_reply, thread_id, conversation_data["ConversationId"]
