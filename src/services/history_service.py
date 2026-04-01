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

# 🔹 FIX: Increased memory limits from 3 to 10 to support long educational interactions
def build_history_list(conversation_id: str, max_user: int = 10, max_assistant: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves recent messages from the database and formats them for the OpenAI API.
    Handles hidden context injection for assistant messages with metadata to prevent History Desync.
    """
    try:
        # 🔹 FIX: Increased DB fetch limit to 40 to guarantee we retrieve the full requested window
        msgs = get_recent_messages(conversation_id=conversation_id, limit=40, ascending=True)
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
                    # GENERALIZED ANTI-DESYNC FIX
                    # Explicitly instruct the AI that the widget is already rendered.
                    hidden_context = (
                        f"\n\n[SYSTEM LOG: I successfully generated and delivered a rich interactive UI widget "
                        f"(type: {metadata.get('type', 'rich_payload')}) to the user with this payload: {metadata_str}. "
                        f"This payload is ALREADY VISIBLE on the user's screen. "
                        f"I MUST NOT re-generate, repeat, or output this data in my text responses. "
                        f"I will only use it as hidden memory context to concisely answer their next specific question.]"
                    )
                    text_content += hidden_context
                except Exception as e:
                    log_event("history_metadata_parse_failed", {"error": str(e)}, level="warning")

            msg_type = "input_text" if role == "user" else "output_text"
            content = [{"type": msg_type, "text": text_content}] 
            history_list.append({"role": role, "content": content})
        
        return history_list
    except Exception as e:
        log_event("history_fetch_failed", {"conversation_id": conversation_id}, level="warning", error=e)
        return []