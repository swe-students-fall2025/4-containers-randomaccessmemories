"""Summarize a transcript and extract keywords via OpenAI Chat Completions.

Provides a single entrypoint `generate_structured_note(transcript)` which
returns a dictionary with at least the keys:
 - `summary` (str)
 - `highlights` (list[str])
 - `keywords` (list[str])
 - `action_items` (list[dict])

The function attempts to return a parsed JSON object from the model's
response. If parsing fails or the OpenAI client is unavailable, it
returns `None` so callers (like the poller) can handle provider failures.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional

try:
    import openai
except Exception:  # pragma: no cover  # pylint: disable=broad-exception-caught
    # pylint: disable=invalid-name
    openai = None

logger = logging.getLogger(__name__)


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1024"))


def _ensure_api_key() -> None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logger.debug("OPENAI_API_KEY not set; OpenAI calls will likely fail")
    if openai and key:
        # the old openai package uses `openai.api_key`
        try:
            openai.api_key = key  # type: ignore
        except Exception:  # pylint: disable=broad-exception-caught
            # newer/openai client variants may use a different config
            pass


def _extract_json(text: str) -> Optional[str]:
    """Attempt to extract a JSON object from `text`.

    Returns the JSON substring if found, otherwise None.
    """
    # First, try to find a top-level JSON object
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        return m.group(0)

    # Try to find the first {...} pair anywhere in text
    m = re.search(r"(\{[\s\S]*?\})", text)
    if m:
        return m.group(1)

    return None


def generate_structured_note(
    transcript: str, *, model: Optional[str] = None, max_tokens: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Generate a structured note (summary, highlights, keywords, actions).

    - `transcript`: the raw text to summarize
    - `model`: optional model override (env `OPENAI_MODEL` used if omitted)
    - `max_tokens`: optional max tokens for the reply

    Returns a dict on success or `None` on failure.
    """
    _ensure_api_key()

    if openai is None:
        logger.warning("openai package not available; cannot generate structured note")
        return None

    model = model or DEFAULT_MODEL
    max_tokens = max_tokens or DEFAULT_MAX_TOKENS

    system_msg = (
        "You are a helpful assistant that converts meeting transcripts "
        "into a compact, machine-readable JSON structured note. "
        "Respond with only valid JSON containing the keys: "
        "summary, highlights, keywords, action_items. "
        "- summary: 1-3 sentence summary string. "
        "- highlights: array of important bullet points (strings). "
        "- keywords: array of short keyword strings. "
        "- action_items: array of objects with fields {assignee, action, due} "
        "(use null when unknown)."
    )

    user_msg = (
        "Transcript:\n" + transcript + "\n\n"
        "Return ONLY valid JSON. Example shape:\n"
        '{\n  "summary": "...",\n  "highlights": ["..."],\n  '
        '"keywords": ["..."],\n  "action_items": [{"assignee": null, '
        '"action": "...", "due": null}]\n}\n'
    )

    try:
        # Try new OpenAI client (v1.0.0+) first
        if hasattr(openai, "OpenAI"):
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.0,
                max_tokens=max_tokens,
                n=1,
            )
            # Extract text from new API response
            raw_text = resp.choices[0].message.content if resp.choices else None
            if not raw_text:
                logger.warning("No content in ChatCompletion response")
                return None

            json_str = _extract_json(raw_text)
            if not json_str:
                logger.warning("No JSON found in response: %s", raw_text[:200])
                return None

            parsed = json.loads(json_str)
            return parsed

        # Fallback to old API
        # pylint: disable=no-member
        resp = openai.ChatCompletion.create(  # type: ignore
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=max_tokens,
            n=1,
        )

        # Response shape differs between client versions; handle common shapes.
        content = None
        if hasattr(resp, "choices"):
            choice = resp.choices[0]
            # Some clients provide .message['content']
            if hasattr(choice, "message") and isinstance(choice.message, dict):
                content = choice.message.get("content")
            else:
                # Fallback: .text or .get
                content = (
                    getattr(choice, "text", None) or choice.get("text")
                    if isinstance(choice, dict)
                    else None
                )

        if content is None:
            # Try mapping as dict-like
            try:
                content = resp["choices"][0]["message"]["content"]
            except Exception:  # pylint: disable=broad-exception-caught
                content = str(resp)

        # Try direct JSON parse
        try:
            obj = json.loads(content)
            return obj
        except Exception:  # pylint: disable=broad-exception-caught
            # Attempt to extract JSON substring and parse
            jtxt = _extract_json(content or "")
            if jtxt:
                try:
                    return json.loads(jtxt)
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.exception("Failed to parse extracted JSON from model output")

        logger.exception(
            "Model did not return parseable JSON; returning raw text summary"
        )
        # As a graceful fallback, return the content under `summary` key
        return {
            "summary": (content or "").strip(),
            "highlights": [],
            "keywords": [],
            "action_items": [],
        }

    except (
        Exception
    ) as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
        logger.exception("OpenAI ChatCompletion call failed: %s", exc)
        return None


__all__ = ["generate_structured_note"]
