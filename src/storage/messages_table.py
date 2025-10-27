# src/storage/messages_table.py

import boto3
from datetime import datetime
from typing import Optional, Dict, Any, List
from boto3.dynamodb.conditions import Key # Added Key

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("ConversationMessages")


def save_message(
    conversation_id: str,
    role: str,
    message_text: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
):
    """
    Save a single message to the ConversationMessages table.

    SCHEMA:
      PK  = ConversationId (S)
      SK  = Timestamp (S, ISO8601)
      Attrs:
        - Role ('user' | 'assistant')
        - MessageText (S)
        - Meta (M, optional for extra info, e.g. image URL, tags)
    """
    timestamp = datetime.utcnow().isoformat()

    item = {
        "ConversationId": conversation_id,  # PK
        "Timestamp": timestamp,             # SK
        "Role": role,
        "MessageText": message_text,
    }

    if meta:
        item["Meta"] = meta

    table.put_item(Item=item)
    return item


def get_recent_messages(
    conversation_id: str,
    limit: int = 10,
    ascending: bool = False # Keep False for newest first by default here
) -> List[Dict[str, Any]]:
    """
    Fetch the most recent N messages from a conversation.

    :param conversation_id: ID of the conversation
    :param limit: number of messages to fetch
    :param ascending: if True, return in chronological order (oldest→newest),
                      if False, return newest→oldest
    :return: list of message items
    """
    if not conversation_id:
        raise ValueError("conversation_id must be provided")

    resp = table.query(
        # Use KeyConditionExpression for querying based on the partition key
        KeyConditionExpression=Key('ConversationId').eq(conversation_id),
        Limit=limit,
        ScanIndexForward=ascending,  # False = newest first (descending SK)
    )

    messages = resp.get("Items", [])
    # If ascending=True was requested, results are already oldest first.
    # If ascending=False (default), results are newest first, reverse them for chat history context.
    return messages if ascending else list(reversed(messages))

# --- NEW FUNCTION ---
def get_all_messages(
    conversation_id: str,
) -> List[Dict[str, Any]]:
    """
    Fetch ALL messages for a given conversation_id, sorted chronologically (oldest first).
    Handles pagination automatically.

    :param conversation_id: ID of the conversation
    :return: list of all message items, oldest first.
    """
    if not conversation_id:
        raise ValueError("conversation_id must be provided")

    messages = []
    last_evaluated_key = None

    while True:
        query_kwargs = {
            'KeyConditionExpression': Key('ConversationId').eq(conversation_id),
            'ScanIndexForward': True # True = Sort Key ascending (oldest first)
        }
        if last_evaluated_key:
            query_kwargs['ExclusiveStartKey'] = last_evaluated_key

        response = table.query(**query_kwargs)

        messages.extend(response.get('Items', []))

        last_evaluated_key = response.get('LastEvaluatedKey', None)
        if not last_evaluated_key:
            break # Exit loop if no more pages

    return messages
# --- END NEW FUNCTION ---