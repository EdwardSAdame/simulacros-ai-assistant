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
        self.WS_CONNECTIONS_TABLE_NAME: str = os.getenv("WS_CONNECTIONS_TABLE_NAME", "WsConnectionsTable")
        self.MESSAGES_TABLE_NAME: str = os.getenv("MESSAGES_TABLE_NAME", "Messages")
        self.CONVERSATIONS_TABLE_NAME: str = os.getenv("CONVERSATIONS_TABLE_NAME", "Conversations")
        self.FEEDBACK_TABLE_NAME: str = os.getenv("FEEDBACK_TABLE_NAME", "Feedback")
        
        # Audio WebSocket Table
        self.WS_AUDIO_TABLE_NAME: str = os.getenv("WS_AUDIO_TABLE_NAME", "WsAudio")

        # --- OpenAI Models ---
        # Audio Model
        self.OPENAI_AUDIO_MODEL: str = os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-transcribe")
        
        # 🔹 Router Model Configuration 🔹
        self.OPENAI_ROUTER_MODEL: str = os.getenv("OPENAI_ROUTER_MODEL", "gpt-4o-mini")
        
        # 💡 FIX: ADD MISSING ROUTER SAMPLING PARAMETERS 💡
        try:
            # OPENAI_ROUTER_TEMP (Default 0.3 for low creativity/high reliability)
            temp_str = os.getenv("OPENAI_ROUTER_TEMP")
            self.OPENAI_ROUTER_TEMP: float = float(temp_str) if temp_str is not None else 0.3
        except ValueError:
            logger.warning("OPENAI_ROUTER_TEMP in .env is not a valid float. Defaulting to 0.3.")
            self.OPENAI_ROUTER_TEMP: float = 0.3

        try:
            # OPENAI_ROUTER_TOP_P (Default 1.0 for broad sampling)
            top_p_str = os.getenv("OPENAI_ROUTER_TOP_P")
            self.OPENAI_ROUTER_TOP_P: float = float(top_p_str) if top_p_str is not None else 1.0
        except ValueError:
            logger.warning("OPENAI_ROUTER_TOP_P in .env is not a valid float. Defaulting to 1.0.")
            self.OPENAI_ROUTER_TOP_P: float = 1.0


    def get_openai_client(self) -> openai.Client:
        # ... (content remains unchanged)
        if not self.OPENAI_API_KEY:
            raise ValueError("Cannot create OpenAI client: OPENAI_API_KEY is not set.")
        
        return openai.Client(api_key=self.OPENAI_API_KEY)

    def get_vector_search_max_results(self) -> int:
        # ... (content remains unchanged)
        return self.VECTOR_SEARCH_MAX_RESULTS

# Create a single, importable instance for the rest of the app.
settings = Settings()


# --- Legacy Function Support ---
def get_openai_client() -> openai.Client:
    # ... (content remains unchanged)
    return settings.get_openai_client()

def get_vector_search_max_results() -> int:
    # ... (content remains unchanged)
    return settings.get_vector_search_max_results()