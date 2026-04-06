# src/services/image_usage_service.py
import uuid
import logging
from datetime import datetime, timezone

# Import the new storage layer
from src.storage.image_usage_table import image_usage_table

logger = logging.getLogger(__name__)

class ImageUsageService:
    """
    Handles tracking and logging the deterministic token cost of 
    OpenAI Image Generations (DALL-E 3 / Nano Banana 2 models).
    """
    def __init__(self):
        # Deterministic Pricing Grid (Base Tokens)
        self.PRICING_GRID = {
            "1024x1024": {"low": 272, "medium": 1056, "high": 4160},
            "1536x1024": {"low": 400, "medium": 1568, "high": 6208},
            "1024x1536": {"low": 408, "medium": 1584, "high": 6240}
        }

    def calculate_tokens(self, size: str, quality: str, partials: int) -> int:
        """
        Calculates the exact token cost based on OpenAI's pricing formula.
        Formula: Base Tokens (Resolution + Quality) + (Partial Images * 100)
        """
        quality_lower = quality.lower()
        size_lower = size.lower()

        # Fallback to standard landscape/medium (1568) if values are missing
        base_tokens = self.PRICING_GRID.get(size_lower, {}).get(quality_lower, 1568)
        
        # Each partial image chunks costs 100 tokens
        partials_cost = partials * 100

        return base_tokens + partials_cost

    def log_image_usage(
        self,
        user_id: str,
        session_id: str,
        context: str,
        tier: str,
        engine: str,
        size: str,
        quality: str,
        partials: int,
        image_count: int = 1
    ) -> dict:
        """
        Calculates the total cost and passes the transaction receipt to the storage layer.
        Returns the token math as a dictionary so the calling function can see it.
        """
        if not user_id or not session_id:
            logger.warning("Missing user_id or session_id. Skipping Image Usage logging.")
            return {}

        # 1. Calculate Cost
        cost_per_image = self.calculate_tokens(size, quality, partials)
        total_tokens = cost_per_image * image_count

        # 2. Prepare Database Item
        timestamp = datetime.now(timezone.utc).isoformat()
        usage_id = str(uuid.uuid4())

        item = {
            "UsageId": usage_id,
            "UserId": user_id,
            "Timestamp": timestamp,
            "SessionId": session_id,
            "Context": context,      # e.g., 'quiz_background', 'creative_chat'
            "Tier": tier,            # e.g., 'alpha', 'omega'
            "Engine": engine,        # e.g., 'gpt-image-1.5'
            "Config": {
                "Size": size,
                "Quality": quality,
                "Partials": partials,
                "ImageCount": image_count
            },
            "TotalTokens": total_tokens
        }

        # 3. Save to DynamoDB via the Storage Layer
        success = image_usage_table.put_item(item)
        
        if success:
            logger.info(f"🪙 Image Usage Logged: {total_tokens} tokens for User {user_id} in {context}")
            return {"total_tokens": total_tokens, "cost_per_image": cost_per_image}
        else:
            logger.error(f"Failed to pass image usage to the storage layer for User {user_id}")
            return {}