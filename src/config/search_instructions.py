def build_search_instructions(intent: str = "chat", category: str = "general") -> str:
    """
    Returns the strict protocols for Web Search, Temporal Awareness, and CITATIONS.
    Dynamically appends domain-specific search strategies based on intent and category.
    """
    base_instructions = """
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

    humanities_categories = [
        "ciencias_sociales", "sociales_ciudadanas", "sociales", 
        "lectura_critica", "analisis_textual", "ingles"
    ]

    if intent == "quiz" and category in humanities_categories:
        base_instructions += """
5. Academic Authority Sourcing: For this specific quiz, you MUST prioritize renowned, serious academic publications, institutional databases, and high-end cultural sites. Maintain an open search scope, but heavily filter for high-authority domains.
"""

    return base_instructions