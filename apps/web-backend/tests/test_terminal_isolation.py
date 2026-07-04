"""Tests for terminal session isolation over WebSocket (C5).

The PTY itself is mocked — these tests pin the ownership/namespacing contract
of /ws/terminal: per-identity session keys, the ownership guard, and cleanup.
"""

from unittest.mock import MagicMock, patch

from core.security import create_access_token


class _FakeSession:
    """Minimal TerminalSession stand-in: never alive, so the reader exits."""

    def __init__(self, session_id: str, owner: str | None):
        self.session_id = session_id
        self.owner = owner

    def is_alive(self) -> bool:
        return False

    def write_input(self, data: str) -> None:  # pragma: no cover - not exercised
        pass

    def resize(self, rows: int, cols: int) -> None:  # pragma: no cover
        pass


def _fake_manager():
    """Mock TerminalManager whose create_session returns a matching fake."""
    manager = MagicMock()
    manager.get_session.return_value = None

    def _create(session_id, working_dir, shell=None, rows=24, cols=80, owner=None, **kw):
        return _FakeSession(session_id, owner)

    manager.create_session.side_effect = _create
    return manager


def _token(sub: str) -> str:
    return create_access_token({"sub": sub, "email": f"{sub}@test.com"})


def test_terminal_sessions_are_namespaced_per_user(test_client):
    """The same client session_id maps to distinct per-identity sessions."""
    fake = _fake_manager()
    with patch("services.terminal_manager.terminal_manager", fake):
        with test_client.websocket_connect(
            f"/ws/terminal?token={_token('1')}&session_id=work"
        ) as ws:
            assert ws.receive_json()["status"] == "connected"

        with test_client.websocket_connect(
            f"/ws/terminal?token={_token('2')}&session_id=work"
        ) as ws:
            assert ws.receive_json()["status"] == "connected"

    lookups = [c.args[0] for c in fake.get_session.call_args_list]
    assert lookups == ["1:work", "2:work"]
    created = [
        (c.kwargs["session_id"], c.kwargs["owner"])
        for c in fake.create_session.call_args_list
    ]
    assert created == [("1:work", "1"), ("2:work", "2")]
    # Cleanup uses the namespaced key too.
    closed = [c.args[0] for c in fake.close_session.call_args_list]
    assert closed == ["1:work", "2:work"]


def test_terminal_rejects_foreign_session(test_client):
    """Defense-in-depth: an existing session owned by someone else is refused."""
    fake = _fake_manager()
    fake.get_session.return_value = _FakeSession("2:work", owner="1")

    with patch("services.terminal_manager.terminal_manager", fake):
        with test_client.websocket_connect(
            f"/ws/terminal?token={_token('2')}&session_id=work"
        ) as ws:
            message = ws.receive_json()
            assert message["type"] == "error"
            assert "another user" in message["message"]

    fake.create_session.assert_not_called()


def test_terminal_reattaches_own_session(test_client):
    """The owner can re-attach to their own existing session."""
    fake = _fake_manager()
    fake.get_session.return_value = _FakeSession("1:work", owner="1")

    with patch("services.terminal_manager.terminal_manager", fake):
        with test_client.websocket_connect(
            f"/ws/terminal?token={_token('1')}&session_id=work"
        ) as ws:
            assert ws.receive_json()["status"] == "connected"

    fake.create_session.assert_not_called()
