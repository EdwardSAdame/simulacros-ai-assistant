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
            "AND a short conversational text confirmation inside the JSON 'reply_text' field. \n\n"
            
            "## Formatting Rules (STRICT):\n"
            "1. **LaTeX Required**: You MUST use standard LaTeX delimiters for ALL math:\n"
            "   - Use `\\(` and `\\)` for inline math (e.g., `\\( x^2 \\)`).\n"
            "   - Use `\\[` and `\\]` for block math (e.g., `\\[ E=mc^2 \\]`).\n"
            "   - Do NOT use `$` signs.\n"
            "2. **Apply to ALL Fields**: This applies to both the `question_text` AND every string inside the `options` array.\n"
            "   - Bad: \"H2O + O2 -> H2O2\" or \"$H_2O$\"\n"
            "   - Good: \"\\( H_2O + O_2 \\rightarrow H_2O_2 \\)\"\n"
            "3. **Descriptive Titles (H1 Format)**: The `question_title` MUST be a short, 3-5 word summary of the specific topic, formatted as a Markdown H1 Header (start with `# `).\n"
            "   - Bad: \"**Balancing Equations**\" (Bold only)\n"
            "   - Good: \"# Balancing Redox Equations\" (H1 Header)\n\n"

            "## Output Format:\n"
            "```json\n"
            "{\n"
            "  \"question_title\": \"# Short Topic Title\",\n"
            "  \"question_text\": \"The actual question stem here... (e.g. Balance \\( Fe + O_2 \\))\",\n"
            "  \"options\": [\n"
            "    \"\\( 2Fe_2O_3 \\)\",\n"
            "    \"\\( 4Fe + 3O_2 \\)\",\n"
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
        Uses a robust 'Seek and Destroy' strategy to ignore conversational filler.
        """
        if not raw_text:
            return None

        try:
            # Strategy 1: Fast Regex for standard Markdown code blocks
            # Matches ```json ... ``` OR just ``` ... ```
            code_block_match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL)
            if code_block_match:
                try:
                    return json.loads(code_block_match.group(1))
                except json.JSONDecodeError:
                    pass # Fall through to Strategy 2 if the block wasn't valid JSON

            # Strategy 2: Robust Brute Force (The "Seek and Destroy" method)
            # Find the first '{' and the last '}' in the entire string.
            # This ignores "Sure! Here is the JSON:" at the start and "Hope this helps!" at the end.
            start_index = raw_text.find('{')
            end_index = raw_text.rfind('}')

            if start_index != -1 and end_index != -1 and end_index > start_index:
                potential_json = raw_text[start_index : end_index + 1]
                return json.loads(potential_json)
            
            return None

        except json.JSONDecodeError as e:
            logger.warning(f"QuizService: JSON Decode failed. Text: {raw_text[:100]}... Error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"QuizService: Critical Extraction error: {str(e)}")
            return None