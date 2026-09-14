import os

class QuotaConfig:
    # Rolling window duration in seconds (Default: 14400 seconds = 4 hours)
    WINDOW_DURATION_SECONDS = int(os.environ.get("QUOTA_WINDOW_SECONDS", 14400))

    # Free tier limits
    FREE_HIGH_COMPUTE_LIMIT = int(os.environ.get("FREE_HIGH_COMPUTE_LIMIT", 2))
    FREE_STANDARD_TEXT_LIMIT = int(os.environ.get("FREE_STANDARD_TEXT_LIMIT", 15))

    # Soft paywall trigger point (e.g., show after 1st deliverable is consumed)
    SOFT_PAYWALL_TRIGGER_COUNT = int(os.environ.get("SOFT_PAYWALL_TRIGGER_COUNT", 1))

    @classmethod
    def get_window_duration(cls) -> int:
        return cls.WINDOW_DURATION_SECONDS

    @classmethod
    def get_high_compute_limit(cls, tier: str = "free") -> int:
        if tier.lower() == "omega" or tier.lower() == "free":
            return cls.FREE_HIGH_COMPUTE_LIMIT
        return 999999  # Unlimited for paid tiers

    @classmethod
    def get_text_limit(cls, tier: str = "free") -> int:
        if tier.lower() == "omega" or tier.lower() == "free":
            return cls.FREE_STANDARD_TEXT_LIMIT
        return 999999