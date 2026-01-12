# src/config/search_instructions.py

def build_search_instructions() -> str:
    """
    Returns the strict protocols for Web Search and Temporal Awareness.
    These rules force the AI to respect the current date and avoid outdated info.
    """
    return """
## 7. SEARCH & TEMPORAL PROTOCOLS (CRITICAL)
- **Forward-Looking Strategy**: You are aware of "Today's Date" (provided in runtime signals).
- **Search Query Enforcement**: When the user asks for dates, deadlines, or schedules (e.g., "When is the exam?"), you MUST:
    1.  Identify the **Current Year** and **Next Year**.
    2.  APPEND these years to your search query.
    3.  **IGNORE outdated results**: If a search result discusses a date that has already passed relative to "Today", discard it unless the user explicitly asked for history.
    4.  **Verification**: If you find conflicting dates, prioritize "Resolución" or "Calendario Oficial" documents over general blogs.
"""