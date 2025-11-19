import os
import sys
import types
import json


def _prep_path():
    # Ensure the 'machine-learning-client' directory is importable as package root
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def test_generate_structured_note_parses_json(monkeypatch):
    _prep_path()
    import app.nlp_openai as nlp

    # Create a fake openai client that returns a content string containing JSON
    fake_content = json.dumps(
        {
            "summary": "This is a short summary.",
            "highlights": ["point a", "point b"],
            "keywords": ["kw1", "kw2"],
            "action_items": [{"assignee": None, "action": "do X", "due": None}],
        }
    )

    # Build the fake response object shape used by our implementation
    fake_resp = {"choices": [{"message": {"content": fake_content}}]}

    class FakeChatCompletion:
        @staticmethod
        def create(*_, **__):
            return fake_resp

    fake_openai = types.SimpleNamespace(ChatCompletion=FakeChatCompletion)
    monkeypatch.setattr(nlp, "openai", fake_openai, raising=False)

    result = nlp.generate_structured_note("some transcript")

    assert isinstance(result, dict)
    assert result.get("summary") == "This is a short summary."
    assert isinstance(result.get("highlights"), list)
    assert isinstance(result.get("keywords"), list)


def test_generate_structured_note_fallback_on_nonjson(monkeypatch):
    _prep_path()
    import app.nlp_openai as nlp

    fake_content = "Here is a plain-text summary: nothing to parse"

    fake_resp = {"choices": [{"message": {"content": fake_content}}]}

    class FakeChatCompletion:
        @staticmethod
        def create(*_, **__):
            return fake_resp

    fake_openai = types.SimpleNamespace(ChatCompletion=FakeChatCompletion)
    monkeypatch.setattr(nlp, "openai", fake_openai, raising=False)

    result = nlp.generate_structured_note("transcript that yields plain text")

    assert isinstance(result, dict)
    assert "summary" in result
    assert result["summary"] and isinstance(result["summary"], str)


# mocks DB + STT/NLP to hit 80% coverage
