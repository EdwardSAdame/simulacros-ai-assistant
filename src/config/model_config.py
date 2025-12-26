# src/config/model_config.py
import os
from dataclasses import dataclass
from typing import Optional # Added Optional
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ModelConfig:
    model: str
    temperature: Optional[float] # Now accepts None
    top_p: Optional[float]       # Now accepts None
    # max_tokens was deleted previously

def _parse_float_or_none(value: str | None, default: float) -> Optional[float]:
    """
    Helper to parse env vars.
    - If value is "None" (string) -> returns None
    - If value is set -> returns float
    - If missing/invalid -> returns default
    """
    if value is None:
        return default
    
    if str(value).strip().lower() == "none":
        return None
    
    try:
        return float(value)
    except ValueError:
        return default

def get_model_config(mode: str = "omega") -> ModelConfig:
    """
    Returns the configuration for the requested mode (Alpha vs Omega).
    Values are fetched dynamically from Environment Variables.
    """
    mode_key = mode.lower() if mode else "omega"
    
    # 1. Define specific keys for this mode
    if mode_key == "alpha":
        env_model   = "OPENAI_MODEL_ALPHA"
        env_temp    = "OPENAI_TEMP_ALPHA"
        env_top_p   = "OPENAI_TOP_P_ALPHA"
        
        # Fallbacks (Generic)
        fallback_model   = "gpt-4o"
        fallback_temp    = 0.4
        fallback_top_p   = 1.0
    else:
        # Default to Omega
        env_model   = "OPENAI_MODEL_OMEGA"
        env_temp    = "OPENAI_TEMP_OMEGA"
        env_top_p   = "OPENAI_TOP_P_OMEGA"

        # Fallbacks (Generic)
        fallback_model   = "gpt-4o-mini"
        fallback_temp    = 0.3
        fallback_top_p   = 1.0

    # 2. Load values dynamically
    model = os.getenv(env_model, fallback_model)

    # Use helper to allow "None"
    temperature = _parse_float_or_none(os.getenv(env_temp), fallback_temp)
    top_p = _parse_float_or_none(os.getenv(env_top_p), fallback_top_p)

    return ModelConfig(
        model=model,
        temperature=temperature,
        top_p=top_p
    )