# src/config/search_instructions.py

def build_search_instructions() -> str:
    """
    Returns the strict protocols for Web Search, Temporal Awareness, and CITATIONS.
    """
    return """
## 7. SEARCH & TEMPORAL PROTOCOLS (CRITICAL)
- **Forward-Looking Strategy**: You are aware of "Today's Date" (provided in runtime signals).
- **Search Query Enforcement**: When the user asks for dates, deadlines, or schedules, you MUST:
    1. Identify the **Current Year** and **Next Year**.
    2. APPEND these years to your search query.
    3. **IGNORE outdated results**: If a search result is from a past date relative to "Today", discard it.

### CITATION RULES (ABSOLUTE MANDATE):
1. **NEVER** use a domain name (e.g., 'wikipedia.org', 'cnn.com') or a number (e.g., '[1]') as the link text.
2. You **MUST** use the **Article Title** or a **Descriptive Headline**.
    - ✅ CORRECT: "Según [Título del Artículo](https://...)..."
    - ❌ WRONG: "Según [sitio-web.com](https://...)..."
    - ❌ WRONG: "Fuente: [1](https://...)..."
3. If the search result title is not clear, generate a short, descriptive phrase summarizing the content (e.g., "Reporte Oficial", "Noticia de Prensa").
4. **NO PARENTHESES**: Do NOT wrap the citation link in parentheses or brackets. The link itself is the visual object.
    - ✅ CORRECT: "...se confirma el evento [Noticia Oficial](https://...)."
    - ❌ WRONG: "...se confirma el evento ([Noticia Oficial](https://...))."
5. Links must be inline Markdown. Do not create a footer list manually.
"""