from flask import current_app
from openai import OpenAI
import json

SUMMARY_PROMPT = """You are a note-taking assistant.
Given a transcript, produce:
1) A concise summary (3-6 bullet points)
2) Key topics (comma-separated)
3) Action items (bulleted, each starts with a verb)
Return strict JSON with keys: summary, topics, action_items.
Transcript:
\"\"\"{t}\"\"\""""


def _client() -> OpenAI:
    key = current_app.config["OPENAI_API_KEY"]
    base = current_app.config.get("OPENAI_BASE_URL")
    return OpenAI(api_key=key, base_url=base) if base else OpenAI(api_key=key)


def summarize_and_keywords(transcript: str) -> dict:
    model = current_app.config["OPENAI_TEXT_MODEL"]
    client = _client()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": SUMMARY_PROMPT.format(t=transcript)}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    return {
        "summary": data.get("summary", ""),
        "keywords": [k.strip() for k in data.get("topics", "").split(",") if k.strip()],
        "action_items": data.get("action_items", []),
    }
