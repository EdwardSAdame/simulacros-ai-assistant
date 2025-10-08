# src/lambda_ai_worker_handler.py
import json
import logging
from src.services.chat_service import get_ai_response
from src.utils.logging_utils import log_event, set_invocation_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Triggered by SQS messages from RomaChatQueue.
    Processes the message payload to generate and save an AI response.
    """
    set_invocation_context(context)

    records = (event or {}).get("Records", [])
    log_event("ai_worker_invocation", {"record_count": len(records)})

    for record in records:
        try:
            # The 'body' of the SQS record contains the JSON payload from the first Lambda
            body_raw = record.get("body", "{}")
            payload = json.loads(body_raw)

            # --- Extract data from the payload ---
            message = payload.get("message")
            image_urls = payload.get("image_urls", [])
            user_id = payload.get("user_id")
            name = payload.get("name")
            email = payload.get("email")
            page = payload.get("page")
            conv_id_in = payload.get("conversation_id")

            # --- Call the existing chat service to get the AI response ---
            # This is the heavy lifting part that now runs asynchronously
            ai_reply, conversation_id = get_ai_response(
                message=message,
                user_id=user_id,
                name=name,
                email=email,
                page=page,
                conversation_id=conv_id_in,
                image_urls=image_urls
            )

            log_event("ai_worker_success", {
                "user_id": user_id,
                "page": page,
                "conversation_id": conversation_id,
                "reply_snippet": (ai_reply or "")[:100]
            })

            # --- TODO: Send the reply back to the user via WebSocket ---
            # For now, we are just logging the success. The next step in our
            # architecture will be to implement this delivery mechanism.

        except Exception as e:
            # If this fails, SQS will automatically retry based on our queue config.
            # After enough failures, the message will go to the DLQ (once we configure it).
            log_event("ai_worker_failed", {
                "record_id": record.get("messageId"),
                "approx_receive_count": record.get("attributes", {}).get("ApproximateReceiveCount")
            }, level="error", error=e)
            
            # Re-raise the exception to signal SQS that this message failed processing
            raise e

    # A successful run (no exceptions) implies messages are processed.
    # Lambda will automatically delete them from the SQS queue.
    return {"status": "ok", "processed_records": len(records)}