import json
import logging
import boto3
import os
from src.storage.messages_table import save_message
from src.storage.conversations_table import (
    update_conversation_last_active,
    get_conversation_metadata,
    save_conversation
)
from src.services.quota_service import quota_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize API Gateway client for WebSocket push
APIGW_ENDPOINT_URL = os.environ.get('APIGW_AUDIO_ENDPOINT_URL', os.environ.get('APIGW_ENDPOINT_URL'))
apigw_client = boto3.client('apigatewaymanagementapi', endpoint_url=APIGW_ENDPOINT_URL) if APIGW_ENDPOINT_URL else None

def handler(event, context):
    try:
        # Extract the WebSocket connection ID for active pushes
        ws_connection_id = event.get('requestContext', {}).get('connectionId')

        # 1. Parse the incoming WebSocket body
        body_str = event.get('body', '{}')
        body = json.loads(body_str)

        # 2. Extract the data payload
        conversation_id = body.get('conversationId')
        role = body.get('role')
        text = body.get('text')
        channel = body.get('channel', 'voice')
        user_id = body.get('userId') 
        
        # Extract the frontend profile fields
        user_name = body.get('name', 'Guest')
        user_email = body.get('email', None)
        user_page = body.get('page', '/')
        ai_mode = body.get('mode', 'omega')
        arena_id = body.get('arenaId', None)

        # 3. Validate required fields
        if not conversation_id or not role or not text:
            logger.warning(f"Missing required fields for voice save. Body received: {body}")
            return {'statusCode': 400, 'body': json.dumps({'error': 'Missing conversationId, role, or text'})}

        logger.info(f"Saving {role} voice message to conversation {conversation_id}")

        # 4. Save to DynamoDB using your existing table logic
        metadata = {"channel": channel}

        save_message(
            conversation_id=conversation_id,
            role=role,
            message_text=text,
            metadata=metadata
        )

        # 5. Handle the Conversation Header and Quota Increment
        quota_metadata = {}
        
        if user_id:
            # Increment quota ONLY for user turns to prevent double-counting
            if role == 'user':
                try:
                    quota_result = quota_service.evaluate_voice_turn(user_id=user_id, user_tier=ai_mode)
                    
                    is_limit_reached = quota_result.get("limit_reached", False) or quota_result.get("limit_reached_now", False)
                    
                    quota_metadata = {
                        "limit_reached_now": quota_result.get("limit_reached_now", False),
                        "limit_reached": quota_result.get("limit_reached", False),
                        "current_count": quota_result.get("current_count", 0),
                        "reset_timestamp": quota_result.get("reset_timestamp")
                    }

                    # MID-CONVERSATION PUSH: Actively notify the frontend if the limit was just hit
                    if is_limit_reached and apigw_client and ws_connection_id:
                        logger.info(f"Voice quota reached for user {user_id}. Pushing termination signal to frontend.")
                        try:
                            apigw_client.post_to_connection(
                                ConnectionId=ws_connection_id,
                                Data=json.dumps({
                                    "action": "error",
                                    "message": "Voice quota limit reached.",
                                    "limit_type": "voice",
                                    "reset_timestamp": quota_result.get("reset_timestamp")
                                })
                            )
                        except Exception as push_err:
                            logger.error(f"Failed to push quota error to client {ws_connection_id}: {push_err}")

                except Exception as qe:
                    logger.error(f"Error evaluating voice quota for {user_id}: {qe}")

            # Check if the conversation already exists
            existing_meta = get_conversation_metadata(user_id=user_id, conversation_id=conversation_id)
            
            if existing_meta:
                # It exists! Just bump it to the top of the list
                update_conversation_last_active(user_id=user_id, conversation_id=conversation_id)
            else:
                # Only allow the 'user' payload to create the header to prevent race duplicates
                if role == 'user':
                    
                    # Dynamically generate the title from the first spoken sentence
                    dynamic_title = text[:40] + ("..." if len(text) > 40 else "")
                    
                    logger.info(f"Creating new conversation header: {conversation_id} with title: {dynamic_title}")
                    
                    save_conversation(
                        user_id=user_id,
                        name=user_name,       
                        email=user_email,     
                        title=dynamic_title,  
                        page=user_page,       
                        conversation_id=conversation_id,
                        arena_id=arena_id,    
                        ai_mode=ai_mode,      
                        channel="voice" 
                    )
                else:
                    logger.info(f"Skipping header creation for 'assistant' message to prevent race duplicate: {conversation_id}")

        # 6. Return success with optional quota metadata
        response_body = {
            "message": "Voice message saved successfully",
            "quota": quota_metadata
        }
        
        return {
            'statusCode': 200, 
            'body': json.dumps(response_body),
            'headers': {'Content-Type': 'application/json'}
        }

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON body")
        return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid JSON'})}
    except Exception as e:
        logger.error(f"Internal error saving voice message: {e}", exc_info=True)
        return {'statusCode': 500, 'body': json.dumps({'error': 'Internal server error'})}