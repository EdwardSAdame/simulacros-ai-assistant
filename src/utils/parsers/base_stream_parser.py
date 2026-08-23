# src/utils/parsers/base_stream_parser.py
import json
import logging
from typing import Generator, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class BaseStreamParser:
    """
    Provides reusable parsing utilities for OpenAI streams, abstracting away
    the low-level stack-based JSON parsing and common event handling.
    """

    @staticmethod
    def extract_json_objects(buffer: str, last_checkpoint: int) -> Generator[Tuple[Dict[str, Any], int], None, None]:
        """
        A generic stack-based JSON parser that finds complete JSON objects 
        within a text buffer starting from a given checkpoint.
        Yields a tuple of (parsed_dictionary, new_checkpoint_index).
        """
        cursor = last_checkpoint
        depth = 0
        in_str = False
        escape = False
        obj_start = -1
        
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
                        # Found a complete object
                        try:
                            json_str = buffer[obj_start:cursor+1]
                            data = json.loads(json_str)
                            yield data, cursor + 1
                        except Exception:
                            pass
                        obj_start = -1
            else:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == '"':
                    in_str = False
            cursor += 1

    @staticmethod
    def handle_common_events(event) -> Tuple[Dict[str, Any] | None, bool, str]:
        """
        Handles refusals, partial images, and text deltas.
        Returns: (Event to yield, is_refusal_flag, appended_text)
        """
        event_type = getattr(event, "type", "")

        # A. Detect Streaming Refusals
        if event_type == "response.content_part.added":
            part = getattr(event, "part", None)
            if part and getattr(part, "type", "") == "refusal":
                reason = getattr(part, "refusal", "Model refused the request for safety reasons.")
                return {"type": "refusal", "reason": reason}, True, ""

        elif event_type == "response.refusal.delta":
            reason = getattr(event, "delta", "Model refused.")
            return {"type": "refusal", "reason": reason}, True, ""

        # B. Detect Partial Images (Standard Tool Calling)
        elif event_type == "response.image_generation_call.partial_image":
            idx = getattr(event, "partial_image_index", 0)
            b64 = getattr(event, "partial_image_b64", "")
            if b64:
                return {"type": "partial_image", "index": idx, "b64_data": b64}, False, ""

        # C. Normal Text Stream Processing
        elif event_type == "response.output_text.delta":
            return None, False, getattr(event, "delta", "")

        return None, False, ""

    @staticmethod
    def finalize_stream(stream, has_refused: bool) -> Generator[Dict[str, Any], None, None]:
        """
        Handles the final response event and yields the full parsed payload.
        """
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