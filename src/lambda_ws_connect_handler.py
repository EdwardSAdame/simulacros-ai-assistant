# src/lambda_ws_connect_handler.py
import logging
from src.storage.ws_connections_table import WsConnectionsTable
from src.utils.logging_utils import log_event, set_invocation_context

# --- Setup logging ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Instantiate the DynamoDB table manager ---
ws_connections_table = WsConnectionsTable()

def lambda_handler(event, context):
    """
    Handles new WebSocket connections.
    It retrieves the userId from query parameters and stores the
    userId -> connectionId mapping in DynamoDB.
    """
    set_invocation_context(context)
    
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    # --- NEW: Get the userId from the query string ---
    # The frontend will connect to wss://.../prod?userId=some-unique-id
    query_params = event.get('queryStringParameters', {})
    user_id = query_params.get('userId') if query_params else None

    if not connection_id or not user_id:
        log_event("ws_connect_failed", {
            "reason": "Missing connectionId or userId",
            "connection_id": connection_id,
            "user_id": user_id
        }, level="warning")
        return {'statusCode': 400, 'body': 'connectionId and userId are required.'}

    try:
        # --- MODIFIED: Save both userId and connectionId ---
        ws_connections_table.add_connection(user_id, connection_id)
        
        log_event("ws_client_connected", {
            "user_id": user_id,
            "connection_id": connection_id
        })
        return {'statusCode': 200, 'body': 'Connected.'}
    
    except Exception as e:
        log_event("ws_connect_exception", {
            "user_id": user_id, 
            "connection_id": connection_id
        }, level="error", error=e)
        return {'statusCode': 500, 'body': 'Failed to connect.'}