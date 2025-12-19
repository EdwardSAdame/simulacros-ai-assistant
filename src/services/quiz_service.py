# src/services/quiz_service.py
import json
import re
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class QuizService:
    """
    Encapsulates all logic related to generating and parsing Quiz content.
    """

    @staticmethod
    def get_system_instruction() -> Dict[str, Any]:
        """
        Returns the specific system instruction to force the AI to generate a structured JSON quiz.
        """
        instruction_text = (
            "SYSTEM INSTRUCTION: The user has requested a quiz/exam. "
            "You must generate a SINGLE JSON object containing the question data, "
            "AND a short conversational text confirmation. \n\n"
            
            "## Formatting Rules (STRICT):\n"
            "1. **LaTeX Required**: You MUST use LaTeX formatting (enclosed in `$`) for ALL mathematical expressions, numbers, variables, and chemical formulas.\n"
            "2. **Apply to ALL Fields**: This applies to both the `question_text` AND every string inside the `options` array.\n"
            "   - Bad: \"H2O + O2 -> H2O2\"\n"
            "   - Good: \"$H_2O + O_2 \\rightarrow H_2O_2$\"\n\n"

            "## Output Format:\n"
            "```json\n"
            "{\n"
            "  \"question_title\": \"Question 1\",\n"
            "  \"question_text\": \"The actual question stem here... (e.g. Balance $Fe + O_2$)\",\n"
            "  \"options\": [\n"
            "    \"$2Fe_2O_3$\",\n"
            "    \"$4Fe + 3O_2$\",\n"
            "    \"Option C\",\n"
            "    \"Option D\"\n"
            "  ],\n"
            "  \"correct_option_index\": 0,\n"
            "  \"image_query\": \"Visual search query for the question topic\",\n"
            "  \"reply_text\": \"I have generated a complex question about [topic] for you.\"\n"
            "}\n"
            "```\n"
            "Ensure the JSON is valid. Do not output any text outside the JSON block."
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }

    @staticmethod
    def extract_quiz_data(raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Parses the AI response to extract the embedded JSON object.
        Returns None if extraction fails.
        """
        try:
            # 1. Attempt to find JSON within Markdown code fences
            match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 2. Fallback: Attempt to find raw JSON object brackets
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
                
            return None
        except json.JSONDecodeError:
            logger.warning(f"QuizService: Failed to decode JSON from text: {raw_text[:50]}...")
            return None
        except Exception as e:
            logger.error(f"QuizService: Extraction error: {e}")
            return None