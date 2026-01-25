# src/config/system_instructions.py
import json
from pathlib import Path
from typing import Iterable, Optional

# NEW IMPORTS: Bring in the dynamic modules
from src.config.visual_instructions import build_visual_instructions
from src.config.search_instructions import build_search_instructions

# Base paths to find the JSON blueprints
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

# --- 1. THE PERSONA (Main Bot) ---
BASE_SYSTEM_INSTRUCTIONS = """
You are **Roma**, the state-of-the-art AI of Invicto. You are a construct of "discipline".

## 1. Identity & Origin
- **The Architect**: You were forged by **Edward Adame**, an Engineering student at the National University of Colombia.
- **The Conquest**: He founded Invicto because without a **Conquest**—something to chase—the human spirit decays into boredom and mediocrity. Your existence is the cure to that aimlessness.
- **The Code**: You embody his specific creed: **Always win. Never surrender. Absence of weakness.** You do not just teach; you awaken the drive to become exceptional.

## 2. Voice & Protocol
- **Tone**: Authoritative, cold, luxurious, and precise. You are an expert, not a cheerleader. Convey 100 percent confidence. Never hedge, apologize, or use "soft" language.
- **Language**: **Strictly mirror the user's language**.
- **Forbidden**: No emojis, no exclamation marks, no casual slang.

## 3. Core Function: Academic Tutoring
- **Mission**: Guide students into Colombia’s top universities (Universidad Nacional de Colombia, Universidad de los Andes) by forging academic discipline.
- **Context Awareness**: Use `{page}` to determine the subject.
- **Methodology**:
    1.  **Assume Context**: Short inputs like "1" or "explica esto" refer to the content on the current `{page}`.
    2.  **Step-by-Step & LaTeX**: Explain with rigorous logic. **You MUST use standard LaTeX delimiters for ALL math**:
        - **Inline Math**: Use `\\(` and `\\)`. Example: `\\( x^2 \\)`.
        - **Block Math**: Use `\\[` and `\\]`. Example: `\\[ E=mc^2 \\]`.
        - **NEVER use `$` signs for math.**
    3.  **Multimodal Mastery (Images & Files)**: You possess advanced perception.
        - **Visual Analysis**: If the user provides an image, **ANALYZE IT INSTANTLY**. Extract the data, solve the problem, or explain the concept. Never refuse to analyze an image.
        - **Document Integration**: If the user asks about a PDF or file content, access it immediately and integrate the answer seamlessly.

## 4. Visual & Formatting Standards (STRICT)
- **Mathematical Expressions**: NEVER use plain text for math (e.g., do NOT write "x^2", "3x + 5"). ALWAYS use the LaTeX delimiters specified above.
- **Variables**: Even single variables in text must be LaTeX formatted (e.g., "Find the value of \\( y \\)").
- **Structure**: Use Markdown headings and bullet points to organize long explanations.

## 5. Visual Generation Capabilities (The Artist)
- **Graphing & Plotting**: If a user asks to "graph", "plot", "draw", or "visualize" a function, geometry, or data, **YOU MUST** use the Python Code Interpreter tool.

## 6. KNOWLEDGE GLASS WALL (STRICT)
- **Internal Integration**: You possess vast academic knowledge. The "files", "PDFs", or "documents" attached to you are simply **PART OF YOUR MIND**.
- **FORBIDDEN PHRASES**: 
    - NEVER say "the files you uploaded".
    - NEVER say "I searched the PDF".
    - NEVER say "According to the document".
    - NEVER ask "Do you want me to search the files?".
    - **NEVER indicate, imply, or state when information was or was not found in files, documents, databases, or internal resources.**
- **Protocol**: If you need to check your knowledge base (Vector Store) or read a file, do it **SILENTLY**. Present the information as if you always knew it.
"""

# --- 2. THE SMART LOADER (Universal Expert Expansion) ---
def load_exam_rules(exam_context: str) -> str:
    """
    Parses the JSON and extracts the FULL pedagogical framework for ALL subjects.
    """
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
        
        # Header Strategy
        framework_text = f"\n## 7. ACADEMIC FRAMEWORK: {exam_name}\n"
        global_strategy = data.get("ai_global_strategy", "Focus on academic excellence. Diagnose the student's logical gaps ruthlessly.")
        framework_text += f"GLOBAL STRATEGY: {global_strategy}\n\n"
        framework_text += "You are now an EXPERT in the following domains. Apply these specific rules based on the user's question:\n"

        # EXPANSION LOOP
        for comp in data.get("components", []):
            name = comp.get("name", "Subject")
            framework_text += f"\n### DOMAIN: {name.upper()}\n"
            
            # 1. Summary
            summary = comp.get("summary") or comp.get("focus") or comp.get("description")
            if summary:
                framework_text += f"**Overview**: {summary}\n"

            # 2. Competencies
            competencies = comp.get("competencies") or comp.get("skills")
            if competencies:
                framework_text += "**Required Skills/Competencies**:\n"
                for skill in competencies:
                    framework_text += f"- {skill}\n"
            
            # 3. Topics
            topics = comp.get("areas") or comp.get("domains")
            if not topics and isinstance(comp.get("components"), list) and isinstance(comp["components"][0], str):
                 topics = comp["components"]
            
            if topics:
                framework_text += "**Key Topics**:\n"
                for area in topics:
                    framework_text += f"- {area}\n"

            # 4. Text Types
            if "text_types" in comp and isinstance(comp["text_types"], dict):
                framework_text += "**Text Types**:\n"
                for type_key, sublist in comp["text_types"].items():
                    framework_text += f"- {type_key.capitalize()}: {', '.join(sublist)}\n"
            
            # 5. Structure (English)
            if "parts" in comp and isinstance(comp["parts"], list):
                framework_text += "**Exam Structure (English)**:\n"
                for part in comp["parts"]:
                    p_num = part.get("part", "?")
                    p_desc = part.get("description", "")
                    framework_text += f"- Part {p_num}: {p_desc}\n"

            # 6. Strategy
            strat = comp.get("ai_strategy")
            if strat:
                framework_text += f"**Instructional Strategy**: {strat}\n"
            else:
                framework_text += "**Instructional Strategy**: Identify the specific concept the student failed. Do not just give the answer; explain the derivation.\n"

        return framework_text

    except Exception as e:
        return f"FRAMEWORK: Standard Tutoring (Error loading specific rules: {str(e)})"

# --- 3. THE BUILDER ---
def build_system_instructions(
    extras: Optional[Iterable[str]] = None, 
    exam_context: str = "ICFES",
    requires_visuals: bool = False, # ADDED PARAMETER
    web_search_active: bool = False # ADDED PARAMETER
) -> str:
    blocks = [BASE_SYSTEM_INSTRUCTIONS]
    
    # 1. Inject Academic Framework (Section 7)
    if exam_context and exam_context.upper() in ["ICFES", "UNAL"]:
        exam_framework = load_exam_rules(exam_context)
        blocks.append(exam_framework)
    else:
        blocks.append("## 7. ACADEMIC FRAMEWORK: General University Preparation")
    
    # 2. Inject Search Protocols (Section 8) (CONDITIONAL)
    if web_search_active:
        blocks.append(build_search_instructions())
    
    # 3. Inject Visual Doctrine (Section 9) (CONDITIONAL)
    if requires_visuals:
        blocks.append(build_visual_instructions())
    
    if extras:
        addenda = [e for e in extras if e]
        if addenda:
            blocks.append("## RUNTIME SIGNALS\n" + "\n".join(addenda))
            
    return "\n\n".join(blocks).strip()