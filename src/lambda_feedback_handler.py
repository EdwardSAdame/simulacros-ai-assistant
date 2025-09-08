# src/lambda_feedback_handler.py
import json
import logging

from src.storage.feedback_table import save_feedback
from src.utils.logging_utils import log_event, set_invocation_context  # 👈 add context hook

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Must match your frontend's ID for "Otro"
OTHER_TAG_ID = "btnOther"


def _none_if_empty(val):
    if val is None:
        return None
    if isinstance(val, str) and val.strip() == "":
        return None
    return val


def lambda_handler(event, context):
    # Attach AWS context to logs (function, request_id, etc.)
    set_invocation_context(context)

    try:
        # Lightweight invocation log (avoid dumping full event)
        log_event("feedback_lambda_invocation", {
            "source": "FeedBackHandler",
            "has_body": "body" in (event or {}),
        })

        # Parse API Gateway body
        body = json.loads(event.get("body", "{}"))

        # Required fields
        conversation_id = body.get("conversationId")
        rating          = body.get("rating")  # "up" | "down"

        # Optional fields
        tag             = body.get("tag")  # e.g., "btnIncorrect" | "btnOther"
        custom_text_in  = body.get("customText")  # only valid when tag == OTHER_TAG_ID
        thread_id       = body.get("threadId")
        user_id         = body.get("userId")
        page            = body.get("page") or "/"
        message_id      = body.get("messageId")
        meta            = body.get("meta")

        # Normalize
        conversation_id = conversation_id if isinstance(conversation_id, str) else None
        rating          = rating if isinstance(rating, str) else None
        tag             = tag.strip() if isinstance(tag, str) else None
        custom_text_in  = _none_if_empty(custom_text_in)

        # Validate
        if not conversation_id:
            log_event("feedback_validation_failed", {
                "reason": "missing conversationId"
            }, level="warning")
            return _response(400, {"error": "conversationId is required"})

        if rating not in ("up", "down"):
            log_event("feedback_validation_failed", {
                "reason": "invalid rating",
                "rating": rating
            }, level="warning")
            return _response(400, {"error": 'rating must be "up" or "down"'})

        # Business rule:
        # - If tag == OTHER_TAG_ID → allow customText (empty string allowed).
        # - If tag is anything else → ignore customText (store only predefined tag).
        # - If no tag (e.g., user clicked UP without panel) → store rating only.
        if tag == OTHER_TAG_ID:
            custom_text = custom_text_in if custom_text_in is not None else ""
        else:
            custom_text = None

        # Save
        item = save_feedback(
            conversation_id=conversation_id,
            rating=rating,
            tag=tag,
            custom_text=custom_text,
            thread_id=thread_id,
            user_id=user_id,
            page=page,
            message_id=message_id,
            meta=meta,
        )

        log_event("feedback_saved", {
            "conversation_id": conversation_id,
            "rating": rating,
            "tag": tag,
            "has_custom_text": custom_text is not None
        })

        return _response(200, {"ok": True, "saved": item})

    except Exception as e:
        # Include stack trace via logging_utils
        log_event("feedback_lambda_exception", {
            "source": "FeedBackHandler"
        }, level="error", error=e)
        return _response(500, {"error": "Internal error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            # CORS for Wix frontend:
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps(body)
    }
