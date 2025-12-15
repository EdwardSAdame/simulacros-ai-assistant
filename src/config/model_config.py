"""
Centralized model & generation settings for OpenAI Responses API.

Dynamic Configuration per Mode:
- OMEGA (Fast): Defaults to gpt-4o-mini, Temp 0.3
- ALPHA (Reasoning): Defaults to gpt-5-nano, Temp 0.4

You can override ANY parameter via Environment Variables:
- OPENAI_MODEL_OMEGA, OPENAI_TEMP_OMEGA, OPENAI_TOP_P_OMEGA
- OPENAI_MODEL_ALPHA, OPENAI_TEMP_ALPHA, OPENAI_TOP_P_ALPHA
"""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelConfig:
    model: str
    temperature: float
    top_p: float

# Default fail-safes (used only if Env Vars are missing)
DEFAULTS = {
    "omega": {
        "model": "gpt-4o-mini",
        "temp": 0.3,
        "top_p": 1.0
    },
    "alpha": {
        "model": "gpt-5-nano",
        "temp": 0.4,
        "top_p": 1.0
    }
}

def get_model_config(mode: str = "omega") -> ModelConfig:
    """
    Returns ModelConfig based on the selected mode, reading from specific Environment Variables.
    """
    # 1. Normalize mode
    safe_mode = mode.lower().strip() if mode else "omega"
    if safe_mode not in DEFAULTS:
        safe_mode = "omega"
    
    defaults = DEFAULTS[safe_mode]
    suffix = safe_mode.upper() # e.g., "OMEGA" or "ALPHA"

    # 2. Resolve Model Name
    # Look for OPENAI_MODEL_OMEGA, else default
    model_name = os.getenv(f"OPENAI_MODEL_{suffix}", defaults["model"])

    # 3. Resolve Temperature
    # Look for OPENAI_TEMP_OMEGA, else default
    try:
        env_temp = os.getenv(f"OPENAI_TEMP_{suffix}")
        temperature = float(env_temp) if env_temp is not None else defaults["temp"]
    except ValueError:
        temperature = defaults["temp"]

    # 4. Resolve Top P
    # Look for OPENAI_TOP_P_OMEGA, else fallback to global OPENAI_TOP_P, else default
    try:
        env_top_p = os.getenv(f"OPENAI_TOP_P_{suffix}")
        if env_top_p is None:
            # Fallback to global setting if specific one isn't set
            env_top_p = os.getenv("OPENAI_TOP_P")
        
        top_p = float(env_top_p) if env_top_p is not None else defaults["top_p"]
    except ValueError:
        top_p = defaults["top_p"]

    # Clamp values to valid OpenAI ranges
    temperature = max(0.0, min(2.0, temperature))
    top_p = max(0.0, min(1.0, top_p))

    return ModelConfig(
        model=model_name, 
        temperature=temperature, 
        top_p=top_p
    )