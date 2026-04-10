# src/config/model_config.py
import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ModelConfig:
    # 🟢 1. ACTIVE MODE (Alpha or Omega)
    model: str
    temperature: Optional[float]
    top_p: Optional[float]
    reasoning_effort: Optional[str]

    # 🟢 2. ROUTER MODE (Classification)
    router_model: str
    router_temperature: Optional[float]
    router_top_p: Optional[float]
    router_reasoning_effort: Optional[str]
    
    # 🟢 3. IMAGE GENERATION MODE
    image_model: str
    image_quality: str 
    
    # 🟢 4. AUDIO TRANSCRIPTION MODE
    audio_transcription_model: str 

    # 🟢 5. REALTIME AUDIO MODE (Speech-to-Speech)
    realtime_model: str
    realtime_voice: str

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
    Loads params for Active Mode (Alpha/Omega), Router, Image Generation, and Audio.
    """
    mode_key = mode.lower() if mode else "omega"
    
    # --- LOAD ALPHA/OMEGA (Active Mode) ---
    if mode_key == "alpha":
        suffix = "ALPHA"
        fallback_model = "gpt-4o"
        fallback_temp = 0.4
        # Premium Image Settings
        fallback_image_model = "gpt-image-1.5"
        fallback_image_quality = "high"
        # Premium Audio Settings
        fallback_audio_model = "gpt-4o-transcribe" 
        # 🟢 Premium Realtime Settings (Speech-to-Speech)
        fallback_realtime_model = "gpt-4o-realtime-preview-2024-12-17"
        fallback_realtime_voice = "alloy"
    else:
        # Defaults to 'omega'
        suffix = "OMEGA"
        fallback_model = "gpt-4o-mini"
        fallback_temp = 0.3
        # Standard Image Settings
        fallback_image_model = "gpt-image-1-mini"
        fallback_image_quality = "medium"
        # Standard Audio Settings
        fallback_audio_model = "gpt-4o-mini-transcribe"
        # 🟢 Standard Realtime Settings (Speech-to-Speech)
        fallback_realtime_model = "gpt-4o-mini-realtime-preview-2024-12-17"
        fallback_realtime_voice = "sage"

    model = os.getenv(f"OPENAI_MODEL_{suffix}", fallback_model)
    temperature = _parse_float_or_none(os.getenv(f"OPENAI_TEMP_{suffix}"), fallback_temp)
    top_p = _parse_float_or_none(os.getenv(f"OPENAI_TOP_P_{suffix}"), 1.0)
    reasoning_effort = _parse_effort(os.getenv(f"OPENAI_REASONING_EFFORT_{suffix}"))

    # --- LOAD ROUTER (Independent) ---
    router_model = os.getenv("OPENAI_MODEL_ROUTER", "gpt-4o-mini")
    router_temp = _parse_float_or_none(os.getenv("OPENAI_TEMP_ROUTER"), 0.1)
    router_top_p = _parse_float_or_none(os.getenv("OPENAI_TOP_P_ROUTER"), 1.0)
    router_effort = _parse_effort(os.getenv("OPENAI_REASONING_EFFORT_ROUTER"))
    
    # --- LOAD IMAGE CONFIG ---
    image_model = os.getenv(f"OPENAI_MODEL_IMAGE_{suffix}", fallback_image_model)
    image_quality = os.getenv(f"IMAGE_GENERATION_QUALITY_{suffix}", fallback_image_quality)

    # --- LOAD AUDIO TRANSCRIPTION CONFIG ---
    audio_transcription_model = os.getenv(f"OPENAI_REALTIME_TRANSCRIPTION_MODEL_{suffix}", fallback_audio_model)

    # 🟢 --- LOAD REALTIME AUDIO CONFIG (Speech-to-Speech) ---
    realtime_model = os.getenv(f"OPENAI_REALTIME_MODEL_{suffix}", fallback_realtime_model)
    realtime_voice = os.getenv(f"OPENAI_REALTIME_VOICE_{suffix}", fallback_realtime_voice)

    return ModelConfig(
        model=model,
        temperature=temperature,
        top_p=top_p,
        reasoning_effort=reasoning_effort,

        router_model=router_model,
        router_temperature=router_temp,
        router_top_p=router_top_p,
        router_reasoning_effort=router_effort,
        
        image_model=image_model,
        image_quality=image_quality,
        
        audio_transcription_model=audio_transcription_model,
        realtime_model=realtime_model,
        realtime_voice=realtime_voice
    )