# src/config/settings.py
import os
from dotenv import load_dotenv
import openai
import logging

# Load .env file once
load_dotenv()

logger = logging.getLogger(__name__)

class Settings:
    """
    Central configuration class that reads from environment variables.
    """
    def __init__(self):
        # OpenAI
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
        if not self.OPENAI_API_KEY:
            # Use warning instead of error to allow app to load
            logger.warning("OPENAI_API_KEY not found in environment variables. OpenAI client will fail.")

        # Vector Search
        try:
            self.VECTOR_SEARCH_MAX_RESULTS: int = int(os.getenv("VECTOR_SEARCH_MAX_RESULTS", "8"))
        except ValueError:
            self.VECTOR_SEARCH_MAX_RESULTS: int = 8

        # --- DynamoDB Table Names ---
        # These are read by your existing storage files
        self.WS_CONNECTIONS_TABLE_NAME: str = os.getenv("WS_CONNECTIONS_TABLE_NAME", "WsConnectionsTable")
        self.MESSAGES_TABLE_NAME: str = os.getenv("MESSAGES_TABLE_NAME", "Messages")
        self.CONVERSATIONS_TABLE_NAME: str = os.getenv("CONVERSATIONS_TABLE_NAME", "Conversations")
        self.FEEDBACK_TABLE_NAME: str = os.getenv("FEEDBACK_TABLE_NAME", "Feedback")
        
        # Audio WebSocket Table
        self.WS_AUDIO_TABLE_NAME: str = os.getenv("WS_AUDIO_TABLE_NAME", "WsAudio")

        # --- OpenAI Models ---
        # Audio Model
        self.OPENAI_AUDIO_MODEL: str = os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-transcribe")
        
        # 🔹 NEW: Router Model Configuration 🔹
        # Defines which fast model to use for the semantic router (classification).
        # Defaults to "gpt-4o-mini" if not set in env.
        self.OPENAI_ROUTER_MODEL: str = os.getenv("OPENAI_ROUTER_MODEL", "gpt-4o-mini")

    def get_openai_client(self) -> openai.Client:
        """
        Returns an authenticated OpenAI client instance.
        """
        if not self.OPENAI_API_KEY:
            raise ValueError("Cannot create OpenAI client: OPENAI_API_KEY is not set.")
        
        return openai.Client(api_key=self.OPENAI_API_KEY)

    def get_vector_search_max_results(self) -> int:
        """
        Returns the maximum number of file_search results to retrieve.
        """
        return self.VECTOR_SEARCH_MAX_RESULTS

# Create a single, importable instance for the rest of the app.
settings = Settings()


# --- Legacy Function Support ---
def get_openai_client() -> openai.Client:
    """
    Legacy support: Returns an authenticated OpenAI client instance.
    """
    return settings.get_openai_client()

def get_vector_search_max_results() -> int:
    """
    Legacy support: Returns the maximum number of file_search results.
    """
    return settings.get_vector_search_max_results()