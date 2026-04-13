import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from src.storage.purchase_table import store_purchase, get_latest_active_subscription

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def process_purchase_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts purchase data, generates precise timestamps, and mathematically
    calculates expiration times down to the exact second.
    """
    try:
        logger.info("Received raw purchase payload for processing.")

        # Step 1: Unwrap the Wix data block safely
        data = payload.get("data", payload) 
        contact = data.get("contact", {})

        # Step 2: Extract identity (Prioritize Member ID over Contact ID)
        user_id = data.get("memberId") or contact.get("memberId") or contact.get("contactId")
        email = contact.get("email") or data.get("site_email", "")

        # Step 3: Extract plan details
        plan_name = data.get("plan_title", "Unknown")
        plan_price_data = data.get("plan_price", {})
        price = float(plan_price_data.get("value", "0.0"))
        currency = plan_price_data.get("currency", "COP")
        order_id = data.get("plan_order_id")
        
        # ========================================================
        # 🟢 NEW EXACT TIMING LOGIC
        # ========================================================
        
        # 1. Grab the exact current UTC time down to the microsecond
        now_utc = datetime.utcnow()
        exact_start_timestamp = now_utc.isoformat() + "Z"
        
        # 2. Determine the duration mathematically based on the plan name
        plan_name_lower = plan_name.lower()
        if "year" in plan_name_lower or "anual" in plan_name_lower or "año" in plan_name_lower:
            days_to_add = 365
        else:
            days_to_add = 30 # Default to exactly 30 days for monthly plans
            
        # 3. Add the exact days to the current exact time
        exact_end_utc = now_utc + timedelta(days=days_to_add)
        calculated_end_date_str = exact_end_utc.isoformat() + "Z"
        
        # ========================================================

        # Step 4: Validate essential fields
        if not user_id or not order_id:
            logger.warning(f"Missing essential fields. UserId: {user_id}, OrderId: {order_id}")
            raise ValueError("Missing required fields: UserId or plan_order_id")

        # Step 5: Package the data with our new precise timing
        purchase_data = {
            "UserId": user_id,
            "Timestamp": exact_start_timestamp,
            "Email": email,
            "PlanName": plan_name,
            "OrderId": order_id,
            "StartDate": exact_start_timestamp, # Discard Wix's sloppy start date
            "EndDate": calculated_end_date_str, # Discard Wix's sloppy end date
            "Price": price,
            "Currency": currency,
            "Source": "wix_pricing_plans"
        }

        # Step 6: Hand off to the storage layer
        store_purchase(purchase_data)
        
        logger.info(f"Purchase successfully processed and stored for user: {user_id}. Precision Expiration: {calculated_end_date_str}")
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
    Evaluates if a user currently has an active subscription using
    strict UTC time comparisons down to the microsecond.
    """
    if not user_id or user_id == "anonymous":
        return False
        
    latest_purchase = get_latest_active_subscription(user_id)
    
    if not latest_purchase:
        return False
        
    end_date_str = latest_purchase.get("EndDate")
    
    if not end_date_str:
        return True 
        
    try:
        # Because we now generate perfect ISO strings in the webhook,
        # we can revert to this clean, lightning-fast parser.
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
        return False