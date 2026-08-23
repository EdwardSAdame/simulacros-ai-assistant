import logging
import ijson
from typing import Generator, Dict, Any

from src.schemas.quiz_schemas import QuizQuestion
from .base_stream_parser import BaseStreamParser

logger = logging.getLogger(__name__)

class QuizStreamParser:
    """
    Consumes the OpenAI stream and yields structured events specifically for Quizzes.
    Utilizes ijson for robust, incremental JSON parsing to stream questions in real-time,
    eliminating the fragility of regex-based extraction.
    """

    @staticmethod
    def parse(stream) -> Generator[Dict[str, Any], None, None]:
        has_refused = False
        control_events = []

        # Helper to intercept SDK control events and yield pure bytes to ijson
        def _byte_generator():
            nonlocal has_refused
            for event in stream:
                event_to_yield, is_refusal, delta = BaseStreamParser.handle_common_events(event)
                
                if event_to_yield:
                    control_events.append(event_to_yield)
                if is_refusal:
                    has_refused = True
                    continue
                if delta:
                    yield delta.encode('utf-8')

        try:
            # ijson.parse yields (prefix, event, value) 
            # e.g., ("groups.item.questions.item.question_text", "string", "What is...")
            parser = ijson.parse(_byte_generator())
            
            eval_metadata = {}
            current_group = {}
            current_question = {}
            current_option = {}
            
            group_idx = -1
            question_idx = -1
            option_idx = -1

            for prefix, event, value in parser:
                # 1. Yield any control events (like status updates) intercepted during byte generation
                while control_events:
                    yield control_events.pop(0)

                # 2. Evaluation Metadata Tracking
                if prefix.startswith("evaluation_metadata"):
                    if event in ("string", "number", "boolean", "null") and len(prefix.split(".")) == 2:
                        key = prefix.split(".")[1]
                        eval_metadata[key] = value
                    elif prefix == "evaluation_metadata" and event == "end_map":
                        yield {"type": "evaluation_metadata", "data": eval_metadata}

                # 3. Group Tracking
                elif prefix == "groups.item":
                    if event == "start_map":
                        group_idx += 1
                        current_group = {"questions": []}
                        
                elif prefix.startswith("groups.item") and len(prefix.split(".")) == 3:
                    key = prefix.split(".")[2]
                    if event in ("string", "number", "boolean", "null") and key != "questions":
                        current_group[key] = value
                        
                # Yield group_start the moment the questions array begins
                elif prefix == "groups.item.questions" and event == "start_array":
                    yield {
                        "type": "group_start",
                        "group_index": group_idx,
                        "group_title": current_group.get("group_title"),
                        "context_text": current_group.get("context_text"),
                        "group_source_url": current_group.get("group_source_url")
                    }

                # 4. Question Tracking
                elif prefix == "groups.item.questions.item":
                    if event == "start_map":
                        question_idx += 1
                        option_idx = -1  # Reset local option index for the new question
                        current_question = {"options": []}
                    elif event == "end_map":
                        try:
                            # Validate the completed dictionary against your Pydantic schema
                            q_obj = QuizQuestion(**current_question)
                            yield {
                                "type": "question",
                                "index": question_idx,
                                "group_index": group_idx,
                                "data": q_obj
                            }
                        except Exception as e:
                            logger.warning(f"Validation skipped for partial question {question_idx}: {e}")
                            yield {
                                "type": "question",
                                "index": question_idx,
                                "group_index": group_idx,
                                "data": current_question
                            }

                elif prefix.startswith("groups.item.questions.item") and len(prefix.split(".")) == 5:
                    key = prefix.split(".")[4]
                    if event in ("string", "number", "boolean", "null") and key != "options":
                        current_question[key] = value
                        
                        # Maintain real-time typing effect on the frontend for the question text
                        if key == "question_text" and value:
                            yield {
                                "type": "question",
                                "index": question_idx,
                                "group_index": group_idx,
                                "data": {"question_text": value, "originalIndex": question_idx}
                            }

                        # Trigger visual worker pipelines instantly without waiting for the full question
                        if key == "image_prompt" and value:
                            yield {
                                "type": "image_request",
                                "index": question_idx,
                                "is_group_level": False,
                                "prompt": value
                            }
                        if key == "plot_prompt" and value:
                            yield {
                                "type": "plot_request",
                                "index": question_idx,
                                "opt_index": None,
                                "is_group_level": False,
                                "prompt": value
                            }

                # 5. Options Tracking
                elif prefix == "groups.item.questions.item.options.item":
                    if event == "start_map":
                        option_idx += 1
                        current_option = {}
                    elif event == "end_map":
                        current_question["options"].append(current_option)
                        
                elif prefix.startswith("groups.item.questions.item.options.item") and len(prefix.split(".")) == 7:
                    key = prefix.split(".")[6]
                    if event in ("string", "number", "boolean", "null"):
                        current_option[key] = value
                        
                        # Trigger visual worker for individual option graphs
                        if key == "plot_prompt" and value:
                            yield {
                                "type": "plot_request",
                                "index": question_idx,
                                "opt_index": option_idx,
                                "is_group_level": False,
                                "prompt": value
                            }

            # Yield any remaining control events
            while control_events:
                yield control_events.pop(0)

            yield from BaseStreamParser.finalize_stream(stream, has_refused)

        except Exception as e:
            logger.error(f"QuizStreamParser parsing failed: {e}")
            yield {"type": "error", "error": str(e)}