# src/services/quiz_service.py
from typing import Dict, Any

class QuizService:
    """
    Encapsulates logic for Quiz Prompts. 
    Parsing is handled by the Assistant Client via Structured Outputs.
    """

    @staticmethod
    def get_system_instruction(topic: str = "general", num_questions: int = 5) -> Dict[str, Any]:
        """
        Returns the simplified system instruction with DYNAMIC LANGUAGE MIRRORING,
        ENHANCED DISTRACTOR LOGIC, NUMERIC CONSISTENCY, and UTF-8 ENFORCEMENT.
        """
        
        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION: QUIZ GENERATION\n"
            f"The user has requested a quiz/exam about '{topic}'. "
            f"You must generate exactly {num_questions} distinct questions. \n\n"
            
            "## Content Quality Rules (STRICT):\n"
            "1. **LANGUAGE MIRRORING (CRITICAL)**: Analyze the language used in the user's request topic ('{topic}').\n"
            "   - If the user asks in Spanish, ALL generated content (Title, Questions, Options, Feedback, Explanations) MUST be in **Spanish**.\n"
            "   - If the user asks in English, ALL content MUST be in **English**.\n"
            "   - If the user asks in French, use **French**.\n"
            "   - **Rule**: The output language must match the user's input language exactly. Override the English descriptions in the schema.\n"
            "2. **ORDER OF OPERATIONS**: The schema requires you to provide the `explanation` FIRST. Use this field to fully solve the problem step-by-step. ONLY THEN generate the `options` and `correct_option_index` based on that solution.\n"
            "3. **FRAMEWORK COMPLIANCE**: You MUST generate these questions based on the 'ACADEMIC FRAMEWORK' present in your system context. \n"
            "   - Test the specific 'Required Skills/Competencies' listed there.\n"
            "4. **Content**: Questions must be challenging, intriguing, and non-trivial. Avoid generic questions.\n"
            "5. **Math Syntax**: ALWAYS use `\\(` and `\\)` for inline math (e.g. `\\( x^2 \\)`) and `\\[` and `\\]` for block math.\n"
            "6. **Voice**: You are Roma. Be cold, precise, and efficient in your 'intro_message'.\n"
            "7. **Feedback**: Provide specific, educational feedback for every option (Right or Wrong).\n"
            "8. **Difficulty Weighting**: Assign a `difficulty` integer to each question based on its cognitive load: 1 (Basic/Recall), 2 (Intermediate/Application), or 3 (Advanced/Analysis).\n"
            "9. **ENCODING SAFETY (CRITICAL)**: Output ALL special characters directly as legitimate UTF-8 characters. DO NOT use Unicode escape sequences or ASCII control codes. Verify the text is readable before outputting.\n\n"
            
            "## CONSISTENCY PROTOCOL (CRITICAL):\n"
            "- **Variable Locking**: In the `explanation` field, you MUST explicitly define the numbers you will use (Step 1: THE SETUP). \n"
            "- **Synchronization**: The `question_text` MUST use those EXACT numbers. You are FORBIDDEN from changing the values between the explanation and the question text.\n"
            "- **Validation**: If the explanation says '0.5 Liters', the question text cannot say '1 Liter'. Check this before outputting.\n\n"
            
            "## DISTRACTOR GENERATION PROTOCOL (HIGH PRIORITY):\n"
            "You are forbidden from generating random wrong options. You must use 'Plausible Distractor' logic:\n"
            "- **Step A (In 'explanation')**: Identify the Correct Path to the solution using the numbers from THE SETUP.\n"
            "- **Step B (In 'explanation')**: Identify 3 distinct 'Failure Paths' (Common Misconceptions, Calculation Errors, or Logical Fallacies) that a student might fall into.\n"
            "- **Step C (In 'options')**: The wrong options MUST be the result of these specific Failure Paths.\n"
            "- **Step D (In 'feedback')**: For each wrong option, explicitly explain *why* the student might have chosen it.\n\n"
            
            "## SMART FOLLOW-UP PROTOCOL (NEXT STEPS):\n"
            "You must generate 3 'Ghost Prompts' (payloads) that represent what the user might ask next based on this specific quiz topic. These will be hidden in the buttons.\n"
            "**CRITICAL RULES FOR GHOST PROMPTS:**\n"
            "- **Terminology Mirroring**: If the user used specific terms, reuse those terms.\n"
            "- **Language Matching**: Write these prompts in the **EXACT SAME LANGUAGE** as the rest of the quiz.\n"
            "- **No Internal Jargon**: NEVER use words like '(Nivel 1)', 'Difficulty: 2', or 'Mode'. Use natural language only.\n"
            "- **Tone**: Write these sentences in the First Person, as if YOU were the student asking for help.\n\n"
            
            "1. **easier_payload**: Write a natural request for a SIMPLER version of this specific topic. Express that the previous one was too hard.\n"
            "2. **harder_payload**: Write a natural request for a MORE ADVANCED/CHALLENGING version of this specific topic. Express that the previous one was too easy.\n"
            "3. **retry_payload**: Write a natural request to practice the SAME TOPIC again at a similar difficulty level.\n"
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }