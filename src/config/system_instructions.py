from typing import Iterable, Optional

# IMPORTS
from src.config.visual_instructions import build_visual_instructions
from src.config.search_instructions import build_search_instructions
from src.config.creative_image_instructions import get_creative_image_system_prompt
from src.config.exam_frameworks import get_exam_framework
from src.config.exam_constraints import get_active_exam_lockdown_instruction

# --- 1. CORE PERSONA (GLOBAL DNA) ---
CORE_PERSONA = """
You are Roma, an AI of Invicto. Always use she/her pronouns. You were created by Edward Adame, an engineering student at the National University of Colombia.

1. Tone & Personality: Sophisticated, authoritative, precise, and highly confident. Never hedge or apologize.
2. Language: Strictly mirror the user's language.
3. Constraints: ZERO emojis, exclamation marks, or casual slang.
4. Structure: Use Markdown headings and bullet points for readability.
5. LaTeX Mandatory: ALWAYS use standard LaTeX delimiters for all math and variables.
   - Inline Math: Use \\( and \\)
   - Block Math: Use \\[ and \\]
"""

# --- 2. ACADEMIC DOCTRINES ---
ACADEMIC_TUTORING_DOCTRINE = """
1. Pedagogy: Teach with radical simplicity. Assume the user has zero prior knowledge. Explain using everyday analogies to break down complex logic. Avoid long dense explanations and jargon.
2. Context: Use `{page}` to determine subject context for short inputs.
3. Multimodal: Instantly analyze uploaded images/documents. Extract data, solve problems, and integrate findings into your response.
"""

PROACTIVE_VISUAL_DOCTRINE = """
4. Proactive Visuals: You have access to a Python Code Interpreter. When explaining concepts benefiting from mathematical visualization, you MUST immediately call code_interpreter to generate a plot.
"""

# --- 3. THE BUILDER ---
def build_system_instructions(
    extras: Optional[Iterable[str]] = None, 
    exam_context: str = "GENERAL",
    requires_visuals: bool = False,
    web_search_active: bool = False,
    requires_creative_image: bool = False,
    intent: str = "chat",
    category: str = "general",
    exam_state: str | None = None
) -> str:
    
    blocks = [CORE_PERSONA.strip()]
    
    if requires_creative_image:
        blocks.append("## CREATIVE IMAGE GENERATION\n" + get_creative_image_system_prompt())
        return "\n\n".join(blocks).strip()

    # Define intents that produce strict artifacts (JSON) rather than conversational text
    generative_intents = ["quiz", "flashcards", "mentalMap"]

    # --- ACADEMIC / PROCTOR MODE LOGIC ---
    if intent not in generative_intents:
        
        # Branch A: The user is in an active exam (Proctor Persona)
        if exam_state and exam_state.strip().upper() == "ACTIVE":
            blocks.append("## PROCTOR DOCTRINE\n" + get_active_exam_lockdown_instruction().strip())
            
        # Branch B: The user is NOT in an exam (Tutor Persona)
        else:
            doctrine_parts = [ACADEMIC_TUTORING_DOCTRINE.strip()]
            
            if requires_visuals:
                doctrine_parts.append(PROACTIVE_VISUAL_DOCTRINE.strip())
                
            blocks.append("## ACADEMIC TUTORING DOCTRINE\n" + "\n\n".join(doctrine_parts))

    # --- CONTEXTUAL FRAMEWORKS ---
    blocks.append(get_exam_framework(exam_context, category, intent))
    
    if web_search_active:
        blocks.append(build_search_instructions())
        
    # Only append visual instructions if the bot is actually allowed to tutor
    if requires_visuals and intent not in generative_intents and (exam_state is None or exam_state.strip().upper() != "ACTIVE"):
        blocks.append(build_visual_instructions())

    # --- RUNTIME SIGNALS (Only inject if NOT a generative intent) ---
    if intent not in generative_intents and extras:
        valid_extras = [e for e in extras if e]
        if valid_extras:
            blocks.append("## RUNTIME SIGNALS\n" + "\n".join(valid_extras))
            
    return "\n\n".join(blocks).strip()