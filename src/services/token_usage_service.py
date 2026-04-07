# src/services/token_usage_service.py
import uuid
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
        conversation_id: str,
        source: str,          
        tier: str,       # 🟢 FIX: Renamed 'model' to 'tier' (e.g., 'omega', 'alpha')
        engine: str,     # 🟢 NEW: Added 'engine' for the exact LLM (e.g., 'gpt-4o')
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        reasoning_tokens: Optional[int] = 0,
        cached_tokens: Optional[int] = 0
    ) -> bool:
        """
        Validates and processes token usage data before persisting it to the database
        using the normalized FinOps schema.
        """
        if not user_id or not tier or not engine:
            log_event(
                event_type="token_logging_missing_fields", 
                details={"user_id": user_id, "tier": tier, "engine": engine}, 
                level="warning"
            )
            return False

        timestamp = datetime.now(timezone.utc).isoformat()
        usage_id = str(uuid.uuid4())

        input_tokens = max(0, input_tokens)
        output_tokens = max(0, output_tokens)
        total_tokens = max(0, total_tokens)
        reasoning_tokens = max(0, reasoning_tokens or 0)
        cached_tokens = max(0, cached_tokens or 0)

        # 🟢 FIX: Map Tier and Engine exactly like ImageUsage
        metadata = {
            "Source": source,
            "Tier": tier,
            "Engine": engine,
            "InputTokens": input_tokens,
            "OutputTokens": output_tokens,
            "ReasoningTokens": reasoning_tokens,
            "CachedTokens": cached_tokens
        }

        return self.storage.record_usage(
            usage_id=usage_id,
            user_id=user_id,
            timestamp=timestamp,
            conversation_id=conversation_id,
            total_tokens=total_tokens,
            metadata=metadata
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