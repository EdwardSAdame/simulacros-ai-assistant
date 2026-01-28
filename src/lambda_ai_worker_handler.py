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
    3. Generates Response (Text + Optional Meta Payload).
    4. Sends Final Answer (Text Bubble + Rich Data Event).
    """
    set_invocation_context(context)

    if not WEBSOCKET_API_ENDPOINT:
        log_event("ai_worker_config_error", {"reason": "WEBSOCKET_API_ENDPOINT is not set"}, level="error")
        raise ValueError("WEBSOCKET_API_ENDPOINT environment variable not set.")
        
    api_gateway_client = get_api_gateway_management_client(WEBSOCKET_API_ENDPOINT)

    records = (event or {}).get("Records", [])
    log_event("ai_worker_invocation", {"record_count": len(records)})

    for record in records:
        # Initialize variables outside try block for safe error handling
        user_id = None
        connection_id = None
        conv_id_in = None
        client_row_id = None
        
        try:
            body_raw = record.get("body", "{}")
            payload = json.loads(body_raw)

            # --- Extract data from the payload ---
            message = payload.get("message")
            image_urls = payload.get("image_urls", [])
            pdf_urls = payload.get("pdf_urls", [])

            # 🟢 NEW: Extract Arena ID from SQS
            arena_id = payload.get("arena_id")

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
            requires_visuals = False # Default
            
            if connection_id:
                try:
                    # 🔹 ROUTER CALL: Get category, creative phrases, AND intent
                    routing_result = semantic_router.determine_category(message)
                    
                    category_key = routing_result.get("category", "general")
                    loading_phrases = routing_result.get("loading_phrases", []) 
                    source_type = routing_result.get("source", "unknown")
                    intent = routing_result.get("intent", "chat") 
                    requires_visuals = routing_result.get("requires_visuals", False) 
                    
                    # 🔹 DETERMINE CLIENT ACTION
                    client_action = None
                    if intent == "quiz":
                        client_action = "OPEN_QUIZ_PANEL"

                    status_payload = json.dumps({
                        "action": "status_update",
                        "category": category_key, 
                        "loading_phrases": loading_phrases,
                        "source": source_type,
                        "client_row_id": client_row_id,
                        "client_action": client_action,
                        "requires_visuals": requires_visuals,
                        "intent": intent  
                    })
                    
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=status_payload
                    )
                    
                    log_event("visual_feedback_sent", {
                        "user_id": user_id, 
                        "category": category_key,
                        "intent": intent,
                        "requires_visuals": requires_visuals,
                        "client_action": client_action,
                        "phrases_count": len(loading_phrases),
                        "source": source_type,
                        "mode": ai_mode,
                        "arena_id": arena_id # Log this
                    })

                except Exception as e:
                    # Don't fail the whole process if just the status update fails
                    log_event("ws_status_send_failed", {"user_id": user_id}, level="warning", error=e)

            # --- 3. Get the AI response (Heavy Processing) ---
            
            ai_reply, conversation_id, assistant_timestamp, meta_payload = get_ai_response(
                message=message,
                user_id=user_id,
                name=name,
                email=email,
                page=page,
                conversation_id=conv_id_in,
                image_urls=image_urls,
                pdf_urls=pdf_urls,
                mode=ai_mode,
                intent=intent,
                requires_visuals=requires_visuals, 
                stream_manager=stream_manager,
                arena_id=arena_id  # 🟢 NEW: Pass Arena ID to the brain
            )

            # --- 4. Send Final Reply ---
            if connection_id:
                try:
                    # A. Send Standard Text Reply (The Chat Bubble + Inline Metadata)
                    response_payload = json.dumps({
                        "action": "ai_reply",
                        "ai_reply": ai_reply,
                        "conversation_id": conversation_id,
                        "client_row_id": client_row_id,
                        "timestamp": assistant_timestamp,
                        "metadata": meta_payload 
                    })
                    
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=response_payload
                    )

                    # B. Send Structured Data Update (ONLY if it's Quiz or Rich Chat)
                    if meta_payload:
                        action_type = None

                        if meta_payload.get("type") == "rich_chat":
                            action_type = "rich_content_update"
                        elif meta_payload.get("quiz_mode") or meta_payload.get("questions"):
                            # Only trigger quiz update if actual quiz data is present
                            action_type = "quiz_data_update"

                        if action_type:
                            data_payload = json.dumps({
                                "action": action_type,
                                "data": meta_payload,
                                "conversation_id": conversation_id
                            })
                            
                            api_gateway_client.post_to_connection(
                                ConnectionId=connection_id,
                                Data=data_payload
                            )
                            log_event("rich_data_pushed_to_client", {
                                "type": action_type, 
                                "conversation_id": conversation_id
                            })

                    log_event("ai_worker_response_sent", {
                        "user_id": user_id, 
                        "connection_id": connection_id,
                        "client_row_id": client_row_id,
                        "timestamp": assistant_timestamp,
                        "has_meta_payload": bool(meta_payload)
                    })

                except api_gateway_client.exceptions.GoneException:
                    log_event("ws_send_failed_gone", {"user_id": user_id, "connection_id": connection_id}, level="warning")
                except Exception as e:
                    log_event("ws_send_failed_exception", {"user_id": user_id}, level="error", error=e)
            else:
                log_event("ws_connection_not_found", {"user_id": user_id}, level="warning")

        except Exception as e:
            # SOFT LANDING: Quota / Billing Error Handling (429)
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "insufficient" in error_str:
                log_event("ai_quota_exceeded_handled", {"user_id": user_id, "error": str(e)}, level="warning")
                
                # The Iconic Fallback Phrase
                fallback_msg = "**Señal nula. Vacío de sistema. Intenta luego.**"
                
                # Send the "Soft Landing" message to the user
                if connection_id:
                    try:
                        err_payload = json.dumps({
                            "action": "ai_reply",
                            "ai_reply": fallback_msg,
                            "conversation_id": conv_id_in,
                            "client_row_id": client_row_id,
                            "timestamp": "", 
                            "metadata": None
                        })
                        api_gateway_client.post_to_connection(
                            ConnectionId=connection_id,
                            Data=err_payload
                        )
                    except Exception as inner_e:
                        log_event("failed_to_send_error_fallback", {"error": str(inner_e)}, level="error")
                
                # IMPORTANT: Do NOT raise 'e'. Return normally to mark the SQS message as processed.
                continue 
            
            # --- For all other errors, behave normally (Log & Crash/Retry) ---
            log_event("ai_worker_failed", { "record_id": record.get("messageId") }, level="error", error=e)
            raise e

    return {"status": "ok", "processed_records": len(records)}