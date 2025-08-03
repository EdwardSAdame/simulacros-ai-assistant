import json
import logging
from src.services.chat_service import get_ai_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Triggered by SQS DLQ messages. Reprocesses failed chatbot requests.
    """
    logger.info("🔁 DLQ event received: %s", json.dumps(event))

    for record in event.get("Records", []):
        try:
            # Body contains the original event as JSON
            body = json.loads(record["body"])

            message = body.get("message")
            image_urls = body.get("imageUrls", [])
            audio_url = body.get("audioUrl")
            user_id = body.get("userId")
            name = body.get("name")
            email = body.get("email")
            page = body.get("page")
            thread_id = body.get("threadId")

            if not message and not image_urls and not audio_url:
                logger.warning("🟡 Skipping invalid DLQ message: %s", record["body"])
                continue

            # Retry processing the failed message
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

            logger.info("✅ Reprocessed DLQ message successfully. Reply: %s", ai_reply)

        except Exception as e:
            logger.exception("❌ Failed to reprocess DLQ message: %s", record["body"])
