# src/storage/arenas_table.py
import boto3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from boto3.dynamodb.conditions import Key, Attr

# 🟢 CONFIG
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserArenas")

# Keys that should be removed if they are empty strings
KEYS_DISALLOW_EMPTY = {"Description", "SystemInstructions", "Icon"} 

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
            # If forbidden to be empty, skip adding it
            if k in KEYS_DISALLOW_EMPTY and v == "":
                continue
        cleaned[k] = v
    return cleaned

def create_arena(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    system_instructions: Optional[str] = None,
    icon: Optional[str] = "folder", # Default icon
    files: Optional[List[Dict[str, str]]] = None # List of {name, url}
) -> Dict[str, Any]:
    """
    Creates a new Arena (Folder) configuration.
    """
    if not user_id:
        raise ValueError("user_id must be provided")
    if not title:
        raise ValueError("Title is required for an Arena")

    arena_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    # Default empty list if no files provided
    safe_files = files if files else []

    item = {
        "UserId": user_id,
        "ArenaId": arena_id,
        "CreatedAt": timestamp,
        "UpdatedAt": timestamp,
        "Title": title.strip(),
        "Description": description,
        "SystemInstructions": system_instructions,
        "Icon": icon,
        "Files": safe_files
    }

    # Clean up (remove empty descriptions, etc.)
    safe_item = _omit_invalid_attrs(item)

    try:
        table.put_item(Item=safe_item)
        print(f"✅ Arena created: {title} ({arena_id})")
    except Exception as e:
        print(f"❌ Error creating arena: {e}")
        raise e

    return safe_item

def get_arenas_for_user(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all Arenas created by a specific user.
    """
    if not user_id:
        raise ValueError("user_id must be provided")

    try:
        response = table.query(
            KeyConditionExpression=Key('UserId').eq(user_id),
            # We assume you might want them sorted by creation time (default behavior of Sort Key if string)
            # If ArenaId is UUID, this order is random. You might need client-side sorting.
        )
        return response.get("Items", [])
    except Exception as e:
        print(f"Error fetching arenas for {user_id}: {e}")
        return []

def get_arena_details(user_id: str, arena_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the full configuration (Instructions, Files) for a specific Arena.
    Used when a Chat starts to inject context.
    """
    try:
        response = table.get_item(
            Key={
                'UserId': user_id,
                'ArenaId': arena_id
            }
        )
        return response.get('Item')
    except Exception as e:
        print(f"Error fetching arena details {arena_id}: {e}")
        return None

def update_arena(
    user_id: str, 
    arena_id: str, 
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Updates specific fields of an Arena (e.g. changing instructions or adding a file).
    'updates' should be a dictionary like {'Title': 'New Name', 'SystemInstructions': '...'}
    """
    allowed_keys = {"Title", "Description", "SystemInstructions", "Icon", "Files"}
    
    # Filter only allowed updates
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_keys}
    if not filtered_updates:
        return {}

    # Build the UpdateExpression dynamically
    update_parts = []
    expression_values = {':ts': datetime.utcnow().isoformat()}
    expression_names = {'#ts': 'UpdatedAt'}

    for key, value in filtered_updates.items():
        # DynamoDB Reserved words handling (if any)
        attr_name = f"#{key}"
        val_name = f":{key}"
        
        update_parts.append(f"{attr_name} = {val_name}")
        expression_names[attr_name] = key
        expression_values[val_name] = value

    update_expression = "SET " + ", ".join(update_parts) + ", #ts = :ts"

    try:
        response = table.update_item(
            Key={'UserId': user_id, 'ArenaId': arena_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW"
        )
        return response.get("Attributes", {})
    except Exception as e:
        print(f"Error updating arena {arena_id}: {e}")
        raise e

def delete_arena(user_id: str, arena_id: str):
    """
    Deletes an Arena configuration. 
    Note: This does NOT delete the chats inside it (unless we add specific logic later).
    """
    try:
        table.delete_item(
            Key={'UserId': user_id, 'ArenaId': arena_id}
        )
        return True
    except Exception as e:
        print(f"Error deleting arena {arena_id}: {e}")
        return False