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
        self.OPENAI_AUDIO_MODEL: str = os.getenv("OPENAI_AUDIO_MODEL")
        
        # =======================================================
        # OPENAI REALTIME: TRANSCRIPTION MODE (Speech-to-Text)
        # =======================================================
        self.OPENAI_REALTIME_TRANSCRIPTION_MODEL: str = os.getenv("OPENAI_REALTIME_TRANSCRIPTION_MODEL")
        
        # =======================================================
        # OPENAI REALTIME: TUTOR MODE (Speech-to-Speech)
        # =======================================================
        self.OPENAI_REALTIME_MODEL: str = os.getenv("OPENAI_REALTIME_MODEL")
        self.OPENAI_REALTIME_VOICE: str = os.getenv("OPENAI_REALTIME_VOICE")
        
        # Router Model Configuration 
        self.OPENAI_ROUTER_MODEL: str = os.getenv("OPENAI_MODEL_ROUTER")
        self.OPENAI_ROUTER_EFFORT: str = os.getenv("OPENAI_REASONING_EFFORT_ROUTER")
        
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

        # Web Search Toggle
        strict_mode = os.getenv("WEB_SEARCH_STRICT_MODE", "true").lower()
        self.WEB_SEARCH_STRICT_MODE: bool = strict_mode == "true"

        # Container Memory Limit Configuration
        self.CODE_INTERPRETER_MEMORY: str = os.getenv("CODE_INTERPRETER_MEMORY", "4g")

        # Global Image Generation Configuration
        self.IMAGE_GENERATION_SIZE: str = os.getenv("IMAGE_GENERATION_SIZE", "1536x1024")
        
        # Dynamic Partial Images count
        try:
            self.IMAGE_GENERATION_PARTIALS: int = int(os.getenv("IMAGE_GENERATION_PARTIALS", "3"))
        except ValueError:
            logger.warning("IMAGE_GENERATION_PARTIALS in .env is not a valid int. Defaulting to 3.")
            self.IMAGE_GENERATION_PARTIALS: int = 3

    def get_openai_client(self) -> openai.Client:
        if not self.OPENAI_API_KEY:
            raise ValueError("Cannot create OpenAI client: OPENAI_API_KEY is not set.")
        return openai.Client(api_key=self.OPENAI_API_KEY)

    def get_vector_search_max_results(self) -> int:
        return self.VECTOR_SEARCH_MAX_RESULTS
        
    def get_code_interpreter_memory(self) -> str:
        return self.CODE_INTERPRETER_MEMORY

    def get_image_generation_size(self) -> str:
        return self.IMAGE_GENERATION_SIZE

    def get_image_generation_partials(self) -> int:
        return self.IMAGE_GENERATION_PARTIALS

settings = Settings()

def get_openai_client() -> openai.Client:
    return settings.get_openai_client()

def get_vector_search_max_results() -> int:
    return settings.get_vector_search_max_results()

def get_code_interpreter_memory() -> str:
    return settings.get_code_interpreter_memory()

def get_image_generation_size() -> str:
    return settings.get_image_generation_size()

def get_image_generation_partials() -> int:
    return settings.get_image_generation_partials()