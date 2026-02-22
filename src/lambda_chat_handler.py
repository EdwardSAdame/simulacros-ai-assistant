# src/lambda_chat_handler.py
import json
import logging
import boto3
import os
import uuid

from src.utils.logging_utils import log_event, set_invocation_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Initialize SQS client ---
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
        
        # 1. Parse Body
        body_str = event.get("body", "{}")
        if not body_str:
            body_str = "{}"
        body = json.loads(body_str)

        # 2. Extract Meta Wrapper
        meta = body.get("meta", {})

        # 3. Extract Data
        message = body.get("message") or body.get("text") or meta.get("text")
        
        # Extract Structured Media (Check meta first, then body)
        media_items = meta.get("media") or body.get("media", [])
        
        # Legacy: Extract simple URL lists
        image_urls = meta.get("imageUrls") or body.get("imageUrls", [])
        pdf_urls = meta.get("pdfUrls") or body.get("pdfUrls", [])
        
        # Extract Context
        arena_id = meta.get("arenaId") or body.get("arenaId")
        
        #  BULLETPROOF FIX: Detect hidden context via magic string in case Velo drops the flag
        is_hidden_flag = body.get("is_hidden") or meta.get("is_hidden", False)
        is_hidden_magic = isinstance(message, str) and message.strip().startswith("[CONTEXTO INTERNO:")
        is_hidden = is_hidden_flag or is_hidden_magic
        
        # Extract Identity
        user_id = body.get("userId") or meta.get("debugClient", {}).get("clientUserId")
        name = body.get("name") or meta.get("name") or meta.get("debugClient", {}).get("clientName")
        email = body.get("email") or meta.get("debugClient", {}).get("clientEmail")
        page = body.get("page") or meta.get("page")
        
        conversation_id_in = body.get("conversationId") or meta.get("conversationId")
        client_row_id = body.get("clientRowId") or meta.get("clientRowId")
        
        # Extract Mode
        ai_mode = body.get("mode") or meta.get("mode", "omega")

        # Idempotency: Generate conversation ID if missing
        if not conversation_id_in:
            conversation_id_in = str(uuid.uuid4())

        # ---- Normalize / sanitize ----
        user_id = user_id or "anonymous"
        name = name if isinstance(name, str) else (name or "")
        email = _none_if_empty(email)
        page = page or "/"
        
        if not isinstance(image_urls, list): image_urls = []
        if not isinstance(pdf_urls, list): pdf_urls = []
        if not isinstance(media_items, list): media_items = []

        # ---- Input Validation ----
        if not message and not image_urls and not pdf_urls and not media_items:
            log_event("input_validation_failed", {"reason": "Missing message or media"}, level="warning")
            return response(400, {"error": "Missing message or media"})

        # --- Construct Payload for SQS ---
        payload = {
            "message": message,
            "user_id": user_id,
            "name": name,
            "email": email,
            "page": page,
            "conversation_id": conversation_id_in, 
            
            # Pass all media types to Worker
            "image_urls": image_urls,
            "pdf_urls": pdf_urls,
            "media_items": media_items, 
            
            "client_row_id": client_row_id,
            "mode": ai_mode,
            "arena_id": arena_id,
            
            #  Pass the guaranteed hidden flag to the worker
            "is_hidden": is_hidden
        }

        # Send the message to the SQS queue
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(payload)
        )

        log_event("message_queued_for_ai_processing", {
            "user_id": user_id,
            "conversation_id": conversation_id_in,
            "mode": ai_mode,
            "has_media_items": bool(media_items),
            "media_count": len(media_items),
            "arena_id": arena_id,
            "is_hidden": is_hidden 
        })

        # Return success
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