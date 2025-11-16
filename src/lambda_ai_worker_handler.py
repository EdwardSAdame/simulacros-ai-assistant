# src/lambda_ai_worker_handler.py
import json
import logging
import boto3
import os
# 🔹 MODIFIED: Import statements now relative to src
from src.services.chat_service import get_ai_response
from src.storage.ws_connections_table import WsConnectionsTable
from src.utils.logging_utils import log_event, set_invocation_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Instantiate the DynamoDB table manager ---
ws_connections_table = WsConnectionsTable()

# --- NEW: Get the WebSocket API endpoint from environment variables ---
# You must set this in your Lambda's configuration.
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT')

# It's more efficient to create the client outside the handler if the
# execution environment is reused, but we need the endpoint which might vary.
# A helper function keeps it clean.
def get_api_gateway_management_client(endpoint_url):
    """Creates a client for the API Gateway Management API."""
    return boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=endpoint_url
    )

def lambda_handler(event, context):
    """
    Triggered by SQS. Gets AI response and sends it back to the user via WebSocket.
    """
    set_invocation_context(context)

    # --- NEW: Create the API Gateway client ---
    if not WEBSOCKET_API_ENDPOINT:
        log_event("ai_worker_config_error", {"reason": "WEBSOCKET_API_ENDPOINT is not set"}, level="error")
        raise ValueError("WEBSOCKET_API_ENDPOINT environment variable not set.")
        
    api_gateway_client = get_api_gateway_management_client(WEBSOCKET_API_ENDPOINT)

    records = (event or {}).get("Records", [])
    log_event("ai_worker_invocation", {"record_count": len(records)})

    for record in records:
        try:
            body_raw = record.get("body", "{}")
            payload = json.loads(body_raw)

            # --- Extract data from the payload ---
            message = payload.get("message")
            image_urls = payload.get("image_urls", [])
            user_id = payload.get("user_id")
            name = payload.get("name")
            email = payload.get("email")
            page = payload.get("page")
            conv_id_in = payload.get("conversation_id")
            
            # 🔹 MODIFICATION: Extract the client's row ID from the payload
            client_row_id = payload.get("client_row_id")

            # --- 🔹 MODIFIED: Get the AI response AND the new timestamp ---
            # get_ai_response now returns three values
            ai_reply, conversation_id, assistant_timestamp = get_ai_response(
                message=message,
                user_id=user_id,
                name=name,
                email=email,
                page=page,
                conversation_id=conv_id_in,
                image_urls=image_urls
            )

            # --- NEW: Send the reply back via WebSocket ---
            # 1. Look up the user's current connectionId
            connection_id = ws_connections_table.get_connection_id(user_id)

            if connection_id:
                try:
                    # 2. Construct the payload to send to the frontend
                    response_payload = json.dumps({
                        "action": "ai_reply", # Good practice to include an action
                        "ai_reply": ai_reply,
                        "conversation_id": conversation_id,
                        
                        # 🔹 MODIFICATION: Echo the client_row_id back
                        "client_row_id": client_row_id,
                        
                        # --- 🔹 NEWLY ADDED 🔹 ---
                        # Add the DynamoDB timestamp (Sort Key) to the payload
                        # This is the key your frontend was missing.
                        "timestamp": assistant_timestamp
                        # --- 🔹 END NEW 🔹 ---
                    })
                    
                    # 3. Post the message to the specific connection
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=response_payload
                    )
                    log_event("ai_worker_response_sent", {
                        "user_id": user_id, 
                        "connection_id": connection_id,
                        "client_row_id": client_row_id, # Added for logging
                        "timestamp": assistant_timestamp # Added for logging
                    })

                except api_gateway_client.exceptions.GoneException:
                    log_event("ws_send_failed_gone", {"user_id": user_id, "connection_id": connection_id}, level="warning")
                except Exception as e:
                    log_event("ws_send_failed_exception", {"user_id": user_id}, level="error", error=e)
            else:
                log_event("ws_connection_not_found", {"user_id": user_id}, level="warning")

        except Exception as e:
            log_event("ai_worker_failed", { "record_id": record.get("messageId") }, level="error", error=e)
            raise e

    return {"status": "ok", "processed_records": len(records)}