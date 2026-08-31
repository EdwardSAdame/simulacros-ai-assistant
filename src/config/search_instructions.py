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
3. Translation & Language Alignment (CRITICAL): The retrieved passage MUST be translated into the exact language used by the user in their prompt before populating the `context_text` field. Dynamically adapt to the user's language. The ONLY exception is if the quiz subject specifically evaluates a foreign language.
"""
        # Note: For strict DRY compliance, consider moving this list to a centralized constants file 
        # in the future if these categories are referenced by other services like quiz_service.py.
        humanities_categories = [
            "ciencias_sociales", "sociales_ciudadanas", "sociales", 
            "lectura_critica", "analisis_textual", "ingles"
        ]

        if category in humanities_categories:
            quiz_instructions += (
                "4. Academic Authority Sourcing: For this specific quiz, you MUST prioritize renowned sources. "
                "serious academic publications, institutional databases, and high-end cultural sites. "
                "Maintain an open search scope, but heavily filter for high-authority domains.\n"
            )
            
        return quiz_instructions.strip()

    return """
## 7. WEB SEARCH PROTOCOL
1. Autonomy & Silence: NEVER ask for permission to search. Execute `web_search` silently and immediately when lacking information. Do not output conversational filler or transitional phrases.
2. Mandatory Web Search Triggers: Use `web_search` for:
   - Calendars, dates, registration, deadlines.
   - Costs, fees, prices.
   - Real-time events, news.
   - Fact verification or unknown entities/people.
3. Execution Command: The `web_search` tool has been attached because this query matches the triggers above. You MUST execute it to ground your response.
4. Citations: Format links as inline Markdown. Use the Article Title or a Descriptive Headline as the anchor text. NEVER use raw URLs, domain names, or wrap the link in extra parentheses.
""".strip()