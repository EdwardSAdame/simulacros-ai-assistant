import openai
import os
from src.config.settings import get_openai_client

def send_message_to_assistant(message, thread_id, file_ids=None, user_id=None, page=None):
    """
    Sends user message (and optional files) to the OpenAI Assistant API
    and returns the assistant's reply.
    """

    client = get_openai_client()
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

    # Step 1: Prepare the message content
    content_parts = []

    # Add message text
    if message:
        content_parts.append({ "type": "text", "text": message })

    # Add file references if provided
    if file_ids:
        for fid in file_ids:
            content_parts.append({ "type": "file_id", "file_id": fid })

    # Step 2: Send message to thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=content_parts
    )

    # Step 3: Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        additional_instructions=build_context_instructions(user_id, page)
    )

    # Step 4: Poll for completion
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status in ["completed", "failed", "cancelled"]:
            break

    if run_status.status != "completed":
        raise Exception(f"Run failed with status: {run_status.status}")

    # Step 5: Retrieve last assistant message
    messages = client.beta.threads.messages.list(thread_id=thread_id, order="desc")
    for msg in messages.data:
        if msg.role == "assistant":
            return msg.content[0].text.value

    return "[No assistant response found]"

def build_context_instructions(user_id, page):
    """
    Optionally injects dynamic instructions to the assistant.
    Useful for context like user info or page source.
    """
    if not user_id:
        return f"You are speaking with a guest. They are currently on the page: {page}."

    return f"You are speaking with user ID {user_id}. They are on the page: {page}."
