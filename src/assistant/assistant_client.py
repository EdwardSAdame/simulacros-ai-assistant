# src/assistant/assistant_client.py
from typing import List, Dict, Any, Type, Generator
import logging
import json
import re
from pydantic import BaseModel, ValidationError

from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.config.page_vectorstores import get_stores_for_page
from src.utils.time_utils import get_current_time_info, infer_target_semester, semester_season

# 🟢 Import the Schema
from src.schemas.quiz_schemas import QuizResponse, QuizQuestion

logger = logging.getLogger(__name__)

def _build_runtime_signals(user_id: str | None, page: str | None, name: str | None, email: str | None) -> str:
    """
    Build the runtime 'RUNTIME SIGNALS' block appended to the base system prompt.
    """
    tinfo = get_current_time_info()
    target = infer_target_semester()
    season = semester_season(target)

    signals = [
        f"Today is {tinfo['full_human']}.",
        f"The user is on the page: {page or '/'}",
        ("They are browsing as a guest." if not user_id or user_id == "anonymous"
         else f"Their user ID is {user_id}."),
        f"Target semester inferred: {target} (season {season}).",
        "All documents accessible via the file_search tool belong to Invicto’s curated knowledge base. Never imply the user provided them.",
    ]
    if name:
        signals.append(f"Display name: {name}.")
    if email:
        signals.append(f"Email: {email}.")
    return build_system_instructions(extras=signals)

