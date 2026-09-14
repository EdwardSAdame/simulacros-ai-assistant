import time
import logging
from src.config.quota_config import QuotaConfig
from src.storage.user_usage_table import UserUsageTable

logger = logging.getLogger(__name__)

# Instantiate the table access layer
user_usage_table = UserUsageTable()

class QuotaService:
    """
    Evaluates user rate limits and manages the dual-bucket quota system.
    Enforces Hard Paywalls (blocking) and Soft Paywalls (upsell metadata).
    """
    def evaluate_quota(self, user_id: str, intent: str, has_attachments: bool, user_tier: str = "omega") -> dict:
        is_free_tier = user_tier.lower() in ["omega", "free"]
        
        # 1. Intent Classification
        is_high_compute = has_attachments or (intent and intent.lower() != "chat")
        
        # 2. Retrieve Configuration Limits
        limit = QuotaConfig.get_high_compute_limit(user_tier) if is_high_compute else QuotaConfig.get_text_limit(user_tier)
        window_duration = QuotaConfig.get_window_duration()
        
        # 3. Retrieve Current Usage State
        current_usage = user_usage_table.get_usage(user_id, window_duration)
        
        if not current_usage:
            return {"allowed": True, "show_upsell": False, "is_high_compute": is_high_compute}

        current_count = int(current_usage.get('HighComputeCount', 0)) if is_high_compute else int(current_usage.get('StandardTextCount', 0))
        reset_timestamp = int(current_usage.get('ExpiresAt', int(time.time()) + window_duration))

        # 4. Reactive Hard Paywall Check (Pre-computation intercept)
        if current_count >= limit:
            return {
                "allowed": False,
                "limit_reached": True,
                "limit_reached_now": False,
                "limit_type": "high_compute" if is_high_compute else "standard_text",
                "reset_timestamp": reset_timestamp,
                "show_upsell": False,
                "is_high_compute": is_high_compute
            }
            
        # 5. Atomic Increment (Execution is authorized)
        updated_attributes = user_usage_table.increment_usage(user_id, is_high_compute, window_duration)
        
        if not updated_attributes:
             return {"allowed": True, "show_upsell": False, "is_high_compute": is_high_compute}
             
        # Extract the new count after incrementing
        new_count = int(updated_attributes.get('HighComputeCount', current_count + 1)) if is_high_compute else int(updated_attributes.get('StandardTextCount', current_count + 1))

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
            "limit_type": "high_compute" if is_high_compute else "standard_text"
        }

# Create a singleton instance to be imported into lambda handlers
quota_service = QuotaService()