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
    Intercepts evaluation metadata, creative images, modular plot prompts, grouped contexts, and citations.
    Strictly isolates nested JSON arrays to prevent stack-parser overflow.
    """

    @staticmethod
    def parse(stream) -> Generator[Dict[str, Any], None, None]:
        buffer = ""
        intro_yielded = False
        metadata_yielded = False
        has_refused = False
        
        yielded_image_prompts = set()
        yielded_plot_prompts = set() 
        
        yielded_group_image_prompts = set()
        yielded_group_plot_prompts = set()
        
        q_format_types = {} 

        yielded_groups = set()
        group_checkpoints = {} 
        global_q_count = 0
        
        yielded_partial_questions = {} 

        questions_array_pattern = re.compile(r'"questions"\s*:\s*\[')

        try:
            for event in stream:
                event_to_yield, is_refusal, delta = BaseStreamParser.handle_common_events(event)
                
                if event_to_yield:
                    yield event_to_yield
                if is_refusal:
                    has_refused = True
                    continue
                if not delta:
                    continue

                buffer += delta

                format_matches = re.finditer(r'"format_type"\s*:\s*"([^"]+)"', buffer)
                for match in format_matches:
                    q_titles_before = buffer.count('"question_title"', 0, match.start())
                    actual_q_index = max(0, q_titles_before - 1)
                    if actual_q_index not in q_format_types:
                        q_format_types[actual_q_index] = match.group(1)

                group_image_matches = re.finditer(r'"group_image_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                for match in group_image_matches:
                    groups_before = len(re.findall(r'"questions"\s*:\s*\[', buffer[:match.start()]))
                    group_idx = max(0, groups_before - 1)
                    
                    if group_idx not in yielded_group_image_prompts:
                        prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                            yield {
                                "type": "image_request", 
                                "group_index": group_idx,
                                "is_group_level": True,
                                "prompt": prompt_text
                            }
                        yielded_group_image_prompts.add(group_idx)

                group_plot_matches = re.finditer(r'"group_plot_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                for match in group_plot_matches:
                    groups_before = len(re.findall(r'"questions"\s*:\s*\[', buffer[:match.start()]))
                    group_idx = max(0, groups_before - 1)
                    
                    if group_idx not in yielded_group_plot_prompts:
                        prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                            yield {
                                "type": "plot_request", 
                                "group_index": group_idx,
                                "is_group_level": True,
                                "prompt": prompt_text
                            }
                        yielded_group_plot_prompts.add(group_idx)

                prompt_matches = re.finditer(r'"image_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                for match in prompt_matches:
                    q_titles_before = buffer.count('"question_title"', 0, match.start())
                    actual_q_index = max(0, q_titles_before - 1)
                    
                    fmt = q_format_types.get(actual_q_index, "text_to_text")
                    is_allowed = fmt in ["image_to_text", "image_to_image"]
                    
                    if is_allowed and actual_q_index not in yielded_image_prompts:
                        prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                            yield {
                                "type": "image_request", 
                                "index": actual_q_index,
                                "is_group_level": False,
                                "prompt": prompt_text
                            }
                        yielded_image_prompts.add(actual_q_index)

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
                                "is_group_level": False,
                                "prompt": prompt_text
                            }
                        yielded_plot_prompts.add(tracker_key)

                if not intro_yielded and '"groups"' in buffer:
                    match = re.search(r'"intro_message"\s*:\s*"(.*?)"', buffer, re.DOTALL)
                    if match:
                        yield {"type": "intro", "text": match.group(1).replace('\\"', '"')}
                        intro_yielded = True

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

                group_matches = list(questions_array_pattern.finditer(buffer))
                
                for i, match in enumerate(group_matches):
                    group_idx = i
                    
                    if group_idx not in yielded_groups:
                        start_search = group_matches[i-1].end() if i > 0 else 0
                        group_chunk = buffer[start_search:match.start()]
                        
                        def extract_field(field_name):
                            m = re.search(fr'"{field_name}"\s*:\s*("(?:[^"\\]|\\.)*"|null)', group_chunk)
                            if not m or m.group(1) == "null": return None
                            try: return json.loads(m.group(1))
                            except: return m.group(1).strip('"')
                            
                        yield {
                            "type": "group_start", 
                            "group_index": group_idx, 
                            "group_title": extract_field("group_title"), 
                            "context_text": extract_field("context_text"),
                            "group_source_url": extract_field("group_source_url")
                        }
                        yielded_groups.add(group_idx)

                    questions_start = match.end() - 1
                    
                    if i + 1 < len(group_matches):
                        buffer_slice_end = group_matches[i+1].start()
                    else:
                        buffer_slice_end = len(buffer)
                        
                    slice_buffer = buffer[questions_start:buffer_slice_end]
                    
                    q_text_matches = list(re.finditer(r'"question_text"\s*:\s*"((?:[^"\\]|\\.)*)', slice_buffer))
                    if q_text_matches:
                        latest_q_match = q_text_matches[-1]
                        absolute_pos = questions_start + latest_q_match.start()
                        q_titles_before = buffer.count('"question_title"', 0, absolute_pos)
                        actual_q_index = max(0, q_titles_before - 1)
                        
                        partial_text = latest_q_match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        last_yielded_len = yielded_partial_questions.get(actual_q_index, 0)
                        
                        if len(partial_text) > last_yielded_len + 15 or (last_yielded_len == 0 and len(partial_text) > 0):
                            class PartialWrapper:
                                def __init__(self, d): self.d = d
                                def dict(self): return self.d
                                
                            yield {
                                "type": "question",
                                "index": actual_q_index,
                                "group_index": group_idx,
                                "data": PartialWrapper({
                                    "question_text": partial_text,
                                    "originalIndex": actual_q_index
                                })
                            }
                            yielded_partial_questions[actual_q_index] = len(partial_text)

                    checkpoint = group_checkpoints.get(group_idx, 0)
                    
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

                yield from BaseStreamParser.finalize_stream(stream, has_refused)

        except Exception as e:
            logger.error(f"QuizStreamParser parsing failed: {e}")
            yield {"type": "error", "error": str(e)}