# src/storage/conversations_table.py
import boto3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserConversations")

KEYS_DISALLOW_EMPTY = {"Email"}

def _omit_invalid_attrs(item: dict) -> dict:
    cleaned = {}
    for k, v in item.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            if k in KEYS_DISALLOW_EMPTY and v == "":
                continue
        cleaned[k] = v
    return cleaned

def _find_conversation_timestamp(user_id: str, conversation_id: str) -> Optional[str]:
    """
    Helper: Finds the Timestamp (Sort Key) for a given ConversationId.
    This is necessary because we need the full Primary Key (UserId + Timestamp) 
    to update or delete an item.
    """
    response = table.query(
        KeyConditionExpression=Key('UserId').eq(user_id),
        FilterExpression=Attr('ConversationId').eq(conversation_id),
        ProjectionExpression="#ts",
        ExpressionAttributeNames={'#ts': 'Timestamp'}
    )
    items = response.get('Items', [])
    if items:
        return items[0]['Timestamp']
    return None

def save_conversation(
    user_id: str,
    name: Optional[str],
    email: Optional[str],
    title: str,
    page: str,
):
    if not user_id or (isinstance(user_id, str) and user_id.strip() == ""):
        raise ValueError("user_id must be a non-empty string")

    conversation_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    item = {
        "UserId": user_id,
        "Timestamp": timestamp,
        "ConversationId": conversation_id,
        "Name": (name if name is not None else ""),
        "Email": email,
        "Title": title,
        "Page": page,
        "IsPinned": False # Default to false
    }

    safe_item = _omit_invalid_attrs(item)
    table.put_item(Item=safe_item)

    return {
        "ConversationId": conversation_id,
        "Timestamp": timestamp,
        "Title": title,
    }

def get_conversations_for_user(
    user_id: str,
    limit: int = 50,
    ascending: bool = False
) -> List[Dict[str, Any]]:
    if not user_id:
        raise ValueError("user_id must be provided")

    expression_attribute_names = {
        '#ts': 'Timestamp'
    }
    # Added IsPinned to projection
    projection_expression = "ConversationId, Title, #ts, IsPinned"

    response = table.query(
        KeyConditionExpression=Key('UserId').eq(user_id),
        ScanIndexForward=ascending,
        Limit=limit,
        ProjectionExpression=projection_expression,
        ExpressionAttributeNames=expression_attribute_names
    )

    return response.get("Items", [])

# --- NEW MANAGEMENT FUNCTIONS ---

def update_conversation_title(user_id: str, conversation_id: str, new_title: str):
    """
    Updates the Title of a conversation.
    """
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        raise ValueError("Conversation not found")

    table.update_item(
        Key={
            'UserId': user_id,
            'Timestamp': timestamp
        },
        UpdateExpression="set Title = :t",
        ExpressionAttributeValues={
            ':t': new_title
        }
    )
    return True

def delete_conversation(user_id: str, conversation_id: str):
    """
    Deletes a conversation.
    """
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        # If it doesn't exist, consider it deleted
        return True

    table.delete_item(
        Key={
            'UserId': user_id,
            'Timestamp': timestamp
        }
    )
    return True

def update_conversation_pin(user_id: str, conversation_id: str, is_pinned: bool):
    """
    Updates the IsPinned status of a conversation.
    """
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        raise ValueError("Conversation not found")

    table.update_item(
        Key={
            'UserId': user_id,
            'Timestamp': timestamp
        },
        UpdateExpression="set IsPinned = :p",
        ExpressionAttributeValues={
            ':p': is_pinned
        }
    )
    return True