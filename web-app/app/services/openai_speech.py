import io
from flask import current_app
from openai import OpenAI

def _client() -> OpenAI:
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
    f = io.BytesIO(audio_bytes)
    f.name = filename
    res = client.audio.transcriptions.create(model=model, file=f)
    return {"text": getattr(res, "text", ""), "language": getattr(res, "language", None)}
