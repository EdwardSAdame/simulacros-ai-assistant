# src/storage/messages_table.py

import boto3
from datetime import datetime

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("ConversationMessages")

def save_message(conversation_id: str, role: str, message_text: str, thread_id: str):
    """
    Save a single message to the ConversationMessages table.

    PK  = ConversationId
    SK  = Timestamp (ISO8601)
    Attrs: Role ('user' | 'assistant'), MessageText, ThreadId

    Adding ThreadId lets you later create a GSI (ThreadId, Timestamp)
    to fetch a whole thread in one query.
    """
    timestamp = datetime.utcnow().isoformat()

    item = {
        "ConversationId": conversation_id,  # PK
        "Timestamp": timestamp,             # SK
        "Role": role,
        "MessageText": message_text,
        "ThreadId": thread_id               # ✅ new attribute
    }

    table.put_item(Item=item)
    return item
