# src/config/model_config.py
import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ModelConfig:
    # 🟢 1. ALPHA MODE (Logic)
    model: str
    temperature: Optional[float]
    top_p: Optional[float]
    reasoning_effort: Optional[str]

    # 🟢 2. WEB SEARCH MODE (Deep Research)
    search_model: str
    search_temperature: Optional[float]
    search_top_p: Optional[float]
    search_reasoning_effort: Optional[str]

    # 🟢 3. ROUTER MODE (Classification)
    router_model: str
    router_temperature: Optional[float]
    router_top_p: Optional[float]
    router_reasoning_effort: Optional[str]

def _parse_float_or_none(value: str | None, default: float) -> Optional[float]:
    if value is None: return default
    if str(value).strip().lower() == "none": return None
    try: return float(value)
    except ValueError: return default

def _parse_effort(value: str | None) -> Optional[str]:
    """Validates reasoning effort values (low, medium, high)."""
    if value and value.lower() in ["low", "medium", "high"]:
        return value.lower()
    return None

def get_model_config(mode: str = "omega") -> ModelConfig:
    """
    Universal Config Loader.
    Loads ALL params for ALL modes (Alpha, Omega, Search, Router).
    """
    mode_key = mode.lower() if mode else "omega"
    
    # --- LOAD ALPHA/OMEGA (Active Mode) ---
    if mode_key == "alpha":
        suffix = "ALPHA"
        fallback_model = "gpt-4o"
        fallback_temp = 0.4
    else:
        suffix = "OMEGA"
        fallback_model = "gpt-4o-mini"
        fallback_temp = 0.3

    model = os.getenv(f"OPENAI_MODEL_{suffix}", fallback_model)
    temperature = _parse_float_or_none(os.getenv(f"OPENAI_TEMP_{suffix}"), fallback_temp)
    top_p = _parse_float_or_none(os.getenv(f"OPENAI_TOP_P_{suffix}"), 1.0)
    reasoning_effort = _parse_effort(os.getenv(f"OPENAI_REASONING_EFFORT_{suffix}"))

    # --- LOAD WEB SEARCH (Independent) ---
    search_model = os.getenv("OPENAI_MODEL_SEARCH", "o4-mini")
    search_temp = _parse_float_or_none(os.getenv("OPENAI_TEMP_SEARCH"), 0.3)
    search_top_p = _parse_float_or_none(os.getenv("OPENAI_TOP_P_SEARCH"), 1.0)
    search_effort = _parse_effort(os.getenv("OPENAI_REASONING_EFFORT_SEARCH"))

    # --- LOAD ROUTER (Independent) ---
    # Usually we want a fast, cheap model for routing, but we allow 'o' models too now.
    router_model = os.getenv("OPENAI_MODEL_ROUTER", "gpt-4o-mini")
    router_temp = _parse_float_or_none(os.getenv("OPENAI_TEMP_ROUTER"), 0.1)
    router_top_p = _parse_float_or_none(os.getenv("OPENAI_TOP_P_ROUTER"), 1.0)
    router_effort = _parse_effort(os.getenv("OPENAI_REASONING_EFFORT_ROUTER"))

    return ModelConfig(
        model=model,
        temperature=temperature,
        top_p=top_p,
        reasoning_effort=reasoning_effort,
        
        search_model=search_model,
        search_temperature=search_temp,
        search_top_p=search_top_p,
        search_reasoning_effort=search_effort,

        router_model=router_model,
        router_temperature=router_temp,
        router_top_p=router_top_p,
        router_reasoning_effort=router_effort
    )

# Legacy helper
def get_search_model_name() -> str:
    return os.getenv("OPENAI_MODEL_SEARCH", "gpt-4o")