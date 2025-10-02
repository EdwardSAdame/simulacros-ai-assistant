# src/config/settings.py
import os
from dotenv import load_dotenv
import openai

# Load .env file once
load_dotenv()

def get_openai_client():
    """
    Returns an authenticated OpenAI client instance using the API key from .env.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    return openai.Client(api_key=api_key)


def get_vector_search_max_results() -> int:
    """
    Returns the maximum number of file_search results to retrieve.
    Defaults to 8 if not set.
    """
    try:
        return int(os.getenv("VECTOR_SEARCH_MAX_RESULTS", "8"))
    except ValueError:
        return 8
