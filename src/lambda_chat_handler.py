# src/lambda_chat_handler.py
import json
import logging
import boto3  # <-- Added boto3 to interact with AWS services
import os     # <-- Added os to get environment variables

from src.utils.logging_utils import log_event, set_invocation_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- NEW: Initialize SQS client ---
sqs = boto3.client('sqs')
QUEUE_URL = os.environ.get('SQS_QUEUE_URL') # We will set this environment variable in the Lambda config

def _none_if_empty(val):
    if val is None: return None
    if isinstance(val, str) and val.strip() == "": return None
    return val

def lambda_handler(event, context):
    set_invocation_context(context)

    try:
        log_event("lambda_invocation", {"source": "RomaChatHandler", "has_body": "body" in (event or {})})
        body = json.loads(event.get("body", "{}"))

        # ---- Raw inputs from client (this part remains the same) ----
        message = body.get("message")
        image_urls = body.get("imageUrls", [])
        user_id = body.get("userId")
        name = body.get("name")
        email = body.get("email")
        page = body.get("page")
        conversation_id_in = body.get("conversationId")

        # ---- Normalize / sanitize (this part remains the same) ----
        user_id = user_id or "anonymous"
        name = name if isinstance(name, str) else (name or "")
        email = _none_if_empty(email)
        page = page or "/"
        if not isinstance(image_urls, list):
            image_urls = []

        # ---- Input Validation (this part remains the same) ----
        if not message and not image_urls:
            log_event("input_validation_failed", {"reason": "Missing message or imageUrls"}, level="warning")
            return response(400, {"error": "Missing message or imageUrls"})

        # --- MODIFIED: Instead of calling the AI service, send to SQS ---
        # 1. Construct the message payload
        payload = {
            "message": message,
            "user_id": user_id,
            "name": name,
            "email": email,
            "page": page,
            "conversation_id": conversation_id_in,
            "image_urls": image_urls
        }

        # 2. Send the message to the SQS queue
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(payload)
        )

        log_event("message_queued_for_ai_processing", {
            "user_id": user_id,
            "conversation_id": conversation_id_in
        })

        # 3. Return an immediate success response to the user
        # This makes the frontend feel instantaneous.
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