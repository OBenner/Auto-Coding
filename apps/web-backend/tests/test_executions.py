"""Tests for agent execution history (C3): model, service, wiring, and API.

Relies on the shared `test_db` fixture (in-memory SQLite with all tables created).
"""

import secrets
from unittest.mock import patch

import pytest
from api.models.agent_execution import AgentExecution
from api.models.user import User
from core.config import settings
from services.execution_log import (
    create_execution,
    get_execution,
    list_executions,
    mark_execution_finished,
    record_execution_result,
)
from services.workspace_service import create_workspace
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


def _make_user(db, email: str) -> User:
    # Random throwaway hash: these tests exercise run history, not auth.
    user = User(email=email, hashed_password=secrets.token_hex(16))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_workspace(db, email: str):
    user = _make_user(db, email)
    return user, create_workspace(db, owner_id=user.id, name="WS")


def test_execution_lifecycle(test_db):
    user, ws = _make_workspace(test_db, "exec-life@test.com")

    execution = create_execution(
        test_db, ws.id, user.id, "001-feature", "planner", "claude-sonnet-4-5"
    )
    assert execution.status == "running"
    assert execution.finished_at is None

    mark_execution_finished(test_db, execution, "completed")
    assert execution.status == "completed"
    assert execution.error is None
    assert execution.finished_at is not None

    failed = create_execution(
        test_db, ws.id, user.id, "001-feature", "coder", "claude-sonnet-4-5"
    )
    mark_execution_finished(test_db, failed, "failed", "boom")
    assert failed.status == "failed"
    assert failed.error == "boom"


def test_record_execution_result_background_path(test_db):
    """The background finisher opens its own session via the injected factory."""
    user, ws = _make_workspace(test_db, "exec-bg@test.com")
    execution = create_execution(
        test_db, ws.id, user.id, "002", "qa_reviewer", "claude-sonnet-4-5"
    )

    factory = sessionmaker(bind=test_db.get_bind())
    record_execution_result(execution.id, "failed", "agent crashed", factory)

    test_db.expire_all()
    refreshed = get_execution(test_db, execution.id)
    assert refreshed.status == "failed"
    assert refreshed.error == "agent crashed"
    assert refreshed.finished_at is not None

    # No-op paths never raise: missing id and unknown record.
    record_execution_result(None, "completed", None, factory)
    record_execution_result(999999, "completed", None, factory)


def test_list_executions_scoped_by_workspace(test_db):
    user_a, ws_a = _make_workspace(test_db, "exec-a@test.com")
    user_b, ws_b = _make_workspace(test_db, "exec-b@test.com")

    for spec in ("001", "002", "003"):
        create_execution(test_db, ws_a.id, user_a.id, spec, "coder", "m")
    create_execution(test_db, ws_b.id, user_b.id, "900", "planner", "m")

    executions, total = list_executions(test_db, ws_a.id, limit=2)
    assert total == 3
    assert len(executions) == 2
    # Newest first, and never another workspace's rows.
    assert [e.spec_id for e in executions] == ["003", "002"]
    assert all(e.workspace_id == ws_a.id for e in executions)


def test_invalid_type_and_status_rejected_by_db(test_db):
    user, ws = _make_workspace(test_db, "exec-ck@test.com")

    test_db.add(
        AgentExecution(
            workspace_id=ws.id, user_id=user.id, spec_id="001",
            agent_type="architect", model="m",
        )
    )
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()

    test_db.add(
        AgentExecution(
            workspace_id=ws.id, user_id=user.id, spec_id="001",
            agent_type="coder", model="m", status="paused",
        )
    )
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def _client_as(test_db, user):
    """TestClient with db + auth overridden to the given user (numeric sub)."""
    from core.database import get_db
    from core.security import require_auth
    from fastapi.testclient import TestClient
    from main import app

    def _override_db():
        yield test_db

    def _override_auth():
        return {"sub": str(user.id), "email": user.email}

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_auth] = _override_auth
    return app, TestClient(app)


