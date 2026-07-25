import logging
from typing import List, Dict, Optional
from src.utils.time_utils import get_current_time_info, infer_target_semester
from src.storage.purchase_table import get_latest_active_subscription 

logger = logging.getLogger(__name__)

def build_runtime_context(
    page: str, 
    user_id: Optional[str], 
    name: Optional[str], 
    email: Optional[str],
    requires_visuals: bool = False,
    attached_documents: Optional[List[Dict[str, str]]] = None
) -> List[str]:
    """
    Constructs the dynamic 'Runtime Signals' list injected into the System Prompt.
    Handles logic for time, target semester, natural language personalization,
    user subscription status, and dynamic document citation rules.
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
            season = target_semester.split("-")[-1]
            signals.append(
                f"TARGET SEMESTER: The user is EXPLICITLY applying for admission for semester {target_semester}. "
                f"You MUST prioritize data, trends, and calculations for historical semesters ending in '-{season}' "
                f"due to seasonality differences in admission scores. If database insights provide a 'recommended_safe_target_for_semesters_ending_in_{season}', you must use that specific calculation."
            )

        # 4. Smart Identity Logic
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

        # 5. Subscription Awareness Hydration
        if user_id:
            try:
                subscription = get_latest_active_subscription(user_id)
                if subscription:
                    plan_name = subscription.get("PlanName", "Premium")
                    end_date = subscription.get("EndDate", "Unknown")
                    signals.append(f"Subscription Status: {plan_name} | Expires: {end_date}")
                else:
                    signals.append("Subscription Status: Free Tier")
            except Exception as e:
                logger.error(f"Failed to hydrate subscription context: {e}")
        
        # 6. Dynamic Document Citation Injection
        if attached_documents:
            doc_context = (
                "DOCUMENT CITATION RULES:\n"
                "You have been provided with attached documents in this request. "
                "When extracting information, quoting, or answering based on these documents, you MUST cite your source using strict Markdown links.\n"
                "Available Documents Mapping:\n"
            )
            
            for doc in attached_documents:
                doc_name = doc.get("name", "Document")
                doc_url = doc.get("url", "")
                doc_context += f"- [{doc_name}]({doc_url})\n"
                
            doc_context += (
                "Citation Format: You must append the exact Markdown link of the document immediately after the relevant sentence or claim. "
                "Example: 'The boiling point is 100 degrees Celsius [Document Name](https://document-url.com).'"
            )
            
            signals.append(doc_context)
            
        return signals

    except Exception as e:
        logger.error(f"Error building runtime context: {e}")
        return [f"Date: {get_current_time_info()['full_human']}"]