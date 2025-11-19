"""STT via OpenAI Audio API (bytes -> transcript).

Provides `transcribe(audio_bytes)` which returns either a string
transcription or a dict like `{"text": str, "confidence": float}`.
The implementation imports `openai` lazily and attempts a few common
client call shapes so it works across client versions.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Any, Dict, Optional

try:
    import openai
except Exception:  # pragma: no cover - openai may not be installed in tests
    # pylint: disable=broad-exception-caught,invalid-name
    openai = None

logger = logging.getLogger(__name__)


DEFAULT_STT_MODEL = os.getenv("OPENAI_STT_MODEL", "gpt-4o-transcribe")


def _ensure_api_key() -> None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logger.debug("OPENAI_API_KEY not set; OpenAI calls will likely fail")
    if openai and key:
        try:
            openai.api_key = key  # type: ignore
        except Exception:  # pylint: disable=broad-exception-caught
            # newer client variants may use the environment or different config
            pass


def _extract_text_from_resp(resp: Any) -> Optional[str]:  # pylint: disable=too-many-return-statements
    """Pull the transcription text from a variety of response shapes."""
    try:
        if resp is None:
            return None
        if isinstance(resp, dict):
            # common shapes: {'text': '...'} or {'transcript': '...'}
            return resp.get("text") or resp.get("transcript")

        # object-like: try attributes
        for attr in ("text", "transcript", "data"):
            if hasattr(resp, attr):
                val = getattr(resp, attr)
                # if .data is list-like with text
                if (
                    attr == "data"
                    and isinstance(val, (list, tuple))
                    and len(val)
                    and isinstance(val[0], dict)
                ):
                    return val[0].get("text") or val[0].get("transcript")
                if isinstance(val, str):
                    return val

        # choice-based (older style): resp.choices[0].text
        choices = getattr(resp, "choices", None)
        if choices and len(choices):
            first = choices[0]
            if isinstance(first, dict):
                return first.get("text") or (first.get("message") or {}).get("content")
            if hasattr(first, "text"):
                return getattr(first, "text")
            if hasattr(first, "message") and isinstance(first.message, dict):
                return first.message.get("content")

        # fallback to string
        return str(resp)
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def transcribe(
    audio_bytes: bytes, *, model: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Transcribe audio bytes to text using OpenAI's audio endpoints.

    Returns a dict with at least the `text` key on success, or `None` on failure.
    """
    _ensure_api_key()

    if openai is None:
        logger.warning("openai package not available; cannot transcribe audio")
        return None

    model = model or DEFAULT_STT_MODEL

    bio = io.BytesIO(audio_bytes)
    # some clients require a filename attribute on the file-like object
    bio.name = getattr(bio, "name", "audio.wav")

    try:
        # Preferred modern shape: openai.Audio.transcribe
        # pylint: disable=no-member
        if hasattr(openai, "Audio") and hasattr(openai.Audio, "transcribe"):
            resp = openai.Audio.transcribe(model=model, file=bio)  # type: ignore
            text = _extract_text_from_resp(resp)
            return {"text": text} if text is not None else None

        # Some clients expose Speech.transcribe
        if hasattr(openai, "Speech") and hasattr(openai.Speech, "transcribe"):
            resp = openai.Speech.transcribe(model=model, file=bio)  # type: ignore
            text = _extract_text_from_resp(resp)
            return {"text": text} if text is not None else None

        # Older / alternate interface: openai.transcribe or top-level helper
        if hasattr(openai, "transcribe"):
            resp = openai.transcribe(model=model, file=bio)  # type: ignore
            text = _extract_text_from_resp(resp)
            return {"text": text} if text is not None else None

        logger.warning("No supported transcribe method found on openai client")
        return None

    except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
        logger.exception("OpenAI STT call failed: %s", exc)
        return None


__all__ = ["transcribe"]