# ------------------------------------------------------------------
# 🟢 STANDARD CHAT
# ------------------------------------------------------------------
def send_message_to_assistant(
    conversation_input: List[Dict[str, Any]],
    user_id: str | None = None,
    page: str | None = None,
    name: str | None = None,
    email: str | None = None,
    mode: str = "omega"
) -> str:
    client = get_openai_client()
    cfg = get_model_config(mode)

    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    
    api_input = [
        {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    ]
    api_input.extend(conversation_input)

    vector_store_ids = get_stores_for_page(page)
    is_reasoning_model = cfg.model.startswith("o1") or "reasoning" in cfg.model or "o4" in cfg.model
    
    request_kwargs = {
        "model": cfg.model,
        "input": api_input,
        "temperature": cfg.temperature,
        "top_p": cfg.top_p,
    }

    if is_reasoning_model:
        logger.info(f"Assistant Client: Detected reasoning model '{cfg.model}'.")
        request_kwargs.pop("temperature", None)
        request_kwargs.pop("top_p", None)
        request_kwargs["tools"] = None 
    else:
        request_kwargs["tools"] = [{
            "type": "file_search",
            "vector_store_ids": vector_store_ids,
            "max_num_results": get_vector_search_max_results(),
        }]

    try:
        final_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        resp = client.responses.create(**final_kwargs)

        text = getattr(resp, "output_text", None)
        if not text:
            try:
                chunks = []
                for block in getattr(resp, "output", []) or []:
                    for c in block.get("content", []) or []:
                        if c.get("type") in ("output_text", "text"):
                            chunks.append(c.get("text", ""))
                text = "\n".join([s for s in chunks if s]).strip()
            except Exception:
                text = ""

        return text or "[No assistant response found]"

    except Exception as e:
        logger.error(f"OpenAI Chat Request Failed. Model: {cfg.model}. Error: {e}")
        raise e


# ------------------------------------------------------------------
# 🟢 BATCH STRUCTURED QUIZ
# ------------------------------------------------------------------
def generate_structured_quiz(
    conversation_input: List[Dict[str, Any]],
    user_id: str | None = None,
    page: str | None = None,
    name: str | None = None,
    email: str | None = None,
    mode: str = "omega"
) -> QuizResponse:
    client = get_openai_client()
    cfg = get_model_config(mode)

    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    
    api_input = [
        {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    ]
    api_input.extend(conversation_input)

    request_kwargs = {
        "model": cfg.model,
        "input": api_input,
        "temperature": cfg.temperature,
        "top_p": cfg.top_p,
        "text_format": QuizResponse
    }

    if cfg.model.startswith("o1") or "o4" in cfg.model:
         request_kwargs.pop("temperature", None)
         request_kwargs.pop("top_p", None)

    try:
        final_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        resp = client.responses.parse(**final_kwargs)
        return resp.output_parsed
    except Exception as e:
        logger.error(f"Structured Quiz Generation Failed. Model: {cfg.model}. Error: {e}")
        raise e

# ------------------------------------------------------------------
# 🟢 NEW: STREAMING STRUCTURED QUIZ (FIXED PARSER)
# ------------------------------------------------------------------
def stream_structured_quiz(
    conversation_input: List[Dict[str, Any]],
    user_id: str | None = None,
    page: str | None = None,
    name: str | None = None,
    email: str | None = None,
    mode: str = "omega"
) -> Generator[Dict[str, Any], None, None]:
    """
    Generates a Quiz strictly adhering to schema, but YIELDS chunks as they are ready.
    Uses a robust 'Checkpoint Parser' to avoid variable scope errors.
    """
    client = get_openai_client()
    cfg = get_model_config(mode)

    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    
    api_input = [
        {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    ]
    api_input.extend(conversation_input)

    request_kwargs = {
        "model": cfg.model,
        "input": api_input,
        "temperature": cfg.temperature,
        "top_p": cfg.top_p,
        "text_format": QuizResponse
    }

    if cfg.model.startswith("o1") or "o4" in cfg.model:
         request_kwargs.pop("temperature", None)
         request_kwargs.pop("top_p", None)

    final_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}

    # -- Internal Parser State --
    buffer = ""
    intro_yielded = False
    question_count = 0
    
    # Checkpoint: index in 'buffer' where the last successfully parsed object ended
    # We initialize it to None, and set it once we find the start of the list.
    last_checkpoint_idx = None 

    try:
        with client.responses.stream(**final_kwargs) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    chunk = event.delta
                    buffer += chunk
                    
                    # 1. Try to find/yield Intro Message
                    if not intro_yielded:
                        if '"questions"' in buffer:
                            intro_match = re.search(r'"intro_message"\s*:\s*"(.*?)"', buffer, re.DOTALL)
                            if intro_match:
                                intro_text = intro_match.group(1)
                                intro_text = intro_text.replace('\\"', '"')
                                logger.info("StreamParser: Intro message detected.")
                                yield {"type": "intro", "text": intro_text}
                                intro_yielded = True
                    
                    # 2. Track Objects in the Stream
                    questions_marker = buffer.find('"questions"')
                    if questions_marker != -1:
                        
                        # Find the first '[' after "questions"
                        array_start = buffer.find('[', questions_marker)
                        if array_start != -1:
                            
                            # Initialize checkpoint if this is the first time we see the array start
                            if last_checkpoint_idx is None:
                                last_checkpoint_idx = array_start
                            
                            # RESUME SCANNING from the last safe checkpoint.
                            # We reset temporary scan variables every time we loop, 
                            # because we are re-playing the buffer from the last known good position.
                            
                            scan_cursor = last_checkpoint_idx
                            scan_brace_depth = 0
                            scan_in_string = False
                            scan_escape = False
                            object_start_idx = -1
                            
                            while scan_cursor < len(buffer):
                                char = buffer[scan_cursor]
                                
                                if not scan_in_string:
                                    if char == '"':
                                        scan_in_string = True
                                    elif char == '{':
                                        if scan_brace_depth == 0:
                                            object_start_idx = scan_cursor
                                        scan_brace_depth += 1
                                    elif char == '}':
                                        scan_brace_depth -= 1
                                        if scan_brace_depth == 0:
                                            # We found a complete object!
                                            raw_obj_str = buffer[object_start_idx : scan_cursor + 1]
                                            try:
                                                q_data = json.loads(raw_obj_str)
                                                
                                                # FORGIVING VALIDATION
                                                try:
                                                    q_obj = QuizQuestion(**q_data)
                                                except ValidationError as ve:
                                                    logger.warning(f"StreamParser: Validation soft-fail Q{question_count}: {ve}")
                                                    # Wrap raw dict to look like Pydantic model for downstream compatibility
                                                    class DictWrapper:
                                                        def __init__(self, d): self.d = d
                                                        def dict(self): return self.d
                                                    q_obj = DictWrapper(q_data)

                                                logger.info(f"StreamParser: Yielding Question {question_count}")
                                                yield {"type": "question", "index": question_count, "data": q_obj}
                                                
                                                # UPDATE STATE
                                                question_count += 1
                                                # Move checkpoint to here, so next loop starts scanning AFTER this object
                                                last_checkpoint_idx = scan_cursor + 1 
                                                
                                            except json.JSONDecodeError:
                                                pass
                                    elif char == '\\':
                                        scan_escape = True 
                                else:
                                    # Inside string
                                    if scan_escape:
                                        scan_escape = False
                                    elif char == '\\':
                                        scan_escape = True
                                    elif char == '"':
                                        scan_in_string = False
                                
                                scan_cursor += 1

            # 3. Final Result
            final_obj = stream.get_final_response()
            logger.info("StreamParser: Stream finished. Getting final object.")
            
            # Use 'output_parsed' property if available (for newer SDKs)
            parsed_response = None
            
            if hasattr(final_obj, 'output_parsed'):
                parsed_response = final_obj.output_parsed
            elif hasattr(final_obj, 'parsed'):
                parsed_response = final_obj.parsed
            else:
                parsed_response = final_obj 

            yield {"type": "done", "full_response": parsed_response}

    except Exception as e:
        logger.error(f"Streaming Quiz Failed: {e}")
        yield {"type": "error", "error": str(e)}