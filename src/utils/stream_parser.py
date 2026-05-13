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
    Extracts structured items progressively so the UI can stream them in real-time.
    """

    @staticmethod
    def parse_quiz_stream(stream) -> Generator[Dict[str, Any], None, None]:
        """
        Consumes the OpenAI stream and yields structured events for Quizzes.
        """
        buffer = ""
        intro_yielded = False
        question_count = 0
        last_checkpoint = None
        has_refused = False
        
        # Track which questions we have already requested visuals for
        yielded_image_prompts = set()
        yielded_plot_prompts = set()

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

                # B. Detect Partial Images (Standard Tool Calling - Kept for fallback safety)
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
                    
                    # -------------------------------------------------------------------------
                    # ASYNC INTERCEPTOR FOR CREATIVE IMAGES
                    # -------------------------------------------------------------------------
                    prompt_matches = re.finditer(r'"image_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                    for match in prompt_matches:
                        # Calculate actual question index by counting how many "question_title" keys came before this
                        q_titles_before = buffer.count('"question_title"', 0, match.start())
                        actual_q_index = max(0, q_titles_before - 1)
                        
                        if actual_q_index not in yielded_image_prompts:
                            prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                            
                            # Only trigger if the AI actually wrote a prompt (ignored if null or empty)
                            if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                                yield {
                                    "type": "image_request", 
                                    "index": actual_q_index, 
                                    "prompt": prompt_text
                                }
                            yielded_image_prompts.add(actual_q_index)

                    # -------------------------------------------------------------------------
                    # ASYNC INTERCEPTOR FOR CODE INTERPRETER PLOTS
                    # -------------------------------------------------------------------------
                    plot_matches = re.finditer(r'"plot_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                    for match in plot_matches:
                        q_titles_before = buffer.count('"question_title"', 0, match.start())
                        actual_q_index = max(0, q_titles_before - 1)
                        
                        if actual_q_index not in yielded_plot_prompts:
                            prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                            
                            if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                                yield {
                                    "type": "plot_request", 
                                    "index": actual_q_index, 
                                    "prompt": prompt_text
                                }
                            yielded_plot_prompts.add(actual_q_index)
                    # -------------------------------------------------------------------------

                    # Detect Intro Message
                    if not intro_yielded and '"questions"' in buffer:
                        match = re.search(r'"intro_message"\s*:\s*"(.*?)"', buffer, re.DOTALL)
                        if match:
                            yield {"type": "intro", "text": match.group(1).replace('\\"', '"')}
                            intro_yielded = True
                    
                    # Detect Questions Array Safely
                    if last_checkpoint is None:
                        match = re.search(r'"questions"\s*:\s*\[', buffer)
                        if match:
                            last_checkpoint = match.end() - 1
                            
                    if last_checkpoint is not None:
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


    # -------------------------------------------------------------------------
    # MIND MAP STREAM PARSER
    # -------------------------------------------------------------------------
    @staticmethod
    def parse_mindmap_stream(stream) -> Generator[Dict[str, Any], None, None]:
        """
        Consumes the OpenAI stream and yields structured events for Mind Maps:
        - {"type": "node", "data": dict}
        - {"type": "edge", "data": dict}
        - {"type": "done", "full_response": MindMapPayload}
        """
        buffer = ""
        last_checkpoint = None
        has_refused = False
        
        try:
            for event in stream:
                event_type = getattr(event, "type", "")

                # A. Detect Streaming Refusals
                if event_type == "response.content_part.added":
                    part = getattr(event, "part", None)
                    if part and getattr(part, "type", "") == "refusal":
                        has_refused = True
                        yield {"type": "refusal", "reason": getattr(part, "refusal", "Model refused.")}
                        continue
                elif event_type == "response.refusal.delta":
                    has_refused = True
                    yield {"type": "refusal", "reason": getattr(event, "delta", "Model refused.")}
                    continue

                # B. Normal Text Stream Processing
                elif event_type == "response.output_text.delta":
                    buffer += getattr(event, "delta", "")
                    
                    # Wait until we see the start of the nodes array safely
                    if last_checkpoint is None:
                        match = re.search(r'"nodes"\s*:\s*\[', buffer)
                        if match:
                            last_checkpoint = match.end() - 1
                    
                    if last_checkpoint is not None:
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
                                    if depth == 0 and obj_start != -1:
                                        try:
                                            json_str = buffer[obj_start:cursor+1]
                                            data = json.loads(json_str)
                                            
                                            # Duck-type the object to decide if it is a node or edge
                                            if "level" in data and "label" in data:
                                                yield {"type": "node", "data": data}
                                            elif ("from" in data or "source" in data) and "to" in data:
                                                yield {"type": "edge", "data": data}
                                                
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

            # 2. Retrieve Final Response
            if hasattr(stream, 'get_final_response'):
                final = stream.get_final_response()
                
                refusal_msg = None
                for output in getattr(final, "output", []):
                    if getattr(output, "type", "") == "message":
                        for item in getattr(output, "content", []):
                            if getattr(item, "type", "") == "refusal":
                                refusal_msg = getattr(item, "refusal", "Model refused.")
                
                if refusal_msg and not has_refused:
                    yield {"type": "refusal", "reason": refusal_msg}
                    return

                parsed = getattr(final, 'output_parsed', None) or getattr(final, 'parsed', None) or final
                yield {"type": "done", "full_response": parsed}
            else:
                yield {"type": "error", "error": "Stream did not contain a final response method."}

        except Exception as e:
            logger.error(f"MindMap StreamParser failed: {e}")
            yield {"type": "error", "error": str(e)}

    # -------------------------------------------------------------------------
    # FLASHCARD STREAM PARSER
    # -------------------------------------------------------------------------
    @staticmethod
    def parse_flashcard_stream(stream) -> Generator[Dict[str, Any], None, None]:
        """
        Consumes the OpenAI stream and yields structured events for Flashcards:
        - {"type": "card", "index": int, "data": dict}
        - {"type": "done", "full_response": FlashcardsPayload}
        """
        buffer = ""
        card_count = 0
        last_checkpoint = None
        has_refused = False
        
        try:
            for event in stream:
                event_type = getattr(event, "type", "")

                # A. Detect Streaming Refusals
                if event_type == "response.content_part.added":
                    part = getattr(event, "part", None)
                    if part and getattr(part, "type", "") == "refusal":
                        has_refused = True
                        yield {"type": "refusal", "reason": getattr(part, "refusal", "Model refused.")}
                        continue
                elif event_type == "response.refusal.delta":
                    has_refused = True
                    yield {"type": "refusal", "reason": getattr(event, "delta", "Model refused.")}
                    continue

                # B. Normal Text Stream Processing
                elif event_type == "response.output_text.delta":
                    buffer += getattr(event, "delta", "")
                    
                    # Wait until we see the start of the cards array safely
                    if last_checkpoint is None:
                        match = re.search(r'"cards"\s*:\s*\[', buffer)
                        if match:
                            last_checkpoint = match.end() - 1
                    
                    if last_checkpoint is not None:
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
                                    if depth == 0 and obj_start != -1:
                                        try:
                                            json_str = buffer[obj_start:cursor+1]
                                            data = json.loads(json_str)
                                            
                                            # Validate the object has the required keys for a flashcard
                                            if "front" in data and "back" in data:
                                                yield {"type": "card", "index": card_count, "data": data}
                                                card_count += 1
                                                
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

            # 2. Retrieve Final Response
            if hasattr(stream, 'get_final_response'):
                final = stream.get_final_response()
                
                refusal_msg = None
                for output in getattr(final, "output", []):
                    if getattr(output, "type", "") == "message":
                        for item in getattr(output, "content", []):
                            if getattr(item, "type", "") == "refusal":
                                refusal_msg = getattr(item, "refusal", "Model refused.")
                
                if refusal_msg and not has_refused:
                    yield {"type": "refusal", "reason": refusal_msg}
                    return

                parsed = getattr(final, 'output_parsed', None) or getattr(final, 'parsed', None) or final
                yield {"type": "done", "full_response": parsed}
            else:
                yield {"type": "error", "error": "Stream did not contain a final response method."}

        except Exception as e:
            logger.error(f"Flashcard StreamParser failed: {e}")
            yield {"type": "error", "error": str(e)}