# src/services/context_resolution.py

def determine_exam_context(page_url: str, message_text: str | None = None, current_locked_context: str | None = None) -> str:
    """
    Decides the Exam Context (UNAL vs ICFES vs GENERAL) with state-locking support.
    Priority:
    1. Explicit User Intent in Message (Overrides everything and establishes a new lock)
    2. Existing Locked Context (Maintains the current conversational state)
    3. URL Explicit Context (Initializes state based on the webpage if no lock exists)
    4. Default (General)
    """
    msg_lower = message_text.lower() if message_text else ""
    url_lower = page_url.lower() if page_url else ""
    
    # 1. Explicit User Intent (Hard Override)
    # Check for UNAL keywords
    if any(x in msg_lower for x in ["unal", "nacional", "universidad nacional"]):
        return "UNAL"
    # Check for ICFES keywords
    if any(x in msg_lower for x in ["icfes", "saber 11", "saber pro", "examen de estado"]):
        return "ICFES"
        
    # 2. Existing Lock (State Persistence)
    # If the database tells us we are locked into an exam, we stay locked.
    if current_locked_context and current_locked_context.upper() in ["UNAL", "ICFES", "GENERAL"]:
        return current_locked_context.upper()
        
    # 3. Analyze URL (Initial Context if no lock exists)
    if "unal" in url_lower: 
        return "UNAL"
    if "icfes" in url_lower: 
        return "ICFES"
            
    # 4. Fallback
    return "GENERAL"