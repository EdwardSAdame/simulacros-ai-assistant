# src/lambda_chat_handler.py
import json
import logging
import boto3
import os
import uuid

from src.utils.logging_utils import log_event, set_invocation_context
from src.services.purchase_service import is_user_paid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs')
QUEUE_URL = os.environ.get('SQS_QUEUE_URL') 

def _none_if_empty(val):
    if val is None: return None
    if isinstance(val, str) and val.strip() == "": return None
    return val

def lambda_handler(event, context):
    set_invocation_context(context)

    try:
        log_event("lambda_invocation", {"source": "RomaChatHandler", "has_body": "body" in (event or {})})
        
        body_str = event.get("body", "{}")
        if not body_str:
            body_str = "{}"
        body = json.loads(body_str)

        meta = body.get("meta", {})
        
        audio_duration = body.get("audioDurationSeconds") if body.get("audioDurationSeconds") is not None else meta.get("audioDurationSeconds")
        sts_in_text = body.get("stsInputText") if body.get("stsInputText") is not None else meta.get("stsInputText")
        sts_in_audio = body.get("stsInputAudio") if body.get("stsInputAudio") is not None else meta.get("stsInputAudio")
        sts_out_text = body.get("stsOutputText") if body.get("stsOutputText") is not None else meta.get("stsOutputText")
        sts_out_audio = body.get("stsOutputAudio") if body.get("stsOutputAudio") is not None else meta.get("stsOutputAudio")

        message = body.get("message") or body.get("text") or meta.get("text")
        media_items = meta.get("media") or body.get("media", [])
        image_urls = meta.get("imageUrls") or body.get("imageUrls", [])
        pdf_urls = meta.get("pdfUrls") or body.get("pdfUrls", [])
        
        arena_id = meta.get("arenaId") or body.get("arenaId")
        
        # 🟢 UPDATED: Extract exam_id from root body OR meta
        exam_id = body.get("examId") or meta.get("examId") 
        
        is_hidden_flag = body.get("is_hidden") or meta.get("is_hidden", False)
        is_hidden_magic = isinstance(message, str) and message.strip().startswith("[CONTEXTO INTERNO:")
        is_hidden = is_hidden_flag or is_hidden_magic
        
        user_id = body.get("userId") or meta.get("debugClient", {}).get("clientUserId")
        name = body.get("name") or meta.get("name") or meta.get("debugClient", {}).get("clientName")
        email = body.get("email") or meta.get("debugClient", {}).get("clientEmail")
        page = body.get("page") or meta.get("page")
        
        conversation_id_in = body.get("conversationId") or meta.get("conversationId")
        client_row_id = body.get("clientRowId") or meta.get("clientRowId")
        
        ai_mode = body.get("mode") or meta.get("mode", "omega")

        if not conversation_id_in:
            conversation_id_in = str(uuid.uuid4())

        user_id = user_id or "anonymous"
        name = name if isinstance(name, str) else (name or "")
        email = _none_if_empty(email)
        page = page or "/"
        
        if not isinstance(image_urls, list): image_urls = []
        if not isinstance(pdf_urls, list): pdf_urls = []
        if not isinstance(media_items, list): media_items = []

        # Prevent non-paid users from forcing alpha mode via API manipulation
        if ai_mode == "alpha":
            is_paid = is_user_paid(user_id)
            if not is_paid:
                log_event("unauthorized_mode_access", {"user_id": user_id, "requested_mode": "alpha"}, level="warning")
                ai_mode = "omega" # Force fallback to omega

        if not message and not image_urls and not pdf_urls and not media_items and audio_duration is None and sts_in_text is None and sts_in_audio is None:
            log_event("input_validation_failed", {"reason": "Missing message or media"}, level="warning")
            return response(400, {"error": "Missing message or media"})

        payload = {
            "message": message,
            "user_id": user_id,
            "name": name,
            "email": email,
            "page": page,
            "conversation_id": conversation_id_in, 
            "image_urls": image_urls,
            "pdf_urls": pdf_urls,
            "media_items": media_items, 
            "client_row_id": client_row_id,
            "mode": ai_mode,
            "arena_id": arena_id,
            "exam_id": exam_id, 
            "is_hidden": is_hidden,
            
            "audioDurationSeconds": audio_duration,
            "stsInputText": sts_in_text,
            "stsInputAudio": sts_in_audio,
            "stsOutputText": sts_out_text,
            "stsOutputAudio": sts_out_audio
        }

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(payload)
        )

        log_event("message_queued_for_ai_processing", {
            "user_id": user_id,
            "conversation_id": conversation_id_in,
            "mode": ai_mode,
            "has_media_items": bool(media_items),
            "arena_id": arena_id,
            "exam_id": exam_id,
            "is_hidden": is_hidden,
            "has_stt_telemetry": audio_duration is not None,
            "has_sts_telemetry": sts_in_text is not None or sts_in_audio is not None
        })

        return response(202, {"status": "accepted", "message": "Request is being processed."})

    except Exception as e:
        log_event("lambda_exception", {"source": "RomaChatHandler"}, level="error", error=e)
        return response(500, {"error": "Internal error"})

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }