# src/lambda_chat_handler.py
import json
import logging
import boto3
import os
import uuid  # 🟢 ADDED: Required for generating IDs

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
        body = json.loads(event.get("body", "{}"))

        # ---- Raw inputs from client ----
        message = body.get("message")
        image_urls = body.get("imageUrls", [])
        # 🟢 NEW: Extract PDF URLs from the request
        pdf_urls = body.get("pdfUrls", [])

        user_id = body.get("userId")
        name = body.get("name")
        email = body.get("email")
        page = body.get("page")
        
        conversation_id_in = body.get("conversationId")
        
        client_row_id = body.get("clientRowId")
        
        # 🔹 Extract the 'mode' (Omega vs Alpha)
        ai_mode = body.get("mode", "omega")

        # 🟢 IDEMPOTENCY FIX: 
        # If client didn't send a conversationId (New Chat), generate it NOW.
        # This ensures that if SQS retries this message, the worker keeps using this SAME ID.
        if not conversation_id_in:
            conversation_id_in = str(uuid.uuid4())

        # ---- Normalize / sanitize ----
        user_id = user_id or "anonymous"
        name = name if isinstance(name, str) else (name or "")
        email = _none_if_empty(email)
        page = page or "/"
        
        if not isinstance(image_urls, list):
            image_urls = []
            
        # 🟢 NEW: Validation for PDF list
        if not isinstance(pdf_urls, list): 
            pdf_urls = []

        # ---- Input Validation ----
        # 🟢 NEW: Allow request if it has message OR images OR pdfs
        if not message and not image_urls and not pdf_urls:
            log_event("input_validation_failed", {"reason": "Missing message or media"}, level="warning")
            return response(400, {"error": "Missing message or media"})

        # --- Construct Payload for SQS ---
        payload = {
            "message": message,
            "user_id": user_id,
            "name": name,
            "email": email,
            "page": page,
            "conversation_id": conversation_id_in, # 🟢 Now guaranteed to be populated
            "image_urls": image_urls,
            "pdf_urls": pdf_urls, # 🟢 NEW: Pass to Worker
            "client_row_id": client_row_id,
            
            # 🔹 Pass the mode to the worker
            "mode": ai_mode
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
            "has_pdfs": bool(pdf_urls)
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