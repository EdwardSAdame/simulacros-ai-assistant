# src/lambda_get_conversations_handler.py
import json
import logging
import os
from src.storage.conversations_table import get_conversations_for_user
from src.utils.logging_utils import log_event, set_invocation_context

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
        # Assumes API Gateway passes query params like ?userId=some-wix-id
        query_params = event.get('queryStringParameters', {})
        user_id = query_params.get('userId') if query_params else None

        if not user_id:
            log_event("get_conversations_failed", {"reason": "Missing userId parameter"}, level="warning")
            return _response(400, {"error": "userId query parameter is required"})

        # --- Fetch conversations from DynamoDB ---
        # Using the function we added to conversations_table.py
        # Fetches newest 50 by default, adjust limit if needed
        conversations = get_conversations_for_user(user_id=user_id, limit=50, ascending=False)

        log_event("get_conversations_success", {
            "user_id": user_id,
            "conversation_count": len(conversations)
        })

        # --- Return the list of conversations ---
        # We only included ConversationId, Title, Timestamp in the projection
        return _response(200, {"conversations": conversations})

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