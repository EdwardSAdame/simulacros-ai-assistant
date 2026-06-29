# src/utils/parsers/quiz_stream_parser.py
import re
import logging
from typing import Generator, Dict, Any

from src.schemas.quiz_schemas import QuizQuestion
from .base_stream_parser import BaseStreamParser

logger = logging.getLogger(__name__)

class QuizStreamParser:
    """
    Consumes the OpenAI stream and yields structured events specifically for Quizzes.
    Intercepts creative images and modular plot prompts for background processing.
    """

    @staticmethod
    def parse(stream) -> Generator[Dict[str, Any], None, None]:
        buffer = ""
        intro_yielded = False
        question_count = 0
        last_checkpoint = None
        has_refused = False
        
        yielded_image_prompts = set()
        yielded_plot_prompts = set() # (q_index, opt_index)

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

                # 2. Intercept Creative Images (Stem Only)
                prompt_matches = re.finditer(r'"image_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                for match in prompt_matches:
                    q_titles_before = buffer.count('"question_title"', 0, match.start())
                    actual_q_index = max(0, q_titles_before - 1)
                    
                    if actual_q_index not in yielded_image_prompts:
                        prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                            yield {"type": "image_request", "index": actual_q_index, "prompt": prompt_text}
                        yielded_image_prompts.add(actual_q_index)

                # 3. Intercept Modular Plot Prompts (Path 2: Stem & Options)
                plot_matches = re.finditer(r'"plot_prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', buffer)
                for match in plot_matches:
                    q_titles_before = buffer.count('"question_title"', 0, match.start())
                    actual_q_index = max(0, q_titles_before - 1)
                    
                    options_starts_before = buffer.count('"options"', 0, match.start())
                    if options_starts_before < q_titles_before:
                        opt_index = None # It's the STEM
                    else:
                        last_options_pos = buffer.rfind('"options"', 0, match.start())
                        texts_since_options = buffer.count('"text"', last_options_pos, match.start())
                        opt_index = max(0, texts_since_options - 1)
                        opt_index = min(opt_index, 3)

                    tracker_key = (actual_q_index, opt_index)
                    
                    if tracker_key not in yielded_plot_prompts:
                        prompt_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                        if prompt_text and prompt_text.lower() not in ["null", "", "none"]:
                            yield {
                                "type": "plot_request", 
                                "index": actual_q_index, 
                                "opt_index": opt_index,
                                "prompt": prompt_text
                            }
                        yielded_plot_prompts.add(tracker_key)

                # 4. Detect Intro Message
                if not intro_yielded and '"questions"' in buffer:
                    match = re.search(r'"intro_message"\s*:\s*"(.*?)"', buffer, re.DOTALL)
                    if match:
                        yield {"type": "intro", "text": match.group(1).replace('\\"', '"')}
                        intro_yielded = True

                # 5. Detect and Parse Question Array
                if last_checkpoint is None:
                    match = re.search(r'"questions"\s*:\s*\[', buffer)
                    if match:
                        last_checkpoint = match.end() - 1
                        
                if last_checkpoint is not None:
                    # Delegate the heavy JSON parsing to the Base Parser
                    for data, new_checkpoint in BaseStreamParser.extract_json_objects(buffer, last_checkpoint):
                        
                        class Wrapper:
                            def __init__(self, d): self.d = d
                            def dict(self): return self.d
                        try: 
                            q_obj = QuizQuestion(**data)
                        except Exception: 
                            q_obj = Wrapper(data)
                            
                        yield {"type": "question", "index": question_count, "data": q_obj}
                        question_count += 1
                        last_checkpoint = new_checkpoint

            # 6. Retrieve Final Response
            yield from BaseStreamParser.finalize_stream(stream, has_refused)

        except Exception as e:
            logger.error(f"QuizStreamParser parsing failed: {e}")
            yield {"type": "error", "error": str(e)}