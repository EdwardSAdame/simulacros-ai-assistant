# src/lambda_ws_connect_handler.py
from src.storage.ws_connections_table import save_connection
from src.utils.logging_utils import log_event, set_invocation_context

def lambda_handler(event, context):
    set_invocation_context(context)
    connection_id = event.get('requestContext', {}).get('connectionId')

    if not connection_id:
        log_event("ws_connect_failed", {"reason": "Missing connectionId"}, level="warning")
        return {'statusCode': 400, 'body': 'connectionId is required.'}

    try:
        save_connection(connection_id)
        log_event("ws_client_connected", {"connection_id": connection_id})
        return {'statusCode': 200, 'body': 'Connected.'}
    
    except Exception as e:
        log_event("ws_connect_exception", {"connection_id": connection_id}, level="error", error=e)
        return {'statusCode': 500, 'body': 'Failed to connect.'}