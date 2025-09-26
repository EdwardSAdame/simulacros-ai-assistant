# src/storage/feedback_table.py

import boto3
from datetime import datetime

# DynamoDB setup (same pattern as your other tables)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("MessageFeedback")  # existing table name


def save_feedback(
    conversation_id: str,
    rating: str,                    # "up" | "down"
    *,
    tag: str | None = None,         # single tag id (e.g., "btnIncorrect", "btnOther")
    custom_text: str | None = None, # free text (only for "Otro" per handler rule)
    user_id: str | None = None,
    page: str | None = None,
    message_id: str | None = None,  # optional: per-message id
    meta: dict | None = None,       # optional: userAgent/ipHash, etc.
):
    """
    Store a single feedback event in the MessageFeedback table.

    PK = ConversationId (string)
    SK = Timestamp (ISO8601, UTC)

    Required: conversation_id, rating ("up" or "down")
    Optional fields are omitted if None.
    """
    if not conversation_id or not isinstance(conversation_id, str):
        raise ValueError("conversation_id must be a non-empty string")
    if rating not in ("up", "down"):
        raise ValueError('rating must be "up" or "down"')

    timestamp = datetime.utcnow().isoformat()

    item = {
        "ConversationId": conversation_id,  # PK
        "Timestamp": timestamp,             # SK
        "Rating": rating,
    }

    # Only include optional attributes when provided
    if tag:
        item["Tag"] = tag.strip()
    if custom_text is not None:  # allow empty string if user opened the box
        item["CustomText"] = str(custom_text)
    if user_id:
        item["UserId"] = user_id
    if page:
        item["Page"] = page
    if message_id:
        item["MessageId"] = message_id
    if meta:
        item["Meta"] = meta

    table.put_item(Item=item)
    return item
