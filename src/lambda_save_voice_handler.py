# src/lambda_save_voice_handler.py

import json
import logging
from src.storage.messages_table import save_message
from src.storage.conversations_table import (
    update_conversation_last_active,
    get_conversation_metadata,
    save_conversation
)

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
        user_id = body.get('userId') 

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

        # 5. Handle the Conversation Header (History List)
        if user_id:
            # Check if the conversation already exists
            existing_meta = get_conversation_metadata(user_id=user_id, conversation_id=conversation_id)
            
            if existing_meta:
                # It exists! Just bump it to the top of the list
                update_conversation_last_active(user_id=user_id, conversation_id=conversation_id)
            else:
                # It doesn't exist! Create a new header row so it shows up in the UI
                logger.info(f"Creating new conversation header for orphaned voice chat: {conversation_id}")
                save_conversation(
                    user_id=user_id,
                    name="User", # Fallback name, you can adjust if you pass name in payload
                    email=None,
                    title="Voice Conversation", # Default title for new voice chats
                    page="/",
                    conversation_id=conversation_id
                )

        return {'statusCode': 200, 'body': 'Voice message saved successfully'}

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON body")
        return {'statusCode': 400, 'body': 'Invalid JSON'}
    except Exception as e:
        logger.error(f"Internal error saving voice message: {e}", exc_info=True)
        return {'statusCode': 500, 'body': 'Internal server error'}