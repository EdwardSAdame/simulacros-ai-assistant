# src/config/model_config.py
import os
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ModelConfig:
    model: str
    temperature: float
    top_p: float      # <--- 🟢 REQUIRED for assistant_client.py
    max_tokens: int

def get_model_config(mode: str = "omega") -> ModelConfig:
    """
    Returns the configuration for the requested mode (Alpha vs Omega).
    Values are fetched dynamically from Environment Variables.
    """
    mode_key = mode.lower() if mode else "omega"
    
    # 1. Define specific keys for this mode
    if mode_key == "alpha":
        env_model   = "OPENAI_MODEL_ALPHA"
        env_tokens  = "OPENAI_MAX_TOKENS_ALPHA"
        env_temp    = "OPENAI_TEMP_ALPHA"
        env_top_p   = "OPENAI_TOP_P_ALPHA"     # <--- 🟢 Dynamic Key
        
        # Fallbacks (Generic)
        fallback_model   = "gpt-4o"
        fallback_tokens  = 4000
        fallback_temp    = 0.4
        fallback_top_p   = 1.0
    else:
        # Default to Omega for any unknown mode
        env_model   = "OPENAI_MODEL_OMEGA"
        env_tokens  = "OPENAI_MAX_TOKENS_OMEGA"
        env_temp    = "OPENAI_TEMP_OMEGA"
        env_top_p   = "OPENAI_TOP_P_OMEGA"     # <--- 🟢 Dynamic Key

        # Fallbacks (Generic)
        fallback_model   = "gpt-4o-mini"
        fallback_tokens  = 10000
        fallback_temp    = 0.3
        fallback_top_p   = 1.0

    # 2. Load values dynamically
    model = os.getenv(env_model, fallback_model)

    try:
        max_tokens = int(os.getenv(env_tokens, str(fallback_tokens)))
    except ValueError:
        logger.warning(f"Invalid integer for {env_tokens}. Using fallback: {fallback_tokens}")
        max_tokens = fallback_tokens

    try:
        temperature = float(os.getenv(env_temp, str(fallback_temp)))
    except ValueError:
        logger.warning(f"Invalid float for {env_temp}. Using fallback: {fallback_temp}")
        temperature = fallback_temp

    try:
        top_p = float(os.getenv(env_top_p, str(fallback_top_p))) 
    except ValueError:
        logger.warning(f"Invalid float for {env_top_p}. Using fallback: {fallback_top_p}")
        top_p = fallback_top_p

    return ModelConfig(
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )