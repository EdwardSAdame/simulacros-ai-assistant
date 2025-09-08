# src/lambda_dlq_reprocessor.py
import json
import logging
from src.services.chat_service import get_ai_response
from src.utils.logging_utils import log_event  # ✅ Structured logger

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Triggered by SQS DLQ messages. Reprocesses failed chatbot requests.
    """

    log_event("dlq_event_received", {
        "record_count": len(event.get("Records", []))
    })

    for record in event.get("Records", []):
        try:
            # Body contains the original event as JSON
            body = json.loads(record["body"])

            message     = body.get("message")
            image_urls  = body.get("imageUrls", [])
            user_id     = body.get("userId")
            name        = body.get("name")
            email       = body.get("email")
            page        = body.get("page")
            thread_id   = body.get("threadId")
            conv_id_in  = body.get("conversationId")

            # Validate: require at least text or images
            if not message and not image_urls:
                log_event("dlq_skipped_message", {
                    "reason": "No valid content (missing message and imageUrls)",
                    "payload": body
                }, level="warning")
                continue

            # Retry processing the failed message
            ai_reply, new_thread_id, conversation_id = get_ai_response(
                message=message,
                user_id=user_id,
                name=name,
                email=email,
                page=page,
                thread_id=thread_id,
                conversation_id=conv_id_in,
                image_urls=image_urls
            )

            log_event("dlq_reprocess_success", {
                "user_id": user_id,
                "page": page,
                "conversation_id": conversation_id,
                "reply_snippet": (ai_reply or "")[:100]
            })

        except Exception as e:
            log_event("dlq_reprocess_failed", {
                "error": str(e),
                "record": record.get("body")
            }, level="error")
