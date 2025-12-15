# src/assistant/assistant_client.py
from typing import List, Dict, Any

from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.config.page_vectorstores import get_stores_for_page
from src.utils.time_utils import get_current_time_info, infer_target_semester, semester_season


def _build_runtime_signals(user_id: str | None, page: str | None, name: str | None, email: str | None) -> str:
    """
    Build the runtime 'RUNTIME SIGNALS' block appended to the base system prompt.
    Also reiterates attribution rules for file_search sources.
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
    mode: str = "omega",  # 🔹 NEW: Accept the AI mode (default: omega)
) -> str:
    """
    Sends a structured conversation to the OpenAI Responses API and
    returns the assistant's reply text.
    """
    client = get_openai_client()
    
    # 🔹 Fetch the specific configuration for the requested mode
    # This resolves the model name (e.g., gpt-5-nano) and temperature from env vars.
    cfg = get_model_config(mode)

    # 1) Build system instructions
    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    
    # 2) Construct the full API input, starting with the system prompt
    api_input = [
        {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    ]
    # Add the structured conversation history (user and assistant turns)
    api_input.extend(conversation_input)

    # 3) Resolve vector stores for this page
    vector_store_ids = get_stores_for_page(page)

    # 4) Call Responses API using the selected configuration (model, temp, top_p)
    resp = client.responses.create(
        model=cfg.model,
        temperature=cfg.temperature,
        top_p=cfg.top_p,
        input=api_input,
        tools=[{
            "type": "file_search",
            "vector_store_ids": vector_store_ids,
            "max_num_results": get_vector_search_max_results(),
        }],
    )

    # 5) Extract text safely
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