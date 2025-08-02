import openai
import os
from src.config.settings import get_openai_client
from src.utils.time_utils import get_current_time_info


def send_message_to_assistant(content_parts, thread_id, user_id=None, page=None):
    """
    Sends structured content (text, audio transcript, image blocks) to the OpenAI Assistant API
    and returns the assistant's reply.
    """

    client = get_openai_client()
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

    # Step 1: Send user message to thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=content_parts
    )

    # Step 2: Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        additional_instructions=build_context_instructions(user_id, page)
    )

    # Step 3: Poll for completion
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status in ["completed", "failed", "cancelled"]:
            break

    if run_status.status != "completed":
        raise Exception(f"Run failed with status: {run_status.status}")

    # Step 4: Retrieve the last assistant message
    messages = client.beta.threads.messages.list(thread_id=thread_id, order="desc")
    for msg in messages.data:
        if msg.role == "assistant":
            return msg.content[0].text.value

    return "[No assistant response found]"

def build_context_instructions(user_id, page):
    """
    Dynamically generates context-aware instructions for the assistant.
    Includes page, user ID (if any), and current date/time info.
    """
    time_info = get_current_time_info()

    base_instruction = (
        f"Today is {time_info['full_human']}.\n"
        f"The user is on the page: {page}.\n"
    )

    if not user_id:
        return base_instruction + "They are browsing as a guest."

    return base_instruction + f"Their user ID is {user_id}."
