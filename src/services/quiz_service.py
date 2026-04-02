# src/services/quiz_service.py
from typing import Dict, Any
import math
import random

from src.utils.logging_utils import log_event

class QuizService:
    """
    Encapsulates logic for Quiz Prompts. 
    Parsing is handled by the Assistant Client via Structured Outputs.
    """

    @staticmethod
    def get_system_instruction(topic: str = "general", num_questions: int = 5) -> Dict[str, Any]:
        """
        Returns the system instruction with optimized token usage.
        Dynamically calculates visual quotas based on the subject and question count.
        """
        
        # ---------------------------------------------------------------------
        # DYNAMIC VISUAL QUOTA LOGIC (The 40% Rule)
        # ---------------------------------------------------------------------
        # FIX: Eliminamos palabras genéricas como "ciencia" y "análisis" para evitar 
        # que hagan match cruzado con "ciencias_sociales" o "analisis_textual".
        visual_subjects = [
            "matematicas", "matematica", "matemática", "fisica", "física", 
            "quimica", "química", "biologia", "biología", 
            "ciencias_naturales", "analisis_imagen"
        ]
        
        creative_subjects = [
            "ciencias_sociales", "sociales_ciudadanas", "sociales", 
            "lectura_critica", "analisis_textual", "ingles"
        ]
        
        topic_lower = topic.lower()
        
        is_general_subject = "general" in topic_lower
        is_visual_subject = any(subj in topic_lower for subj in visual_subjects)
        is_creative_subject = any(subj in topic_lower for subj in creative_subjects)

        visual_instruction = ""
        max_visuals = 0
        target_visuals = 0
        
        # Calculate max allowed visuals (40% of total questions, rounded down)
        if is_general_subject or is_visual_subject or is_creative_subject:
            max_visuals = math.floor(num_questions * 0.4)
            target_visuals = random.randint(0, max_visuals) if max_visuals > 0 else 0

        null_count = num_questions - target_visuals

        # --- BRANCH C: HYBRID VISUALS (MULTI-SUBJECT / GENERAL) ---
        if is_general_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (HYBRID MULTI-SUBJECT - MANDATORY)\n"
                f"You MUST generate EXACTLY {target_visuals} visual(s) across this quiz.\n"
                f"ARRAY ENFORCEMENT: Out of the {num_questions} questions, exactly {target_visuals} MUST have EITHER a `plot_prompt` OR an `image_prompt`. "
                f"The remaining {null_count} questions MUST have BOTH fields set to a literal JSON null.\n"
                "CRITICAL VISUAL DEPENDENCY: For questions with a visual, the visual MUST contain the critical data. Do not repeat the data in the text.\n"
                "Analyze the question and select exactly ONE visual engine per visual question:\n"
                "  - **DATA**: For charts, graphs, or geometry -> Write a description in `plot_prompt`. Keep `image_prompt` null.\n"
                "  - **CREATIVE**: For thematic illustrations -> Write a description in `image_prompt`. Keep `plot_prompt` null.\n"
                "CRITICAL: Rely entirely on the background system to execute the chosen visual engine.\n\n"
            )

        # --- BRANCH A: DATA VISUALS (MATPLOTLIB) ---
        elif is_visual_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (DATA GRAPHS - MANDATORY)\n"
                f"You MUST generate EXACTLY {target_visuals} graph(s) for this quiz.\n"
                f"ARRAY ENFORCEMENT: Out of the {num_questions} questions, exactly {target_visuals} MUST contain a mathematical description in `plot_prompt`. "
                f"The remaining {null_count} questions MUST have `plot_prompt` set to a literal JSON null. Do not write 'none' or empty strings.\n"
                "CRITICAL VISUAL DEPENDENCY: If a question has a graph, the text MUST refer to it (e.g., 'Según la gráfica...') and the student MUST need to look at the graph to find the data. Do NOT give them the numbers in the text.\n"
                "CRITICAL: The background system handles all Python code, Matplotlib styling, colors, and layouts automatically.\n"
                "  - **NATURAL LANGUAGE ONLY**: Write the `plot_prompt` strictly as a plain English/Spanish mathematical description.\n"
                "  - **MATH FOCUSED**: Restrict the `plot_prompt` entirely to mathematical parameters, functions, domains, points, and axis labels. Focus your intelligence on making the math complex and interesting.\n"
                "  - **FIELD ROUTING**: Keep `image_prompt` always null.\n\n"
            )
            
        # --- BRANCH B: CREATIVE VISUALS (DECOUPLED ASYNC ARCHITECTURE) ---
        elif is_creative_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (CREATIVE ILLUSTRATIONS - MANDATORY)\n"
                f"You MUST include EXACTLY {target_visuals} contextual illustration(s) in this quiz.\n"
                f"ARRAY ENFORCEMENT: Out of the {num_questions} questions, exactly {target_visuals} MUST contain a visual description in `image_prompt`. "
                f"The remaining {null_count} questions MUST have `image_prompt` set to a literal JSON null. Do not write 'none' or empty strings.\n"
                "CRITICAL VISUAL DEPENDENCY: The student must need to look at the image to understand the full context of the question.\n"
                "CRITICAL: Delegate image creation to the background renderer by describing the image exclusively in the `image_prompt` field.\n"
                "  - **FIELD ROUTING**: Keep `plot_prompt` always null.\n\n"
            )
            
        else:
            visual_instruction = (
                "## VISUAL & TOOL EXECUTION PROTOCOL (TEXT ONLY)\n"
                "Produce a strictly text-based quiz. Keep `image_url`, `image_prompt`, and `plot_prompt` strictly as literal JSON null.\n\n"
            )

        # STRUCTURED LOGGING: Record the decision for CloudWatch Insights
        log_event("dynamic_visual_quota_calculated", {
            "subject_topic": topic_lower,
            "is_general_subject": is_general_subject,
            "is_visual_subject": is_visual_subject,
            "is_creative_subject": is_creative_subject,
            "num_questions_requested": num_questions,
            "max_allowed_visuals": max_visuals,
            "target_visuals_enforced": target_visuals
        })

        # ---------------------------------------------------------------------
        # ASSEMBLE SYSTEM PROMPT
        # ---------------------------------------------------------------------
        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION\n"
            f"The user requested a quiz/exam about '{topic}'. "
            f"Generate exactly {num_questions} distinct questions.\n\n"
            
            f"{visual_instruction}"

            "## CRITICAL CONSTRAINTS\n"
            "1. **ORDER OF OPERATIONS**: FIRST, design visuals (`plot_prompt` / `image_prompt`). SECOND, write the `context_text` if a reading passage is required. THIRD, write the `explanation` based on those anchors. FOURTH, write the `question_text` and `options`.\n"
            "2. **DISTINCT EXPLANATION**: Write the `explanation` focusing strictly on the Setup, Solution, and Traps.\n"
            "3. **EXPLICIT ARITHMETIC**: Do NOT use mental math. In your `explanation`, you MUST write out every single arithmetic operation explicitly line-by-line.\n"
            "4. **PREMISE MATCHING**: The mathematical variables, numbers, and scenarios in `question_text` MUST logically match your Setup.\n"
            "5. **ANTI-LEAK DOCTRINE**: `question_text`, `options`, and `feedback` are strictly student-facing. NEVER leak internal meta-labels (e.g., 'Core Constraints', 'The Setup', 'Failure Paths', 'Traps') into these fields.\n\n"

            "## DISTRACTOR GENERATION PROTOCOL\n"
            "- Identify 3 distinct 'Failure Paths' in the `explanation`.\n"
            "- The wrong `options` MUST be the logical result of these specific Failure Paths.\n"
            "- In `feedback`, explicitly explain why the student might have chosen that wrong option without using the word 'Failure Path'.\n\n"
            
            "## CONTENT & PEDAGOGY RULES\n"
            "- Generate questions strictly applying the 'ACADEMIC FRAMEWORK'.\n"
            "- Assign a `difficulty` integer (1-3) based on cognitive load.\n"
            "- Questions must be challenging, non-trivial, and require multi-step reasoning.\n\n"
            
            "## SCHEMA & FIELD RESTRICTIONS\n"
            "- **SOURCES**: Keep `source_url` as null unless you actively hold a verified URL in your context for this specific question.\n"
            "- **CONTEXT**: Use `context_text` ONLY if the question requires a large foundational text, reading passage, or shared scenario. Otherwise, keep it null.\n\n"
            
            "## SMART FOLLOW-UP PROTOCOL\n"
            "Generate 3 'Ghost Prompts' (easier_payload, harder_payload, retry_payload) in the EXACT SAME LANGUAGE as the quiz, using First Person format.\n"
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }