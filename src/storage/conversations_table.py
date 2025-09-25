# src/storage/conversations_table.py
import boto3
import uuid
from datetime import datetime
from typing import Optional

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserConversations")

# Only these attrs must NOT be empty (because of GSIs)
KEYS_DISALLOW_EMPTY = {"Email"}

def _omit_invalid_attrs(item: dict) -> dict:
    """
    Remove attributes that are None.
    Remove empty strings ONLY for attributes listed in KEYS_DISALLOW_EMPTY.
    Keep empty strings for non-key, informational fields like Name.
    """
    cleaned = {}
    for k, v in item.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            if k in KEYS_DISALLOW_EMPTY and v == "":
                continue
        if v == [] or v == {}:
            continue
        cleaned[k] = v
    return cleaned


def save_conversation(
    user_id: str,
    name: Optional[str],
    email: Optional[str],
    title: str,
    page: str,
):
    """
    Create a new conversation header in UserConversations.

    SCHEMA:
      PK: UserId (S)
      SK: Timestamp (S, ISO8601 creation time)
      Attrs:
        - ConversationId (S)   # unique identifier
        - Title (S)
        - Page (S)
        - Name (S)
        - Email (S, optional)
    """
    if not user_id or (isinstance(user_id, str) and user_id.strip() == ""):
        raise ValueError("user_id must be a non-empty string")

    conversation_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    item = {
        # Keys
        "UserId": user_id,         # PK
        "Timestamp": timestamp,    # SK (chronological ordering)

        # Attributes
        "ConversationId": conversation_id,
        "Name": (name if name is not None else ""),
        "Email": email,  # omitted if empty/None
        "Title": title,
        "Page": page,
    }

    safe_item = _omit_invalid_attrs(item)
    table.put_item(Item=safe_item)

    return {
        "ConversationId": conversation_id,
        "Timestamp": timestamp,
        "Name": item["Name"],
        "Email": email,
        "Title": title,
        "Page": page,
    }
