import logging
import time
from typing import Any, Dict
from src.config.quota_config import QuotaConfig
from src.storage.user_usage_table import UserUsageTable

logger = logging.getLogger(__name__)

# Instantiate the table access layer
user_usage_table = UserUsageTable()


class QuotaService:
    """
    Evaluates user rate limits across text, high-compute deliverables, and voice channels.
    Enforces Hard Paywalls (blocking) and Soft Paywalls (upsell metadata).
    """

    def check_voice_quota(self, user_id: str, user_tier: str = "omega", is_paid: bool = False) -> Dict[str, Any]:
        """
        Performs a pre-flight read-only validation for voice interactions.
        Does not increment the usage counter. Used prior to generating real-time audio tokens.
        """
        window_duration = QuotaConfig.get_window_duration()
        limit = QuotaConfig.get_voice_limit(user_tier)
        current_time = int(time.time())

        # Database Bypass for Paid Subscribers
        if is_paid:
            return {
                "allowed": True,
                "limit_reached": False,
                "current_count": 0,
                "limit": limit,
                "limit_type": "voice",
                "reset_timestamp": current_time + window_duration
            }

        current_usage = user_usage_table.get_usage(user_id, window_duration)
        if not current_usage:
            return {
                "allowed": True,
                "limit_reached": False,
                "current_count": 0,
                "limit": limit,
                "limit_type": "voice",
                "reset_timestamp": current_time + window_duration
            }

        current_count = int(current_usage.get("VoiceCount", 0))
        reset_timestamp = int(current_usage.get("ExpiresAt", current_time + window_duration))
        limit_reached = current_count >= limit

        return {
            "allowed": not limit_reached,
            "limit_reached": limit_reached,
            "current_count": current_count,
            "limit": limit,
            "limit_type": "voice",
            "reset_timestamp": reset_timestamp
        }

    def evaluate_voice_turn(self, user_id: str, user_tier: str = "omega", is_paid: bool = False) -> Dict[str, Any]:
        """
        Convenience method to evaluate and atomically increment voice quota.
        Called when a transcribed user turn is successfully persisted.
        """
        return self.evaluate_quota(
            user_id=user_id,
            intent="chat",
            has_attachments=False,
            user_tier=user_tier,
            channel="voice",
            is_paid=is_paid
        )

    def evaluate_quota(
        self,
        user_id: str,
        intent: str = "chat",
        has_attachments: bool = False,
        user_tier: str = "omega",
        channel: str = "text",
        is_paid: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates current limits and atomically increments usage if authorized.
        Supports standard text, high compute, and voice channels.
        Bypasses usage tracking entirely for paid subscribers.
        """
        tier_normalized = (user_tier or "omega").lower()
        is_free_tier = tier_normalized in ["omega", "free"]
        window_duration = QuotaConfig.get_window_duration()
        current_time = int(time.time())

        # 1. Resource Classification
        is_voice = bool(channel and channel.lower() == "voice")
        is_high_compute = not is_voice and (has_attachments or (intent and intent.lower() != "chat"))

        if is_voice:
            limit_type = "voice"
            limit = QuotaConfig.get_voice_limit(user_tier)
            count_key = "VoiceCount"
            storage_usage_type = "voice"
        elif is_high_compute:
            limit_type = "high_compute"
            limit = QuotaConfig.get_high_compute_limit(user_tier)
            count_key = "HighComputeCount"
            storage_usage_type = "high_compute"
        else:
            limit_type = "standard_text"
            limit = QuotaConfig.get_text_limit(user_tier)
            count_key = "StandardTextCount"
            storage_usage_type = "standard_text"

        # 2. Database Bypass for Paid Subscribers
        if is_paid:
            return {
                "allowed": True,
                "limit_reached": False,
                "limit_reached_now": False,
                "show_upsell": False,
                "is_high_compute": is_high_compute,
                "limit_type": limit_type,
                "reset_timestamp": current_time + window_duration,
                "current_count": 0,
                "limit": limit
            }

        # 3. Retrieve Current Usage State
        current_usage = user_usage_table.get_usage(user_id, window_duration)
        if not current_usage:
            return {
                "allowed": True,
                "limit_reached": False,
                "limit_reached_now": False,
                "show_upsell": False,
                "is_high_compute": is_high_compute,
                "limit_type": limit_type,
                "reset_timestamp": current_time + window_duration
            }

        current_count = int(current_usage.get(count_key, 0))
        reset_timestamp = int(current_usage.get("ExpiresAt", current_time + window_duration))

        # 4. Reactive Hard Paywall Check (Pre-computation intercept)
        if current_count >= limit:
            return {
                "allowed": False,
                "limit_reached": True,
                "limit_reached_now": False,
                "limit_type": limit_type,
                "reset_timestamp": reset_timestamp,
                "show_upsell": False,
                "is_high_compute": is_high_compute,
                "current_count": current_count,
                "limit": limit
            }

        # 5. Atomic Increment (Execution is authorized)
        updated_attributes = user_usage_table.increment_usage(
            user_id=user_id,
            usage_type=storage_usage_type,
            window_duration=window_duration
        )

        if not updated_attributes:
            return {
                "allowed": True,
                "limit_reached": False,
                "limit_reached_now": False,
                "show_upsell": False,
                "is_high_compute": is_high_compute,
                "limit_type": limit_type,
                "reset_timestamp": reset_timestamp
            }

        new_count = int(updated_attributes.get(count_key, current_count + 1))

        # 6. Predictive Hard Paywall Check (Zero balance reached on this exact request)
        limit_reached_now = (new_count >= limit)

        # 7. Soft Paywall Check (Post-computation injection)
        show_upsell = False
        if is_free_tier and is_high_compute and new_count == QuotaConfig.SOFT_PAYWALL_TRIGGER_COUNT and not limit_reached_now:
            show_upsell = True

        return {
            "allowed": True,
            "limit_reached": False,
            "limit_reached_now": limit_reached_now,
            "show_upsell": show_upsell,
            "reset_timestamp": reset_timestamp,
            "is_high_compute": is_high_compute,
            "limit_type": limit_type,
            "current_count": new_count,
            "limit": limit
        }


# Create a singleton instance to be imported into lambda handlers
quota_service = QuotaService()