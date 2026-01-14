# src/config/web_search_config.py

"""
Web Search Configuration
Defines the allowed domains for the AI's web browsing capabilities.
"""

from typing import Dict, Any, Optional
from src.config.settings import settings  # 🟢 Import settings to check toggle

# ------------------------------------------------------------------
# 🔹 TRUSTED DOMAINS (ALLOW-LISTS)
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
    
    # 🟢 1. CHECK GLOBAL TOGGLE
    # If Strict Mode is FALSE (set in AWS), we return a dummy truthy dict.
    # This ensures the assistant_client ADDS the web_search tool,
    # but applies NO domain filters.
    if not settings.WEB_SEARCH_STRICT_MODE:
        return {"scope": "open_web"} 

    # 🟢 2. STRICT MODE LOGIC (Default)
    # If we are here, we MUST filter by specific domains.
    
    context_upper = context.upper().strip() if context else ""
    
    # Base list always includes your domain
    target_domains = INVICTO_DOMAINS.copy()
    
    if context_upper == "ICFES":
        target_domains.extend(ICFES_DOMAINS)
        return {"allowed_domains": target_domains}
    
    if context_upper == "UNAL":
        target_domains.extend(UNAL_DOMAINS)
        return {"allowed_domains": target_domains}
        
    if context_upper in ["UNIANDES", "BECAS", "SCHOLARSHIPS"]:
        target_domains.extend(UNIANDES_DOMAINS)
        return {"allowed_domains": target_domains}
        
    # General Context in Strict Mode:
    # If strict mode is ON, "General" usually implies NO search is allowed 
    # (or search only Invicto). Returning None disables the tool.
    return None