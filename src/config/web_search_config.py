# src/config/web_search_config.py

"""
Web Search Configuration
Defines the allowed domains for the AI's web browsing capabilities.
"""

from typing import Dict, Any, Optional

# ------------------------------------------------------------------
# 🔹 TRUSTED DOMAINS (ALLOW-LISTS)
# ------------------------------------------------------------------

# Your Domain (Always accessible)
# Covers: https://invicto.com.co/
INVICTO_DOMAINS = [
    "invicto.com.co"
]

# ICFES Context
# Authorizes: www.icfes.gov.co, mineducacion.gov.co
ICFES_DOMAINS = [
    "icfes.gov.co",
    "mineducacion.gov.co"
]

# UNAL Context
# Authorizes: admisiones.unal.edu.co, registro.unal.edu.co, unal.edu.co
UNAL_DOMAINS = [
    "unal.edu.co"
]

# Scholarships / Financial Context (Uniandes)
# Authorizes: aspirantes.uniandes.edu.co
UNIANDES_DOMAINS = [
    "uniandes.edu.co"
]

# ------------------------------------------------------------------
# 🔹 HELPER FUNCTION
# ------------------------------------------------------------------

def get_search_filters(context: str) -> Optional[Dict[str, Any]]:
    """
    Returns the domain filter configuration based on the conversation context.
    We inject INVICTO_DOMAINS into every specific context so the bot 
    can always cross-reference official info with your content.
    """
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
        
    # General Context: Return None (Open Web)
    # The bot can search Wikipedia, News, AND invicto.com.co freely.
    return None