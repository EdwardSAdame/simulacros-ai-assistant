# src/services/image_usage_service.py
import uuid
import logging
from datetime import datetime, timezone
from src.storage.image_usage_table import image_usage_table

logger = logging.getLogger(__name__)

class ImageUsageService:
    def __init__(self):
        self.PRICING_GRID = {
            "1024x1024": {"low": 272, "medium": 1056, "high": 4160},
            "1536x1024": {"low": 400, "medium": 1568, "high": 6208},
            "1024x1536": {"low": 408, "medium": 1584, "high": 6240}
        }

    def calculate_tokens(self, size: str, quality: str, partials: int) -> int:
        quality_lower = quality.lower()
        size_lower = size.lower()
        base_tokens = self.PRICING_GRID.get(size_lower, {}).get(quality_lower, 1568)
        partials_cost = partials * 100
        return base_tokens + partials_cost

    def log_image_usage(
        self,
        user_id: str,
        conversation_id: str,  # 🟢 FIX: Renamed to match your UserConversation table
        source: str,         
        tier: str,
        engine: str,
        size: str,
        quality: str,
        partials: int,
        image_count: int = 1,
        image_url: str = None  
    ) -> dict:
        
        if not user_id or not conversation_id:
            logger.warning("Missing user_id or conversation_id. Skipping Image Usage logging.")
            return {}

        cost_per_image = self.calculate_tokens(size, quality, partials)
        total_tokens = cost_per_image * image_count

        timestamp = datetime.now(timezone.utc).isoformat()
        usage_id = str(uuid.uuid4())

        metadata = {
            "Source": source,       
            "ConversationId": conversation_id,  # 🟢 FIX: Cleaned up the key name!
            "Tier": tier,            
            "Engine": engine,        
            "Size": size,
            "Quality": quality,
            "Partials": partials,
            "ImageCount": image_count
        }
        
        if image_url:
            metadata["ImageUrl"] = image_url

        item = {
            "UsageId": usage_id,
            "UserId": user_id,
            "Timestamp": timestamp,
            "TotalTokens": total_tokens,
            "Metadata": metadata
        }

        success = image_usage_table.put_item(item)
        
        if success:
            logger.info(f"🪙 Image Usage Logged: {total_tokens} tokens for User {user_id} via {source}")
            return {"total_tokens": total_tokens, "cost_per_image": cost_per_image}
        else:
            logger.error(f"Failed to pass image usage to the storage layer for User {user_id}")
            return {}