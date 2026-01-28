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

def _parse_body(event):
    """Safely parses the body from JSON string to Dictionary"""
    try:
        if 'body' in event and event['body']:
            if isinstance(event['body'], str):
                return json.loads(event['body'])
            return event['body']
        return {}
    except Exception:
        return {}

def _get_user_id(event, parsed_body):
    """
    Extracts User ID from the event. 
    Checks Cognito claims first, then falls back to request body (for testing).
    """
    # Option A: Cognito Authorizer
    if 'requestContext' in event and 'authorizer' in event['requestContext']:
        claims = event['requestContext']['authorizer'].get('claims', {})
        sub = claims.get('sub') or claims.get('username')
        if sub:
            return sub
    
    # Option B: For testing (passed in body)
    # Check for both snake_case and camelCase
    if parsed_body:
        return parsed_body.get('user_id') or parsed_body.get('userId')
    
    return None

def lambda_handler(event, context):
    """
    CRUD Handler for Arenas (Folders).
    Supports HTTP API v2 and REST API v1 payloads.
    """
    # 1. Determine HTTP Method (Support v1 and v2)
    method = event.get('httpMethod')
    if not method and 'requestContext' in event:
        http_context = event['requestContext'].get('http', {})
        method = http_context.get('method')

    # 2. Get Path Parameters
    path_params = event.get('pathParameters') or {}
    arena_id = path_params.get('id')  # e.g. /arenas/{id}
    
    # 3. Parse Body
    body = _parse_body(event)

    # 4. Handle OPTIONS (CORS Preflight)
    if method == 'OPTIONS':
        return _build_response(200, "")

    try:
        user_id = _get_user_id(event, body)
        
        # Log the request for debugging
        logger.info(f"Method: {method}, User: {user_id}, ArenaID: {arena_id}")

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
            new_arena = arena_service.create_arena_folder(
                user_id=user_id,
                title=body.get('title'),
                description=body.get('description'),
                system_instructions=body.get('system_instructions') or body.get('systemInstructions'),
                files=body.get('files', []) 
            )
            return _build_response(201, new_arena)

        # --- 4. UPDATE ARENA (PUT /arenas/{id}) ---
        if method == 'PUT' and arena_id:
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