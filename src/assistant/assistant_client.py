# src/assistant/assistant_client.py
from typing import List, Dict, Any, Type
import logging
from pydantic import BaseModel

from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.config.page_vectorstores import get_stores_for_page
from src.utils.time_utils import get_current_time_info, infer_target_semester, semester_season

# 🟢 Import the Schema
from src.schemas.quiz_schemas import QuizResponse

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
# 🟢 OLD FUNCTION (Kept for Chat Mode)
# ------------------------------------------------------------------
def send_message_to_assistant(
    conversation_input: List[Dict[str, Any]],
    user_id: str | None = None,
    page: str | None = None,
    name: str | None = None,
    email: str | None = None,
    mode: str = "omega"
) -> str:
    """
    Standard text-based chat response.
    """
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
# 🟢 NEW FUNCTION (Structured Outputs for Quizzes)
# ------------------------------------------------------------------
def generate_structured_quiz(
    conversation_input: List[Dict[str, Any]],
    user_id: str | None = None,
    page: str | None = None,
    name: str | None = None,
    email: str | None = None,
    mode: str = "omega"
) -> QuizResponse:
    """
    Generates a Quiz strictly adhering to the QuizResponse schema.
    Uses 'client.responses.parse' for strict validation.
    """
    client = get_openai_client()
    cfg = get_model_config(mode)

    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    
    api_input = [
        {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    ]
    api_input.extend(conversation_input)

    # Note: We disable Tools/FileSearch for Structured Outputs usually to reduce complexity,
    # unless you explicitly need RAG for the quiz generation. For now, let's keep it simple.
    
    request_kwargs = {
        "model": cfg.model,
        "input": api_input,
        "temperature": cfg.temperature,
        "top_p": cfg.top_p,
        "text_format": QuizResponse # 🟢 PASSING THE PYDANTIC MODEL
    }

    # Handle Reasoning Models
    if cfg.model.startswith("o1") or "o4" in cfg.model:
         request_kwargs.pop("temperature", None)
         request_kwargs.pop("top_p", None)

    try:
        final_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        
        # 🟢 Using the .parse() method as per your documentation
        resp = client.responses.parse(**final_kwargs)
        
        # The result is automatically parsed into your Pydantic model
        return resp.output_parsed

    except Exception as e:
        logger.error(f"Structured Quiz Generation Failed. Model: {cfg.model}. Error: {e}")
        raise e