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
