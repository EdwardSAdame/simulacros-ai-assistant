import openai
import requests
import tempfile
import os
from src.config.settings import get_openai_client

def transcribe_audio_url(audio_url: str) -> str:
    """
    Downloads and transcribes an audio file from a URL using OpenAI Whisper.
    Returns the transcript text.
    """
    client = get_openai_client()

    try:
        response = requests.get(audio_url)
        response.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to download audio from URL: {e}")

    # Use delete=False to avoid Windows lock error
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_file.write(response.content)
        tmp_path = tmp_file.name

    try:
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript.strip()

    finally:
        os.remove(tmp_path)
