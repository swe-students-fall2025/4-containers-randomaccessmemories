"""Tests for main application module."""

import os
import sys
import types


def _prep_path():
    """Prepare Python path for imports."""
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def test_find_poller_callable_prefers_app_module(monkeypatch):
    """Test that _find_poller_callable prefers app.poller module."""
    _prep_path()

    # Create a fake app.poller module with process_pending
    fake_poller = types.ModuleType("app.poller")

    def fake_process():
        """Fake process function."""
        return "ok"

    fake_poller.process_pending = fake_process

    # Ensure package-level app exists and points to our poller
    fake_app = types.ModuleType("app")
    fake_app.poller = fake_poller

    monkeypatch.setitem(sys.modules, "app", fake_app)
    monkeypatch.setitem(sys.modules, "app.poller", fake_poller)

    # import the main module and call the discovery helper
    from app import main  # pylint: disable=import-outside-toplevel

    # pylint: disable=protected-access
    func = main._find_poller_callable()
    assert callable(func)
    assert func is fake_process


def test_loop_returns_2_when_no_poller(monkeypatch):
    """Test that loop returns exit code 2 when no poller is found."""
    _prep_path()
    from app import main  # pylint: disable=import-outside-toplevel

    # prevent test from changing signal handlers
    monkeypatch.setattr(
        main,
        "signal",
        types.SimpleNamespace(signal=lambda *a, **k: None, SIGINT=None, SIGTERM=None),
    )

    monkeypatch.setattr(main, "_find_poller_callable", lambda: None)
    rc = main.loop(run_once=True)
    assert rc == 2


def test_loop_run_once_invokes_poller_once(monkeypatch):
    """Test that loop with run_once=True invokes poller exactly once."""
    _prep_path()
    from app import main  # pylint: disable=import-outside-toplevel

    calls = {"count": 0}

    def fake_poller():
        """Fake poller function."""
        calls["count"] += 1

    monkeypatch.setattr(
        main,
        "signal",
        types.SimpleNamespace(signal=lambda *a, **k: None, SIGINT=None, SIGTERM=None),
    )
    monkeypatch.setattr(main, "_find_poller_callable", lambda: fake_poller)

    rc = main.loop(run_once=True)
    assert rc == 0
    assert calls["count"] == 1


def test_loop_handles_poller_exception_gracefully(monkeypatch):
    """Test that loop handles poller exceptions gracefully."""
    _prep_path()
    from app import main  # pylint: disable=import-outside-toplevel

    def bad_poller():
        """Poller that raises an exception."""
        raise RuntimeError("boom")

    monkeypatch.setattr(
        main,
        "signal",
        types.SimpleNamespace(signal=lambda *a, **k: None, SIGINT=None, SIGTERM=None),
    )
    monkeypatch.setattr(main, "_find_poller_callable", lambda: bad_poller)

    # Should not raise
    rc = main.loop(run_once=True)
    assert rc == 0
