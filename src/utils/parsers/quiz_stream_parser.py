import io
import logging
import traceback
import ijson
from typing import Generator, Dict, Any

from src.schemas.quiz_schemas import QuizQuestion
from .base_stream_parser import BaseStreamParser

logger = logging.getLogger(__name__)


class BytesGeneratorStream(io.RawIOBase):
    """
    Adapts a generator yielding bytes into a file-like stream object
    with a .read() method compatible with ijson.
    """

    def __init__(self, generator):
        self.generator = generator
        self.buffer = b""

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            data = self.buffer + b"".join(self.generator)
            self.buffer = b""
            return data

        while len(self.buffer) < size:
            try:
                self.buffer += next(self.generator)
            except StopIteration:
                break

        data = self.buffer[:size]
        self.buffer = self.buffer[size:]
        return data


class QuizStreamParser:
    """
    Consumes the OpenAI stream and yields structured events specifically for Quizzes.
    Utilizes ijson for robust, incremental JSON parsing to stream questions in real-time.
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
            # Wrap generator in a file-like stream interface for ijson
            stream_adapter = BytesGeneratorStream(_byte_generator())
            parser = ijson.parse(stream_adapter)

            eval_metadata = {}
            current_group = {}
            current_question = {}
            current_option = {}

            group_idx = -1
            question_idx = -1
            option_idx = -1

            for prefix, event, value in parser:
                # 1. Yield control events intercepted during byte generation
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
                        option_idx = -1
                        current_question = {"options": []}
                    elif event == "end_map":
                        try:
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

                        if key == "question_text" and value:
                            yield {
                                "type": "question",
                                "index": question_idx,
                                "group_index": group_idx,
                                "data": {"question_text": value, "originalIndex": question_idx}
                            }

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