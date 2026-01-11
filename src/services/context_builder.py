# src/services/context_builder.py
import logging
from typing import List, Optional
from src.utils.time_utils import get_current_time_info, infer_target_semester

logger = logging.getLogger(__name__)

def build_runtime_context(
    page: str, 
    user_id: str | None, 
    name: str | None, 
    email: str | None
) -> List[str]:
    """
    Constructs the dynamic 'Runtime Signals' list injected into the System Prompt.
    Handles logic for time, target semester, and natural language personalization.
    """
    try:
        # 1. Calculate Temporal Context
        time_info = get_current_time_info()
        target_semester = infer_target_semester()

        # 2. Build Base Signals
        signals = [
            f"Today is {time_info['full_human']}.",
            f"Page: {page if page else '/'}",
            f"Target: {target_semester}",
            "Sources: Invicto Knowledge Base."
        ]

        # 3. VALIDATE THE NAME (The Fix)
        # We explicitly block "Guest", "Visitor", etc. to prevent false positives.
        has_valid_name = False
        if name and name.strip():
            clean_name = name.strip().lower()
            # If the name is generic, we treat it as if it doesn't exist
            if clean_name not in ["guest", "visitor", "user", "anonymous", "undefined"]:
                has_valid_name = True

        # 4. Inject Logic
        if has_valid_name:
            signals.insert(1, f"The user is named {name}.")
        else:
            # 🟢 STRICT NEGATIVE CONSTRAINT
            # We tell the bot explicitly: "Do NOT guess."
            signals.insert(1, "The user is anonymous. Do NOT refer to them as 'Guest'. If asked for their name, state clearly that you do not know it.")

        return signals

    except Exception as e:
        logger.error(f"Error building runtime context: {e}")
        return [f"Page: {page}", "Sources: Invicto Knowledge Base."]