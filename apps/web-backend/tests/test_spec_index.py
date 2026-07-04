"""Tests for the spec index/audit layer (C4): sync service and API wiring.

Relies on the shared `test_db` fixture (in-memory SQLite with all tables created).
"""

import secrets
from unittest.mock import patch

import pytest
from api.models.spec_record import SpecAuditEntry, SpecRecord
from api.models.user import User
from core.config import settings
from services.spec_index import (
    get_spec_record,
    sync_specs_index,
    sync_specs_index_safely,
)
from services.workspace_service import create_workspace
from sqlalchemy.exc import IntegrityError


def _make_user(db, email: str) -> User:
    # Random throwaway hash: these tests exercise the spec index, not auth.
    user = User(email=email, hashed_password=secrets.token_hex(16))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_workspace(db, email: str):
    user = _make_user(db, email)
    return user, create_workspace(db, owner_id=user.id, name="WS")


def _spec(folder="001-auth", status="in_progress", progress="1/3", **kw):
    number, name = folder.split("-", 1)
    return {
        "number": number,
        "name": name,
        "folder": folder,
        "status": status,
        "progress": progress,
        "has_build": kw.get("has_build", True),
    }


def test_sync_creates_records_and_audit(test_db):
    _, ws = _make_workspace(test_db, "idx-create@test.com")

    counters = sync_specs_index(test_db, ws.id, [_spec(), _spec("002-billing")])
    assert counters == {"created": 2, "updated": 0, "deleted": 0}

    records = test_db.query(SpecRecord).filter_by(workspace_id=ws.id).all()
    assert {r.folder for r in records} == {"001-auth", "002-billing"}
    for r in records:
        assert [e.action for e in r.audit_entries] == ["created"]


def test_sync_is_idempotent_when_unchanged(test_db):
    _, ws = _make_workspace(test_db, "idx-idem@test.com")
    sync_specs_index(test_db, ws.id, [_spec()])

    counters = sync_specs_index(test_db, ws.id, [_spec()])
    assert counters == {"created": 0, "updated": 0, "deleted": 0}
    record = get_spec_record(test_db, ws.id, "001-auth")
    assert len(record.audit_entries) == 1  # only the original 'created'


def test_sync_audits_field_changes(test_db):
    _, ws = _make_workspace(test_db, "idx-upd@test.com")
    sync_specs_index(test_db, ws.id, [_spec(status="in_progress", progress="1/3")])

    sync_specs_index(test_db, ws.id, [_spec(status="complete", progress="3/3")])

    record = get_spec_record(test_db, ws.id, "001-auth")
    assert record.status == "complete"
    actions = [e.action for e in record.audit_entries]
    assert actions == ["created", "updated"]
    detail = record.audit_entries[-1].detail
    assert "status: in_progress -> complete" in detail
    assert "progress: 1/3 -> 3/3" in detail


def test_sync_detects_deletion_and_restore(test_db):
    _, ws = _make_workspace(test_db, "idx-del@test.com")
    sync_specs_index(test_db, ws.id, [_spec()])

    # Folder gone from the FS listing -> deleted.
    sync_specs_index(test_db, ws.id, [])
    record = get_spec_record(test_db, ws.id, "001-auth")
    assert record.deleted_at is not None
    assert [e.action for e in record.audit_entries] == ["created", "deleted"]

    # Repeat sync without the folder: no duplicate 'deleted' entries.
    sync_specs_index(test_db, ws.id, [])
    assert len(record.audit_entries) == 2

    # Folder reappears -> restored.
    counters = sync_specs_index(test_db, ws.id, [_spec()])
    assert counters["created"] == 1
    test_db.refresh(record)
    assert record.deleted_at is None
    assert record.audit_entries[-1].action == "created"
    assert record.audit_entries[-1].detail == "restored from filesystem"


