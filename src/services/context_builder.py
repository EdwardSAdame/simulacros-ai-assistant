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

        # 3. Inject Name (or Anonymity)
        if name and name.strip():
            # ✅ Case A: User is Logged In
            signals.insert(1, f"The user is named {name}.")
        else:
            # 🟢 Case B: User is Guest (The Fix)
            # We explicitly state the name is unknown so the bot doesn't say "Guest"
            signals.insert(1, "The user has not provided a name. If asked, state that you do not know it.")

        return signals

    except Exception as e:
        logger.error(f"Error building runtime context: {e}")
        return [f"Page: {page}", "Sources: Invicto Knowledge Base."]