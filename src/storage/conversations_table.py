# src/storage/conversations_table.py
import boto3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from boto3.dynamodb.conditions import Key, Attr

# 🟢 CONFIG
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserConversations")

# These keys will be REMOVED if they are empty strings.
# Other keys (like Name) will be kept even if empty, unless we fix them below.
KEYS_DISALLOW_EMPTY = {"Email"} 

def _omit_invalid_attrs(item: dict) -> dict:
    """
    Cleans up the dictionary before sending to DynamoDB.
    Removes None values and empty strings for restricted keys.
    """
    cleaned = {}
    for k, v in item.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            # If forbidden to be empty (e.g. Email), skip adding it
            if k in KEYS_DISALLOW_EMPTY and v == "":
                continue
        cleaned[k] = v
    return cleaned

def _find_conversation_timestamp(user_id: str, conversation_id: str) -> Optional[str]:
    """
    Helper: Finds the Timestamp (Sort Key) for a given ConversationId.
    Required because Primary Key = UserId (Partition) + Timestamp (Sort).
    """
    try:
        response = table.query(
            KeyConditionExpression=Key('UserId').eq(user_id),
            FilterExpression=Attr('ConversationId').eq(conversation_id),
            ProjectionExpression="#ts",
            ExpressionAttributeNames={'#ts': 'Timestamp'}
        )
        items = response.get('Items', [])
        if items:
            return items[0]['Timestamp']
    except Exception as e:
        print(f"Error finding timestamp for conversation {conversation_id}: {e}")
    return None

def save_conversation(
    user_id: str,
    name: Optional[str],
    email: Optional[str],
    title: str,
    page: str,
) -> Dict[str, Any]:
    """
    Creates a new conversation record in DynamoDB.
    """
    if not user_id or (isinstance(user_id, str) and user_id.strip() == ""):
        raise ValueError("user_id must be a non-empty string")

    conversation_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    # 🟢 CRITICAL: Ensure Name has a fallback if it's None or Empty
    safe_name = name.strip() if name and name.strip() else "Guest"

    item = {
        "UserId": user_id,
        "Timestamp": timestamp,
        "ConversationId": conversation_id,
        "Name": safe_name,
        "Email": email,
        "Title": title,
        "Page": page,
        "IsPinned": False # Default to false
    }

    # Clean up (removes empty email, etc.)
    safe_item = _omit_invalid_attrs(item)

    try:
        table.put_item(Item=safe_item)
        print(f"✅ Conversation saved: {conversation_id} for {safe_name}")
    except Exception as e:
        print(f"❌ Error saving conversation: {e}")
        raise e

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
    """
    Fetches conversations for a user.
    """
    if not user_id:
        raise ValueError("user_id must be provided")

    # Projecting relevant fields
    expression_attribute_names = {
        '#ts': 'Timestamp',
        '#n': 'Name'
    }
    projection_expression = "ConversationId, Title, #ts, IsPinned, #n, Page"

    try:
        response = table.query(
            KeyConditionExpression=Key('UserId').eq(user_id),
            ScanIndexForward=ascending,
            Limit=limit,
            ProjectionExpression=projection_expression,
            ExpressionAttributeNames=expression_attribute_names
        )
        return response.get("Items", [])
    except Exception as e:
        print(f"Error fetching conversations for {user_id}: {e}")
        return []

# --- MANAGEMENT FUNCTIONS ---

def update_conversation_title(user_id: str, conversation_id: str, new_title: str):
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        raise ValueError("Conversation not found")

    table.update_item(
        Key={'UserId': user_id, 'Timestamp': timestamp},
        UpdateExpression="set Title = :t",
        ExpressionAttributeValues={':t': new_title}
    )
    return True

def delete_conversation(user_id: str, conversation_id: str):
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        return True # Treat as already deleted

    table.delete_item(
        Key={'UserId': user_id, 'Timestamp': timestamp}
    )
    return True

def update_conversation_pin(user_id: str, conversation_id: str, is_pinned: bool):
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        raise ValueError("Conversation not found")

    table.update_item(
        Key={'UserId': user_id, 'Timestamp': timestamp},
        UpdateExpression="set IsPinned = :p",
        ExpressionAttributeValues={':p': is_pinned}
    )
    return True