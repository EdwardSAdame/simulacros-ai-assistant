import json
import logging
from src.services.chat_service import get_ai_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        logger.info("Event received: %s", event)

        # Parse request body
        body = json.loads(event.get("body", "{}"))

        message = body.get("message")          # User input (text)
        file_url = body.get("fileUrl")         # Optional (audio/image)
        user_id = body.get("userId")           # null for guests
        page = body.get("page")                # Page path (e.g., "/simulacro-icfes/ingles")
        thread_id = body.get("threadId")       # null for new thread

        if not message and not file_url:
            return response(400, {"error": "Missing message or fileUrl"})

        # Get AI response
        ai_reply, new_thread_id = get_ai_response(
            message=message,
            file_url=file_url,
            user_id=user_id,
            page=page,
            thread_id=thread_id
        )

        return response(200, {
            "reply": ai_reply,
            "threadId": new_thread_id
        })

    except Exception as e:
        logger.exception("Error in lambda_handler")
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
