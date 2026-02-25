# src/config/audio_config.py
from src.config.settings import settings

"""
Configuration profiles for OpenAI Realtime Audio sessions.
Each key represents a 'mode' requested by the frontend.
"""

AUDIO_PROFILES = {
    "transcription": {
        "model": "gpt-4o-realtime-preview-2024-10-01",
        "voice": None,  # Transcribers don't speak back
        "instructions": (
            "You are a professional transcriber. "
            "Transcribe the user's speech accurately and quickly. "
            "If the audio is a fragment, do your best to punctuate it logically."
        ),
        "silence_duration_ms": 500,
        "requires_transcription_model": True
    },
    
    "language_tutor": {
        "model": settings.OPENAI_REALTIME_MODEL,         # 👈 Pulled from .env / settings
        "voice": settings.OPENAI_REALTIME_VOICE,         # 👈 Pulled from .env / settings
        "instructions": (                                # 👈 Hardcoded
            "You are a friendly, encouraging language tutor. "
            "Help the user practice speaking a foreign language. "
            "Respond conversationally, correct major mistakes gently, and keep your answers concise to encourage the user to speak more. "
            "If they ask you to speak in a specific language, seamlessly switch to that language."
        ),
        "silence_duration_ms": 800,
        "requires_transcription_model": False
    }
}