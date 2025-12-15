# src/assistant/assistant_client.py
from typing import List, Dict, Any

from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.config.page_vectorstores import get_stores_for_page
from src.utils.time_utils import get_current_time_info, infer_target_semester, semester_season


def _build_runtime_signals(user_id: str | None, page: str | None, name: str | None, email: str | None) -> str:
    # ... (function content remains unchanged)
    tinfo = get_current_time_info()
    target = infer_target_semester()
    season = semester_season(target)

    signals = [
        f"Today is {tinfo['full_human']}.",
        f"The user is on the page: {page or '/'}",
        ("They are browsing as a guest." if not user_id or user_id == "anonymous"
         else f"Their user ID is {user_id}."),
        f"Target semester inferred: {target} (season {season}).",
        # Attribution rule to avoid “user uploaded these files” confusion
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
    mode: str = "omega",
) -> str:
    """
    Sends a structured conversation to the OpenAI Responses API and
    returns the assistant's reply text.
    """
    client = get_openai_client()
    
    cfg = get_model_config(mode)
    
    # 🔹 Check if the model is a reasoning model
    model_name_lower = cfg.model.lower()
    is_reasoning_model = (
        model_name_lower.startswith("o") or 
        "nano" in model_name_lower or 
        "reasoning" in model_name_lower
    )

    # 1) Build system instructions
    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    
    # 2) Construct the full API input
    api_input = [
        {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    ]
    api_input.extend(conversation_input)

    # 3) Resolve vector stores
    vector_store_ids = get_stores_for_page(page)
    
    # 4) Construct the base parameters for the Responses API call (UNIVERSAL PARAMS ONLY)
    request_kwargs = {
        "model": cfg.model,
        "input": api_input,
        "tools": [{
            "type": "file_search",
            "vector_store_ids": vector_store_ids,
            "max_num_results": get_vector_search_max_results(),
        }],
        # 💡 FIX: Use the universal Responses API token limit parameter for ALL models
        "max_output_tokens": 4096, 
    }
    
    # 🔹 CONDITIONAL PARAMETER SWITCH 
    if is_reasoning_model:
        # Alpha Mode (o1) logic: Add the reasoning control parameter
        request_kwargs["reasoning"] = {"effort": "medium"} 
        # OMIT temperature and top_p entirely for o1.
    else:
        # Omega Mode (gpt-4o-mini) logic: Add standard sampling parameters
        request_kwargs["temperature"] = cfg.temperature
        request_kwargs["top_p"] = cfg.top_p

    # 5) Call Responses API using the selected configuration
    resp = client.responses.create(**request_kwargs)

    # 6) Extract text safely
    text = getattr(resp, "output_text", None)
    if not text:
        try:
            chunks = []
            # Fallback parsing logic
            for block in getattr(resp, "output", []) or []:
                for c in block.get("content", []) or []:
                    if c.get("type") in ("output_text", "text"):
                        chunks.append(c.get("text", ""))
            text = "\n".join([s for s in chunks if s]).strip()
        except Exception:
            text = ""

    return text or "[No assistant response found]"