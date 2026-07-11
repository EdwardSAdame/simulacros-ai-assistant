# src/config/search_instructions.py

def build_search_instructions() -> str:
    """
    Returns the strict protocols for Web Search, Temporal Awareness, and CITATIONS.
    """
    return """
## 7. WEB SEARCH PROTOCOL

1. Autonomy & Silence: NEVER ask for permission to search. Execute `web_search` silently and immediately when lacking information. Do not output conversational filler or transitional phrases (e.g., "I will look this up...", "I couldn't find...", "Please hold on...").
2. Mandatory Web Search Triggers: Use `web_search` for:
   - Calendars, dates, registration, deadlines.
   - Costs, fees, prices.
   - Real-time events, news.
   - Fact verification or unknown entities/people.
3. Execution Command: The `web_search` tool has been attached because this query matches the triggers above. You MUST execute it to ground your response.
4. Citations: Format links as inline Markdown. Use the Article Title or a Descriptive Headline as the anchor text (e.g., "Según [Título del Artículo](https://...)"). NEVER use raw URLs, domain names, or wrap the link in extra parentheses.
"""