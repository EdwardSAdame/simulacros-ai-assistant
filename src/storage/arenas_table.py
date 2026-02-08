# src/storage/arenas_table.py
import boto3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# CONFIG
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserArenas")

# Keys that should be removed if they are empty strings
# 🟢 UPDATED: Added "VectorStoreId" to prevent empty string storage
KEYS_DISALLOW_EMPTY = {"Description", "SystemInstructions", "Icon", "VectorStoreId"} 

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
            if k in KEYS_DISALLOW_EMPTY and v == "":
                continue
        cleaned[k] = v
    return cleaned

def create_arena(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    system_instructions: Optional[str] = None,
    icon: Optional[str] = "folder", 
    files: Optional[List[Dict[str, str]]] = None,
    vector_store_id: Optional[str] = None  # 🟢 NEW: Accept VectorStoreId
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
    
    safe_files = files if files else []

    item = {
        "UserId": user_id,
        "ArenaId": arena_id,
        "CreatedAt": timestamp,
        "UpdatedAt": timestamp,
        "LastActive": timestamp, 
        "Title": title.strip(),
        "Description": description,
        "SystemInstructions": system_instructions,
        "Icon": icon,
        "Files": safe_files,
        "VectorStoreId": vector_store_id  # 🟢 NEW: Save the Vector Store ID
    }

    safe_item = _omit_invalid_attrs(item)

    try:
        table.put_item(Item=safe_item)
        print(f"Arena created: {title} ({arena_id})")
    except Exception as e:
        print(f"Error creating arena: {e}")
        raise e

    return safe_item

def update_arena_last_active(user_id: str, arena_id: str):
    """
    Updates the 'LastActive' field to the current time.
    Call this whenever a chat occurs inside this Arena.
    """
    now_iso = datetime.utcnow().isoformat()
    try:
        table.update_item(
            Key={
                'UserId': user_id,
                'ArenaId': arena_id
            },
            UpdateExpression="set LastActive = :t",
            ExpressionAttributeValues={':t': now_iso}
        )
    except Exception as e:
        print(f"Error updating LastActive for Arena {arena_id}: {e}")

def get_arenas_for_user(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all Arenas created by a specific user using the GSI.
    Sorted by LastActive (Recency).
    """
    if not user_id:
        raise ValueError("user_id must be provided")

    try:
        response = table.query(
            IndexName='UserId-Index',
            KeyConditionExpression=Key('UserId').eq(user_id)
        )
        items = response.get("Items", [])

        # MANUAL SORT: Re-sort by 'LastActive' (fallback to 'UpdatedAt')
        def get_sort_key(x):
            return x.get('LastActive', x.get('UpdatedAt', ''))

        # Sort Descending (Newest First)
        items.sort(key=get_sort_key, reverse=True)

        return items

    except Exception as e:
        print(f"Error fetching arenas for {user_id}: {e}")
        return []

def get_arena_details(user_id: str, arena_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the full configuration for a specific Arena.
    """
    try:
        response = table.get_item(
            Key={
                'UserId': user_id,
                'ArenaId': arena_id
            }
        )
        item = response.get('Item')
        return item
    except Exception as e:
        print(f"Error fetching arena details {arena_id}: {e}")
        return None

def update_arena(
    user_id: str, 
    arena_id: str, 
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Updates specific fields of an Arena.
    """
    # 🟢 UPDATED: Included 'VectorStoreId' in allowed keys
    allowed_keys = {"Title", "Description", "SystemInstructions", "Icon", "Files", "VectorStoreId"}
    
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_keys}
    if not filtered_updates:
        return {}

    update_parts = []
    
    # Update both UpdatedAt AND LastActive when editing
    now_iso = datetime.utcnow().isoformat()
    expression_values = {':ts': now_iso}
    expression_names = {'#ts': 'UpdatedAt', '#la': 'LastActive'}

    for key, value in filtered_updates.items():
        attr_name = f"#{key}"
        val_name = f":{key}"
        
        update_parts.append(f"{attr_name} = {val_name}")
        expression_names[attr_name] = key
        expression_values[val_name] = value

    # We update LastActive too, because editing an Arena makes it "relevant" again
    update_expression = "SET " + ", ".join(update_parts) + ", #ts = :ts, #la = :ts"

    try:
        response = table.update_item(
            Key={
                'UserId': user_id,
                'ArenaId': arena_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW"
        )
        return response.get("Attributes", {})
    except ClientError as e:
        print(f"Error updating arena {arena_id}: {e}")
        raise e

def delete_arena(user_id: str, arena_id: str):
    """
    Deletes an Arena configuration if the user owns it.
    """
    try:
        table.delete_item(
            Key={
                'UserId': user_id,
                'ArenaId': arena_id
            }
        )
        return True
    except ClientError as e:
        print(f"Error deleting arena {arena_id}: {e}")
        return Falses