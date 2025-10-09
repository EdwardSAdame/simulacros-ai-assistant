# src/lambda_ws_disconnect_handler.py
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
    Handles WebSocket disconnections.
    It removes the connection entry from DynamoDB using the connectionId.
    """
    set_invocation_context(context)
    
    connection_id = event.get('requestContext', {}).get('connectionId')

    if not connection_id:
        log_event("ws_disconnect_failed", {"reason": "Missing connectionId"}, level="warning")
        return {'statusCode': 400, 'body': 'connectionId is required.'}

    try:
        # --- MODIFIED: Use the new method to remove by connectionId ---
        ws_connections_table.remove_connection_by_id(connection_id)
        
        log_event("ws_client_disconnected", {"connection_id": connection_id})
        return {'statusCode': 200, 'body': 'Disconnected.'}

    except Exception as e:
        log_event("ws_disconnect_exception", {"connection_id": connection_id}, level="error", error=e)
        return {'statusCode': 500, 'body': 'Failed to disconnect.'}