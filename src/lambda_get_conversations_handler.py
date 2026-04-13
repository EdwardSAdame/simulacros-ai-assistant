# src/lambda_get_conversations_handler.py
import json
import logging
import os
from src.storage.conversations_table import get_conversations_for_user
from src.utils.logging_utils import log_event, set_invocation_context

# --- NEW: Import the purchase service ---
from src.services.purchase_service import is_user_paid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- CORS Headers ---
# Adjust '*' to your specific Wix domain in production for better security
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,GET" # Allow GET for fetching data
}

def lambda_handler(event, context):
    """
    API Gateway handler to fetch conversation list for a user.
    Expects userId as a query string parameter.
    """
    set_invocation_context(context)
    log_event("get_conversations_invocation", {"source": "GetConversationsHandler"})

    try:
        # --- Extract userId from query parameters ---
        query_params = event.get('queryStringParameters', {})
        user_id = query_params.get('userId') if query_params else None

        if not user_id:
            log_event("get_conversations_failed", {"reason": "Missing userId parameter"}, level="warning")
            return _response(400, {"error": "userId query parameter is required"})

        # --- NEW: Check the user's subscription tier ---
        # Evaluate if the user is paid. If so, they get alpha. Otherwise, omega.
        is_paid = is_user_paid(user_id)
        user_tier = "alpha" if is_paid else "omega"

        # --- Fetch conversations from DynamoDB ---
        conversations = get_conversations_for_user(user_id=user_id, limit=50, ascending=False)

        log_event("get_conversations_success", {
            "user_id": user_id,
            "conversation_count": len(conversations),
            "tier": user_tier # Log the evaluated tier
        })

        # --- MODIFIED: Return the tier alongside conversations ---
        return _response(200, {
            "tier": user_tier,
            "conversations": conversations
        })

    except Exception as e:
        log_event("get_conversations_exception", {"user_id": user_id if 'user_id' in locals() else 'unknown'}, level="error", error=e)
        return _response(500, {"error": "Internal server error fetching conversations"})

def _response(status_code, body):
    """Helper to format API Gateway responses with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body)
    }