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

        # 3. Inject Name with LLM Discretion (The Fix)
        if name and name.strip():
            clean_name = name.strip()
            
            # Basic hygiene: still block obvious system defaults
            if clean_name.lower() in ["guest", "visitor", "user", "anonymous", "undefined"]:
                signals.insert(1, "The user is anonymous. Do NOT refer to them as 'Guest'.")
            else:
                # 🟢 LLM SELF-CORRECTION INSTRUCTION
                signals.insert(1, f"The user's display name is '{clean_name}'. Use it ONLY if it is a valid human name. If it is numbers, gibberish, or a handle, ignore it.")
        else:
            signals.insert(1, "The user is anonymous. Do NOT refer to them as 'Guest'.")

        return signals

    except Exception as e:
        logger.error(f"Error building runtime context: {e}")
        return [f"Page: {page}", "Sources: Invicto Knowledge Base."]