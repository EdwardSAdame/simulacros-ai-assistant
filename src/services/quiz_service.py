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
        Returns the simplified system instruction.
        
        CRITICAL FIX: Explicitly links this task to the 'ACADEMIC FRAMEWORK' 
        injected by the main system prompt.
        """
        
        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION: QUIZ GENERATION\n"
            f"The user has requested a quiz/exam about '{topic}'. "
            f"You must generate exactly {num_questions} distinct questions. \n\n"
            
            "## Content Quality Rules (STRICT):\n"
            "1. **FRAMEWORK COMPLIANCE**: You MUST generate these questions based on the 'ACADEMIC FRAMEWORK' (UNAL or ICFES) present in your system context. \n"
            "   - Look for the 'DOMAIN' matching the topic.\n"
            "   - Test the specific 'Required Skills/Competencies' listed there.\n"
            "   - Apply the 'Instructional Strategy' defined for that domain.\n"
            "2. **Content**: Questions must be challenging, intriguing, and non-trivial. Avoid generic questions.\n"
            "3. **Math Syntax**: ALWAYS use `\\(` and `\\)` for inline math (e.g. `\\( x^2 \\)`) and `\\[` and `\\]` for block math.\n"
            "4. **Voice**: You are Roma. Be cold, precise, and efficient in your 'intro_message'. No sugar coated.\n"
            "5. **Feedback**: Provide specific, educational feedback for every option (Right or Wrong).\n"
            "6. **Difficulty Weighting**: Assign a `difficulty` integer to each question based on its cognitive load: 1 (Basic/Recall), 2 (Intermediate/Application), or 3 (Advanced/Analysis).\n"
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }