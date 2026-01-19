# src/services/context_builder.py
import logging
from typing import List, Optional
from src.utils.time_utils import get_current_time_info, infer_target_semester

logger = logging.getLogger(__name__)

def build_runtime_context(
    page: str, 
    user_id: str | None, 
    name: str | None, 
    email: str | None,
    requires_visuals: bool = False # Kept for compatibility with chat_service call
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
            f"Current Date: {time_info['full_human']}."
        ]

        # 3. Contextual Page Signal (Narrative)
        if page and page != "/" and page.strip():
            signals.append(f"Context: The user is currently browsing the page '{page}'. Tailor your answers to this specific section if relevant.")
        else:
            signals.append("Context: The user is on the home page.")

        # 4. Meaningful Target Signal (Goal-Oriented)
        if target_semester:
            signals.append(f"Goal: The user is likely preparing now to pass the admission exam and begin their university studies in semester {target_semester}.")

        # 5. Smart Identity Logic (AI-Driven Name Parsing)
        if name and name.strip():
            clean_name = name.strip()
            
            # Basic hygiene: still block obvious system defaults
            if clean_name.lower() in ["guest", "visitor", "user", "anonymous", "undefined"]:
                signals.append("User Identity: The user is anonymous. Do NOT refer to them as 'Guest'.")
            else:
                # 🟢 LOGIC: Give the AI the full name but instruct it to be smart.
                # It handles "EdwardAdame" -> "Edward", "123User" -> Ignore, etc.
                signals.append(
                    f"User Identity: The user's name is '{clean_name}'. "
                    "Use it ONLY if it is a valid human name. If it is numbers, gibberish, or a handle, ignore it. "
                    "Address them naturally by their first name."
                )
        else:
            signals.append("User Identity: The user is anonymous. Do NOT refer to them as 'Guest'.")

        return signals

    except Exception as e:
        logger.error(f"Error building runtime context: {e}")
        return [f"Page: {page}", f"Date: {get_current_time_info()['full_human']}"]