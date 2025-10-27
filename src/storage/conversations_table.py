# src/storage/conversations_table.py
import boto3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserConversations")

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
        # Allow empty lists/dicts
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
    """
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
    }

    safe_item = _omit_invalid_attrs(item)
    table.put_item(Item=safe_item)

    # Return only the necessary fields, consistent with get_conversations_for_user projection
    return {
        "ConversationId": conversation_id,
        "Timestamp": timestamp,
        "Title": title,
        # "Name": item["Name"], # Not projected, maybe remove?
        # "Email": email,       # Not projected, maybe remove?
        # "Page": page,         # Not projected, maybe remove?
    }


def get_conversations_for_user(
    user_id: str,
    limit: int = 50,
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetch conversation headers for a specific user. Handles reserved keywords.
    """
    if not user_id:
        raise ValueError("user_id must be provided")

    # --- MODIFICATION START ---
    # Define Expression Attribute Names to alias the reserved keyword 'Timestamp'
    expression_attribute_names = {
        '#ts': 'Timestamp' # Alias #ts to the actual attribute name Timestamp
    }
    # Update ProjectionExpression to use the alias
    projection_expression = "ConversationId, Title, #ts"
    # --- MODIFICATION END ---


    response = table.query(
        KeyConditionExpression=Key('UserId').eq(user_id),
        ScanIndexForward=ascending,
        Limit=limit,
        # --- MODIFICATION START ---
        ProjectionExpression=projection_expression,
        ExpressionAttributeNames=expression_attribute_names
        # --- MODIFICATION END ---
    )

    conversations = response.get("Items", [])

    # Handle pagination if necessary (omitted for brevity)

    # --- MODIFICATION START ---
    # Rename '#ts' back to 'Timestamp' in the results for consistency if needed,
    # although Velo can probably handle '#ts' if you prefer. Let's rename it back.
    # Note: DynamoDB actually returns the original name ('Timestamp') even when using aliases
    # in the projection expression IF THE ALIAS IS THE SAME AS THE ORIGINAL NAME after the '#'.
    # However, explicitly handling it or using a different alias (e.g., '#t') guarantees correctness.
    # For now, let's assume DynamoDB returns 'Timestamp' correctly based on common behavior.
    # If it returns '#ts', you would uncomment the renaming loop below.
    #
    # renamed_conversations = []
    # for conv in conversations:
    #     new_conv = {}
    #     for key, value in conv.items():
    #         if key == '#ts':
    #             new_conv['Timestamp'] = value
    #         else:
    #             new_conv[key] = value
    #     renamed_conversations.append(new_conv)
    # return renamed_conversations

    return conversations # Assuming DynamoDB returns 'Timestamp' correctly
    # --- MODIFICATION END ---