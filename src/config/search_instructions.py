def build_search_instructions(intent: str = "chat", category: str = "general") -> str:
    """
    Returns the strict protocols for Web Search, Temporal Awareness, and CITATIONS.
    Dynamically branches into strictly isolated search strategies based on intent and category.
    """
    if intent == "quiz":
        quiz_instructions = """
## 7. WEB SEARCH PROTOCOL (STIMULUS ACQUISITION)
1. Execution Command: You MUST execute the `web_search` tool immediately to fetch a real-world reading passage, article, or stimulus to ground your quiz questions.
2. Citations: Append the source URL as an inline Markdown link at the end of your context blocks.
"""
        humanities_categories = [
            "ciencias_sociales", "sociales_ciudadanas", "sociales", 
            "lectura_critica", "analisis_textual", "ingles"
        ]

        if category in humanities_categories:
            quiz_instructions += (
                "3. Academic Authority Sourcing: For this specific quiz, you MUST prioritize renowned, "
                "serious academic publications, institutional databases, and high-end cultural sites. "
                "Maintain an open search scope, but heavily filter for high-authority domains.\n"
            )
            
        return quiz_instructions.strip()

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
""".strip()