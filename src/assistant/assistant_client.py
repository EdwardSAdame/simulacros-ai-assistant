# src/assistant/assistant_client.py

from typing import List, Dict, Any, Optional, Tuple

from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.config.page_vectorstores import get_stores_for_page
from src.utils.time_utils import get_current_time_info, infer_target_semester, semester_season


def _to_responses_content(parts: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    """
    Convert legacy content parts ({"type":"text"|"image_url"}) to Responses API format
    ({"type":"input_text"|"input_image"}). Already-correct items pass through.
    """
    converted: List[Dict[str, Any]] = []
    for p in parts or []:
        t = p.get("type")

        # Pass-through if already in Responses shape
        if t in ("input_text", "input_image"):
            converted.append(p)
            continue

        # Legacy text
        if t == "text" and "text" in p:
            converted.append({"type": "input_text", "text": p["text"]})
            continue

        # Legacy image_url
        if t == "image_url":
            url = None
            if isinstance(p.get("image_url"), dict):
                url = p["image_url"].get("url")
            elif isinstance(p.get("image_url"), str):
                url = p["image_url"]
            if url:
                converted.append({"type": "input_image", "image_url": url})
            continue

        # Fallback: stringify anything unknown
        converted.append({"type": "input_text", "text": str(p)})
    return converted


def _normalize_page(page: Optional[str]) -> str:
    """
    Normalize page for consistent routing and context:
    - keep only path (strip domain)
    - ensure leading '/'
    - remove trailing '/' (except root)
    - lowercase
    """
    if not page:
        return "/"
    p = page.strip()
    if "://" in p:
        try:
            p = p.split("://", 1)[1]
            p = p[p.find("/"):] if "/" in p else "/"
        except Exception:
            p = "/"
    if not p.startswith("/"):
        p = "/" + p
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p.lower()


def _derive_context_from_page(page: str) -> Optional[Tuple[str, str]]:
    """
    From a normalized page like '/simulacro-icfes/ingles' return ('ICFES', 'Inglés').
    Returns None if it cannot be derived.
    """
    parts = [s for s in page.split("/") if s]
    if len(parts) >= 2 and parts[0] == "simulacro-icfes":
        exam = "ICFES"
        comp = parts[1]
    elif len(parts) >= 2 and parts[0] == "simulacro-unal":
        exam = "UNAL"
        comp = parts[1]
    else:
        return None

    # Humanize component label
    comp_label = comp.replace("-", " ").title()
    return (exam, comp_label)


def _build_runtime_signals(user_id: str | None, page: str | None, name: str | None, email: str | None) -> str:
    """
    Build the runtime 'RUNTIME SIGNALS' block appended to the base system prompt.
    Also reiterates attribution rules for file_search sources.
    """
    norm_page = _normalize_page(page)
    tinfo = get_current_time_info()
    target = infer_target_semester()
    season = semester_season(target)

    header = []
    derived = _derive_context_from_page(norm_page)
    if derived:
        exam, comp = derived
        header.append(f"Contexto: {exam} · {comp}")

    signals = [
        *(header or []),
        f"Today is {tinfo['full_human']}.",
        f"The user is on the page: {norm_page}",
        ("They are browsing as a guest." if not user_id or user_id == "anonymous"
         else f"Their user ID is {user_id}."),
        f"Target semester inferred: {target} (season {season}).",
        # Attribution rules to avoid implying user uploads
        "All documents accessible via the file_search tool belong to Invicto’s curated knowledge base.",
        "They are NOT user uploads. Never imply the user provided them.",
    ]
    if name:
        signals.append(f"Display name: {name}.")
    if email:
        signals.append(f"Email: {email}.")
    return build_system_instructions(extras=signals)


def send_message_to_assistant(
    content_parts,
    user_id: str | None = None,
    page: str | None = None,
    name: str | None = None,
    email: str | None = None,
) -> str:
    """
    Sends structured content (text + images) via OpenAI Responses API and
    returns the assistant's reply text. No threads/runs used.
    """
    client = get_openai_client()
    cfg = get_model_config()

    # 1) System + user content
    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    user_content = _to_responses_content(content_parts)

    # 2) Resolve vector stores for this page (after normalization inside get_stores_for_page)
    vector_store_ids = get_stores_for_page(page)

    # 3) Call Responses API with file_search tool
    resp = client.responses.create(
        model=cfg.model,
        temperature=cfg.temperature,
        top_p=cfg.top_p,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": system_text}]},
            {"role": "user",   "content": user_content},
        ],
        tools=[{
            "type": "file_search",
            "vector_store_ids": vector_store_ids,
            "max_num_results": get_vector_search_max_results(),
        }],
    )

    # 4) Extract text safely
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
