"""Tests for poller module."""

import os
import sys
import types


def _prep_path_and_bson():
    """Prepare Python path and mock bson if needed."""
    # Ensure the 'machine-learning-client' directory is importable as package root
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Provide a minimal bson.ObjectId if bson isn't installed in the test env
    if "bson" not in sys.modules:
        mod = types.ModuleType("bson")
        # ObjectId constructor: return the value unchanged (tests treat IDs as opaque)
        setattr(mod, "ObjectId", lambda v=None: v)
        sys.modules["bson"] = mod


def test_process_pending_success(monkeypatch):
    """Test successful processing of pending records."""
    _prep_path_and_bson()
    import app.poller as poller  # pylint: disable=import-outside-toplevel

    # Setup a single pending record
    pending = [{"_id": "rid-1", "file_id": "fid-1"}]

    monkeypatch.setattr(poller.db, "find_pending", lambda limit=10: pending)

    calls = {"status": [], "transcriptions": [], "notes": [], "errors": []}

    def mark_status(rid, status):
        """Mock mark_record_status."""
        calls["status"].append((rid, status))

    def get_audio(fid):  # pylint: disable=unused-argument
        """Mock get_audio."""
        return b"FAKEAUDIO"

    def insert_transcription(rid, text, confidence=None):
        """Mock insert_transcription."""
        calls["transcriptions"].append((rid, text, confidence))
        return "trid-1"

    def insert_note(transcription_id, note):
        """Mock insert_structured_note."""
        calls["notes"].append((transcription_id, note))
        return "note-1"

    def set_error(rid, err):
        """Mock set_record_error."""
        calls["errors"].append((rid, err))

    monkeypatch.setattr(poller.db, "mark_record_status", mark_status)
    monkeypatch.setattr(poller.db, "get_audio", get_audio)
    monkeypatch.setattr(poller.db, "insert_transcription", insert_transcription)
    monkeypatch.setattr(poller.db, "insert_structured_note", insert_note)
    monkeypatch.setattr(poller.db, "set_record_error", set_error)

    # Replace provider wrappers to return predictable values
    monkeypatch.setattr(
        poller,
        "_safe_transcribe",
        lambda audio: {"text": "hello world", "confidence": 0.9},
    )
    monkeypatch.setattr(
        poller,
        "_safe_generate_notes",
        lambda text: {
            "summary": "s",
            "highlights": [],
            "keywords": [],
            "action_items": [],
        },
    )

    processed = poller.process_pending(limit=1)

    assert processed == 1
    # status should include processing and done
    assert any(s == "processing" for _, s in calls["status"]) and any(
        s == "done" for _, s in calls["status"]
    )
    assert calls["transcriptions"] and calls["notes"]
    assert not calls["errors"]


def test_process_pending_stt_failure_sets_error(monkeypatch):
    """Test that STT failure properly sets error status."""
    _prep_path_and_bson()
    import app.poller as poller  # pylint: disable=import-outside-toplevel

    pending = [{"_id": "rid-err", "file_id": "fid-err"}]
    monkeypatch.setattr(poller.db, "find_pending", lambda limit=10: pending)

    calls = {"status": [], "errors": []}

    def mark_status(rid, status):
        """Mock mark_record_status."""
        calls["status"].append((rid, status))

    def get_audio(fid):  # pylint: disable=unused-argument
        """Mock get_audio."""
        return b"FAKEAUDIO"

    def set_error(rid, err):
        """Mock set_record_error."""
        calls["errors"].append((rid, err))

    monkeypatch.setattr(poller.db, "mark_record_status", mark_status)
    monkeypatch.setattr(poller.db, "get_audio", get_audio)
    monkeypatch.setattr(poller.db, "set_record_error", set_error)

    # Simulate STT failure
    monkeypatch.setattr(poller, "_safe_transcribe", lambda audio: None)
    monkeypatch.setattr(poller, "_safe_generate_notes", lambda text: None)

    processed = poller.process_pending(limit=1)

    assert processed == 0
    # ensure we attempted to mark processing and then set an error
    assert any(s == "processing" for _, s in calls["status"])
    assert calls["errors"]
