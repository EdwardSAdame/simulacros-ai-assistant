import boto3
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from boto3.dynamodb.conditions import Key

# Setup logger
logger = logging.getLogger(__name__)

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("PurchasesTable") 

def store_purchase(purchase_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stores a single web purchase event in DynamoDB.
    Uses UserId as the Partition Key and Timestamp as the Sort Key.
    """
    try:
        user_id = purchase_data.get("UserId")
        if not user_id:
            raise ValueError("UserId is required to store a purchase.")

        timestamp = purchase_data.get("Timestamp", datetime.utcnow().isoformat())

        item = {
            "UserId": user_id,
            "Timestamp": timestamp,
            "Email": purchase_data.get("Email", ""),
            "PlanName": purchase_data.get("PlanName", "Unknown"),
            "OrderId": purchase_data.get("OrderId", ""),
            "StartDate": purchase_data.get("StartDate", ""),
            "EndDate": purchase_data.get("EndDate", ""),
            "Price": Decimal(str(purchase_data.get("Price", 0.0))),
            "Currency": purchase_data.get("Currency", "COP"),
            "Source": purchase_data.get("Source", "wix_pricing_plans")
        }

        # Clean up any purely empty strings before saving (optional, but good practice)
        safe_item = {k: v for k, v in item.items() if v != ""}

        table.put_item(Item=safe_item)
        logger.info(f"✅ Stored purchase for web user {user_id} | Plan: {item.get('PlanName')}")
        
        return safe_item

    except Exception as e:
        logger.error(f"❌ Failed to store web purchase for user {purchase_data.get('UserId', 'Unknown')}: {e}")
        raise


def get_latest_active_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the most recent purchase for a specific UserId.
    Because UserId is the Partition Key and Timestamp is the Sort Key,
    we can query this directly and sort descending.
    """
    if not user_id:
        logger.warning("get_latest_active_subscription called without a user_id.")
        return None

    try:
        response = table.query(
            KeyConditionExpression=Key('UserId').eq(user_id),
            ScanIndexForward=False, # Sorts descending by Timestamp (newest first)
            Limit=1
        )
        
        items = response.get("Items", [])
        if items:
            latest_purchase = items[0]
            logger.info(f"🛒 Found latest purchase for {user_id}: {latest_purchase.get('PlanName')}")
            return latest_purchase
        else:
            logger.info(f"🟡 No purchases found for web user {user_id}")
            return None

    except Exception as e:
        logger.error(f"❌ Error querying latest purchase for {user_id}: {e}")
        return None