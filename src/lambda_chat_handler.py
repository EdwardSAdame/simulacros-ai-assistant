import json
import logging
from src.services.chat_service import get_ai_response
from src.utils.logging_utils import log_event  # ✅ NEW: structured logger

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Log raw event
        log_event("lambda_invocation", {
            "source": "RomaChatHandler",
            "event": event
        })

        # Parse request body
        body = json.loads(event.get("body", "{}"))

        message = body.get("message")              # Optional text
        image_urls = body.get("imageUrls", [])     # Optional list of image URLs
        audio_url = body.get("audioUrl")           # Optional single audio URL
        user_id = body.get("userId")               # Null for guests
        name = body.get("name")
        email = body.get("email")
        page = body.get("page")
        thread_id = body.get("threadId")           # Optional thread reuse

        # Validate input: at least one of the three must be present
        if not message and not image_urls and not audio_url:
            log_event("input_validation_failed", {
                "message": message,
                "image_urls": image_urls,
                "audio_url": audio_url
            }, level="warning")
            return response(400, {"error": "Missing message, imageUrls, or audioUrl"})

        # Call service layer
        ai_reply, new_thread_id, conversation_id = get_ai_response(
            message=message,
            user_id=user_id,
            name=name,
            email=email,
            page=page,
            thread_id=thread_id,
            image_urls=image_urls,
            audio_url=audio_url
        )

        log_event("chat_response_success", {
            "user_id": user_id,
            "thread_id": new_thread_id,
            "conversation_id": conversation_id,
            "reply_snippet": ai_reply[:100]
        })

        return response(200, {
            "reply": ai_reply,
            "threadId": new_thread_id,
            "conversationId": conversation_id
        })

    except Exception as e:
        log_event("lambda_exception", {
            "error": str(e)
        }, level="error")
        return response(500, {"error": str(e)})

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"  # Allow Wix to call this from browser
        },
        "body": json.dumps(body)
    }
