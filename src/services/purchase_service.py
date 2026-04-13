import logging
from datetime import datetime
from typing import Dict, Any
from src.storage.purchase_table import store_purchase, get_latest_active_subscription

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def process_purchase_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts and normalizes purchase data from the Wix webhook payload.
    Validates required fields and delegates storage to the database layer.
    """
    try:
        logger.info("Received raw purchase payload for processing.")

        # Step 1: Unwrap the Wix data block safely
        data = payload.get("data", payload) 
        contact = data.get("contact", {})

        # Step 2: Extract identity and contact fields
        user_id = contact.get("contactId")
        email = contact.get("email") or data.get("site_email", "")

        # Step 3: Extract plan details
        plan_name = data.get("plan_title", "Unknown")
        
        plan_price_data = data.get("plan_price", {})
        price = float(plan_price_data.get("value", "0.0"))
        currency = plan_price_data.get("currency", "COP")

        order_id = data.get("plan_order_id")
        start_date = data.get("plan_start_date", "")
        end_date = data.get("plan_valid_until", "")
        
        timestamp = datetime.utcnow().isoformat()

        # Step 4: Validate essential fields
        if not user_id or not order_id:
            logger.warning(f"Missing essential fields. UserId: {user_id}, OrderId: {order_id}")
            raise ValueError("Missing required fields: contactId or plan_order_id")

        # Step 5: Package the data to perfectly match our DynamoDB schema
        purchase_data = {
            "UserId": user_id,
            "Timestamp": timestamp,
            "Email": email,
            "PlanName": plan_name,
            "OrderId": order_id,
            "StartDate": start_date,
            "EndDate": end_date,
            "Price": price,
            "Currency": currency,
            "Source": "wix_pricing_plans"
        }

        # Step 6: Hand off to the storage layer
        store_purchase(purchase_data)
        
        logger.info(f"Purchase successfully processed and stored for user: {user_id}")
        return {
            "statusCode": 200, 
            "message": f"Purchase recorded successfully for user {user_id}"
        }

    except Exception as e:
        logger.error(f"Error in process_purchase_webhook: {str(e)}")
        return {
            "statusCode": 500, 
            "message": "Failed to process purchase webhook"
        }

def is_user_paid(user_id: str) -> bool:
    """
    Evaluates if a user currently has an active, unexpired subscription.
    """
    if not user_id or user_id == "anonymous":
        return False
        
    latest_purchase = get_latest_active_subscription(user_id)
    
    if not latest_purchase:
        return False
        
    end_date_str = latest_purchase.get("EndDate")
    
    # If there's a purchase but no end date, we treat it as a lifetime active plan
    # Adjust this logic if your Wix plans ALWAYS have an end date.
    if not end_date_str:
        return True 
        
    try:
        # Clean the string to handle ISO formats cleanly
        end_date_clean = end_date_str.replace("Z", "+00:00")
        end_date = datetime.fromisoformat(end_date_clean)
        
        # Strip timezone info for a safe UTC comparison
        end_date_utc = end_date.replace(tzinfo=None)
        current_time_utc = datetime.utcnow()
        
        is_active = current_time_utc < end_date_utc
        
        logger.info(f"User {user_id} paid status: {is_active} (Expires: {end_date_utc})")
        return is_active
        
    except ValueError as e:
        logger.error(f"Failed to parse EndDate '{end_date_str}' for user {user_id}: {e}")
        # Default to false if we cannot verify the expiration securely
        return False