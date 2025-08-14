# src/storage/conversations_table.py

import boto3
import uuid
from datetime import datetime

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserConversations")


def _omit_empty_attrs(item: dict) -> dict:
    """
    Remove attributes that DynamoDB shouldn't store:
    - None
    - empty strings
    - empty lists/dicts
    """
    cleaned = {}
    for k, v in item.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        if v == [] or v == {}:
            continue
        cleaned[k] = v
    return cleaned


def save_conversation(user_id, name, email, title, page, thread_id):
    """
    Inserts a new conversation row into the UserConversations table.

    NOTE:
    - Email is OPTIONAL. If it's empty/None, it will be omitted so that
      your EmailIndex (GSI) remains sparse and you avoid ValidationException.
    """
    if not user_id or (isinstance(user_id, str) and user_id.strip() == ""):
        raise ValueError("user_id must be a non-empty string")

    conversation_id = str(uuid.uuid4())  # Sort key
    timestamp = datetime.utcnow().isoformat()

    item = {
        "UserId": user_id,                 # PK
        "ConversationId": conversation_id, # SK
        "Name": name,
        "Email": email,                    # will be omitted if empty/None
        "Title": title,
        "Page": page,
        "ThreadId": thread_id,
        "Timestamp": timestamp,
    }

    safe_item = _omit_empty_attrs(item)
    table.put_item(Item=safe_item)

    # Return original values (even if some were omitted in DynamoDB)
    return {
        "ConversationId": conversation_id,
        "ThreadId": thread_id,
        "Timestamp": timestamp,
        "Name": name,
        "Email": email,
        "Title": title,
        "Page": page,
    }
