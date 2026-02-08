# src/services/context_resolution.py

def determine_exam_context(page_url: str, message_text: str | None = None) -> str:
    """
    Decides the Exam Context (UNAL vs ICFES vs GENERAL).
    Priority:
    1. URL Explicit Context (e.g. user is inside /simulacro-unal)
    2. User Intent in Message (e.g. user says "quiero unal" on homepage)
    3. Default (General)
    """
    # 1. Analyze URL (The "Room" the user is in)
    if page_url:
        url_lower = page_url.lower()
        if "unal" in url_lower: return "UNAL"
        if "icfes" in url_lower: return "ICFES"
    
    # 2. Analyze Message (Only if URL is generic)
    if message_text:
        msg_lower = message_text.lower()
        # Check for UNAL keywords
        if any(x in msg_lower for x in ["unal", "nacional", "universidad nacional"]):
            return "UNAL"
        # Check for ICFES keywords
        if any(x in msg_lower for x in ["icfes", "saber 11", "saber pro", "estado"]):
            return "ICFES"
            
    # 3. Fallback
    return "GENERAL"