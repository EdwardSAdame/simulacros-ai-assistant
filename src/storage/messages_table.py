# src/storage/messages_table.py

import boto3
import logging # 🔹 NEW: Added for logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from boto3.dynamodb.conditions import Key 

# 🔹 NEW: Setup logger
logger = logging.getLogger(__name__)

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
        "Timestamp": timestamp,            # SK
        "Role": role,
        "MessageText": message_text,
    }

    if meta:
        item["Meta"] = meta

    try:
        table.put_item(Item=item)
    except Exception as e:
        logger.error(f"Failed to save message for ConversationId {conversation_id}: {e}")
        # Re-raise the exception so the caller can handle it
        raise
        
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

    try:
        resp = table.query(
            # Use KeyConditionExpression for querying based on the partition key
            KeyConditionExpression=Key('ConversationId').eq(conversation_id),
            Limit=limit,
            ScanIndexForward=ascending,  # False = newest first (descending SK)
        )
    except Exception as e:
        logger.error(f"Failed to get recent messages for ConversationId {conversation_id}: {e}")
        return [] # Return empty list on error

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
        try:
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
        except Exception as e:
            logger.error(f"Failed during paginated get_all_messages for ConversationId {conversation_id}: {e}")
            # Return what we have so far
            break

    return messages
# --- END NEW FUNCTION ---


# --- 🔹 NEW FUNCTION TO UPDATE MESSAGE 🔹 ---
def update_message_text(conversation_id: str, timestamp: str, partial_text: str):
    """
    Updates the 'MessageText' for a specific message, identified by its composite key.
    This is used to save partial text from a user-stopped generation.

    :param conversation_id: The Partition Key (PK) of the message.
    :param timestamp: The Sort Key (SK) of the message.
    :param partial_text: The new (partial) text to overwrite the message with.
    """
    if not conversation_id or not timestamp:
        logger.warning("update_message_text called without conversation_id or timestamp.")
        raise ValueError("conversation_id and timestamp are required.")

    logger.info(f"Updating message {conversation_id}/{timestamp} with partial text.")
    try:
        table.update_item(
            Key={
                'ConversationId': conversation_id,
                'Timestamp': timestamp
            },
            UpdateExpression="SET MessageText = :text",
            ExpressionAttributeValues={
                ':text': partial_text
            }
        )
        logger.info(f"Successfully updated message {conversation_id}/{timestamp}.")
    except Exception as e:
        logger.error(f"Failed to update message {conversation_id}/{timestamp}: {e}")
        # Re-raise the exception so the handler can return a 500
        raise
# --- 🔹 END NEW FUNCTION 🔹 ---