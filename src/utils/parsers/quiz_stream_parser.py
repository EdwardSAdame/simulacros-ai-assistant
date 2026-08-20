import re
import json
import logging
from typing import Generator, Dict, Any

from src.schemas.quiz_schemas import QuizQuestion
from .base_stream_parser import BaseStreamParser

logger = logging.getLogger(__name__)

class QuizStreamParser:
    """
    Consumes the OpenAI stream and yields structured events specifically for Quizzes.
    Intercepts evaluation metadata, creative images, modular plot prompts, and grouped contexts.
    Strictly isolates nested JSON arrays to prevent stack-parser overflow.
    """

    @staticmethod
    def parse(stream) -> Generator[Dict[str, Any], None, None]:
        buffer = ""
        intro_yielded = False
        metadata_yielded = False
        has_refused = False
        
        yielded_image_prompts = set()
        yielded_plot_prompts = set() # (global_q_index, opt_index)
        q_format_types = {} # Maps global_q_index -> format_type string

        yielded_groups = set()
        group_checkpoints = {} # Maps group_index -> last_checkpoint
        global_q_count = 0

        # OpenAI Structured Outputs guarantees strict key ordering.
        # This regex safely captures the group context before the questions array begins.
        group_pattern = re.compile(
            r'"group_title"\s*:\s*(null|"(?:[^"\\]|\\.)*")\s*,\s*'
            r'"context_text"\s*:\s*(null|"(?:[^"\\]|\\.)*")\s*,\s*'
            r'"questions"\s*:\s*\['
        )

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

                # 2. Intercept and Track Format Types
                format_matches = re.finditer(r'"format_type"\s*:\s*"([^"]+)"', buffer)
                for match in format_matches:
                    q_titles_before = buffer.count('"question_title"', 0, match.start())
                    actual_q_index = max(0, q_titles_before - 1)
                    if actual_q_index not in q_format_types:
                        q_format_types[actual_q_index] = match.group(1)

                # 3. Intercept Creative Images (Stem Only)
                prompt_matches = re.finditer(r'"image_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                for match in prompt_matches:
                    q_titles_before = buffer.count('"question_title"', 0, match.start())
                    actual_q_index = max(0, q_titles_before - 1)
                    
                    fmt = q_format_types.get(actual_q_index, "text_to_text")
                    is_allowed = fmt in ["image_to_text", "image_to_image"]
                    
                    if is_allowed and actual_q_index not in yielded_image_prompts:
                        prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                            yield {"type": "image_request", "index": actual_q_index, "prompt": prompt_text}
                        yielded_image_prompts.add(actual_q_index)

                # 4. Intercept Modular Plot Prompts (Stem & Options)
                plot_matches = re.finditer(r'"plot_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                for match in plot_matches:
                    q_titles_before = buffer.count('"question_title"', 0, match.start())
                    actual_q_index = max(0, q_titles_before - 1)
                    
                    options_starts_before = buffer.count('"options"', 0, match.start())
                    is_stem = options_starts_before < q_titles_before
                    
                    fmt = q_format_types.get(actual_q_index, "text_to_text")
                    
                    if is_stem:
                        opt_index = None
                        is_allowed = fmt in ["image_to_text", "image_to_image"]
                    else:
                        last_options_pos = buffer.rfind('"options"', 0, match.start())
                        texts_since_options = buffer.count('"text"', last_options_pos, match.start())
                        opt_index = max(0, texts_since_options - 1)
                        opt_index = min(opt_index, 3)
                        is_allowed = fmt in ["text_to_image", "image_to_image"]

                    tracker_key = (actual_q_index, opt_index)
                    
                    if is_allowed and tracker_key not in yielded_plot_prompts:
                        prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                            yield {
                                "type": "plot_request", 
                                "index": actual_q_index, 
                                "opt_index": opt_index,
                                "prompt": prompt_text
                            }
                        yielded_plot_prompts.add(tracker_key)

                # 5. Detect Intro Message
                if not intro_yielded and '"groups"' in buffer:
                    match = re.search(r'"intro_message"\s*:\s*"(.*?)"', buffer, re.DOTALL)
                    if match:
                        yield {"type": "intro", "text": match.group(1).replace('\\"', '"')}
                        intro_yielded = True

                # 6. Detect and Parse Evaluation Metadata
                if not metadata_yielded and '"evaluation_metadata"' in buffer:
                    start_idx = buffer.find('"evaluation_metadata"')
                    brace_idx = buffer.find('{', start_idx)
                    
                    if brace_idx != -1:
                        open_braces = 0
                        in_string = False
                        escape = False
                        end_idx = -1
                        
                        for i in range(brace_idx, len(buffer)):
                            char = buffer[i]
                            if escape:
                                escape = False
                                continue
                            if char == '\\':
                                escape = True
                                continue
                            if char == '"':
                                in_string = not in_string
                                continue
                            
                            if not in_string:
                                if char == '{':
                                    open_braces += 1
                                elif char == '}':
                                    open_braces -= 1
                                    if open_braces == 0:
                                        end_idx = i
                                        break
                        
                        if end_idx != -1:
                            meta_str = buffer[brace_idx:end_idx+1]
                            try:
                                meta_obj = json.loads(meta_str)
                                yield {"type": "evaluation_metadata", "data": meta_obj}
                                metadata_yielded = True
                            except json.JSONDecodeError:
                                pass

                # 7. Detect and Parse Groups and their Nested Questions
                group_matches = list(group_pattern.finditer(buffer))
                
                for i, match in enumerate(group_matches):
                    group_idx = i
                    
                    # Yield the group passage to the frontend immediately
                    if group_idx not in yielded_groups:
                        title_raw = match.group(1)
                        context_raw = match.group(2)
                        
                        group_title = json.loads(title_raw) if title_raw != "null" else None
                        context_text = json.loads(context_raw) if context_raw != "null" else None
                        
                        yield {
                            "type": "group_start", 
                            "group_index": group_idx, 
                            "group_title": group_title, 
                            "context_text": context_text
                        }
                        yielded_groups.add(group_idx)

                    # Isolate the buffer for this specific group to prevent parser overflow
                    questions_start = match.end() - 1
                    
                    if i + 1 < len(group_matches):
                        buffer_slice_end = group_matches[i+1].start()
                    else:
                        buffer_slice_end = len(buffer)
                        
                    slice_buffer = buffer[:buffer_slice_end]
                    checkpoint = group_checkpoints.get(group_idx, questions_start)
                    
                    # Delegate strictly bounds-checked buffer to the generic parser
                    for data, new_ckpt in BaseStreamParser.extract_json_objects(slice_buffer, checkpoint):
                        class Wrapper:
                            def __init__(self, d): self.d = d
                            def dict(self): return self.d
                            
                        try: 
                            q_obj = QuizQuestion(**data)
                        except Exception: 
                            q_obj = Wrapper(data)
                            
                        yield {
                            "type": "question", 
                            "index": global_q_count, 
                            "group_index": group_idx,
                            "data": q_obj
                        }
                        global_q_count += 1
                        group_checkpoints[group_idx] = new_ckpt

            # 8. Retrieve Final Response
            yield from BaseStreamParser.finalize_stream(stream, has_refused)

        except Exception as e:
            logger.error(f"QuizStreamParser parsing failed: {e}")
            yield {"type": "error", "error": str(e)}