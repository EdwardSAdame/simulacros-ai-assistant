import logging
from src.storage.audio_usage_table import AudioUsageTable

logger = logging.getLogger(__name__)

class AudioUsageService:
    def __init__(self):
        self.table = AudioUsageTable()

    def log_audio_usage(self, user_id: str, conversation_id: str, source: str, tier: str, engine: str, duration_seconds: int, audio_type: str = "speech-to-text"):
        if duration_seconds <= 0:
            logger.warning("Attempted to log 0 or negative audio duration. Skipping.")
            return False
            
        success = self.table.log_audio_usage(
            user_id=user_id,
            conversation_id=conversation_id,
            source=source,
            tier=tier,
            engine=engine,
            duration_seconds=duration_seconds,
            audio_type=audio_type
        )
        
        if success:
            logger.info(f"Logged {duration_seconds}s of {audio_type} audio usage for user {user_id} on {engine} ({tier})")
        return success