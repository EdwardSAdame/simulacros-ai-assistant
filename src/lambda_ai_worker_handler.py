# src/lambda_ai_worker_handler.py
import json
import logging
import boto3
import os
from src.services.chat_service import get_ai_response
from src.storage.ws_connections_table import WsConnectionsTable
from src.utils.logging_utils import log_event, set_invocation_context

# 🔹 IMPORT: The Hybrid Semantic Router
from src.services.semantic_router import semantic_router

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Instantiate the DynamoDB table manager ---
ws_connections_table = WsConnectionsTable()

# --- Get the WebSocket API endpoint from environment variables ---
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT')

def get_api_gateway_management_client(endpoint_url):
    """Creates a client for the API Gateway Management API."""
    return boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=endpoint_url
    )

def lambda_handler(event, context):
    """
    Triggered by SQS. 
    1. Determines status/category + Creative Loading Phrases.
    2. Sends Visual Feedback (Action: status_update).
    3. Generates Response.
    4. Sends Final Answer.
    """
    set_invocation_context(context)

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
            client_row_id = payload.get("client_row_id")
            
            # 🔹 NEW: Extract the AI mode (sent by chat_handler)
            ai_mode = payload.get("mode", "omega")

            # --- 1. Get Connection ID ---
            connection_id = ws_connections_table.get_connection_id(user_id)

            # --- 2. Send Visual Feedback (The "Thinking" Phase) ---
            if connection_id:
                try:
                    # 🔹 ROUTER CALL: Get category AND creative phrases
                    routing_result = semantic_router.determine_category(message)
                    
                    category_key = routing_result.get("category", "general")
                    # Extract the list of creative phrases
                    loading_phrases = routing_result.get("loading_phrases", []) 
                    source_type = routing_result.get("source", "unknown")
                    
                    status_payload = json.dumps({
                        "action": "status_update",
                        "category": category_key, 
                        "loading_phrases": loading_phrases, # <--- SENDING THE LIST TO FRONTEND
                        "source": source_type,    
                        "client_row_id": client_row_id
                    })
                    
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=status_payload
                    )
                    
                    log_event("visual_feedback_sent", {
                        "user_id": user_id, 
                        "category": category_key,
                        "phrases_count": len(loading_phrases),
                        "source": source_type,
                        "mode": ai_mode
                    })

                except Exception as e:
                    # Don't fail the whole process if just the status update fails
                    log_event("ws_status_send_failed", {"user_id": user_id}, level="warning", error=e)

            # --- 3. Get the AI response (Heavy Processing) ---
            ai_reply, conversation_id, assistant_timestamp = get_ai_response(
                message=message,
                user_id=user_id,
                name=name,
                email=email,
                page=page,
                conversation_id=conv_id_in,
                image_urls=image_urls,
                mode=ai_mode  # 🔹 Pass the mode to the service layer
            )

            # --- 4. Send Final Reply ---
            if connection_id:
                try:
                    response_payload = json.dumps({
                        "action": "ai_reply",
                        "ai_reply": ai_reply,
                        "conversation_id": conversation_id,
                        "client_row_id": client_row_id,
                        "timestamp": assistant_timestamp
                    })
                    
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=response_payload
                    )
                    log_event("ai_worker_response_sent", {
                        "user_id": user_id, 
                        "connection_id": connection_id,
                        "client_row_id": client_row_id,
                        "timestamp": assistant_timestamp
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