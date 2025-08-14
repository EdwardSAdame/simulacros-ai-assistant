# src/storage/conversations_table.py

import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserConversations")

# Only these attrs must NOT be empty (because of keys/GSIs)
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
            # Trim whitespace
            v = v.strip()
            # For keys like Email (on a GSI), drop if empty
            if k in KEYS_DISALLOW_EMPTY and v == "":
                continue
            # For non-key fields (e.g., Name), allow "" to persist if you prefer;
            # DynamoDB permits empty strings for non-key attributes.
        if v == [] or v == {}:
            continue
        cleaned[k] = v
    return cleaned


def save_conversation(user_id, name, email, title, page, thread_id):
    """
    Inserts a new conversation row into the UserConversations table.
    Email is OPTIONAL; it will be omitted if empty/None to keep the EmailIndex sparse.
    Name is PRESERVED even if empty, so the attribute always exists if you pass "".
    """
    if not user_id or (isinstance(user_id, str) and user_id.strip() == ""):
        raise ValueError("user_id must be a non-empty string")

    conversation_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    item = {
        "UserId": user_id,                 # PK
        "ConversationId": conversation_id, # SK
        "Name": (name if name is not None else ""),  # keep "" if unresolved
        "Email": email,                    # will be omitted if empty/None
        "Title": title,
        "Page": page,
        "ThreadId": thread_id,
        "Timestamp": timestamp,
    }

    safe_item = _omit_invalid_attrs(item)
    table.put_item(Item=safe_item)

    return {
        "ConversationId": conversation_id,
        "ThreadId": thread_id,
        "Timestamp": timestamp,
        "Name": item["Name"],  # return what we attempted to save
        "Email": email,
        "Title": title,
        "Page": page,
    }
