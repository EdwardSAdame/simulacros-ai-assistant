# src/storage/conversations_table.py
import boto3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from boto3.dynamodb.conditions import Key, Attr

# CONFIG
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserConversations")

# These keys will be REMOVED if they are empty strings.
KEYS_DISALLOW_EMPTY = {"Email", "ArenaId"} 

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
    conversation_id: Optional[str] = None, # Allow passing an existing ID
    arena_id: Optional[str] = None,        # Link to an Arena
    ai_mode: str = "omega",                # 🔹 Persist the selected mode
    channel: str = "text"                  # 🔹 NEW: Distinguish text vs voice chats
) -> Dict[str, Any]:
    """
    Creates a new conversation record in DynamoDB.
    If conversation_id is provided, it uses it; otherwise generates a new one.
    """
    if not user_id or (isinstance(user_id, str) and user_id.strip() == ""):
        raise ValueError("user_id must be a non-empty string")

    # IDEMPOTENCY FIX: Use provided ID or generate new
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        
    timestamp = datetime.utcnow().isoformat()

    # CRITICAL: Ensure Name has a fallback if it's None or Empty
    safe_name = name.strip() if name and name.strip() else "Guest"

    item = {
        "UserId": user_id,
        "Timestamp": timestamp,
        "ConversationId": conversation_id,
        "Name": safe_name,
        "Email": email,
        "Title": title,
        "Page": page,
        "IsPinned": False, # Default to false
        "ArenaId": arena_id,
        "LastUpdated": timestamp, # Initialize LastUpdated same as creation
        "AiMode": ai_mode,        # 🔹 Save the mode
        "Channel": channel        # 🔹 NEW: Save the channel (text, voice)
    }

    # Clean up (removes empty email, empty arena_id, etc.)
    safe_item = _omit_invalid_attrs(item)

    try:
        table.put_item(Item=safe_item)
        print(f"Conversation saved: {conversation_id} (Arena: {arena_id}, Mode: {ai_mode}, Channel: {channel})")
    except Exception as e:
        print(f"Error saving conversation: {e}")
        raise e

    return {
        "ConversationId": conversation_id,
        "Timestamp": timestamp,
        "Title": title,
        "ArenaId": arena_id,
        "AiMode": ai_mode,
        "Channel": channel
    }

def update_conversation_last_active(user_id: str, conversation_id: str):
    """
    Updates the 'LastUpdated' field to the current time.
    Call this whenever a new message is sent.
    """
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        print(f"Cannot update LastActive: Conversation {conversation_id} not found.")
        return

    now_iso = datetime.utcnow().isoformat()

    try:
        table.update_item(
            Key={'UserId': user_id, 'Timestamp': timestamp},
            UpdateExpression="set LastUpdated = :t",
            ExpressionAttributeValues={':t': now_iso}
        )
    except Exception as e:
        print(f"Error updating LastActive: {e}")

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
    
    # 🔹 Added Channel to the projection expression
    projection_expression = "ConversationId, Title, #ts, IsPinned, #n, Page, ArenaId, LastUpdated, AiMode, Channel"

    try:
        response = table.query(
            KeyConditionExpression=Key('UserId').eq(user_id),
            ScanIndexForward=ascending,
            Limit=limit,
            ProjectionExpression=projection_expression,
            ExpressionAttributeNames=expression_attribute_names
        )
        items = response.get("Items", [])

        # MANUAL SORT: Re-sort by 'LastUpdated' (fallback to 'Timestamp')
        def get_sort_key(x):
            return x.get('LastUpdated', x.get('Timestamp', ''))

        # If we asked for descending (newest first), reverse=True
        should_reverse = not ascending
        
        items.sort(key=get_sort_key, reverse=should_reverse)

        return items
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

def get_conversation_metadata(user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches basic metadata (Title, ArenaId, AiMode, Channel) for a conversation.
    """
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        return None

    try:
        response = table.get_item(
            Key={'UserId': user_id, 'Timestamp': timestamp},
            ProjectionExpression="ConversationId, Title, ArenaId, AiMode, Channel"
        )
        return response.get('Item')
    except Exception as e:
        print(f"Error fetching metadata for {conversation_id}: {e}")
        return None

def update_conversation_arena(user_id: str, conversation_id: str, arena_id: Optional[str]):
    """
    Updates the ArenaId for a conversation (Moves it to a folder or removes it).
    """
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        raise ValueError("Conversation not found")

    table.update_item(
        Key={'UserId': user_id, 'Timestamp': timestamp},
        UpdateExpression="set ArenaId = :a",
        ExpressionAttributeValues={':a': arena_id}
    )
    return True

# 🔹 NEW FUNCTION: Allows updating the AiMode mid-conversation
def update_conversation_mode(user_id: str, conversation_id: str, new_mode: str):
    """
    Updates the AiMode for an existing conversation.
    """
    timestamp = _find_conversation_timestamp(user_id, conversation_id)
    if not timestamp:
        print(f"Cannot update AiMode: Conversation {conversation_id} not found.")
        return False

    try:
        table.update_item(
            Key={'UserId': user_id, 'Timestamp': timestamp},
            UpdateExpression="set AiMode = :m",
            ExpressionAttributeValues={':m': new_mode}
        )
        print(f"Successfully updated conversation {conversation_id} to mode: {new_mode}")
        return True
    except Exception as e:
        print(f"Error updating AiMode for {conversation_id}: {e}")
        return False