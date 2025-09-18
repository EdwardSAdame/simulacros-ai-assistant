import os
from src.config.settings import get_openai_client
from src.utils.time_utils import get_current_time_info


def send_message_to_assistant(
    content_parts,
    thread_id,
    user_id=None,
    page=None,
    name=None,
    email=None
):
    """
    Sends structured content (text, audio transcript, image blocks) to the OpenAI Assistant API
    and returns the assistant's reply.

    Context provided to the run includes: date/time, page, user_id (or guest),
    and optionally user's name and email when available.
    """
    client = get_openai_client()
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

    # 1) Send user message to thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=content_parts
    )

    # 2) Run the assistant with rich context
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        additional_instructions=build_context_instructions(
            user_id=user_id,
            page=page,
            name=name,
            email=email
        )
    )

    # 3) Poll for completion
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status in ["completed", "failed", "cancelled"]:
            break

    if run_status.status != "completed":
        raise Exception(f"Run failed with status: {run_status.status}")

    # 4) Retrieve the last assistant message
    messages = client.beta.threads.messages.list(thread_id=thread_id, order="desc")
    for msg in messages.data:
        if msg.role == "assistant":
            return msg.content[0].text.value

    return "[No assistant response found]"


def build_context_instructions(user_id=None, page=None, name=None, email=None):
    """
    Dynamically generates context-aware instructions for the assistant.
    Includes page, user identity (if any), current date/time info, and (optionally) name/email.
    """
    time_info = get_current_time_info()

    lines = [
        f"Today is {time_info['full_human']}.",
        f"The user is on the page: {page}. Respond strictly according to the context of that page."
    ]

    # Identity
    if not user_id or user_id == "anonymous":
        lines.append("They are browsing as a guest.")
    else:
        lines.append(f"Their user ID is {user_id}.")

    # Optional enrichments
    if name:
        lines.append(f"The user's display name is {name}.")
    if email:
        lines.append(f"The user's email is {email}.")

    # You can also add any guardrails or preferences here if needed.

    return "\n".join(lines)
