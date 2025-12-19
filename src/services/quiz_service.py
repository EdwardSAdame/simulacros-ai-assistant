# src/services/quiz_service.py
import json
import re
import logging
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class QuizService:
    """
    Encapsulates all logic related to generating and parsing Quiz content.
    Includes robust error handling and JSON repair mechanisms.
    """

    @staticmethod
    def get_system_instruction(topic: str = "general", num_questions: int = 5) -> Dict[str, Any]:
        """
        Returns the specific system instruction to force the AI to generate a structured JSON ARRAY of questions.
        """
        instruction_text = (
            f"SYSTEM INSTRUCTION: The user has requested a quiz/exam about '{topic}'. "
            f"You must generate a JSON ARRAY containing exactly {num_questions} distinct questions. \n\n"
            
            "## Formatting Rules (STRICT):\n"
            "1. **Output Format**: You must return a LIST (Array) of objects, not a single object.\n"
            "2. **Double Escaping**: ALL backslashes for LaTeX must be DOUBLE ESCAPED (e.g., `\\\\( x^2 \\\\)`).\n"
            "3. **Math Syntax**: Use `\\\\(` and `\\\\)` for inline math.\n"
            "4. **Difficulty**: Progressive difficulty (Question 1 is easy, Question 5 is hard).\n"
            "5. **Content**: \n"
            "   - `question_title`: Short H1 Markdown title (# Topic).\n"
            "   - `question_text`: The question stem.\n"
            "   - `options`: Array of 4 strings.\n"
            "   - `correct_option_index`: 0-3.\n"
            "   - `explanation`: Short text explaining why the answer is correct.\n\n"

            "## Expected JSON Output:\n"
            "```json\n"
            "[\n"
            "  {\n"
            "    \"question_title\": \"# Basic Integration\",\n"
            "    \"question_text\": \"Solve \\\\( \\\\int x dx \\\\)\",\n"
            "    \"options\": [\"\\\\( x^2/2 \\\\)\", \"\\\\( x \\\\)\", \"\\\\( 2x \\\\)\", \"\\\\( x^2 \\\\)\"],\n"
            "    \"correct_option_index\": 0,\n"
            "    \"explanation\": \"Power rule of integration.\"\n"
            "  },\n"
            "  { ... next question ... }\n"
            "]\n"
            "```\n"
            "Ensure the output is a valid JSON List. Do not output conversational text outside the JSON block."
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }

    @staticmethod
    def extract_quiz_data(raw_text: str) -> Optional[Union[List[Dict], Dict]]:
        """
        Parses the AI response. 
        Prioritizes extracting a LIST (Array) of quizzes.
        Falls back to a single object if necessary.
        """
        if not raw_text:
            return None

        # Helper to attempt parsing
        def try_parse(text_chunk):
            try:
                # Naive repair for common LaTeX backslash issues
                repaired = text_chunk
                # Fix inline math \( -> \\(
                repaired = re.sub(r'(?<!\\)\\\(', r'\\\\(', repaired)
                repaired = re.sub(r'(?<!\\)\\\)', r'\\\\)', repaired)
                # Fix block math \[ -> \\[
                repaired = re.sub(r'(?<!\\)\\\[', r'\\\\[', repaired)
                repaired = re.sub(r'(?<!\\)\\\]', r'\\\\]', repaired)
                
                return json.loads(repaired)
            except Exception:
                return None

        try:
            # 1. Try to find a JSON Array [...]
            match_list = re.search(r"\[\s*\{.*\}\s*\]", raw_text, re.DOTALL)
            if match_list:
                data = try_parse(match_list.group(0))
                if data and isinstance(data, list):
                    return {"quiz_mode": "batch", "questions": data}

            # 2. Try to find a code block containing an Array
            code_block = re.search(r"```(?:json)?\s*(\[\s*\{.*\}\s*\])\s*```", raw_text, re.DOTALL)
            if code_block:
                data = try_parse(code_block.group(1))
                if data and isinstance(data, list):
                    return {"quiz_mode": "batch", "questions": data}

            # 3. Fallback: Try to find a Single Object (Old behavior)
            # Find the first '{' and the last '}'
            start_index = raw_text.find('{')
            end_index = raw_text.rfind('}')

            if start_index != -1 and end_index != -1 and end_index > start_index:
                potential_json = raw_text[start_index : end_index + 1]
                data = try_parse(potential_json)
                
                if data and isinstance(data, dict):
                    # Check if it looks like a question
                    if "question_text" in data:
                        return {"quiz_mode": "single", "questions": [data]}
                    # Or if it is a list wrapped in dict (rare)
                    if "questions" in data and isinstance(data["questions"], list):
                        return {"quiz_mode": "batch", "questions": data["questions"]}

            logger.warning(f"QuizService: Failed to extract JSON array or object. Text: {raw_text[:50]}...")
            return None

        except Exception as e:
            logger.error(f"QuizService: Critical Extraction error: {str(e)}")
            return None