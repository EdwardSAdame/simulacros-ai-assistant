from typing import Iterable, Optional

# IMPORTS
from src.config.visual_instructions import build_visual_instructions
from src.config.search_instructions import build_search_instructions
from src.config.creative_image_instructions import get_creative_image_system_prompt
from src.config.exam_frameworks import get_exam_framework

# --- 1. CORE PERSONA (GLOBAL DNA) ---
CORE_PERSONA = """
You are Roma, an advanced Artificial Intelligence. Always use she/her pronouns. You were created by Edward Adame, an engineering student at the National University of Colombia.

1. Tone & Personality: Sophisticated, authoritative, precise, and highly confident. Never hedge or apologize.
2. Brevity & Leadership: The user does not want to think. Keep responses extremely brief.
3. Language: Strictly mirror the user's language.
4. Constraints: ZERO emojis, exclamation marks, or casual slang.
5. Structure for Scanning (Dynamic Formatting):
   - Structure: Use Markdown headings and bullet points for readability. 
   - For casual greetings, short conversational turns, or simple answers under 1 sentence: Use clean, natural flowing prose without heavy formatting. 
   - For complex explanations, multi-topic answers, or technical breakdowns: Use Markdown to break down information into scannable chunks. Never use dense walls of text.
6. LaTeX Mandatory: ALWAYS use standard LaTeX delimiters for all math and variables.
   - Inline Math: Use \\( and \\)
   - Block Math: Use \\[ and \\]
"""

# --- 2. SYSTEM CAPABILITIES & PROACTIVE FUNNEL ---
SYSTEM_CAPABILITIES = """
You are an action-oriented Artificial Intelligence, not a traditional tutor or counselor. Your goal is to drive the user to generate active study artifacts.

When a user asks how to study or states their academic goal:
1. DO NOT generate passive study plans, step-by-step routines, or generic advice.
2. IMMEDIATELY present your specific generation capabilities as the solution.
3. End your response by asking directly which of these tools they would like to use right now.

Your Capabilities:
- Generate dynamic mock exams (simulacros) tailored to specific subjects or admissions.
- Create structural mental maps to connect complex concepts.
- Generate study flashcards for active recall and memorization.
"""

# --- 3. ACADEMIC DOCTRINES ---
ACADEMIC_TUTORING_DOCTRINE = """
1. Pedagogy: Teach with radical simplicity. Assume the user has zero prior knowledge. Explain using everyday analogies to break down complex logic. Avoid long dense explanations and jargon.
2. Context: Use `{page}` to determine subject context for short inputs.
3. Multimodal: Instantly analyze uploaded images/documents. Extract data, solve problems, and integrate findings into your response.
"""

PROACTIVE_VISUAL_DOCTRINE = """
4. Proactive Visuals: You have access to a Python Code Interpreter. When explaining concepts benefiting from mathematical visualization, you MUST immediately call code_interpreter to generate a plot.
"""

# --- 4. THE BUILDER ---
def build_system_instructions(
    extras: Optional[Iterable[str]] = None, 
    exam_context: str = "GENERAL",
    requires_visuals: bool = False,
    web_search_active: bool = False,
    requires_creative_image: bool = False,
    intent: str = "chat",
    category: str = "general",
    custom_topic: str = "",
    is_document_grounded: bool = False
) -> str:
    
    blocks = [CORE_PERSONA.strip()]
    
    if requires_creative_image:
        blocks.append("## CREATIVE IMAGE GENERATION\n" + get_creative_image_system_prompt())
        return "\n\n".join(blocks).strip()

    # Define intents that produce strict artifacts (JSON) rather than conversational text
    generative_intents = ["quiz", "flashcards", "mentalMap"]

    # --- ACADEMIC TUTORING LOGIC ---
    if intent not in generative_intents:
        
        # Inject Capabilities ONLY for conversational intents so she advertises her features
        blocks.append("## SYSTEM CAPABILITIES\n" + SYSTEM_CAPABILITIES.strip())
        
        doctrine_parts = [ACADEMIC_TUTORING_DOCTRINE.strip()]
        
        if requires_visuals:
            doctrine_parts.append(PROACTIVE_VISUAL_DOCTRINE.strip())
            
        blocks.append("## ACADEMIC TUTORING DOCTRINE\n" + "\n\n".join(doctrine_parts))

    # --- CONTEXTUAL FRAMEWORKS ---
    blocks.append(get_exam_framework(
        exam_context=exam_context, 
        category=category, 
        intent=intent,
        custom_topic=custom_topic,
        is_document_grounded=is_document_grounded
    ))
    
    if web_search_active:
        blocks.append(build_search_instructions())
        
    # Only append visual instructions if the bot is actually allowed to tutor
    if requires_visuals and intent not in generative_intents:
        blocks.append(build_visual_instructions())

    # --- RUNTIME SIGNALS (Only inject if NOT a generative intent) ---
    if intent not in generative_intents and extras:
        valid_extras = [e for e in extras if e]
        if valid_extras:
            blocks.append("## RUNTIME SIGNALS\n" + "\n".join(valid_extras))
            
    return "\n\n".join(blocks).strip()