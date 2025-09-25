# src/storage/messages_table.py

import boto3
from datetime import datetime
from typing import Optional, Dict, Any, List

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
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetch the most recent N messages from a conversation.

    :param conversation_id: ID of the conversation
    :param limit: number of messages to fetch
    :param ascending: if True, return in chronological order (oldest→newest),
                      if False, return newest→oldest
    :return: list of message items
    """
    resp = table.query(
        KeyConditionExpression="ConversationId = :cid",
        ExpressionAttributeValues={":cid": conversation_id},
        Limit=limit,
        ScanIndexForward=ascending,  # False = newest first
    )

    messages = resp.get("Items", [])
    return messages if ascending else list(reversed(messages))
