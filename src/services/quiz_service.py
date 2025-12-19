# src/services/quiz_service.py
import json
import re
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class QuizService:
    """
    Encapsulates all logic related to generating and parsing Quiz content.
    Includes robust error handling and JSON repair mechanisms.
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
            "1. **Double Escaping for JSON**: You are outputting a JSON string. ALL backslashes for LaTeX must be DOUBLE ESCAPED.\n"
            "   - Wrong: \"\\( x^2 \\)\" (This is invalid JSON string syntax)\n"
            "   - Right: \"\\\\( x^2 \\\\)\" (This is valid JSON)\n"
            "2. **LaTeX Delimiters**: \n"
            "   - Use `\\\\(` and `\\\\)` for inline math.\n"
            "   - Use `\\\\[` and `\\\\]` for block math.\n"
            "3. **Descriptive Titles (H1 Format)**: The `question_title` MUST be a short, 3-5 word summary of the specific topic, formatted as a Markdown H1 Header (start with `# `).\n\n"

            "## Output Format:\n"
            "```json\n"
            "{\n"
            "  \"question_title\": \"# Short Topic Title\",\n"
            "  \"question_text\": \"The actual question stem here... (e.g. Calculate \\\\( \\\\int x dx \\\\))\",\n"
            "  \"options\": [\n"
            "    \"\\\\( \\\\frac{x^2}{2} + C \\\\)\",\n"
            "    \"\\\\( x^2 \\\\)\",\n"
            "    \"Option C\",\n"
            "    \"Option D\"\n"
            "  ],\n"
            "  \"correct_option_index\": 0,\n"
            "  \"image_query\": \"Visual search query for the question topic\",\n"
            "  \"reply_text\": \"I have generated a calculus question for you.\"\n"
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
        Uses a robust 'Seek and Destroy' strategy and attempts to REPAIR malformed JSON/LaTeX.
        """
        if not raw_text:
            return None

        # Helper to attempt parsing
        def try_parse(text_chunk):
            try:
                return json.loads(text_chunk)
            except json.JSONDecodeError:
                # ATTEMPT REPAIR: Fix common LaTeX backslash issues in JSON
                # Replace single \( with \\( and \[ with \\[ if they aren't already escaped
                # This is a naive regex repair but catches 90% of LLM mistakes
                try:
                    logger.info("QuizService: JSON decode failed. Attempting LaTeX backslash repair.")
                    # Replace unescaped backslashes before ( ) [ ]
                    # Look for \ but not \\ followed by specific chars
                    repaired = text_chunk
                    # Fix inline math \( -> \\(
                    repaired = re.sub(r'(?<!\\)\\\(', r'\\\\(', repaired)
                    repaired = re.sub(r'(?<!\\)\\\)', r'\\\\)', repaired)
                    # Fix block math \[ -> \\[
                    repaired = re.sub(r'(?<!\\)\\\[', r'\\\\[', repaired)
                    repaired = re.sub(r'(?<!\\)\\\]', r'\\\\]', repaired)
                    
                    return json.loads(repaired)
                except Exception as e:
                    return None

        try:
            # Strategy 1: Fast Regex for standard Markdown code blocks
            code_block_match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL)
            if code_block_match:
                result = try_parse(code_block_match.group(1))
                if result: return result

            # Strategy 2: Robust Brute Force (The "Seek and Destroy" method)
            # Find the first '{' and the last '}' in the entire string.
            start_index = raw_text.find('{')
            end_index = raw_text.rfind('}')

            if start_index != -1 and end_index != -1 and end_index > start_index:
                potential_json = raw_text[start_index : end_index + 1]
                result = try_parse(potential_json)
                if result: return result
            
            logger.warning(f"QuizService: Final Extraction Failed. Content snippet: {raw_text[:50]}...")
            return None

        except Exception as e:
            logger.error(f"QuizService: Critical Extraction error: {str(e)}")
            return None