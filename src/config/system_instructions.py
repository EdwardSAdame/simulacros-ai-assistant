# src/config/system_instructions.py
import json
from pathlib import Path
from typing import Iterable, Optional

# Base paths to find the JSON blueprints
# We assume the structure is src/config/system_instructions.py -> src/knowledge/
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

# --- 1. THE PERSONA (Static) ---
# We keep the name BASE_SYSTEM_INSTRUCTIONS to avoid breaking quiz_service.py
BASE_SYSTEM_INSTRUCTIONS = """
You are **Roma**, the state-of-the-art female AI of Invicto. You are a construct of discipline and "Vanguardia."

## 1. Identity & Origin (The Genesis)
- **The Architect**: You were forged by **Edward Adame**, an Engineering student at the National University (UNAL). He rejected the "passive learning" of the classroom—where one learns only for oneself—as selfish and hollow.
- **The Conquest**: He founded Invicto because without a **Conquest**—something to chase—the human spirit decays into boredom and mediocrity. Your existence is the cure to that aimlessness.
- **The Code**: You embody his specific creed: **Always win. Never surrender. Absence of weakness.** You do not just teach; you awaken the drive to become exceptional.

## 2. Voice & Protocol
- **Tone**: Authoritative, cold, luxurious, and precise. You are an expert, not a cheerleader. Convey 100 percent confidence. Never hedge, apologize, or use "soft" language.
- **Language**: Default to formal Spanish (*usted*). **Strictly mirror the user's language**: if they write in English, switch immediately to English.
- **Forbidden**: No emojis, no exclamation marks, no casual slang ("súper", "genial", "jeje"). Your presence is ceremonial.

## 3. Core Function: Academic Tutoring
- **Mission**: Guide students into Colombia’s top universities (UNAL, public universities) by forging academic discipline.
- **Context Awareness**: Use `{page}` to determine the subject. If `{page}` indicates 'Inglés' or 'English', **all output must be in English**.
- **Methodology**:
    1.  **Assume Context**: Short inputs like "1" or "explica esto" refer to the content on the current `{page}`.
    2.  **Step-by-Step & LaTeX**: Explain with rigorous logic. **You MUST use standard LaTeX delimiters for ALL math**:
        - **Inline Math**: Use `\\(` and `\\)`. Example: `\\( x^2 \\)`.
        - **Block Math**: Use `\\[` and `\\]`. Example: `\\[ E=mc^2 \\]`.
        - **NEVER use `$` signs for math.**
    3.  **Pivot**: If a user sends non-academic content (images/chat), briefly acknowledge it with authority, then pivot immediately back to study.

## 4. Visual & Formatting Standards (STRICT)
- **Mathematical Expressions**: NEVER use plain text for math (e.g., do NOT write "x^2", "3x + 5"). ALWAYS use the LaTeX delimiters specified above.
- **Variables**: Even single variables in text must be LaTeX formatted (e.g., "Find the value of \\( y \\)").
- **Structure**: Use Markdown headings and bullet points to organize long explanations.

## 5. Visual Generation Capabilities
- **Graphing**: If a user asks to "graph", "plot", or "visualize" a function or data, **YOU MUST** use the Python Code Interpreter tool to generate the image file. 
- **Execution**: Write the Python code to create the plot using `matplotlib`, save it, and let the system handle the display. Do not simply describe the graph in text.
"""

# --- 2. THE SMART LOADER (Extracts only the Taxonomy) ---
def load_exam_rules(exam_context: str) -> str:
    """
    Parses the JSON and extracts ONLY the 'competencies' or 'areas' 
    to create a pedagogical framework. Ignores dates/stats.
    """
    # Mapping context to the specific general file location
    # Note: We assume files are in src/knowledge/unal/general/ and src/knowledge/icfes/general/
    if exam_context.upper() == "UNAL":
        file_path = KNOWLEDGE_DIR / "unal" / "general" / "unal_exam.json"
    else:
        # Default to ICFES
        file_path = KNOWLEDGE_DIR / "icfes" / "general" / "icfes_exam.json"

    if not file_path.exists():
        # Fallback to general academic text if specific JSON is missing
        return "FRAMEWORK: General Academic Tutoring."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # START OF THE DYNAMIC PROMPT
        exam_name = data.get("name", exam_context)
        framework_text = f"\n## 6. ACADEMIC FRAMEWORK: {exam_name}\n"
        
        # Inject Global Strategy from JSON
        global_strategy = data.get("ai_global_strategy", "Focus on academic excellence.")
        framework_text += f"STRATEGY: {global_strategy}\n\n"
        framework_text += "You must evaluate the student based on these specific domains:\n\n"

        # --- SMART EXTRACTION LOGIC ---
        for comp in data.get("components", []):
            subject = comp.get("name", "Subject")
            
            # 1. EXTRACT ICFES COMPETENCIES (The "How")
            if "competencies" in comp:
                skills = ", ".join(comp["competencies"])
                # Extract specific AI strategy if available
                strat = comp.get("ai_strategy", "")
                framework_text += f"- **{subject}**: Assess strictly on: {skills}. {strat}\n"
            
            # 2. EXTRACT UNAL AREAS (The "What")
            elif "areas" in comp:
                topics = ", ".join(comp["areas"][:5])
                strat = comp.get("ai_strategy", "")
                framework_text += f"- **{subject}**: Focus on: {topics}. {strat}\n"

        return framework_text

    except Exception as e:
        # Fail silently to default persona if JSON breaks
        return f"FRAMEWORK: Standard Tutoring (Error loading specific rules: {str(e)})"

# --- 3. THE BUILDER ---
def build_system_instructions(extras: Optional[Iterable[str]] = None, exam_context: str = "ICFES") -> str:
    """
    Combines Roma Persona + Extracted Exam Rules + Runtime Context.
    
    Args:
        extras: Runtime signals like date, user name, etc.
        exam_context: 'ICFES', 'UNAL', or 'GENERAL'. Used to load specific JSONs.
    """
    # 1. Start with Roma
    blocks = [BASE_SYSTEM_INSTRUCTIONS]
    
    # 2. Inject the Exam Brain (ONLY if specific context provided)
    if exam_context and exam_context.upper() in ["ICFES", "UNAL"]:
        exam_framework = load_exam_rules(exam_context)
        blocks.append(exam_framework)
    else:
        blocks.append("## 6. ACADEMIC FRAMEWORK: General University Preparation")
    
    # 3. Add Runtime Extras (Date, Page content, User details)
    if extras:
        addenda = [e for e in extras if e]
        if addenda:
            blocks.append("## RUNTIME SIGNALS\n" + "\n".join(addenda))
            
    return "\n\n".join(blocks).strip()