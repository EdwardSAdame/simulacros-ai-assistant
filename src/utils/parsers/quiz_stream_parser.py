# FILE: src/utils/parsers/quiz_stream_parser.py
import logging
import traceback
import ijson
from typing import Generator, Dict, Any

from src.schemas.quiz_schemas import QuizQuestion
from .base_stream_parser import BaseStreamParser

logger = logging.getLogger(__name__)


class BytesGeneratorStream:
    """
    Duck-typed stream adapter that wraps a byte generator and exposes
    a non-blocking .read() interface required by ijson for real-time streaming.
    """

    def __init__(self, generator):
        self._gen = generator
        self._buffer = b""

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            chunks = [self._buffer]
            chunks.extend(self._gen)
            self._buffer = b""
            return b"".join(chunks)

        while not self._buffer:
            try:
                chunk = next(self._gen)
                if chunk:
                    self._buffer += chunk
            except StopIteration:
                break

        if not self._buffer:
            return b""

        data = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return data


class QuizStreamParser:
    """
    Consumes the OpenAI stream and yields structured events specifically for Quizzes.
    Implements Cluster Buffering: Standalone questions stream instantly, while 
    clustered questions (sharing a reading passage) wait until the entire block forms.
    """

    @staticmethod
    def parse(stream) -> Generator[Dict[str, Any], None, None]:
        has_refused = False
        control_events = []

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
            stream_adapter = BytesGeneratorStream(_byte_generator())
            parser = ijson.parse(stream_adapter)

            eval_metadata = {}
            current_group = {}
            current_question = {}
            current_option = {}

            group_idx = -1
            question_idx = -1
            option_idx = -1
            
            buffered_questions = []
            group_started_sent = set()

            for prefix, event, value in parser:
                while control_events:
                    yield control_events.pop(0)

                # 1. Evaluation Metadata Tracking
                if prefix.startswith("evaluation_metadata"):
                    if event in ("string", "number", "boolean", "null") and len(prefix.split(".")) == 2:
                        key = prefix.split(".")[1]
                        eval_metadata[key] = value
                    elif prefix == "evaluation_metadata" and event == "end_map":
                        yield {"type": "evaluation_metadata", "data": eval_metadata}

                # 2. Group Tracking
                elif prefix == "groups.item":
                    if event == "start_map":
                        group_idx += 1
                        current_group = {"questions": []}
                    elif event == "end_map":
                        # FLUSH BUFFER: Yield all questions for this clustered group at once
                        for q_event in buffered_questions:
                            yield q_event
                        buffered_questions.clear()

                elif prefix.startswith("groups.item") and len(prefix.split(".")) == 3:
                    key = prefix.split(".")[2]
                    if event in ("string", "number", "boolean", "null") and key != "questions":
                        current_group[key] = value

                # The safest point to emit group metadata is exactly when the questions array starts,
                # ensuring all preceding parent fields (title, context, images) have been fully parsed.
                elif prefix == "groups.item.questions" and event == "start_array":
                    if group_idx > -1 and group_idx not in group_started_sent:
                        group_started_sent.add(group_idx)
                        yield {
                            "type": "group_start",
                            "group_index": group_idx,
                            "group_title": current_group.get("group_title"),
                            "context_text": current_group.get("context_text"),
                            "group_source_url": current_group.get("group_source_url"),
                            "group_plot_prompt": current_group.get("group_plot_prompt"),
                            "group_image_prompt": current_group.get("group_image_prompt")
                        }

                # 3. Question Tracking
                elif prefix == "groups.item.questions.item":
                    if event == "start_map":
                        question_idx += 1
                        option_idx = -1
                        current_question = {"options": []}
                    elif event == "end_map":
                        try:
                            q_obj = QuizQuestion(**current_question)
                            q_payload = q_obj
                        except Exception as e:
                            logger.warning(f"Validation skipped for partial question {question_idx}: {e}")
                            q_payload = current_question

                        q_event = {
                            "type": "question",
                            "index": question_idx,
                            "group_index": group_idx,
                            "data": q_payload
                        }

                        # Fallback safeguard: if group start hasn't fired yet for a context group, force it now
                        if group_idx not in group_started_sent:
                            group_started_sent.add(group_idx)
                            yield {
                                "type": "group_start",
                                "group_index": group_idx,
                                "group_title": current_group.get("group_title"),
                                "context_text": current_group.get("context_text"),
                                "group_source_url": current_group.get("group_source_url"),
                                "group_plot_prompt": current_group.get("group_plot_prompt"),
                                "group_image_prompt": current_group.get("group_image_prompt")
                            }

                        has_context = bool(
                            current_group.get("group_title") or 
                            current_group.get("context_text") or 
                            current_group.get("group_image_prompt") or 
                            current_group.get("group_plot_prompt")
                        )

                        if has_context:
                            buffered_questions.append(q_event)
                        else:
                            yield q_event

                elif prefix.startswith("groups.item.questions.item") and len(prefix.split(".")) == 5:
                    key = prefix.split(".")[4]
                    if event in ("string", "number", "boolean", "null") and key != "options":
                        current_question[key] = value

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

                # 4. Options Tracking
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

                        if key == "plot_prompt" and value:
                            yield {
                                "type": "plot_request",
                                "index": question_idx,
                                "opt_index": option_idx,
                                "is_group_level": False,
                                "prompt": value
                            }

            while control_events:
                yield control_events.pop(0)

            yield from BaseStreamParser.finalize_stream(stream, has_refused)

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"QuizStreamParser parsing failed: {e}\nTraceback:\n{error_trace}")
            yield {"type": "error", "error": f"Stream Parsing Error: {str(e)}"}