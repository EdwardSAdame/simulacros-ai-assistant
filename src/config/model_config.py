"""
Centralized model & generation settings for OpenAI Responses API.

Env (optional):
- OPENAI_TEXT_MODEL (default: gpt-4o-mini)
- OPENAI_TEMPERATURE (default: 0.3)
- OPENAI_TOP_P (default: 1.0)
"""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelConfig:
    model: str
    temperature: float
    top_p: float

def get_model_config() -> ModelConfig:
    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    try:
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    except ValueError:
        temperature = 0.3
    try:
        top_p = float(os.getenv("OPENAI_TOP_P", "1.0"))
    except ValueError:
        top_p = 1.0

    temperature = max(0.0, min(2.0, temperature))
    top_p = max(0.0, min(1.0, top_p))
    return ModelConfig(model=model, temperature=temperature, top_p=top_p)
