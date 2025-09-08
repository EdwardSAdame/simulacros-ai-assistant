# src/lambda_chat_handler.py
import json
import logging
from src.services.chat_service import get_ai_response
from src.utils.logging_utils import log_event, set_invocation_context  # 👈 add context hook

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _none_if_empty(val):
    """Return None for empty strings/whitespace; pass through other values."""
    if val is None:
        return None
    if isinstance(val, str) and val.strip() == "":
        return None
    return val


def lambda_handler(event, context):
    # Attach AWS context to all subsequent logs (function, request_id, etc.)
    set_invocation_context(context)

    try:
        # Log raw event (lightweight)
        log_event("lambda_invocation", {
            "source": "RomaChatHandler",
            "has_body": "body" in (event or {}),
        })

        # Parse request body
        body = json.loads(event.get("body", "{}"))

        # ---- Raw inputs from client ----
        message     = body.get("message")                # Optional text
        image_urls  = body.get("imageUrls", [])          # Optional list of image URLs
        user_id     = body.get("userId")                 # Null/None for guests
        name        = body.get("name")
        email       = body.get("email")
        page        = body.get("page")
        thread_id   = body.get("threadId")               # Optional thread reuse
        conversation_id_in = body.get("conversationId")  # Optional conversation reuse

        # ---- Normalize / sanitize ----
        user_id = user_id or "anonymous"
        name = name if isinstance(name, str) else (name or "")
        email = _none_if_empty(email)  # '' -> None so we can omit Email in Dynamo
        page = page or "/"
        if not isinstance(image_urls, list):
            image_urls = []

        # Validate input: require at least message or images
        if not message and not image_urls:
            log_event("input_validation_failed", {
                "reason": "Missing message or imageUrls",
                "has_message": bool(message),
                "image_count": len(image_urls or []),
            }, level="warning")
            return response(400, {"error": "Missing message or imageUrls"})

        # Call service layer
        ai_reply, new_thread_id, conversation_id = get_ai_response(
            message=message,
            user_id=user_id,
            name=name,
            email=email,                    # already normalized
            page=page,
            thread_id=thread_id,
            conversation_id=conversation_id_in,
            image_urls=image_urls
        )

        log_event("chat_response_success", {
            "user_id": user_id,
            "thread_id": new_thread_id,
            "conversation_id": conversation_id,
            "reply_snippet": (ai_reply or "")[:100]
        })

        return response(200, {
            "reply": ai_reply,
            "threadId": new_thread_id,
            "conversationId": conversation_id
        })

    except Exception as e:
        # Capture stack trace in CloudWatch (via logging_utils)
        log_event("lambda_exception", {
            "source": "RomaChatHandler"
        }, level="error", error=e)
        return response(500, {"error": "Internal error"})


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"  # Allow Wix to call this from browser
        },
        "body": json.dumps(body)
    }
