# src/lambda_update_message_handler.py

import json
import os
import logging  # 🔹 CORRECTED: Import the standard logging module
from src.storage import messages_table

# 🔹 CORRECTED: Setup logger using the standard pattern
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# CORS Headers (to allow requests from your Wix site)
cors_headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token"
}

def lambda_handler(event, context):
    """
    Handles API Gateway requests to update an assistant message with partial text.
    """
    
    # Handle OPTIONS preflight request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': ''
        }

    try:
        # Parse the incoming request body from Wix
        body = json.loads(event.get('body', '{}'))
        
        # Get the three required parameters
        conversation_id = body.get('conversationId')
        timestamp = body.get('timestamp')
        partial_text = body.get('partialText')

        # Validate that we received all necessary data
        # partial_text can be an empty string "", but not null (None)
        if not conversation_id or not timestamp or partial_text is None:
            logger.warning(f"Missing required parameters. conversationId: {conversation_id}, timestamp: {timestamp}, partialText_is_None: {partial_text is None}")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'conversationId, timestamp, and partialText are required.'})
            }

        # Log the action
        logger.info(f"Received request to update message: {conversation_id}/{timestamp}")

        # Call the update function from your messages_table module
        messages_table.update_message_text(
            conversation_id=conversation_id,
            timestamp=timestamp,
            partial_text=partial_text
        )

        # Send a 200 OK success response
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'status': 'success', 'message': 'Message updated successfully.'})
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON format in request body.'})
        }
    except Exception as e:
        # Catch any errors from the database update or other issues
        logger.error(f"An error occurred updating message {conversation_id}/{timestamp}: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'An internal error occurred.'})
        }