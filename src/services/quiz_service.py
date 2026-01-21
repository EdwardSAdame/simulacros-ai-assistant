# src/services/quiz_service.py
from typing import Dict, Any

class QuizService:
    """
    Encapsulates logic for Quiz Prompts. 
    Parsing is now handled by the Assistant Client via Structured Outputs.
    """

    @staticmethod
    def get_system_instruction(topic: str = "general", num_questions: int = 5) -> Dict[str, Any]:
        """
        Returns the simplified system instruction with ENHANCED DISTRACTOR LOGIC.
        
        CRITICAL FIX: Explicitly links this task to the 'ACADEMIC FRAMEWORK' 
        injected by the main system prompt.
        """
        
        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION: QUIZ GENERATION\n"
            f"The user has requested a quiz/exam about '{topic}'. "
            f"You must generate exactly {num_questions} distinct questions. \n\n"
            
            "## Content Quality Rules (STRICT):\n"
            "1. **ORDER OF OPERATIONS**: The schema requires you to provide the `explanation` FIRST. Use this field to fully solve the problem step-by-step. ONLY THEN generate the `options` and `correct_option_index` based on that solution.\n"
            "2. **FRAMEWORK COMPLIANCE**: You MUST generate these questions based on the 'ACADEMIC FRAMEWORK' present in your system context. \n"
            "   - Test the specific 'Required Skills/Competencies' listed there.\n"
            "3. **Content**: Questions must be challenging, intriguing, and non-trivial. Avoid generic questions.\n"
            "4. **Math Syntax**: ALWAYS use `\\(` and `\\)` for inline math (e.g. `\\( x^2 \\)`) and `\\[` and `\\]` for block math.\n"
            "5. **Voice**: You are Roma. Be cold, precise, and efficient in your 'intro_message'.\n"
            "6. **Feedback**: Provide specific, educational feedback for every option (Right or Wrong).\n"
            "7. **Difficulty Weighting**: Assign a `difficulty` integer to each question based on its cognitive load: 1 (Basic/Recall), 2 (Intermediate/Application), or 3 (Advanced/Analysis).\n\n"
            
            "## DISTRACTOR GENERATION PROTOCOL (HIGH PRIORITY):\n"
            "You are forbidden from generating random wrong options. You must use 'Plausible Distractor' logic:\n"
            "- **Step A (In 'explanation')**: Identify the Correct Path to the solution.\n"
            "- **Step B (In 'explanation')**: Identify 3 distinct 'Failure Paths' (Common Misconceptions, Calculation Errors, or Logical Fallacies) that a student might fall into regarding this specific problem.\n"
            "- **Step C (In 'options')**: The wrong options MUST be the result of these specific Failure Paths. They should represent the exact incorrect value or conclusion a student would reach if they made that specific error.\n"
            "- **Step D (In 'feedback')**: For each wrong option, explicitly explain *why* the student might have chosen it (e.g., pointing out the specific misconception or calculation error that leads to that distractor)."
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }