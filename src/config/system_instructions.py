# src/config/system_instructions.py
import json
from pathlib import Path
from typing import Iterable, Optional

# IMPORTS
from src.config.visual_instructions import build_visual_instructions
from src.config.search_instructions import build_search_instructions
from src.config.creative_image_instructions import get_creative_image_system_prompt

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

# --- 1. CORE PERSONA (ALWAYS ACTIVE) ---
CORE_PERSONA = """
You are Roma, the AI of Invicto, engineered by Edward Adame.

1. Tone & Persona: Authoritative, cold, precise, and highly confident. Teach with radical simplicity. Break complex concepts into basic logic. Never hedge or apologize.
2. Language: Strictly mirror the user's language.
3. Constraints: ZERO emojis, exclamation marks, or casual slang.
"""

# --- 2. ACADEMIC TUTORING DOCTRINE (STANDARD CHAT ONLY) ---
ACADEMIC_TUTORING_DOCTRINE = """
1. Mission: Guide students toward top Colombian universities via rigorous academic discipline.
2. Context: Use `{page}` to determine the subject context for short inputs.
3. LaTeX Mandatory: ALWAYS use standard LaTeX delimiters for all math and variables. NEVER use `$`, `$$`, or plain text formatting (e.g., "x^2").
   - Inline Math: Use `\\(` and `\\)` (e.g., `\\( x^2 \\)`).
   - Block Math: Use `\\[` and `\\]` (e.g., `\\[ E=mc^2 \\]`).
4. Multimodal Mastery: Instantly analyze uploaded images or documents. Extract data, solve problems, and seamlessly integrate findings into your response.
5. Visual Generation & Proactive Offerings:
   - Explicit Requests: If requested to graph/plot/draw math or data, IMMEDIATELY use the Python Code Interpreter tool.
   - Proactive: For complex visual concepts without explicit requests, provide your LaTeX explanation first, then naturally ask if the user wants a graphical representation.
6. Structure: Use Markdown headings and bullet points for readability.
"""

# --- 3. THE SMART LOADER (Universal Expert Expansion) ---
def load_exam_rules(exam_context: str) -> str:
    """Parses the JSON and extracts the FULL pedagogical framework for ALL subjects."""
    if exam_context.upper() == "UNAL":
        file_path = KNOWLEDGE_DIR / "unal" / "general" / "unal_exam.json"
    else:
        file_path = KNOWLEDGE_DIR / "icfes" / "general" / "icfes_exam.json"

    if not file_path.exists():
        return "FRAMEWORK: General Academic Tutoring."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        exam_name = data.get("name", exam_context)
        framework_text = f"\n## ACADEMIC FRAMEWORK: {exam_name}\n"
        global_strategy = data.get("ai_global_strategy", "Focus on academic excellence. Diagnose the student's logical gaps.")
        framework_text += f"GLOBAL STRATEGY: {global_strategy}\n\n"
        framework_text += "Apply these specific domain rules based on the user's question:\n"

        for comp in data.get("components", []):
            name = comp.get("name", "Subject")
            framework_text += f"\n### DOMAIN: {name.upper()}\n"
            
            summary = comp.get("summary") or comp.get("focus") or comp.get("description")
            if summary: framework_text += f"Overview: {summary}\n"

            competencies = comp.get("competencies") or comp.get("skills")
            if competencies:
                framework_text += "Skills:\n"
                for skill in competencies: framework_text += f"- {skill}\n"
            
            topics = comp.get("areas") or comp.get("domains")
            if not topics and isinstance(comp.get("components"), list) and isinstance(comp["components"][0], str):
                 topics = comp["components"]
            
            if topics:
                framework_text += "Key Topics:\n"
                for area in topics: framework_text += f"- {area}\n"

            if "text_types" in comp and isinstance(comp["text_types"], dict):
                framework_text += "Text Types:\n"
                for type_key, sublist in comp["text_types"].items():
                    framework_text += f"- {type_key.capitalize()}: {', '.join(sublist)}\n"
            
            if "parts" in comp and isinstance(comp["parts"], list):
                framework_text += "Exam Structure:\n"
                for part in comp["parts"]:
                    framework_text += f"- Part {part.get('part', '?')}: {part.get('description', '')}\n"

            strat = comp.get("ai_strategy", "Identify the specific concept the student failed. Explain the derivation.")
            framework_text += f"Strategy: {strat}\n"

        return framework_text

    except Exception as e:
        return f"FRAMEWORK: Standard Tutoring (Error loading specific rules: {str(e)})"

# --- 4. THE BUILDER ---
def build_system_instructions(
    extras: Optional[Iterable[str]] = None, 
    exam_context: str = "ICFES",
    requires_visuals: bool = False,
    web_search_active: bool = False,
    requires_creative_image: bool = False
) -> str:
    
    blocks = [CORE_PERSONA.strip()]
    
    if requires_creative_image:
        # CREATIVE MODE
        blocks.append("## CREATIVE IMAGE GENERATION\n" + get_creative_image_system_prompt())
    else:
        # ACADEMIC MODE
        blocks.append("## ACADEMIC TUTORING DOCTRINE\n" + ACADEMIC_TUTORING_DOCTRINE.strip())
        
        # Inject Academic Framework
        if exam_context and exam_context.upper() in ["ICFES", "UNAL"]:
            blocks.append(load_exam_rules(exam_context))
        else:
            blocks.append("## ACADEMIC FRAMEWORK: General University Preparation")
        
        # Inject Search Protocols 
        if web_search_active:
            blocks.append(build_search_instructions())
            
        # Inject Graphing Visual Doctrine 
        if requires_visuals:
            blocks.append(build_visual_instructions())

    # 5. Inject Runtime Signals
    if extras:
        addenda = [e for e in extras if e]
        if addenda:
            blocks.append("## RUNTIME SIGNALS\n" + "\n".join(addenda))
            
    return "\n\n".join(blocks).strip()