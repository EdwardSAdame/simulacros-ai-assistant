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
        self.WS_AUDIO_TABLE_NAME: str = os.getenv("WS_AUDIO_TABLE_NAME", "WsAudio")

        # AWS S3 Configuration
        self.S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "invicto-quiz-assets")
        self.AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
        self.S3_CUSTOM_DOMAIN: str = os.getenv("S3_CUSTOM_DOMAIN", "") 

        # --- OpenAI Models ---
        self.OPENAI_AUDIO_MODEL: str = os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-transcribe")
        
        # 🟢 NEW: --- Realtime Audio (WebRTC) ---
        self.OPENAI_REALTIME_MODEL: str = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
        self.OPENAI_REALTIME_VOICE: str = os.getenv("OPENAI_REALTIME_VOICE", "alloy")
        
        # 🔹 Router Model Configuration 🔹
        self.OPENAI_ROUTER_MODEL: str = os.getenv("OPENAI_MODEL_ROUTER", "gpt-4o-mini")
        self.OPENAI_ROUTER_EFFORT: str = os.getenv("OPENAI_REASONING_EFFORT_ROUTER", "low")
        
        # Router Sampling
        try:
            temp_str = os.getenv("OPENAI_TEMP_ROUTER")
            self.OPENAI_ROUTER_TEMP: float = float(temp_str) if temp_str is not None else 0.3
        except ValueError:
            logger.warning("OPENAI_TEMP_ROUTER in .env is not a valid float. Defaulting to 0.3.")
            self.OPENAI_ROUTER_TEMP: float = 0.3

        try:
            top_p_str = os.getenv("OPENAI_TOP_P_ROUTER")
            self.OPENAI_ROUTER_TOP_P: float = float(top_p_str) if top_p_str is not None else 1.0
        except ValueError:
            logger.warning("OPENAI_TOP_P_ROUTER in .env is not a valid float. Defaulting to 1.0.")
            self.OPENAI_ROUTER_TOP_P: float = 1.0

        # 🟢 NEW: Web Search Toggle
        # Default is True (Strict) for safety. Set to "false" in AWS to open the web.
        strict_mode = os.getenv("WEB_SEARCH_STRICT_MODE", "true").lower()
        self.WEB_SEARCH_STRICT_MODE: bool = strict_mode == "true"

    def get_openai_client(self) -> openai.Client:
        if not self.OPENAI_API_KEY:
            raise ValueError("Cannot create OpenAI client: OPENAI_API_KEY is not set.")
        return openai.Client(api_key=self.OPENAI_API_KEY)

    def get_vector_search_max_results(self) -> int:
        return self.VECTOR_SEARCH_MAX_RESULTS

settings = Settings()

def get_openai_client() -> openai.Client:
    return settings.get_openai_client()

def get_vector_search_max_results() -> int:
    return settings.get_vector_search_max_results()