# src/config/web_search_config.py

"""
Web Search Configuration
Defines the allowed domains for the AI's web browsing capabilities.
"""

from typing import Dict, Any, Optional
from src.config.settings import settings  # 🟢 Kept for compatibility if used elsewhere

# ------------------------------------------------------------------
# 🔹 TRUSTED DOMAINS (ALLOW-LISTS) - Kept for reference only
# ------------------------------------------------------------------

INVICTO_DOMAINS = [
    "invicto.com.co"
]

ICFES_DOMAINS = [
    "icfes.gov.co"
]

UNAL_DOMAINS = [
    "unal.edu.co"
]

UNIANDES_DOMAINS = [
    "uniandes.edu.co"
]

# ------------------------------------------------------------------
# 🔹 HELPER FUNCTION
# ------------------------------------------------------------------

def get_search_filters(context: str) -> Optional[Dict[str, Any]]:
    """
    Returns the domain filter configuration based on the conversation context.
    """
    
    # 🟢 WEB SEARCH FILTERS DEACTIVATED
    # We are deliberately ignoring the Strict Mode toggle and domain arrays.
    # By returning a dictionary WITHOUT the 'allowed_domains' key, we instruct 
    # the assistant_client to use the Web Search tool in unrestricted OPEN WEB mode.

    context_upper = context.upper().strip() if context else ""
    
    # Enable unrestricted Web Search for these specific exam contexts
    if context_upper in ["ICFES", "UNAL", "UNIANDES", "BECAS", "SCHOLARSHIPS"]:
        return {"scope": "open_web", "search_enabled": True}
        
    # General Context:
    # Currently, general chat uses the AI's internal knowledge (returns None). 
    # If you want general chat to ALSO search the entire web, 
    # change the line below to: return {"scope": "open_web", "search_enabled": True}
    return None