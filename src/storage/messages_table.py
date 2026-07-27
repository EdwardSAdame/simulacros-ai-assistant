# Backend: simulacros-ai-assistant
# File: src/storage/messages_table.py

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("ConversationMessages")


def save_message(
    conversation_id: str,
    role: str,
    message_text: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Save a single message to the ConversationMessages table.
    Stores all extra payload data and file attachments inside the Metadata attribute.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    item = {
        "ConversationId": conversation_id,
        "Timestamp": timestamp,
        "Role": role,
        "MessageText": message_text,
    }

    if metadata:
        metadata_copy = dict(metadata)

        if "sentImages" in metadata_copy and "attachments" not in metadata_copy:
            metadata_copy["attachments"] = metadata_copy.pop("sentImages")

        if metadata_copy:
            item["Metadata"] = metadata_copy

    try:
        table.put_item(Item=item)
    except Exception as e:
        logger.error(f"Failed to save message for ConversationId {conversation_id}: {e}")
        raise

    return item


def get_recent_messages(
    conversation_id: str,
    limit: int = 10,
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetch the most recent N messages from a conversation.
    """
    if not conversation_id:
        raise ValueError("conversation_id must be provided")

    try:
        resp = table.query(
            KeyConditionExpression=Key('ConversationId').eq(conversation_id),
            Limit=limit,
            ScanIndexForward=ascending,
        )
    except Exception as e:
        logger.error(f"Failed to get recent messages for ConversationId {conversation_id}: {e}")
        return []

    messages = resp.get("Items", [])
    return messages if ascending else list(reversed(messages))


def get_all_messages(
    conversation_id: str,
) -> List[Dict[str, Any]]:
    """
    Fetch ALL messages for a given conversation_id, sorted chronologically.
    """
    if not conversation_id:
        raise ValueError("conversation_id must be provided")

    messages = []
    last_evaluated_key = None

    while True:
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('ConversationId').eq(conversation_id),
                'ScanIndexForward': True
            }
            if last_evaluated_key:
                query_kwargs['ExclusiveStartKey'] = last_evaluated_key

            response = table.query(**query_kwargs)

            messages.extend(response.get('Items', []))

            last_evaluated_key = response.get('LastEvaluatedKey', None)
            if not last_evaluated_key:
                break
        except Exception as e:
            logger.error(f"Failed during paginated get_all_messages for ConversationId {conversation_id}: {e}")
            break

    return messages


def update_message_text(conversation_id: str, timestamp: str, partial_text: str) -> None:
    """
    Updates the MessageText for a specific message.
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
        raise


def delete_messages_for_conversation(conversation_id: str) -> bool:
    """
    Deletes ALL messages associated with a specific ConversationId using BatchWrite.
    """
    if not conversation_id:
        raise ValueError("conversation_id is required for deletion")

    logger.info(f"Starting batch deletion of messages for ConversationId: {conversation_id}")

    try:
        with table.batch_writer() as batch:
            last_evaluated_key = None

            while True:
                query_params = {
                    'KeyConditionExpression': Key('ConversationId').eq(conversation_id),
                    'ProjectionExpression': "#ts",
                    'ExpressionAttributeNames': {"#ts": "Timestamp"}
                }
                if last_evaluated_key:
                    query_params['ExclusiveStartKey'] = last_evaluated_key

                response = table.query(**query_params)
                items = response.get('Items', [])

                for item in items:
                    batch.delete_item(
                        Key={
                            'ConversationId': conversation_id,
                            'Timestamp': item['Timestamp']
                        }
                    )

                last_evaluated_key = response.get('LastEvaluatedKey')
                if not last_evaluated_key:
                    break

        logger.info(f"Successfully deleted all messages for ConversationId: {conversation_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to batch delete messages for {conversation_id}: {e}")
        raise