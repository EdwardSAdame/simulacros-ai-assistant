# src/lambda_save_voice_handler.py

import json
import logging
from src.storage.messages_table import save_message
from src.storage.conversations_table import update_conversation_last_active

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    try:
        # 1. Parse the incoming WebSocket body
        body_str = event.get('body', '{}')
        body = json.loads(body_str)

        # 2. Extract the data payload
        conversation_id = body.get('conversationId')
        role = body.get('role')
        text = body.get('text')
        channel = body.get('channel', 'voice')
        user_id = body.get('userId') # Good practice to pass this for the update

        # 3. Validate required fields
        if not conversation_id or not role or not text:
            logger.warning(f"Missing required fields for voice save. Body received: {body}")
            return {'statusCode': 400, 'body': 'Missing conversationId, role, or text'}

        logger.info(f"Saving {role} voice message to conversation {conversation_id}")

        # 4. Save to DynamoDB using your existing table logic
        metadata = {"channel": channel}

        save_message(
            conversation_id=conversation_id,
            role=role,
            message_text=text,
            metadata=metadata
        )

        # 5. Bump the conversation to the top of the history list
        if user_id:
            update_conversation_last_active(user_id=user_id, conversation_id=conversation_id)

        return {'statusCode': 200, 'body': 'Voice message saved successfully'}

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON body")
        return {'statusCode': 400, 'body': 'Invalid JSON'}
    except Exception as e:
        logger.error(f"Internal error saving voice message: {e}", exc_info=True)
        return {'statusCode': 500, 'body': 'Internal server error'}