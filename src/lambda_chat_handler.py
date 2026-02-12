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
        # 1. Parse Body
        body_str = event.get("body", "{}")
        if not body_str:
            body_str = "{}"
        body = json.loads(body_str)

        # 🔍 DEBUG LOG 1: Print the Raw Meta Object
        # We need to see if the frontend is actually sending the 'meta' wrapper
        meta = body.get("meta", {})
        print(f"🔍 [DEBUG] RAW META RECEIVED: {json.dumps(meta)}")

        # 3. Extract Data
        message = body.get("message") or body.get("text") or meta.get("text")
        
        # 🔍 DEBUG LOG 2: Extract Media specifically
        # We check both locations (meta.media and body.media)
        media_from_meta = meta.get("media")
        media_from_body = body.get("media")
        
        print(f"🔍 [DEBUG] Media in Meta: {type(media_from_meta)} - Count: {len(media_from_meta) if isinstance(media_from_meta, list) else 'N/A'}")
        print(f"🔍 [DEBUG] Media in Body: {type(media_from_body)} - Count: {len(media_from_body) if isinstance(media_from_body, list) else 'N/A'}")

        # Consolidate logic
        media_items = media_from_meta or media_from_body or []
        
        if len(media_items) > 0:
            print(f"🔍 [DEBUG] First Item content: {media_items[0]}")
        else:
            print("🔍 [DEBUG] No media items found in extraction.")

        # Legacy Fallbacks
        image_urls = meta.get("imageUrls") or body.get("imageUrls", [])
        pdf_urls = meta.get("pdfUrls") or body.get("pdfUrls", [])
        
        # Extract Context
        arena_id = meta.get("arenaId") or body.get("arenaId")
        
        # Extract Identity
        user_id = body.get("userId") or meta.get("debugClient", {}).get("clientUserId")
        name = body.get("name") or meta.get("name") or meta.get("debugClient", {}).get("clientName")
        email = body.get("email") or meta.get("debugClient", {}).get("clientEmail")
        page = body.get("page") or meta.get("page")
        
        conversation_id_in = body.get("conversationId") or meta.get("conversationId")
        client_row_id = body.get("clientRowId") or meta.get("clientRowId")
        ai_mode = body.get("mode") or meta.get("mode", "omega")

        if not conversation_id_in:
            conversation_id_in = str(uuid.uuid4())

        # Normalize
        user_id = user_id or "anonymous"
        name = name if isinstance(name, str) else (name or "")
        email = _none_if_empty(email)
        page = page or "/"
        
        if not isinstance(media_items, list): media_items = []

        # ---- Input Validation ----
        if not message and not image_urls and not pdf_urls and not media_items:
            print("🔍 [DEBUG] Input validation failed. Nothing to process.")
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
            "image_urls": image_urls,
            "pdf_urls": pdf_urls,
            "media_items": media_items, # Passing to Worker
            "client_row_id": client_row_id,
            "mode": ai_mode,
            "arena_id": arena_id 
        }

        # 🔍 DEBUG LOG 3: Confirm Payload before sending to SQS
        print(f"🔍 [DEBUG] Sending to SQS Queue ({QUEUE_URL}). Payload media_items count: {len(payload['media_items'])}")

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(payload)
        )

        return response(202, {"status": "accepted", "message": "Request is being processed."})

    except Exception as e:
        print(f"🔍 [DEBUG] CRITICAL ERROR: {str(e)}")
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