# src/assistant/assistant_client.py
from typing import List, Dict, Any
import logging

from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.config.page_vectorstores import get_stores_for_page
from src.utils.time_utils import get_current_time_info, infer_target_semester, semester_season

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


def send_message_to_assistant(
    conversation_input: List[Dict[str, Any]],
    user_id: str | None = None,
    page: str | None = None,
    name: str | None = None,
    email: str | None = None,
    mode: str = "omega"
) -> str:
    """
    Sends a structured conversation to the OpenAI API.
    Handles 'Reasoning Model' (o1) constraints automatically.
    """
    client = get_openai_client()
    cfg = get_model_config(mode)

    # 1) Build system instructions
    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    
    # 2) Construct input
    # Note: 'o1' models currently process 'system' messages as 'user' messages under the hood,
    # but the API now accepts 'developer' or 'system' roles in newer versions.
    # We stick to standard 'system' for compatibility.
    api_input = [
        {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    ]
    api_input.extend(conversation_input)

    # 3) Resolve vector stores
    vector_store_ids = get_stores_for_page(page)

    # ------------------------------------------------------------------
    # 🟢 4) DYNAMIC PARAMETER SANITIZATION (The Fix)
    # ------------------------------------------------------------------
    is_reasoning_model = cfg.model.startswith("o1") or "reasoning" in cfg.model

    # Base arguments common to all models
    request_kwargs = {
        "model": cfg.model,
        "input": api_input, # Assuming your custom client uses 'input'
    }

    if is_reasoning_model:
        # ⚠️ REASONING MODEL RULES (o1-preview, o1-mini)
        logger.info(f"Assistant Client: Detected reasoning model '{cfg.model}'. Adjusting params.")
        
        # Rule A: Use max_completion_tokens, NOT max_tokens
        request_kwargs["max_completion_tokens"] = cfg.max_tokens
        
        # Rule B: Temperature and Top P are NOT supported (or fixed at 1)
        # We deliberately OMIT them to avoid 400 Errors.
        
        # Rule C: Tools (File Search) might not be supported in Beta
        # We attempt to send them, but if it fails, we catch it.
        # Currently, o1 DOES NOT support tools. We omit them to prevent crash.
        logger.warning("Assistant Client: Tools (File Search) disabled for reasoning model.")
        request_kwargs["tools"] = None 

    else:
        # ✅ STANDARD MODEL RULES (gpt-4o, gpt-3.5)
        request_kwargs["max_tokens"] = cfg.max_tokens
        request_kwargs["temperature"] = cfg.temperature
        request_kwargs["top_p"] = cfg.top_p
        
        # Include Tools
        request_kwargs["tools"] = [{
            "type": "file_search",
            "vector_store_ids": vector_store_ids,
            "max_num_results": get_vector_search_max_results(),
        }]

    # ------------------------------------------------------------------
    # 5) Call the API with sanitized arguments
    # ------------------------------------------------------------------
    try:
        # Clean up None values (like tools if omitted)
        final_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        
        resp = client.responses.create(**final_kwargs)

        # 6) Extract text safely
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
        logger.error(f"OpenAI Request Failed. Model: {cfg.model}, Mode: {mode}. Error: {e}")
        raise e