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
    Minimal, strict: always ground answers in the current page's vector-store content.
    Assumes `page` is the FULL URL coming from the frontend (getFullUrl()).
    """
    time_info = get_current_time_info()
    page_url = page or "/"

    lines = [
        f"Today is {time_info['full_human']}.",
        # Core requirement: ALWAYS ground in the current page
        f"The user is currently on this page URL: {page_url}",
        "Always use only the authoritative Invicto vector-store content associated with THIS exact page.",
        "Ignore any retrieved content that belongs to other pages, even if it looks relevant.",
        "Do not ask the user where they are — you already have the page URL.",
        # UX rule we’re keeping
        "If the user asks about a specific question, provide only the explanation; "
        "do not re-render the full question unless the user explicitly asks.",
    ]

    # Identity (unchanged)
    if not user_id or user_id == 'anonymous':
        lines.append("They are browsing as a guest.")
    else:
        lines.append(f"Their user ID is {user_id}.")

    if name:
        lines.append(f"The user's display name is {name}.")
    if email:
        lines.append(f"The user's email is {email}.")

    return "\n".join(lines)
