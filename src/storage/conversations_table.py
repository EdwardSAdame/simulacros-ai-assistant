# src/storage/conversations_table.py
import boto3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any # Added List, Dict, Any
from boto3.dynamodb.conditions import Key # Added Key for querying

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserConversations")

# Only these attrs must NOT be empty (because of GSIs)
KEYS_DISALLOW_EMPTY = {"Email"}

def _omit_invalid_attrs(item: dict) -> dict:
    """
    Remove attributes that are None.
    Remove empty strings ONLY for attributes listed in KEYS_DISALLOW_EMPTY.
    Keep empty strings for non-key, informational fields like Name.
    """
    cleaned = {}
    for k, v in item.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            if k in KEYS_DISALLOW_EMPTY and v == "":
                continue
        # Keep empty lists/dicts if they are not keys causing issues
        # if v == [] or v == {}:
        #    continue
        cleaned[k] = v
    return cleaned


def save_conversation(
    user_id: str,
    name: Optional[str],
    email: Optional[str],
    title: str,
    page: str,
):
    """
    Create a new conversation header in UserConversations.

    SCHEMA:
      PK: UserId (S)
      SK: Timestamp (S, ISO8601 creation time)
      Attrs:
        - ConversationId (S)   # unique identifier
        - Title (S)
        - Page (S)
        - Name (S)
        - Email (S, optional)
    """
    if not user_id or (isinstance(user_id, str) and user_id.strip() == ""):
        raise ValueError("user_id must be a non-empty string")

    conversation_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    item = {
        # Keys
        "UserId": user_id,         # PK
        "Timestamp": timestamp,    # SK (chronological ordering)

        # Attributes
        "ConversationId": conversation_id,
        "Name": (name if name is not None else ""),
        "Email": email,  # omitted if empty/None
        "Title": title,
        "Page": page,
    }

    safe_item = _omit_invalid_attrs(item)
    table.put_item(Item=safe_item)

    return {
        "ConversationId": conversation_id,
        "Timestamp": timestamp,
        "Name": item["Name"],
        "Email": email,
        "Title": title,
        "Page": page,
    }

# --- NEW FUNCTION ---
def get_conversations_for_user(
    user_id: str,
    limit: int = 50,
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetch conversation headers for a specific user.

    :param user_id: The ID of the user whose conversations to fetch.
    :param limit: Maximum number of conversations to return.
    :param ascending: If True, return oldest first; if False (default), return newest first.
    :return: A list of conversation header items (dictionaries).
    """
    if not user_id:
        raise ValueError("user_id must be provided")

    response = table.query(
        KeyConditionExpression=Key('UserId').eq(user_id),
        ScanIndexForward=ascending, # False = Sort Key descending (newest first)
        Limit=limit,
        # ProjectionExpression can be used to only fetch specific attributes if needed
        # e.g., "ConversationId, Title, Timestamp"
        ProjectionExpression="ConversationId, Title, Timestamp" # Fetch only needed fields
    )
    
    conversations = response.get("Items", [])
    
    # Note: DynamoDB Query results are already sorted by the sort key (Timestamp)
    # based on ScanIndexForward. No extra sorting needed here.
    
    # Handle pagination if you expect more than 'limit' or > 1MB of data
    # (For simplicity, pagination is omitted here but might be needed for large histories)
    # while 'LastEvaluatedKey' in response:
    #     response = table.query(...)
    #     conversations.extend(response.get('Items', []))

    return conversations
# --- END NEW FUNCTION ---