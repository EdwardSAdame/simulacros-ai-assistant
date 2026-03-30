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
    Extracts the 'intro_message', individual 'QuizQuestion' JSON objects,
    and progressive image chunks from the stream.
    """

    @staticmethod
    def parse_quiz_stream(stream) -> Generator[Dict[str, Any], None, None]:
        """
        Consumes the OpenAI stream and yields structured events:
        - {"type": "intro", "text": "..."}
        - {"type": "question", "index": int, "data": QuizQuestion}
        - {"type": "partial_image", "index": int, "b64_data": str}
        - {"type": "refusal", "reason": str}
        - {"type": "done", "full_response": QuizResponse}
        - {"type": "error", "error": str}
        """
        buffer = ""
        intro_yielded = False
        question_count = 0
        last_checkpoint = None
        has_refused = False

        try:
            # 1. Iterate over the stream events
            for event in stream:
                event_type = getattr(event, "type", "")

                # A. Detect Streaming Refusals
                if event_type == "response.content_part.added":
                    part = getattr(event, "part", None)
                    if part and getattr(part, "type", "") == "refusal":
                        has_refused = True
                        yield {"type": "refusal", "reason": getattr(part, "refusal", "Model refused the request for safety reasons.")}
                        continue

                elif event_type == "response.refusal.delta":
                    has_refused = True
                    yield {"type": "refusal", "reason": getattr(event, "delta", "Model refused.")}
                    continue

                # B. Detect Partial Images (Streaming Image Generation)
                elif event_type == "response.image_generation_call.partial_image":
                    idx = getattr(event, "partial_image_index", 0)
                    b64 = getattr(event, "partial_image_b64", "")
                    if b64:
                        yield {
                            "type": "partial_image", 
                            "index": idx, 
                            "b64_data": b64
                        }
                    continue

                # C. Normal Text Stream Processing
                elif event_type == "response.output_text.delta":
                    buffer += getattr(event, "delta", "")
                    
                    # Detect Intro Message
                    if not intro_yielded and '"questions"' in buffer:
                        match = re.search(r'"intro_message"\s*:\s*"(.*?)"', buffer, re.DOTALL)
                        if match:
                            yield {"type": "intro", "text": match.group(1).replace('\\"', '"')}
                            intro_yielded = True
                    
                    # Detect Questions Array
                    q_marker = buffer.find('"questions"')
                    if q_marker != -1:
                        arr_start = buffer.find('[', q_marker)
                        if arr_start != -1:
                            if last_checkpoint is None: 
                                last_checkpoint = arr_start
                            
                            cursor = last_checkpoint
                            depth = 0
                            in_str = False
                            escape = False
                            obj_start = -1
                            
                            # Stack-based parser to find balanced braces {}
                            while cursor < len(buffer):
                                char = buffer[cursor]
                                if not in_str:
                                    if char == '"': 
                                        in_str = True
                                    elif char == '{':
                                        if depth == 0: 
                                            obj_start = cursor
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
                                                
                                                try: 
                                                    q_obj = QuizQuestion(**data)
                                                except: 
                                                    q_obj = Wrapper(data)
                                                
                                                yield {"type": "question", "index": question_count, "data": q_obj}
                                                question_count += 1
                                                last_checkpoint = cursor + 1
                                            except Exception: 
                                                pass
                                elif char == '\\': 
                                    escape = True
                                else:
                                    if escape: 
                                        escape = False
                                    elif char == '\\': 
                                        escape = True
                                    elif char == '"': 
                                        in_str = False
                                cursor += 1

            # 2. Retrieve Final Response (Standard OpenAI SDK method)
            if hasattr(stream, 'get_final_response'):
                final = stream.get_final_response()
                
                # Double-check for refusals in the final payload
                refusal_msg = None
                for output in getattr(final, "output", []):
                    if getattr(output, "type", "") == "message":
                        for item in getattr(output, "content", []):
                            if getattr(item, "type", "") == "refusal":
                                refusal_msg = getattr(item, "refusal", "Model refused the request.")
                
                if refusal_msg and not has_refused:
                    yield {"type": "refusal", "reason": refusal_msg}
                    return

                parsed = getattr(final, 'output_parsed', None) or getattr(final, 'parsed', None) or final
                yield {"type": "done", "full_response": parsed}
            else:
                yield {"type": "error", "error": "Stream did not contain a final response method."}

        except Exception as e:
            logger.error(f"StreamParser parsing failed: {e}")
            yield {"type": "error", "error": str(e)}