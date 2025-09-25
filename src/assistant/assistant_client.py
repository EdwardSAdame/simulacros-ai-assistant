# src/assistant/assistant_client.py

from typing import List, Dict, Any

from src.config.settings import get_openai_client
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.utils.time_utils import get_current_time_info


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


def _build_runtime_signals(user_id: str | None, page: str | None, name: str | None, email: str | None) -> str:
    """
    Build the runtime 'RUNTIME SIGNALS' block that gets appended to the base system prompt.
    """
    tinfo = get_current_time_info()
    signals = [
        f"Today is {tinfo['full_human']}.",
        f"The user is on the page: {page or '/'} — respond strictly according to the context of that page.",
        ("They are browsing as a guest." if not user_id or user_id == "anonymous"
         else f"Their user ID is {user_id}."),
    ]
    if name:
        signals.append(f"Display name: {name}.")
    if email:
        signals.append(f"Email: {email}.")
    return build_system_instructions(extras=signals)


def send_message_to_assistant(
    content_parts,
    thread_id,          # kept for interface compatibility; not used with Responses API
    user_id=None,
    page=None,
    name=None,
    email=None
):
    """
    Sends structured content (text + images) via OpenAI Responses API and
    returns the assistant's reply text. No assistant_id / runs / threads.
    """
    client = get_openai_client()
    cfg = get_model_config()

    # 1) System + user content
    system_text = _build_runtime_signals(user_id=user_id, page=page, name=name, email=email)
    user_content = _to_responses_content(content_parts)

    # 2) Call Responses API
    resp = client.responses.create(
        model=cfg.model,
        temperature=cfg.temperature,
        top_p=cfg.top_p,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": system_text}]},
            {"role": "user",   "content": user_content},
        ],
    )

    # 3) Extract text safely
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
