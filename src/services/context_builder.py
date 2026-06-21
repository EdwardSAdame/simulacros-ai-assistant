# src/services/context_builder.py
import logging
from typing import List, Optional
from src.utils.time_utils import get_current_time_info, infer_target_semester
from src.storage.purchase_table import get_latest_active_subscription 

logger = logging.getLogger(__name__)

def build_runtime_context(
    page: str, 
    user_id: str | None, 
    name: str | None, 
    email: str | None,
    requires_visuals: bool = False, # Kept for compatibility with chat_service call
    exam_state: str | None = None   # Left in signature to prevent breaking function calls, but no longer used here
) -> List[str]:
    """
    Constructs the dynamic 'Runtime Signals' list injected into the System Prompt.
    Handles logic for time, target semester, natural language personalization,
    and user subscription status.
    """
    try:
        # 1. Calculate Temporal Context
        time_info = get_current_time_info()
        target_semester = infer_target_semester()

        # 2. Time Signal
        signals = [
            f"Current Date: {time_info['full_human']}."
        ]

        # 3. Target Semester Signal
        if target_semester:
            season = target_semester.split("-")[-1] # Extracts '1' or '2'
            signals.append(
                f"TARGET SEMESTER: The user is EXPLICITLY applying for admission for semester {target_semester}. "
                f"You MUST prioritize data, trends, and calculations for historical semesters ending in '-{season}' "
                f"due to seasonality differences in admission scores. If database insights provide a 'recommended_safe_target_for_semesters_ending_in_{season}', you must use that specific calculation."
            )

        # 4. Smart Identity Logic (Restored to original robust logic)
        if name and name.strip():
            clean_name = name.strip()
            
            if clean_name.lower() in ["guest", "visitor", "user", "anonymous", "undefined"]:
                signals.append("User Identity: The user is anonymous. Do NOT refer to them as 'Guest'.")
            else:
                signals.append(
                    f"User Identity: The user's name is '{clean_name}'. "
                    "Use it ONLY if it is a valid human name. If it is numbers, gibberish, or a handle, ignore it. "
                    "Address them naturally by only their first name."
                )
        else:
            signals.append("User Identity: The user is anonymous. Do NOT refer to them as 'Guest'.")

        # 5. Subscription Awareness Hydration (Minimalist format)
        if user_id:
            try:
                subscription = get_latest_active_subscription(user_id)
                if subscription:
                    plan_name = subscription.get("PlanName", "Premium")
                    end_date = subscription.get("EndDate", "Unknown")
                    # Clean, token-saving injection
                    signals.append(f"Subscription Status: {plan_name} | Expires: {end_date}")
                else:
                    signals.append("Subscription Status: Free Tier")
            except Exception as e:
                logger.error(f"Failed to hydrate subscription context: {e}")
        
        # NOTE: The anti-cheat lockdown has been moved to src/config/exam_constraints.py 
        # and injected directly into system_instructions.py
        
        return signals

    except Exception as e:
        logger.error(f"Error building runtime context: {e}")
        return [f"Date: {get_current_time_info()['full_human']}"]