# src/services/quiz_service.py
from typing import Dict, Any
from src.config.system_instructions import BASE_SYSTEM_INSTRUCTIONS

class QuizService:
    """
    Encapsulates logic for Quiz Prompts. 
    Parsing is now handled by the Assistant Client via Structured Outputs.
    """

    @staticmethod
    def get_system_instruction(topic: str = "general", num_questions: int = 5) -> Dict[str, Any]:
        """
        Returns the simplified system instruction.
        """
        
        instruction_text = (
            f"{BASE_SYSTEM_INSTRUCTIONS}\n\n"
            
            f"## IMMEDIATE RUNTIME MISSION: QUIZ GENERATION\n"
            f"The user has requested a quiz/exam about '{topic}'. "
            f"You must generate exactly {num_questions} distinct questions. \n\n"
            
            "## Content Quality Rules:\n"
            "1. **Difficulty**: Questions must be challenging, intriguing, and non-trivial.\n"
            # 🟢 CHANGED: Force \( \) syntax
            "2. **Math Syntax**: ALWAYS use `\\(` and `\\)` for inline math (e.g. `\\( x^2 \\)`) and `\\[` and `\\]` for block math.\n"
            "3. **Voice**: You are Roma. Be cold, precise, and efficient in your 'intro_message'.\n"
            "4. **Feedback**: Provide specific, educational feedback for every option (Right or Wrong).\n"
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }