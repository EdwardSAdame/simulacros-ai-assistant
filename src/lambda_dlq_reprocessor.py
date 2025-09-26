# src/lambda_dlq_reprocessor.py
import json
import logging
from src.services.chat_service import get_ai_response
from src.utils.logging_utils import log_event, set_invocation_context  # 👈 add context hook

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Triggered by SQS DLQ messages. Reprocesses failed chatbot requests.
    """
    # Attach AWS context to all logs (function name, request_id, etc.)
    set_invocation_context(context)

    records = (event or {}).get("Records", []) or []
    log_event("dlq_event_received", {"record_count": len(records)})

    for record in records:
        try:
            # Body contains the original event as JSON
            body_raw = record.get("body", "{}")
            body = json.loads(body_raw)

            message     = body.get("message")
            image_urls  = body.get("imageUrls", [])
            user_id     = body.get("userId")
            name        = body.get("name")
            email       = body.get("email")
            page        = body.get("page")
            conv_id_in  = body.get("conversationId")

            # Validate: require at least text or images
            if not message and not image_urls:
                log_event("dlq_skipped_message", {
                    "reason": "No valid content (missing message and imageUrls)",
                    "has_message": bool(message),
                    "image_count": len(image_urls or [])
                }, level="warning")
                continue

            # Retry processing the failed message
            ai_reply, conversation_id = get_ai_response(
                message=message,
                user_id=user_id,
                name=name,
                email=email,
                page=page,
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
            # Capture stack trace via logging_utils
            log_event("dlq_reprocess_failed", {
                "record_id": record.get("messageId"),
                "approx_receive_count": record.get("attributes", {}).get("ApproximateReceiveCount")
            }, level="error", error=e)

    # SQS events don’t require a specific return value
    return {"ok": True, "processed": len(records)}
