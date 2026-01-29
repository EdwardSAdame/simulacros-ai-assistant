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
    files: Optional[List[Dict[str, str]]] = None 
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
        "Title": title.strip(),
        "Description": description,
        "SystemInstructions": system_instructions,
        "Icon": icon,
        "Files": safe_files
    }

    safe_item = _omit_invalid_attrs(item)

    try:
        table.put_item(Item=safe_item)
        print(f"Arena created: {title} ({arena_id})")
    except Exception as e:
        print(f"Error creating arena: {e}")
        raise e

    return safe_item

def get_arenas_for_user(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all Arenas created by a specific user using the GSI.
    """
    if not user_id:
        raise ValueError("user_id must be provided")

    try:
        # CRITICAL UPDATE: Uses the IndexName to query by UserId
        response = table.query(
            IndexName='UserId-Index',
            KeyConditionExpression=Key('UserId').eq(user_id)
        )
        return response.get("Items", [])
    except Exception as e:
        print(f"Error fetching arenas for {user_id}: {e}")
        return []

def get_arena_details(user_id: str, arena_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the full configuration for a specific Arena.
    """
    try:
        # Assumes ArenaId is the Primary Key
        response = table.get_item(
            Key={'ArenaId': arena_id}
        )
        item = response.get('Item')

        # Security Check: Ensure the user owns this arena
        if item and item.get('UserId') == user_id:
            return item
        return None
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
    allowed_keys = {"Title", "Description", "SystemInstructions", "Icon", "Files"}
    
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_keys}
    if not filtered_updates:
        return {}

    update_parts = []
    expression_values = {':ts': datetime.utcnow().isoformat(), ':uid': user_id}
    expression_names = {'#ts': 'UpdatedAt'}

    for key, value in filtered_updates.items():
        attr_name = f"#{key}"
        val_name = f":{key}"
        
        update_parts.append(f"{attr_name} = {val_name}")
        expression_names[attr_name] = key
        expression_values[val_name] = value

    update_expression = "SET " + ", ".join(update_parts) + ", #ts = :ts"

    try:
        # ConditionExpression ensures we only update if the UserId matches
        response = table.update_item(
            Key={'ArenaId': arena_id},
            UpdateExpression=update_expression,
            ConditionExpression="UserId = :uid",
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW"
        )
        return response.get("Attributes", {})
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            print(f"Unauthorized update attempt for Arena {arena_id}")
            return {}
        print(f"Error updating arena {arena_id}: {e}")
        raise e

def delete_arena(user_id: str, arena_id: str):
    """
    Deletes an Arena configuration if the user owns it.
    """
    try:
        table.delete_item(
            Key={'ArenaId': arena_id},
            ConditionExpression="UserId = :uid",
            ExpressionAttributeValues={':uid': user_id}
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            print(f"Unauthorized delete attempt for Arena {arena_id}")
            return False
        print(f"Error deleting arena {arena_id}: {e}")
        return False