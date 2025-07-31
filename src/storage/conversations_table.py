# src/storage/conversations_table.py

import boto3
import os
import uuid
from datetime import datetime

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table_name = "UserConversations"
table = dynamodb.Table(table_name)

def save_conversation(user_id, name, email, title, page, thread_id):
    """
    Inserts a new conversation row into the UserConversations table.
    """
    conversation_id = str(uuid.uuid4())  # Sort key
    timestamp = datetime.utcnow().isoformat()

    item = {
        'UserId': user_id,                   # Partition Key
        'ConversationId': conversation_id,   # Sort Key
        'Name': name,
        'Email': email,
        'Title': title,
        'Page': page,
        'ThreadId': thread_id,
        'Timestamp': timestamp
    }

    table.put_item(Item=item)
    return {
        "ConversationId": conversation_id,
        "ThreadId": thread_id,
        "Timestamp": timestamp,
        "Name": name,
        "Email": email,
        "Title": title,
        "Page": page
    }
