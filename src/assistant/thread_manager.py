import openai
from src.config.settings import get_openai_client

def get_or_create_thread(user_id=None, existing_thread_id=None):
    """
    Returns an existing thread_id if provided, otherwise creates a new one.
    """
    if existing_thread_id:
        return existing_thread_id

    client = get_openai_client()
    thread = client.beta.threads.create()
    return thread.id
