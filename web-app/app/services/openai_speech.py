"""OpenAI speech transcription service."""

import io
from flask import current_app
from openai import OpenAI


def _client() -> OpenAI:
    """Create OpenAI client."""
    key = current_app.config["OPENAI_API_KEY"]
    base = current_app.config.get("OPENAI_BASE_URL")
    return OpenAI(api_key=key, base_url=base) if base else OpenAI(api_key=key)


def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """
    Call OpenAI Audio Transcriptions API.
    Returns {"text": "...", "language": Optional[str]}.
    """
    model = current_app.config["OPENAI_TRANSCRIBE_MODEL"]
    client = _client()
    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = filename
    res = client.audio.transcriptions.create(model=model, file=file_obj)
    return {
        "text": getattr(res, "text", ""),
        "language": getattr(res, "language", None),
    }
