# src/lambda_get_messages_handler.py
import json
import logging
import os
from decimal import Decimal
from src.storage.messages_table import get_all_messages # Import the new function
from src.utils.logging_utils import log_event, set_invocation_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- CORS Headers ---
# Adjust '*' to your specific Wix domain in production
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,GET" # Allow GET for fetching data
}

# 🟢 HELPER: Convert DynamoDB Decimal objects to JSON-compatible types
def decimal_default(obj):
    if isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    API Gateway handler to fetch all messages for a specific conversation.
    Expects conversationId as a path parameter (e.g., /messages/{conversationId}).
    """
    set_invocation_context(context)
    log_event("get_messages_invocation", {"source": "GetMessagesHandler"})

    conversation_id = None # Initialize conversation_id

    try:
        # --- Extract conversationId from path parameters ---
        # Assumes API Gateway is configured for a path like /messages/{conversationId}
        path_params = event.get('pathParameters', {})
        conversation_id = path_params.get('conversationId') if path_params else None

        if not conversation_id:
            log_event("get_messages_failed", {"reason": "Missing conversationId path parameter"}, level="warning")
            return _response(400, {"error": "conversationId path parameter is required"})

        # --- Fetch all messages from DynamoDB ---
        # Using the function we added to messages_table.py
        messages = get_all_messages(conversation_id=conversation_id) # Returns oldest first

        # 🟢 NORMALIZATION STEP: Match WebSocket format (Metadata -> metadata)
        # This fixes the reload mismatch issue.
        cleaned_messages = []
        for msg in messages:
            # Create a shallow copy to modify safely
            clean_msg = msg.copy()
            
            # Rename 'Metadata' (DynamoDB) to 'metadata' (Frontend/WebSocket standard)
            if "Metadata" in clean_msg:
                clean_msg["metadata"] = clean_msg.pop("Metadata")
            elif "Meta" in clean_msg:
                 clean_msg["metadata"] = clean_msg.pop("Meta")
                 
            cleaned_messages.append(clean_msg)

        log_event("get_messages_success", {
            "conversation_id": conversation_id,
            "message_count": len(cleaned_messages)
        })

        # --- Return the list of messages ---
        return _response(200, {"messages": cleaned_messages}) # Key is "messages"

    except Exception as e:
        log_event("get_messages_exception", {"conversation_id": conversation_id if conversation_id else 'unknown'}, level="error", error=e)
        return _response(500, {"error": "Internal server error fetching messages"})

def _response(status_code, body):
    """Helper to format API Gateway responses with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        # 🟢 UPDATED: Use the decimal_default helper to safely serialize DynamoDB data
        "body": json.dumps(body, default=decimal_default)
    }