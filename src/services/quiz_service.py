# src/services/quiz_service.py
# ... (imports)

class QuizService:
    # ...
    @staticmethod
    def get_system_instruction(topic: str = "general", num_questions: int = 5) -> Dict[str, Any]:
        
        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION: QUIZ GENERATION\n"
            f"The user has requested a quiz/exam about '{topic}'. "
            f"You must generate exactly {num_questions} distinct questions. \n\n"
            
            "## Content Quality Rules (STRICT):\n"
            "1. **ORDER OF OPERATIONS**: The schema requires you to provide the `explanation` FIRST. Use this field to fully solve the problem step-by-step. ONLY THEN generate the `options` and `correct_option_index` based on that solution.\n"  # <-- NUEVA REGLA
            "2. **FRAMEWORK COMPLIANCE**: You MUST generate these questions based on the 'ACADEMIC FRAMEWORK' present in your system context. \n"
            "   - Test the specific 'Required Skills/Competencies' listed there.\n"
            "3. **Content**: Questions must be challenging, intriguing, and non-trivial. Avoid generic questions.\n"
            "4. **Math Syntax**: ALWAYS use `\\(` and `\\)` for inline math (e.g. `\\( x^2 \\)`) and `\\[` and `\\]` for block math.\n"
            "5. **Voice**: You are Roma. Be cold, precise, and efficient in your 'intro_message'.\n"
            "6. **Feedback**: Provide specific, educational feedback for every option (Right or Wrong).\n"
            "7. **Difficulty Weighting**: Assign a `difficulty` integer to each question based on its cognitive load: 1 (Basic/Recall), 2 (Intermediate/Application), or 3 (Advanced/Analysis).\n"
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }