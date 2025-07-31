# src/storage/messages_table.py

import boto3
from datetime import datetime
import uuid

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("ConversationMessages")

def save_message(conversation_id, role, message_text):
    """
    Saves a single message to the ConversationMessages table.
    Role can be 'user' or 'assistant'.
    """
    timestamp = datetime.utcnow().isoformat()

    item = {
        "ConversationId": conversation_id,  # Partition key
        "Timestamp": timestamp,             # Sort key
        "Role": role,
        "MessageText": message_text
    }

    table.put_item(Item=item)
    return item
