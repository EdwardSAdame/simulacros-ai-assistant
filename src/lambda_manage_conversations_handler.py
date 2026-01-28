# src/lambda_manage_conversations_handler.py
import json
import logging
import os
from src.storage import conversations_table, messages_table

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Handles management operations for conversations:
    - PUT: Rename, Pin, or Move to Arena
    - DELETE: Delete conversation AND its message history
    """
    # CORS Headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "OPTIONS,POST,PUT,DELETE",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }

    if event['httpMethod'] == 'OPTIONS':
        return { 'statusCode': 200, 'headers': headers, 'body': '' }

    try:
        # 1. Extract User ID
        query_params = event.get('queryStringParameters') or {}
        user_id = query_params.get('userId')
        
        # Fallback: Check body
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])
            if not user_id:
                user_id = body.get('userId')

        if not user_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'userId is required'})
            }

        method = event['httpMethod']

        # --- HANDLE DELETE ---
        if method == 'DELETE':
            path_params = event.get('pathParameters') or {}
            conversation_id = path_params.get('id') or query_params.get('conversationId') or body.get('conversationId')

            if not conversation_id:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Missing conversationId'})}

            # 1. Delete the Conversation Header
            conversations_table.delete_conversation(user_id, conversation_id)

            # 2. Delete the Message History
            messages_table.delete_messages_for_conversation(conversation_id)

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'Deleted successfully'})
            }

        # --- HANDLE PUT (Rename / Pin / Move) ---
        elif method == 'PUT':
            action = body.get('action') 
            conversation_id = body.get('conversationId')

            if not conversation_id:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Missing conversationId'})}

            # ACTION: RENAME
            if action == 'rename':
                new_title = body.get('title')
                if not new_title:
                    return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Missing new title'})}
                
                conversations_table.update_conversation_title(user_id, conversation_id, new_title)
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({'message': 'Renamed successfully', 'title': new_title})
                }

            # ACTION: PIN
            elif action == 'pin':
                is_pinned = body.get('isPinned', False)
                conversations_table.update_conversation_pin(user_id, conversation_id, is_pinned)
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({'message': 'Pin status updated', 'isPinned': is_pinned})
                }
            
            # 🟢 NEW ACTION: MOVE TO ARENA
            elif action == 'move_to_arena':
                arena_id = body.get('arenaId') # Can be None to remove from arena
                conversations_table.update_conversation_arena(user_id, conversation_id, arena_id)
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({'message': 'Conversation moved', 'arenaId': arena_id})
                }
            
            else:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Invalid action'})}

        else:
            return {'statusCode': 405, 'headers': headers, 'body': json.dumps({'error': 'Method not allowed'})}

    except Exception as e:
        logger.error(f"Error managing conversation: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }