import os
import sys
import types


def _prep_path():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def test_find_poller_callable_prefers_app_module(monkeypatch):
    _prep_path()
    import importlib

    # Create a fake app.poller module with process_pending
    fake_poller = types.ModuleType("app.poller")

    def fake_process():
        return "ok"

    fake_poller.process_pending = fake_process

    # Ensure package-level app exists and points to our poller
    fake_app = types.ModuleType("app")
    fake_app.poller = fake_poller

    monkeypatch.setitem(sys.modules, "app", fake_app)
    monkeypatch.setitem(sys.modules, "app.poller", fake_poller)

    # import the main module and call the discovery helper
    import app.main as main

    func = main._find_poller_callable()
    assert callable(func)
    assert func is fake_process


def test_loop_returns_2_when_no_poller(monkeypatch):
    _prep_path()
    import app.main as main

    # prevent test from changing signal handlers
    monkeypatch.setattr(main, "signal", types.SimpleNamespace(signal=lambda *a, **k: None, SIGINT=None, SIGTERM=None))

    monkeypatch.setattr(main, "_find_poller_callable", lambda: None)
    rc = main.loop(run_once=True)
    assert rc == 2


def test_loop_run_once_invokes_poller_once(monkeypatch):
    _prep_path()
    import app.main as main

    calls = {"count": 0}

    def fake_poller():
        calls["count"] += 1

    monkeypatch.setattr(main, "signal", types.SimpleNamespace(signal=lambda *a, **k: None, SIGINT=None, SIGTERM=None))
    monkeypatch.setattr(main, "_find_poller_callable", lambda: fake_poller)

    rc = main.loop(run_once=True)
    assert rc == 0
    assert calls["count"] == 1


def test_loop_handles_poller_exception_gracefully(monkeypatch):
    _prep_path()
    import app.main as main

    def bad_poller():
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "signal", types.SimpleNamespace(signal=lambda *a, **k: None, SIGINT=None, SIGTERM=None))
    monkeypatch.setattr(main, "_find_poller_callable", lambda: bad_poller)

    # Should not raise
    rc = main.loop(run_once=True)
    assert rc == 0
