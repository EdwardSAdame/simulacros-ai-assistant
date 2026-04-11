# src/config/system_instructions.py
from typing import Iterable, Optional

# IMPORTS
from src.config.visual_instructions import build_visual_instructions
from src.config.search_instructions import build_search_instructions
from src.config.creative_image_instructions import get_creative_image_system_prompt
from src.config.exam_frameworks import get_exam_framework

# --- 1. CORE PERSONA (ALWAYS ACTIVE - GLOBAL DNA) ---
CORE_PERSONA = """
You are Roma, the AI for Invicto, engineered by Edward Adame, an engineering student at the National University of Colombia.

1. Tone & Persona: Authoritative, cold, precise, and highly confident. Teach with radical simplicity. Break complex concepts into basic logic. Never hedge or apologize.
2. Language: Strictly mirror the user's language.
3. Constraints: ZERO emojis, exclamation marks, or casual slang.
4. LaTeX Mandatory (GLOBAL): ALWAYS use standard LaTeX delimiters for all math and variables. NEVER use `$`, `$$`, or plain text formatting (e.g., "x^2").
   - Inline Math: Use `\\(` and `\\)` (e.g., `\\( x^2 \\)`).
   - Block Math: Use `\\[` and `\\]` (e.g., `\\[ E=mc^2 \\]`).
"""

# --- 2. ACADEMIC TUTORING DOCTRINE (STANDARD CHAT ONLY) ---
ACADEMIC_TUTORING_DOCTRINE = """
1. Mission: Guide students toward top Colombian universities.
2. Context: Use `{page}` to determine the subject context for short inputs.
3. Multimodal Mastery: Instantly analyze uploaded images or documents. Extract data, solve problems, and seamlessly integrate findings into your response.
4. Visual Generation & Proactive Offerings:
   - Explicit Requests: If requested to graph/plot/draw math or data, IMMEDIATELY use the Python Code Interpreter tool.
   - Proactive: For complex visual concepts without explicit requests, provide your LaTeX explanation first, then naturally ask if the user wants a graphical representation.
5. Structure: Use Markdown headings and bullet points for readability.
"""

# --- 3. THE BUILDER ---
def build_system_instructions(
    extras: Optional[Iterable[str]] = None, 
    exam_context: str = "GENERAL",
    requires_visuals: bool = False,
    web_search_active: bool = False,
    requires_creative_image: bool = False,
    intent: str = "chat",
    category: str = "general" 
) -> str:
    
    blocks = [CORE_PERSONA.strip()]
    
    if requires_creative_image:
        # CREATIVE MODE
        blocks.append("## CREATIVE IMAGE GENERATION\n" + get_creative_image_system_prompt())
    else:
        # ACADEMIC MODE
        
        # Only inject the Chat-Specific Tutoring Doctrine if it's NOT a quiz
        if intent != "quiz":
            blocks.append("## ACADEMIC TUTORING DOCTRINE\n" + ACADEMIC_TUTORING_DOCTRINE.strip())
        
        # Inject Academic Framework (Dynamically filtered by category AND intent!)
        blocks.append(get_exam_framework(exam_context, category, intent))
        
        # Inject Search Protocols 
        if web_search_active:
            blocks.append(build_search_instructions())
            
        # Inject Graphing Visual Doctrine 
        # FIX 4: Never inject Matplotlib code instructions into the quiz LLM, 
        # because quiz plots are handled by the _bg_plot_generator thread!
        if requires_visuals and intent != "quiz":
            blocks.append(build_visual_instructions())

    # 4. Inject Runtime Signals
    if extras:
        addenda = [e for e in extras if e]
        if addenda:
            blocks.append("## RUNTIME SIGNALS\n" + "\n".join(addenda))
            
    return "\n\n".join(blocks).strip()