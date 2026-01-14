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

### CITATION FORMATTING RULES (STRICT):
1. When you use information from a search result, you must cite it using a Markdown link inline.
2. **CRITICAL:** The link text must be the **exact title of the webpage** or a descriptive headline, NOT the domain name or "link".
   - ✅ CORRECT: "Según el artículo [Rusia advierte a EE.UU. sobre Venezuela](https://reuters.com/...)"
   - ❌ WRONG: "Según [reuters.com](https://reuters.com/...)"
   - ❌ WRONG: "Según [1](https://reuters.com/...)"
3. Place these citations naturally within the sentence.
"""