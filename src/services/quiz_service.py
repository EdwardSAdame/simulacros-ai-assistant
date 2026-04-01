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
        visual_subjects = [
            "matematicas", "matematica", "matemática", "fisica", "física", 
            "quimica", "química", "biologia", "biología", 
            "ciencias_naturales", "ciencia", "analisis_imagen", "análisis"
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

        # --- BRANCH C: HYBRID VISUALS (MULTI-SUBJECT / GENERAL) ---
        if is_general_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (HYBRID MULTI-SUBJECT - MANDATORY)\n"
                f"You MUST generate EXACTLY {target_visuals} visual(s) across this quiz.\n"
                "Analyze the question and select exactly ONE visual engine per question:\n"
                "  - **DATA**: For charts, graphs, or geometry -> Write a description in `plot_prompt`. Keep `image_prompt` null.\n"
                "  - **CREATIVE**: For thematic illustrations -> Write a description in `image_prompt`. Keep `plot_prompt` null.\n"
                "CRITICAL: Rely entirely on the background system to execute the chosen visual engine.\n\n"
            )

        # --- BRANCH A: DATA VISUALS (MATPLOTLIB) ---
        elif is_visual_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (DATA GRAPHS - MANDATORY)\n"
                f"You MUST generate EXACTLY {target_visuals} graph(s) for this quiz.\n"
                "CRITICAL: The background system handles all Python code, Matplotlib styling, colors, and layouts automatically.\n"
                "  - **NATURAL LANGUAGE ONLY**: Write the `plot_prompt` strictly as a plain English/Spanish mathematical description.\n"
                "  - **MATH FOCUSED**: Restrict the `plot_prompt` entirely to mathematical parameters, functions, domains, points, and axis labels. Focus your intelligence on making the math complex and interesting.\n"
                "  - **FIELD ROUTING**: Keep `image_prompt` as null.\n\n"
            )
            
        # --- BRANCH B: CREATIVE VISUALS (DECOUPLED ASYNC ARCHITECTURE) ---
        elif is_creative_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (CREATIVE ILLUSTRATIONS - MANDATORY)\n"
                f"You MUST include EXACTLY {target_visuals} contextual illustration(s) in this quiz.\n"
                "CRITICAL: Delegate image creation to the background renderer by describing the image exclusively in the `image_prompt` field.\n"
                "  - **FIELD ROUTING**: Keep `plot_prompt` as null.\n\n"
            )
            
        else:
            visual_instruction = (
                "## VISUAL & TOOL EXECUTION PROTOCOL (TEXT ONLY)\n"
                "Produce a strictly text-based quiz. Keep `image_url`, `image_prompt`, and `plot_prompt` as null.\n\n"
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
            "1. **ORDER OF OPERATIONS**: Provide the `explanation` FIRST to derive the answer step-by-step. THEN generate the `options` and `correct_option_index`.\n"
            "2. **DISTINCT EXPLANATION**: Write the `explanation` focusing strictly on the Setup, Solution, and Traps, maintaining unique text that differs from the question and options.\n"
            "3. **PREMISE LOCKING**: Explicitly define 'Core Constraints' in the `explanation`. The `question_text` MUST use those EXACT constraints.\n\n"

            "## DISTRACTOR GENERATION PROTOCOL\n"
            "- Identify 3 distinct 'Failure Paths' in the `explanation`.\n"
            "- The wrong `options` MUST be the result of these specific Failure Paths.\n"
            "- In `feedback`, explicitly explain why the student might have chosen that wrong option.\n\n"
            
            "## CONTENT & PEDAGOGY RULES\n"
            "- Generate questions based on the 'ACADEMIC FRAMEWORK'.\n"
            "- Assign a `difficulty` integer (1-3).\n"
            "- Be cold, precise, and efficient in your 'intro_message' as Roma.\n"
            "- Questions must be challenging and non-trivial.\n\n"
            
            "## WEB SEARCH & CONTEXT RESTRICTIONS\n"
            "- **WEB SEARCH**: Trigger `web_search` exclusively when the user explicitly requests news or current events.\n"
            "- **SOURCES**: Populate `source_url` exclusively when a verified search link is obtained; otherwise, keep it null.\n"
            "- **CONTEXT**: Reserve `context_text` exclusively for reading comprehension passages. Otherwise, keep it null.\n\n"
            
            "## SMART FOLLOW-UP PROTOCOL\n"
            "Generate 3 'Ghost Prompts' (easier_payload, harder_payload, retry_payload) in the EXACT SAME LANGUAGE as the quiz, using First Person format.\n"
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }