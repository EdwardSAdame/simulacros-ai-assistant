# src/lambda_ai_worker_handler.py
import json
import logging
import boto3
import os
from src.services.chat_service import get_ai_response
from src.storage.ws_connections_table import WsConnectionsTable
from src.utils.logging_utils import log_event, set_invocation_context

# 🟢 IMPORT: The Stream Manager
from src.streaming.stream_manager import StreamManager

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
    1. Determines status/category + Creative Loading Phrases + INTENT.
    2. Sends Visual Feedback (Action: status_update) containing CLIENT ACTIONS.
    3. Generates Response (Text + Optional Quiz JSON).
    4. Sends Final Answer (Text Bubble + Quiz Event).
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
            
            # Extract the AI mode (sent by chat_handler)
            ai_mode = payload.get("mode", "omega")

            # --- 1. Get Connection ID ---
            connection_id = ws_connections_table.get_connection_id(user_id)

            # 🟢 Initialize Stream Manager (if connected)
            stream_manager = None
            if connection_id:
                stream_manager = StreamManager(connection_id, api_gateway_client)

            # --- 2. Send Visual Feedback (The "Thinking" Phase) ---
            intent = "chat" 
            
            if connection_id:
                try:
                    # 🔹 ROUTER CALL: Get category, creative phrases, AND intent
                    routing_result = semantic_router.determine_category(message)
                    
                    category_key = routing_result.get("category", "general")
                    loading_phrases = routing_result.get("loading_phrases", []) 
                    source_type = routing_result.get("source", "unknown")
                    intent = routing_result.get("intent", "chat") # <--- CAPTURE INTENT
                    
                    # 🔹 DETERMINE CLIENT ACTION
                    # This tells the frontend to expand the panel (Animation 70vw/30vw)
                    client_action = None
                    if intent == "quiz":
                        client_action = "OPEN_QUIZ_PANEL"

                    status_payload = json.dumps({
                        "action": "status_update",
                        "category": category_key, 
                        "loading_phrases": loading_phrases,
                        "source": source_type,
                        "client_row_id": client_row_id,
                        "client_action": client_action 
                    })
                    
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=status_payload
                    )
                    
                    log_event("visual_feedback_sent", {
                        "user_id": user_id, 
                        "category": category_key,
                        "intent": intent, 
                        "client_action": client_action,
                        "phrases_count": len(loading_phrases),
                        "source": source_type,
                        "mode": ai_mode
                    })

                except Exception as e:
                    # Don't fail the whole process if just the status update fails
                    log_event("ws_status_send_failed", {"user_id": user_id}, level="warning", error=e)

            # --- 3. Get the AI response (Heavy Processing) ---
            # 🟢 PASS THE STREAM MANAGER
            ai_reply, conversation_id, assistant_timestamp, quiz_data = get_ai_response(
                message=message,
                user_id=user_id,
                name=name,
                email=email,
                page=page,
                conversation_id=conv_id_in,
                image_urls=image_urls,
                mode=ai_mode,
                intent=intent,
                stream_manager=stream_manager # <--- 🟢 PASSED HERE
            )

            # --- 4. Send Final Reply ---
            if connection_id:
                try:
                    # A. Send Standard Text Reply (The Chat Bubble)
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

                    # B. Send Quiz Data (Consistency Check)
                    # Even if we streamed the questions, sending this "Final" update guarantees
                    # the client has the complete, correct state stored in the DB.
                    if quiz_data:
                        quiz_payload = json.dumps({
                            "action": "quiz_data_update",
                            "data": quiz_data,
                            "conversation_id": conversation_id
                        })
                        api_gateway_client.post_to_connection(
                            ConnectionId=connection_id,
                            Data=quiz_payload
                        )
                        log_event("quiz_data_pushed_to_client", {"conversation_id": conversation_id})

                    log_event("ai_worker_response_sent", {
                        "user_id": user_id, 
                        "connection_id": connection_id,
                        "client_row_id": client_row_id,
                        "timestamp": assistant_timestamp,
                        "has_quiz_data": bool(quiz_data)
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