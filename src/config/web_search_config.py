# src/config/web_search_config.py

"""
Web Search Configuration
Defines the search availability for the AI's web browsing capabilities.
"""

from typing import Dict, Any, Optional
from src.config.settings import settings  # Kept for compatibility if used elsewhere

# ------------------------------------------------------------------
# 🔹 HELPER FUNCTION
# ------------------------------------------------------------------

def get_search_filters(context: str) -> Optional[Dict[str, Any]]:
    """
    Returns the search configuration based on the conversation context.
    Instructs the assistant_client to use the Web Search tool in unrestricted OPEN WEB mode.
    """
    
    context_upper = context.upper().strip() if context else ""
    
    # Enable unrestricted Web Search for these specific exam contexts
    if context_upper in ["ICFES", "UNAL", "UNIANDES", "BECAS", "SCHOLARSHIPS"]:
        return {"scope": "open_web", "search_enabled": True}
        
    # General Context:
    # Currently, general chat uses the AI's internal knowledge (returns None). 
    # If you want general chat to ALSO search the entire web, 
    # change the line below to: return {"scope": "open_web", "search_enabled": True}
    return None