# src/services/context_builder.py
import logging
from typing import List, Optional
from src.utils.time_utils import get_current_time_info, infer_target_semester

# 🟢 NEW IMPORT: This connects to your DynamoDB table
from src.storage.purchase_table import get_latest_active_subscription 

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
    Handles logic for time, target semester, natural language personalization,
    and user subscription status.
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

        # 4. Meaningful Target Signal (Strict Goal-Oriented Directive)
        if target_semester:
            season = target_semester.split("-")[-1] # Extracts '1' or '2'
            signals.append(
                f"TARGET SEMESTER: The user is EXPLICITLY applying for admission for semester {target_semester}. "
                f"You MUST prioritize data, trends, and calculations for historical semesters ending in '-{season}' "
                f"due to seasonality differences in admission scores. If database insights provide a 'recommended_safe_target_for_semesters_ending_in_{season}', you must use that specific calculation."
            )

        # 5. Smart Identity Logic (AI-Driven Name Parsing)
        if name and name.strip():
            clean_name = name.strip()
            
            # Basic hygiene: still block obvious system defaults
            if clean_name.lower() in ["guest", "visitor", "user", "anonymous", "undefined"]:
                signals.append("User Identity: The user is anonymous. Do NOT refer to them as 'Guest'.")
            else:
                signals.append(
                    f"User Identity: The user's name is '{clean_name}'. "
                    "Use it ONLY if it is a valid human name. If it is numbers, gibberish, or a handle, ignore it. "
                    "Address them naturally by their first name."
                )
        else:
            signals.append("User Identity: The user is anonymous. Do NOT refer to them as 'Guest'.")

        # 🟢 6. SUBSCRIPTION AWARENESS HYDRATION
        # This is where we extract the data from your DynamoDB table!
        if user_id:
            try:
                subscription = get_latest_active_subscription(user_id)
                if subscription:
                    plan_name = subscription.get("PlanName", "Premium")
                    end_date = subscription.get("EndDate", "Unknown")
                    # Tell the AI exactly what plan they have and when it expires
                    signals.append(
                        f"Subscription Status: The user has an active premium subscription called '{plan_name}'. "
                        f"If they ask, their subscription is valid until {end_date}."
                    )
                else:
                    signals.append("Subscription Status: The user is on the Free Tier.")
            except Exception as e:
                logger.error(f"Failed to hydrate subscription context: {e}")
                signals.append("Subscription Status: Unknown.")
        else:
            signals.append("Subscription Status: Anonymous User.")

        return signals

    except Exception as e:
        logger.error(f"Error building runtime context: {e}")
        return [f"Page: {page}", f"Date: {get_current_time_info()['full_human']}"]