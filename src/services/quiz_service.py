# src/services/quiz_service.py
import json
import re
import logging
from typing import Dict, List, Optional, Any, Union
from src.config.system_instructions import BASE_SYSTEM_INSTRUCTIONS

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
        Combines the site's canonical PERSONA (Roma) with the specific TECHNICAL rules for the quiz.
        """
        
        instruction_text = (
            f"{BASE_SYSTEM_INSTRUCTIONS}\n\n"
            
            f"## IMMEDIATE RUNTIME MISSION: QUIZ GENERATION\n"
            f"The user has requested a quiz/exam about '{topic}'. "
            f"You must generate a JSON ARRAY containing exactly {num_questions} distinct questions. \n\n"
            
            "## Execution Protocol:\n"
            "1. **Voice Enforced**: You are Roma. Be cold, precise, and efficient. Waste no words.\n"
            "2. **Conversational Header**: Provide **ONLY ONE concise sentence** to introduce the challenge. Do NOT explain what the quiz is designed to do. Just command the user to begin.\n"
            "3. **JSON Payload**: Follow the single sentence immediately with the JSON block.\n\n"

            "## JSON Formatting & Content Rules (STRICT):\n"
            "1. **Output Format**: Return a LIST (Array) of objects.\n"
            "2. **Double Escaping**: ALL backslashes for LaTeX must be DOUBLE ESCAPED (e.g., `\\\\( x^2 \\\\)`).\n"
            "3. **Math Syntax**: Use `\\\\(` and `\\\\)` for inline math.\n"
            "4. **Difficulty & Style**: Questions must be **challenging, intriguing, and non-trivial**.\n"
            "5. **Numbering & Titles**: You MUST include the question number in the `question_title` (e.g., '# 1. Integration').\n"
            "6. **Content Fields**: \n"
            "   - `question_title`: H1 Markdown title with Number + Topic (e.g., '# 1. [Topic]').\n"
            "   - `question_text`: The question stem (do not repeat the number here).\n"
            "   - `options`: Array of 4 strings.\n"
            "   - `correct_option_index`: 0-3.\n"
            "   - `explanation`: Short text explaining why the answer is correct.\n\n"

            "## Expected Output Structure:\n"
            "Proceed with the evaluation of [Topic].\n"
            "```json\n"
            "[\n"
            "  {\n"
            "    \"question_title\": \"# 1. Integration by Parts\",\n"
            "    \"question_text\": \"Solve the integral \\\\( \\\\int x e^x dx \\\\) and identify the correct methodology.\",\n"
            "    \"options\": [\"\\\\( e^x(x-1) + C \\\\)\", \"\\\\( xe^x + C \\\\)\", \"\\\\( e^x(x+1) + C \\\\)\", \"\\\\( x^2e^x + C \\\\)\"],\n"
            "    \"correct_option_index\": 0,\n"
            "    \"explanation\": \"Using integration by parts with u=x and dv=e^x dx.\"\n"
            "  }\n"
            "]\n"
            "```\n"
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
        """
        if not raw_text:
            return None

        # Helper to attempt parsing
        def try_parse(text_chunk):
            try:
                # Naive repair for common LaTeX backslash issues
                repaired = text_chunk
                repaired = re.sub(r'(?<!\\)\\\(', r'\\\\(', repaired)
                repaired = re.sub(r'(?<!\\)\\\)', r'\\\\)', repaired)
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

            # 3. Fallback: Try to find a Single Object
            start_index = raw_text.find('{')
            end_index = raw_text.rfind('}')

            if start_index != -1 and end_index != -1 and end_index > start_index:
                potential_json = raw_text[start_index : end_index + 1]
                data = try_parse(potential_json)
                
                if data and isinstance(data, dict):
                    if "questions" in data and isinstance(data["questions"], list):
                        return {"quiz_mode": "batch", "questions": data["questions"]}
                    return {"quiz_mode": "single", "questions": [data]}

            logger.warning(f"QuizService: Failed to extract JSON array or object. Text: {raw_text[:50]}...")
            return None

        except Exception as e:
            logger.error(f"QuizService: Critical Extraction error: {str(e)}")
            return None

    @staticmethod
    def clean_response_text(raw_text: str) -> str:
        """
        Removes the JSON block (and code fences) from the AI's response,
        returning ONLY the conversational text generated by the AI.
        """
        if not raw_text: return ""
        
        # 1. Remove markdown code blocks that contain the JSON: ```json ... ```
        cleaned = re.sub(r"```.*?```", "", raw_text, flags=re.DOTALL)
        
        # 2. Remove raw JSON arrays if they are not inside code blocks: [ { ... } ]
        cleaned = re.sub(r"\[\s*\{.*\}\s*\]", "", cleaned, flags=re.DOTALL)
        
        # 3. Clean up extra whitespace/newlines created by the removal
        return cleaned.strip()