def test_executions_api(test_db, monkeypatch):
    """History listing is workspace-scoped; single records enforce access."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    from services.workspace_service import get_or_create_personal_workspace

    user = _make_user(test_db, "exec-api@test.com")
    personal = get_or_create_personal_workspace(test_db, user.id)
    mine = create_execution(test_db, personal.id, user.id, "001", "planner", "m")

    stranger, foreign_ws = _make_workspace(test_db, "exec-api-other@test.com")
    foreign = create_execution(
        test_db, foreign_ws.id, stranger.id, "777", "coder", "m"
    )

    app, client = _client_as(test_db, user)
    try:
        resp = client.get("/api/executions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert [e["id"] for e in body["executions"]] == [mine.id]

        own = client.get(f"/api/executions/{mine.id}")
        assert own.status_code == 200
        assert own.json()["spec_id"] == "001"

        denied = client.get(f"/api/executions/{foreign.id}")
        assert denied.status_code == 403

        missing = client.get("/api/executions/999999")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_run_agent_creates_execution_record(test_db, monkeypatch):
    """POST /api/agents/run persists a running record for numeric-sub callers."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    user = _make_user(test_db, "exec-run@test.com")

    app, client = _client_as(test_db, user)
    try:
        with patch(
            "api.routes.agents.start_agent_task", return_value="001:planner"
        ) as started:
            resp = client.post(
                "/api/agents/run", json={"spec_id": "001", "agent_type": "planner"}
            )
        assert resp.status_code == 202

        rows = test_db.query(AgentExecution).all()
        assert len(rows) == 1
        assert rows[0].status == "running"
        assert rows[0].user_id == user.id
        # The record id is threaded into the background task.
        assert started.call_args.kwargs["execution_id"] == rows[0].id
    finally:
        app.dependency_overrides.clear()


def test_run_agent_marks_failed_when_start_raises(test_db, monkeypatch):
    """A start-time failure finishes the record as failed (409 duplicate run)."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    user = _make_user(test_db, "exec-run-fail@test.com")

    app, client = _client_as(test_db, user)
    try:
        with patch(
            "api.routes.agents.start_agent_task",
            side_effect=RuntimeError("already running"),
        ):
            resp = client.post(
                "/api/agents/run", json={"spec_id": "001", "agent_type": "coder"}
            )
        assert resp.status_code == 409

        rows = test_db.query(AgentExecution).all()
        assert len(rows) == 1
        assert rows[0].status == "failed"
        assert "already running" in rows[0].error
    finally:
        app.dependency_overrides.clear()


def test_run_agent_legacy_sub_skips_recording(test_db, monkeypatch):
    """Non-numeric subs (legacy/service tokens) run without an audit row."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    from core.database import get_db
    from core.security import require_auth
    from fastapi.testclient import TestClient
    from main import app

    def _override_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_auth] = lambda: {"sub": "test-user"}
    try:
        client = TestClient(app)
        with patch(
            "api.routes.agents.start_agent_task", return_value="001:planner"
        ) as started:
            resp = client.post(
                "/api/agents/run", json={"spec_id": "001", "agent_type": "planner"}
            )
        assert resp.status_code == 202
        assert started.call_args.kwargs["execution_id"] is None
        assert test_db.query(AgentExecution).count() == 0
    finally:
        app.dependency_overrides.clear()


def test_run_agent_team_mode_requires_workspace(test_db, monkeypatch):
    """Team mode: workspace_id required (400) and access enforced (403)."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "team")
    user = _make_user(test_db, "exec-team@test.com")
    outsider, foreign_ws = _make_workspace(test_db, "exec-team-owner@test.com")

    app, client = _client_as(test_db, user)
    try:
        resp = client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "planner"}
        )
        assert resp.status_code == 400

        resp = client.post(
            "/api/agents/run",
            json={
                "spec_id": "001",
                "agent_type": "planner",
                "workspace_id": foreign_ws.id,
            },
        )
        assert resp.status_code == 403
        assert test_db.query(AgentExecution).count() == 0
    finally:
        app.dependency_overrides.clear()
