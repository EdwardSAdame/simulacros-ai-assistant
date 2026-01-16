# src/utils/stream_parser.py
import json
import re
import logging
from typing import Generator, Dict, Any
from src.schemas.quiz_schemas import QuizQuestion

logger = logging.getLogger(__name__)

class StreamParser:
    """
    Handles the low-level parsing of the text stream from OpenAI.
    Extracts the 'intro_message' and individual 'QuizQuestion' JSON objects
    from the incomplete string buffer.
    """

    @staticmethod
    def parse_quiz_stream(stream) -> Generator[Dict[str, Any], None, None]:
        """
        Consumes the OpenAI stream and yields structured events:
        - {"type": "intro", "text": "..."}
        - {"type": "question", "index": int, "data": QuizQuestion}
        - {"type": "done", "full_response": QuizResponse}
        - {"type": "error", "error": str}
        """
        buffer = ""
        intro_yielded = False
        question_count = 0
        last_checkpoint = None

        try:
            # 1. Iterate over the stream events
            for event in stream:
                if event.type == "response.output_text.delta":
                    buffer += event.delta
                    
                    # A. Detect Intro Message
                    if not intro_yielded and '"questions"' in buffer:
                        match = re.search(r'"intro_message"\s*:\s*"(.*?)"', buffer, re.DOTALL)
                        if match:
                            yield {"type": "intro", "text": match.group(1).replace('\\"', '"')}
                            intro_yielded = True
                    
                    # B. Detect Questions Array
                    q_marker = buffer.find('"questions"')
                    if q_marker != -1:
                        arr_start = buffer.find('[', q_marker)
                        if arr_start != -1:
                            if last_checkpoint is None: last_checkpoint = arr_start
                            cursor = last_checkpoint
                            depth = 0
                            in_str = False
                            escape = False
                            obj_start = -1
                            
                            # Stack-based parser to find balanced braces {}
                            while cursor < len(buffer):
                                char = buffer[cursor]
                                if not in_str:
                                    if char == '"': in_str = True
                                    elif char == '{':
                                        if depth == 0: obj_start = cursor
                                        depth += 1
                                    elif char == '}':
                                        depth -= 1
                                        if depth == 0:
                                            # Found a complete object
                                            try:
                                                json_str = buffer[obj_start:cursor+1]
                                                data = json.loads(json_str)
                                                
                                                # Helper for partial validation/wrapping
                                                class Wrapper:
                                                    def __init__(self, d): self.d = d
                                                    def dict(self): return self.d
                                                
                                                try: q_obj = QuizQuestion(**data)
                                                except: q_obj = Wrapper(data)
                                                
                                                yield {"type": "question", "index": question_count, "data": q_obj}
                                                question_count += 1
                                                last_checkpoint = cursor + 1
                                            except Exception: pass
                                    elif char == '\\': escape = True
                                else:
                                    if escape: escape = False
                                    elif char == '\\': escape = True
                                    elif char == '"': in_str = False
                                cursor += 1

            # 2. Retrieve Final Response (Standard OpenAI SDK method)
            final = stream.get_final_response()
            parsed = getattr(final, 'output_parsed', None) or getattr(final, 'parsed', None) or final
            
            yield {"type": "done", "full_response": parsed}

        except Exception as e:
            logger.error(f"StreamParser parsing failed: {e}")
            yield {"type": "error", "error": str(e)}