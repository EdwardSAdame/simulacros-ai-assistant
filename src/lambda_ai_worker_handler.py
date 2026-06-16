# src/lambda_ai_worker_handler.py
import json
import logging
import boto3
import os
from datetime import datetime, timezone

from src.services.orchestrator_service import OrchestratorService
from src.storage.ws_connections_table import WsConnectionsTable
from src.utils.logging_utils import log_event, set_invocation_context
from src.streaming.stream_manager import StreamManager
from src.services.semantic_router import semantic_router
from src.services.token_usage_service import TokenUsageService
from src.services.context_resolution import determine_exam_context
from src.storage.conversations_table import get_conversation_metadata

from src.services.history_service import build_history_list 

# For Audio FinOps
from src.services.audio_usage_service import AudioUsageService
from src.config.model_config import get_model_config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ws_connections_table = WsConnectionsTable()
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT')

def get_api_gateway_management_client(endpoint_url):
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
        connection_ids = []  
        conv_id_in = None
        client_row_id = None
        
        try:
            body_raw = record.get("body", "{}")
            payload = json.loads(body_raw)

            message = payload.get("message", "")
            user_id = payload.get("user_id")
            conv_id_in = payload.get("conversation_id")
            
            ai_mode = payload.get("mode", "omega")
            
            audio_duration = payload.get("audioDurationSeconds")
            sts_in_text = payload.get("stsInputText")
            sts_in_audio = payload.get("stsInputAudio")
            sts_out_text = payload.get("stsOutputText", 0)
            sts_out_audio = payload.get("stsOutputAudio", 0)

            # THE BULLETPROOF FAILSAFE: Intercept exactly by message text
            if message in ["[AUDIO_TELEMETRY]", "[STS_TELEMETRY]"]:
                logger.info(f"Intercepting Telemetry Ghost Message: {message} for user {user_id}")
                
                if message == "[AUDIO_TELEMETRY]" and audio_duration is not None and int(audio_duration) > 0:
                    cfg = get_model_config(ai_mode)
                    audio_svc = AudioUsageService()
                    audio_svc.log_audio_usage(
                        user_id=user_id or "anonymous", 
                        conversation_id=conv_id_in or "unknown", 
                        source="telemetry",                      
                        tier=ai_mode,                            
                        engine=cfg.audio_transcription_model,   
                        duration_seconds=int(audio_duration),
                        audio_type="speech-to-text"
                    )
                
                elif message == "[STS_TELEMETRY]":
                    svc = TokenUsageService()
                    session_str = conv_id_in or "unknown"
                    uid_str = user_id or "anonymous"
                    
                    cfg = get_model_config(ai_mode)
                    realtime_engine = getattr(cfg, 'realtime_model', 'gpt-4o-realtime')
                    
                    if (sts_in_text is not None and int(sts_in_text) > 0) or (sts_out_text is not None and int(sts_out_text) > 0):
                        svc.log_token_usage(
                            user_id=uid_str, 
                            conversation_id=session_str,         
                            source="telemetry-text",                  
                            tier=ai_mode,              
                            engine=realtime_engine,        
                            input_tokens=int(sts_in_text or 0), 
                            output_tokens=int(sts_out_text or 0), 
                            total_tokens=int(sts_in_text or 0) + int(sts_out_text or 0)
                        )
                    
                    if (sts_in_audio is not None and int(sts_in_audio) > 0) or (sts_out_audio is not None and int(sts_out_audio) > 0):
                        svc.log_token_usage(
                            user_id=uid_str, 
                            conversation_id=session_str,         
                            source="telemetry-audio",                  
                            tier=ai_mode,              
                            engine=realtime_engine,        
                            input_tokens=int(sts_in_audio or 0), 
                            output_tokens=int(sts_out_audio or 0), 
                            total_tokens=int(sts_in_audio or 0) + int(sts_out_audio or 0)
                        )
                
                continue 

            image_urls = payload.get("image_urls", [])
            pdf_urls = payload.get("pdf_urls", [])
            media_items = payload.get("media_items", [])
            arena_id = payload.get("arena_id")
            exam_id = payload.get("exam_id") # --- NEW: Extract exam_id from payload ---
            is_hidden = payload.get("is_hidden", False)
            name = payload.get("name")
            email = payload.get("email")
            page = payload.get("page")
            client_row_id = payload.get("client_row_id")

            connection_ids = ws_connections_table.get_connection_ids(user_id)

            stream_manager = None
            if connection_ids:
                stream_manager = StreamManager(connection_ids, api_gateway_client)

            intent = "chat" 
            requires_visuals = False 
            category_key = "general" 
            num_questions = 5 
            
            if connection_ids and not is_hidden:
                try:
                    persisted_exam_context = None
                    current_activity = "chat"
                    recent_history = [] 
                    if conv_id_in and user_id:
                        try:
                            recent_history = build_history_list(conv_id_in, max_user=2, max_assistant=2, include_system_logs=False)
                            existing_meta = get_conversation_metadata(user_id, conv_id_in)
                            if existing_meta:
                                persisted_exam_context = existing_meta.get("ExamContext")
                                current_activity = existing_meta.get("CurrentActivity", "chat")
                        except Exception as meta_e:
                            logger.warning(f"Could not fetch conversation metadata/history: {meta_e}")

                    current_exam_context = determine_exam_context(page, message, current_locked_context=persisted_exam_context)

                    routing_result = semantic_router.determine_category(
                        text=message, 
                        user_id=user_id, 
                        conversation_id=conv_id_in, 
                        exam_context=current_exam_context,
                        history=recent_history,
                        current_activity=current_activity 
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
                    elif intent == "mentalmap" or intent == "mind_map":
                        client_action = "OPEN_MENTAL_MAP_PANEL"

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
                    
                    for conn_id in connection_ids:
                        try:
                            api_gateway_client.post_to_connection(ConnectionId=conn_id, Data=status_payload)
                        except api_gateway_client.exceptions.GoneException:
                            pass
                        except Exception as inner_e:
                            logger.warning(f"Failed to send status to {conn_id}: {inner_e}")
                    
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
                        "arena_id": arena_id,
                        "exam_id": exam_id,
                        "exam_context": current_exam_context 
                    })

                except Exception as e:
                    log_event("ws_status_send_failed", {"user_id": user_id}, level="warning", error=e)

            ai_reply, conversation_id, assistant_timestamp, meta_payload = OrchestratorService.process_ai_request(
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
                exam_id=exam_id, # --- NEW: Pass exam_id to the Orchestrator ---
                is_hidden=is_hidden, 
                num_questions=num_questions
            )

            if connection_ids and not is_hidden:
                for conn_id in connection_ids:
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
                            ConnectionId=conn_id,
                            Data=response_payload
                        )

                        if meta_payload:
                            action_type = None
                            if meta_payload.get("type") == "rich_chat":
                                action_type = "rich_content_update"
                            elif meta_payload.get("quiz_mode") or meta_payload.get("questions"):
                                action_type = "quiz_data_update"
                            elif meta_payload.get("type") == "mindmap_data":
                                action_type = "mindmap_data_update"
                            elif meta_payload.get("type") == "flashcards_data":
                                action_type = "flashcards_data_update"

                            if action_type:
                                data_payload = json.dumps({
                                    "action": action_type,
                                    "data": meta_payload,
                                    "conversation_id": conversation_id
                                }, default=str)
                                
                                api_gateway_client.post_to_connection(
                                    ConnectionId=conn_id,
                                    Data=data_payload
                                )
                                log_event("rich_data_pushed_to_client", {
                                    "type": action_type, 
                                    "conversation_id": conversation_id
                                })

                    except api_gateway_client.exceptions.GoneException:
                        log_event("ws_send_failed_gone", {"user_id": user_id, "connection_id": conn_id}, level="warning")
                    except Exception as e:
                        log_event("ws_send_failed_exception", {"user_id": user_id, "connection_id": conn_id}, level="error", error=e)

            log_event("ai_worker_response_sent", {
                "user_id": user_id, 
                "connections_count": len(connection_ids),
                "client_row_id": client_row_id,
                "timestamp": assistant_timestamp,
                "has_meta_payload": bool(meta_payload)
            })

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "insufficient" in error_str:
                log_event("ai_quota_exceeded_handled", {"user_id": user_id, "error": str(e)}, level="warning")
                fallback_msg = "**Señal nula. Vacío de sistema. Intenta luego.**"
                
                if connection_ids:
                    for conn_id in connection_ids:
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
                                ConnectionId=conn_id,
                                Data=err_payload
                            )
                        except Exception as inner_e:
                            log_event("failed_to_send_error_fallback", {"error": str(inner_e)}, level="error")
                
                continue 
            
            log_event("ai_worker_failed", { "record_id": record.get("messageId") }, level="error", error=e)
            raise e

    return {"status": "ok", "processed_records": len(records)}