# src/utils/parsers/flashcard_stream_parser.py
import re
import logging
from typing import Generator, Dict, Any

from .base_stream_parser import BaseStreamParser

logger = logging.getLogger(__name__)

class FlashcardStreamParser:
    """
    Consumes the OpenAI stream and yields structured events specifically for Flashcards.
    Intercepts the background image request and yields individual cards progressively.
    """

    @staticmethod
    def parse(stream) -> Generator[Dict[str, Any], None, None]:
        buffer = ""
        card_count = 0
        last_checkpoint = None
        has_refused = False
        image_prompt_yielded = False

        try:
            for event in stream:
                # 1. Handle common events via Base Parser
                event_to_yield, is_refusal, delta = BaseStreamParser.handle_common_events(event)
                
                if event_to_yield:
                    yield event_to_yield
                if is_refusal:
                    has_refused = True
                    continue
                if not delta:
                    continue

                buffer += delta

                # 2. Interceptor for Deck Background Image
                if not image_prompt_yielded:
                    match = re.search(r'"image_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                    if match:
                        prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                            yield {
                                "type": "image_request",
                                "prompt": prompt_text
                            }
                        image_prompt_yielded = True

                # 3. Wait until we see the start of the cards array safely
                if last_checkpoint is None:
                    match = re.search(r'"cards"\s*:\s*\[', buffer)
                    if match:
                        last_checkpoint = match.end() - 1

                # 4. Detect and Parse JSON Objects (Flashcards)
                if last_checkpoint is not None:
                    # Delegate the heavy JSON parsing to the Base Parser
                    for data, new_checkpoint in BaseStreamParser.extract_json_objects(buffer, last_checkpoint):
                        
                        # Validate the object has the required keys for a flashcard
                        if "front" in data and "back" in data:
                            yield {"type": "card", "index": card_count, "data": data}
                            card_count += 1
                            
                        last_checkpoint = new_checkpoint

            # 5. Retrieve Final Response
            yield from BaseStreamParser.finalize_stream(stream, has_refused)

        except Exception as e:
            logger.error(f"Flashcard StreamParser failed: {e}")
            yield {"type": "error", "error": str(e)}