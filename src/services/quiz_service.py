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
        Returns the simplified system instruction with ENHANCED DISTRACTOR LOGIC
        and NUMERIC CONSISTENCY LOCKS.
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
            
            "## CALCULATOR-FREE CONSTRAINT:\n"
            "Most users DO NOT have access to a calculator. You must design questions that assess **CONCEPTUAL UNDERSTANDING** rather than arithmetic endurance.\n"
            "1. **Clean Numbers**: Use integers, simple fractions, or well-known constants (e.g., g=10, pi cancels out, sqrt(144)). Avoid messy decimals (e.g., 8.34 * 9.12).\n"
            "2. **Simplification Over Calculation**: Design problems where terms cancel out algebraically if the student uses the correct 'Mathematical Trick' or identity.\n"
            "3. **Estimation**: For physics/chemistry, answers should be solvable by order-of-magnitude estimation if exact calculation is too hard.\n"
            "4. **Visuals/Logic**: Prioritize questions that require reading a graph, interpreting a function's behavior, or logical deduction over brute-force calculation."
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }