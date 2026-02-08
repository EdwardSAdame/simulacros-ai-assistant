# src/services/history_service.py
import json
from decimal import Decimal
from typing import List, Dict, Any
from src.storage.messages_table import get_recent_messages
from src.utils.logging_utils import log_event

def decimal_default(obj):
    """Helper to serialize Decimal objects for JSON."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def build_history_list(conversation_id: str, max_user: int = 3, max_assistant: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves recent messages from the database and formats them for the OpenAI API.
    Handles hidden context injection for assistant messages with metadata.
    """
    try:
        msgs = get_recent_messages(conversation_id=conversation_id, limit=20, ascending=True)
        if not msgs: 
            return []

        user_msgs = [m for m in msgs if m.get("Role") == "user"][-max_user:]
        asst_msgs = [m for m in msgs if m.get("Role") == "assistant"][-max_assistant:]
        
        # Merge and sort by timestamp to maintain conversation flow
        merged = sorted(user_msgs + asst_msgs, key=lambda m: m["Timestamp"])

        history_list = []
        for m in merged:
            role = m.get("Role", "user")
            text_content = m.get("MessageText", "")
            
            # Inject metadata context if available (Assistant only)
            metadata = m.get("Metadata") or m.get("Meta")
            if role == "assistant" and metadata:
                try:
                    metadata_str = json.dumps(metadata, default=decimal_default)
                    hidden_context = (
                        f"\n\n[SYSTEM CONTEXT: User cannot see this. "
                        f"I previously generated this interactive content: {metadata_str}. "
                        f"I must use this data to answer follow-up questions.]"
                    )
                    text_content += hidden_context
                except Exception:
                    pass

            msg_type = "input_text" if role == "user" else "output_text"
            content = [{"type": msg_type, "text": text_content}] 
            history_list.append({"role": role, "content": content})
        
        return history_list
    except Exception as e:
        log_event("history_fetch_failed", {"conversation_id": conversation_id}, level="warning", error=e)
        return []