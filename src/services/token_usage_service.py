# src/services/token_usage_service.py
from datetime import datetime, timezone
from typing import Optional
from src.storage.token_usage_table import TokenUsageTable
from src.utils.logging_utils import log_event

class TokenUsageService:
    def __init__(self):
        self.storage = TokenUsageTable()

    def log_token_usage(
        self,
        user_id: str,
        session_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        reasoning_tokens: Optional[int] = 0,
        cached_tokens: Optional[int] = 0
    ) -> bool:
        """
        Validates and processes token usage data before persisting it to the database.
        """
        if not user_id or not model:
            log_event(
                event_type="token_logging_missing_fields", 
                details={"user_id": user_id, "model": model}, 
                level="warning"
            )
            return False

        timestamp = datetime.now(timezone.utc).isoformat()

        prompt_tokens = max(0, prompt_tokens)
        completion_tokens = max(0, completion_tokens)
        total_tokens = max(0, total_tokens)
        reasoning_tokens = max(0, reasoning_tokens or 0)
        cached_tokens = max(0, cached_tokens or 0)

        log_event(
            event_type="processing_token_usage", 
            details={"user_id": user_id, "model": model, "total_tokens": total_tokens}
        )

        return self.storage.record_usage(
            user_id=user_id,
            timestamp=timestamp,
            session_id=session_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            reasoning_tokens=reasoning_tokens,
            cached_tokens=cached_tokens
        )

    def get_user_usage_history(self, user_id: str) -> list:
        """
        Retrieves the raw token usage history for a specific user.
        """
        if not user_id:
            log_event(
                event_type="token_history_missing_user", 
                details={}, 
                level="warning"
            )
            return []
            
        return self.storage.get_user_usage(user_id)