# src/lambda_ai_worker_handler.py
import json
import logging
import boto3
import os
from src.services.chat_service import get_ai_response
from src.storage.ws_connections_table import WsConnectionsTable
from src.utils.logging_utils import log_event, set_invocation_context

# IMPORT: The Stream Manager
from src.streaming.stream_manager import StreamManager

# IMPORT: The Hybrid Semantic Router
from src.services.semantic_router import semantic_router

# 🟢 NEW: Import Token Usage Service
from src.services.token_usage_service import TokenUsageService

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
    set_invocation_context(context)

    if not WEBSOCKET_API_ENDPOINT:
        log_event("ai_worker_config_error", {"reason": "WEBSOCKET_API_ENDPOINT is not set"}, level="error")
        raise ValueError("WEBSOCKET_API_ENDPOINT environment variable not set.")
        
    api_gateway_client = get_api_gateway_management_client(WEBSOCKET_API_ENDPOINT)

    records = (event or {}).get("Records", [])
    log_event("ai_worker_invocation", {"record_count": len(records)})

    for record in records:
        user_id = None
        connection_id = None
        conv_id_in = None
        client_row_id = None
        
        try:
            body_raw = record.get("body", "{}")
            payload = json.loads(body_raw)

            # --- Extract data from the payload ---
            message = payload.get("message")
            user_id = payload.get("user_id")
            conv_id_in = payload.get("conversation_id")
            
            # 🟢 Extract Telemetry Data
            audio_duration = payload.get("audioDurationSeconds")
            
            # 🟢 Extract Split STS Data
            sts_in_text = payload.get("stsInputText")
            sts_in_audio = payload.get("stsInputAudio")
            sts_out_text = payload.get("stsOutputText", 0)
            sts_out_audio = payload.get("stsOutputAudio", 0)

            # 🟢 INTERCEPT SPEECH-TO-TEXT (Time-based)
            if audio_duration is not None and int(audio_duration) > 0:
                logger.info(f"Intercepted STT Telemetry: {audio_duration} seconds for user {user_id}")
                svc = TokenUsageService()
                svc.log_token_usage(
                    user_id=user_id or "anonymous",
                    session_id=conv_id_in or "unknown",
                    model="speech-to-text",
                    input_tokens=int(audio_duration), 
                    output_tokens=0,
                    total_tokens=int(audio_duration)
                )
                continue # Skip the rest of the worker loop!

            # 🟢 INTERCEPT SPEECH-TO-SPEECH (Split Text vs Audio)
            if sts_in_text is not None or sts_in_audio is not None:
                svc = TokenUsageService()
                session_str = conv_id_in or "unknown"
                uid_str = user_id or "anonymous"
                
                # 1. Log the Text Context
                if int(sts_in_text or 0) > 0 or int(sts_out_text or 0) > 0:
                    svc.log_token_usage(
                        user_id=uid_str, session_id=session_str,
                        model="sts-text", input_tokens=int(sts_in_text or 0), 
                        output_tokens=int(sts_out_text or 0), 
                        total_tokens=int(sts_in_text or 0) + int(sts_out_text or 0)
                    )
                
                # 2. Log the Audio Context
                if int(sts_in_audio or 0) > 0 or int(sts_out_audio or 0) > 0:
                    svc.log_token_usage(
                        user_id=uid_str, session_id=session_str,
                        model="sts-audio", input_tokens=int(sts_in_audio or 0), 
                        output_tokens=int(sts_out_audio or 0), 
                        total_tokens=int(sts_in_audio or 0) + int(sts_out_audio or 0)
                    )
                
                logger.info(f"Intercepted Split STS Telemetry for {uid_str}. Text({sts_in_text}/{sts_out_text}), Audio({sts_in_audio}/{sts_out_audio})")
                continue # Skip the rest of the worker loop!

            image_urls = payload.get("image_urls", [])
            pdf_urls = payload.get("pdf_urls", [])
            media_items = payload.get("media_items", [])
            arena_id = payload.get("arena_id")
            is_hidden = payload.get("is_hidden", False)
            name = payload.get("name")
            email = payload.get("email")
            page = payload.get("page")
            client_row_id = payload.get("client_row_id")
            ai_mode = payload.get("mode", "omega")

            # --- 1. Get Connection ID ---
            connection_id = ws_connections_table.get_connection_id(user_id)

            stream_manager = None
            if connection_id:
                stream_manager = StreamManager(connection_id, api_gateway_client)

            # --- 2. Send Visual Feedback ---
            intent = "chat" 
            requires_visuals = False 
            category_key = "general" 
            num_questions = 5 
            
            if connection_id and not is_hidden:
                try:
                    routing_result = semantic_router.determine_category(
                        text=message, 
                        user_id=user_id, 
                        session_id=conv_id_in
                    )
                    
                    category_key = routing_result.get("category", "general")
                    loading_phrases = routing_result.get("loading_phrases", []) 
                    source_type = routing_result.get("source", "unknown")
                    
                    raw_intent = routing_result.get("intent", "chat")
                    intent = str(raw_intent).strip().lower()
                    
                    requires_visuals = routing_result.get("requires_visuals", False) 
                    num_questions = routing_result.get("num_questions", 5)
                    
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
                        "num_questions": num_questions,
                        "client_action": client_action,
                        "phrases_count": len(loading_phrases),
                        "source": source_type,
                        "mode": ai_mode,
                        "arena_id": arena_id 
                    })

                except Exception as e:
                    log_event("ws_status_send_failed", {"user_id": user_id}, level="warning", error=e)

            # --- 3. Get the AI response ---
            ai_reply, conversation_id, assistant_timestamp, meta_payload = get_ai_response(
                message=message,
                user_id=user_id,
                name=name,
                email=email,
                page=page,
                conversation_id=conv_id_in,
                image_urls=image_urls,
                pdf_urls=pdf_urls,
                media_items=media_items, 
                mode=ai_mode,
                intent=intent,
                category=category_key, 
                requires_visuals=requires_visuals, 
                stream_manager=stream_manager,
                arena_id=arena_id,
                is_hidden=is_hidden, 
                num_questions=num_questions
            )

            # --- 4. Send Final Reply ---
            if connection_id and not is_hidden:
                try:
                    response_payload = json.dumps({
                        "action": "ai_reply",
                        "ai_reply": ai_reply,
                        "conversation_id": conversation_id,
                        "client_row_id": client_row_id,
                        "timestamp": assistant_timestamp,
                        "metadata": meta_payload 
                    }, default=str)
                    
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=response_payload
                    )

                    if meta_payload:
                        action_type = None
                        if meta_payload.get("type") == "rich_chat":
                            action_type = "rich_content_update"
                        elif meta_payload.get("quiz_mode") or meta_payload.get("questions"):
                            action_type = "quiz_data_update"

                        if action_type:
                            data_payload = json.dumps({
                                "action": action_type,
                                "data": meta_payload,
                                "conversation_id": conversation_id
                            }, default=str)
                            
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
            elif not connection_id:
                log_event("ws_connection_not_found", {"user_id": user_id}, level="warning")

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "insufficient" in error_str:
                log_event("ai_quota_exceeded_handled", {"user_id": user_id, "error": str(e)}, level="warning")
                fallback_msg = "**Señal nula. Vacío de sistema. Intenta luego.**"
                
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
                
                continue 
            
            log_event("ai_worker_failed", { "record_id": record.get("messageId") }, level="error", error=e)
            raise e

    return {"status": "ok", "processed_records": len(records)}