def test_sync_scoped_by_workspace(test_db):
    _, ws_a = _make_workspace(test_db, "idx-a@test.com")
    _, ws_b = _make_workspace(test_db, "idx-b@test.com")
    sync_specs_index(test_db, ws_a.id, [_spec()])

    # Same folder in another workspace is an independent record.
    sync_specs_index(test_db, ws_b.id, [_spec()])
    assert test_db.query(SpecRecord).filter_by(folder="001-auth").count() == 2
    # And an empty listing in B does not delete A's record.
    sync_specs_index(test_db, ws_b.id, [])
    assert get_spec_record(test_db, ws_a.id, "001-auth").deleted_at is None


def test_get_spec_record_by_number(test_db):
    _, ws = _make_workspace(test_db, "idx-num@test.com")
    sync_specs_index(test_db, ws.id, [_spec()])

    assert get_spec_record(test_db, ws.id, "001").folder == "001-auth"
    assert get_spec_record(test_db, ws.id, "001-auth").folder == "001-auth"
    assert get_spec_record(test_db, ws.id, "999") is None


def test_invalid_audit_action_rejected_by_db(test_db):
    _, ws = _make_workspace(test_db, "idx-ck@test.com")
    sync_specs_index(test_db, ws.id, [_spec()])
    record = get_spec_record(test_db, ws.id, "001-auth")

    test_db.add(SpecAuditEntry(spec_record_id=record.id, action="renamed"))
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_sync_safely_never_raises(test_db):
    # The wrapper's contract: a sync failure is swallowed and rolled back
    # (SQLite doesn't enforce FKs by default, so force the failure directly).
    with patch(
        "services.spec_index.sync_specs_index", side_effect=RuntimeError("boom")
    ):
        sync_specs_index_safely(test_db, 1, [_spec()])
    assert test_db.query(SpecRecord).count() == 0


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


_FAKE_SPECS = [
    {
        "number": "001",
        "name": "auth",
        "folder": "001-auth",
        "status": "in_progress",
        "progress": "1/3",
        "has_build": True,
    }
]


def test_listing_syncs_index_and_audit_api(test_db, monkeypatch):
    """GET /api/specs mirrors the FS into the index; audit API serves the trail."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    user = _make_user(test_db, "idx-api@test.com")

    app, client = _client_as(test_db, user)
    try:
        with patch("api.routes.specs.list_specs", return_value=_FAKE_SPECS):
            resp = client.get("/api/specs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        # The listing side effect indexed the spec into the Personal workspace.
        record = test_db.query(SpecRecord).one()
        assert record.folder == "001-auth"

        audit = client.get("/api/specs/001-auth/audit")
        assert audit.status_code == 200
        body = audit.json()
        assert body["folder"] == "001-auth"
        assert [e["action"] for e in body["entries"]] == ["created"]

        # By bare number too; unknown spec -> 404.
        assert client.get("/api/specs/001/audit").status_code == 200
        assert client.get("/api/specs/999/audit").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_listing_skips_sync_for_legacy_tokens(test_db, monkeypatch):
    """Non-numeric subs keep the legacy contract: 200, no index rows."""
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
        with patch("api.routes.specs.list_specs", return_value=_FAKE_SPECS):
            resp = client.get("/api/specs")
        assert resp.status_code == 200
        assert test_db.query(SpecRecord).count() == 0
    finally:
        app.dependency_overrides.clear()


def test_listing_team_mode_workspace_param(test_db, monkeypatch):
    """Team mode: explicit workspace_id syncs there; foreign workspace -> 403."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "team")
    user, ws = _make_workspace(test_db, "idx-team@test.com")
    _, foreign_ws = _make_workspace(test_db, "idx-team-other@test.com")

    app, client = _client_as(test_db, user)
    try:
        with patch("api.routes.specs.list_specs", return_value=_FAKE_SPECS):
            # Without workspace_id: listing works, sync skipped.
            resp = client.get("/api/specs")
            assert resp.status_code == 200
            assert test_db.query(SpecRecord).count() == 0

            # With own workspace: synced.
            resp = client.get(f"/api/specs?workspace_id={ws.id}")
            assert resp.status_code == 200
            assert test_db.query(SpecRecord).one().workspace_id == ws.id

            # Foreign workspace: hard 403.
            resp = client.get(f"/api/specs?workspace_id={foreign_ws.id}")
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
