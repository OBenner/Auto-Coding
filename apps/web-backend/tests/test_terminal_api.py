"""Tests for the terminal-session management API (C5): owner-scoped list/close.

The PTY is never started — sessions are lightweight fakes, so these tests pin
the ownership/namespacing contract, not real shell behavior.
"""

from unittest.mock import MagicMock, patch

from services.terminal_manager import TerminalManager


class _FakeSession:
    # working_dir is a plain placeholder string (no FS access in these tests);
    # avoid "/tmp" so Sonar S5443 doesn't read it as world-writable dir usage.
    def __init__(self, owner, working_dir="/project", rows=24, cols=80, alive=True):
        self.owner = owner
        self.working_dir = working_dir
        self.rows = rows
        self.cols = cols
        self._alive = alive
        self.closed = False

    def is_alive(self) -> bool:
        return self._alive

    def close(self) -> None:
        self.closed = True


def _manager_with(sessions: dict) -> TerminalManager:
    mgr = TerminalManager()
    mgr.sessions = dict(sessions)
    return mgr


def test_list_sessions_for_owner_is_scoped():
    mgr = _manager_with(
        {
            "1:work": _FakeSession("1", working_dir="/a", rows=30, cols=100),
            "1:logs": _FakeSession("1"),
            "2:work": _FakeSession("2"),
        }
    )

    mine = mgr.list_sessions_for_owner("1")
    assert {s["session_id"] for s in mine} == {"work", "logs"}  # prefix stripped
    work = next(s for s in mine if s["session_id"] == "work")
    assert work == {
        "session_id": "work",
        "alive": True,
        "working_dir": "/a",
        "rows": 30,
        "cols": 100,
    }
    assert mgr.list_sessions_for_owner("3") == []


def test_close_session_for_owner_enforces_ownership():
    s_owned = _FakeSession("1")
    s_foreign = _FakeSession("2")
    mgr = _manager_with({"1:work": s_owned, "2:work": s_foreign})

    # Owner closes their own -> True, session actually closed + removed.
    assert mgr.close_session_for_owner("1", "work") is True
    assert s_owned.closed is True
    assert "1:work" not in mgr.sessions

    # Cannot close another owner's session (key is rebuilt from caller's owner).
    assert mgr.close_session_for_owner("1", "work") is False  # already gone
    assert mgr.close_session_for_owner("3", "work") is False  # never existed
    assert s_foreign.closed is False
    assert "2:work" in mgr.sessions


def _fake_api_manager(owner_to_sessions: dict):
    mgr = MagicMock()
    mgr.list_sessions_for_owner.side_effect = lambda o: owner_to_sessions.get(o, [])

    def _close(owner, session_id):
        return any(
            s["session_id"] == session_id for s in owner_to_sessions.get(owner, [])
        )

    mgr.close_session_for_owner.side_effect = _close
    return mgr


def _client_as(sub: str):
    """TestClient whose require_auth resolves to the given identity."""
    from core.security import require_auth
    from fastapi.testclient import TestClient
    from main import app

    app.dependency_overrides[require_auth] = lambda: {
        "sub": sub,
        "email": f"{sub}@test.com",
    }
    return app, TestClient(app)


def _session(session_id):
    return {
        "session_id": session_id,
        "alive": True,
        "working_dir": "/a",
        "rows": 24,
        "cols": 80,
    }


def test_terminal_api_lists_only_own_sessions():
    fake = _fake_api_manager({"1": [_session("work")], "2": [_session("other")]})
    app, client = _client_as("1")
    try:
        with patch("api.routes.terminals.terminal_manager", fake):
            resp = client.get("/api/terminals")
        assert resp.status_code == 200
        assert [s["session_id"] for s in resp.json()["sessions"]] == ["work"]
        fake.list_sessions_for_owner.assert_called_once_with("1")
    finally:
        app.dependency_overrides.clear()


def test_terminal_api_close_own_and_missing():
    fake = _fake_api_manager({"1": [_session("work")]})
    app, client = _client_as("1")
    try:
        with patch("api.routes.terminals.terminal_manager", fake):
            ok = client.delete("/api/terminals/work")
            missing = client.delete("/api/terminals/nope")
        assert ok.status_code == 204
        assert missing.status_code == 404
        fake.close_session_for_owner.assert_any_call("1", "work")
    finally:
        app.dependency_overrides.clear()


def test_terminal_api_cannot_close_foreign_session():
    # Session "work" belongs to owner "1"; caller "2" gets 404, and the close
    # is attempted with the caller's own owner id (never "1").
    fake = _fake_api_manager({"1": [_session("work")]})
    app, client = _client_as("2")
    try:
        with patch("api.routes.terminals.terminal_manager", fake):
            resp = client.delete("/api/terminals/work")
        assert resp.status_code == 404
        fake.close_session_for_owner.assert_called_once_with("2", "work")
    finally:
        app.dependency_overrides.clear()
