# src/lambda_arenas_handler.py
import json
import logging
from typing import Dict, Any

from src.services.arena_service import arena_service
from src.utils.logging_utils import log_event

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _build_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Helper to build API Gateway response with CORS"""
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        },
        "body": json.dumps(body)
    }

def _get_user_id(event):
    """
    Extracts User ID from the event. 
    Adjust this depending on if you use Cognito, Custom Auth, or pass it in the body.
    """
    # Option A: Cognito Authorizer
    if 'requestContext' in event and 'authorizer' in event['requestContext']:
        claims = event['requestContext']['authorizer'].get('claims', {})
        return claims.get('sub') or claims.get('username')
    
    # Option B: For testing (passed in body/query) - REMOVE IN PRODUCTION
    body = json.loads(event.get('body', '{}') or '{}')
    if 'user_id' in body:
        return body['user_id']
    
    return None

def lambda_handler(event, context):
    """
    CRUD Handler for Arenas (Folders).
    """
    method = event.get('httpMethod')
    path_params = event.get('pathParameters') or {}
    arena_id = path_params.get('id')  # e.g. /arenas/{id}
    
    try:
        user_id = _get_user_id(event)
        if not user_id:
            return _build_response(401, {"error": "Unauthorized: No user_id found"})

        # --- 1. LIST ARENAS (GET /arenas) ---
        if method == 'GET' and not arena_id:
            arenas = arena_service.get_user_arenas(user_id)
            return _build_response(200, {"arenas": arenas})

        # --- 2. GET DETAILS (GET /arenas/{id}) ---
        if method == 'GET' and arena_id:
            details = arena_service.get_arena_context(user_id, arena_id)
            if not details:
                return _build_response(404, {"error": "Arena not found"})
            return _build_response(200, details)

        # --- 3. CREATE ARENA (POST /arenas) ---
        if method == 'POST':
            body = json.loads(event.get('body', '{}'))
            
            new_arena = arena_service.create_arena_folder(
                user_id=user_id,
                title=body.get('title'),
                description=body.get('description'),
                system_instructions=body.get('system_instructions'),
                files=body.get('files', []) # List of {name, url}
            )
            return _build_response(201, new_arena)

        # --- 4. UPDATE ARENA (PUT /arenas/{id}) ---
        if method == 'PUT' and arena_id:
            body = json.loads(event.get('body', '{}'))
            updated = arena_service.update_arena_details(user_id, arena_id, body)
            return _build_response(200, updated)

        # --- 5. DELETE ARENA (DELETE /arenas/{id}) ---
        if method == 'DELETE' and arena_id:
            success = arena_service.delete_arena_folder(user_id, arena_id)
            if success:
                return _build_response(200, {"message": "Arena deleted"})
            return _build_response(400, {"error": "Failed to delete arena"})

        return _build_response(400, {"error": f"Unsupported method: {method}"})

    except Exception as e:
        logger.error(f"Arena Handler Error: {str(e)}", exc_info=True)
        return _build_response(500, {"error": str(e)})