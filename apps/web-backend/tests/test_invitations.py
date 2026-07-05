"""Tests for workspace invitations (C7): service, registration hook, and API.

Relies on the shared `test_db` fixture (in-memory SQLite with all tables created).
"""

import secrets

import pytest
from api.models.user import User
from api.models.workspace import WorkspaceInvitation, WorkspaceUser
from core.config import settings
from services.workspace_service import (
    InvitationConflict,
    InvitationInvalid,
    accept_pending_invitations,
    create_workspace,
    get_membership,
    invite_member,
    list_invitations,
    revoke_invitation,
)
from sqlalchemy.exc import IntegrityError


def _make_user(db, email: str) -> User:
    # Random throwaway hash: these tests exercise invitations, not auth.
    user = User(email=email, hashed_password=secrets.token_hex(16))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_workspace(db, email: str):
    user = _make_user(db, email)
    return user, create_workspace(db, owner_id=user.id, name="WS")


def test_invite_unknown_email_stays_pending(test_db):
    owner, ws = _make_workspace(test_db, "inv-owner@test.com")

    invitation = invite_member(
        test_db, ws, "NewComer@Test.com", "editor", invited_by=owner.id
    )
    assert invitation.status == "pending"
    assert invitation.email == "newcomer@test.com"  # normalized
    assert invitation.role == "editor"

    # Duplicate pending invite for the same (workspace, email) -> conflict,
    # case-insensitively (race-safe via the partial unique index).
    with pytest.raises(InvitationConflict):
        invite_member(test_db, ws, "newcomer@TEST.com", "viewer", owner.id)


def test_invite_existing_user_becomes_member_immediately(test_db):
    owner, ws = _make_workspace(test_db, "inv-owner2@test.com")
    member = _make_user(test_db, "Existing@Test.com")

    invitation = invite_member(
        test_db, ws, "existing@test.com", "viewer", invited_by=owner.id
    )
    assert invitation.status == "accepted"
    assert invitation.responded_at is not None
    membership = get_membership(test_db, ws.id, member.id)
    assert membership is not None and membership.role == "viewer"

    # Inviting them again -> already a member.
    with pytest.raises(InvitationConflict):
        invite_member(test_db, ws, "existing@test.com", "editor", owner.id)
    # Inviting the owner -> invalid.
    with pytest.raises(InvitationInvalid):
        invite_member(test_db, ws, owner.email, "editor", owner.id)


def test_revoke_only_pending(test_db):
    owner, ws = _make_workspace(test_db, "inv-rev@test.com")
    invitation = invite_member(test_db, ws, "ghost@test.com", "viewer", owner.id)

    revoked = revoke_invitation(test_db, ws.id, invitation.id)
    assert revoked.status == "revoked" and revoked.responded_at is not None
    # Second revoke -> conflict; unknown id -> None.
    with pytest.raises(InvitationConflict):
        revoke_invitation(test_db, ws.id, invitation.id)
    assert revoke_invitation(test_db, ws.id, 999999) is None

    # After revocation the same email can be invited again (partial index
    # only covers pending rows).
    again = invite_member(test_db, ws, "ghost@test.com", "viewer", owner.id)
    assert again.status == "pending"


def test_accept_pending_invitations_on_registration(test_db):
    owner_a, ws_a = _make_workspace(test_db, "inv-a@test.com")
    owner_b, ws_b = _make_workspace(test_db, "inv-b@test.com")
    invite_member(test_db, ws_a, "late@test.com", "editor", owner_a.id)
    invite_member(test_db, ws_b, "Late@Test.com", "viewer", owner_b.id)

    # The user registers later (mixed-case email must still match).
    user = _make_user(test_db, "LATE@test.com")
    accepted = accept_pending_invitations(test_db, user)
    assert accepted == 2

    assert get_membership(test_db, ws_a.id, user.id).role == "editor"
    assert get_membership(test_db, ws_b.id, user.id).role == "viewer"
    assert all(
        i.status == "accepted"
        for i in test_db.query(WorkspaceInvitation).all()
    )
    # Idempotent: nothing pending remains.
    assert accept_pending_invitations(test_db, user) == 0


def test_invalid_role_and_status_rejected_by_db(test_db):
    owner, ws = _make_workspace(test_db, "inv-ck@test.com")

    test_db.add(
        WorkspaceInvitation(workspace_id=ws.id, email="x@test.com", role="admin")
    )
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()

    test_db.add(
        WorkspaceInvitation(
            workspace_id=ws.id, email="x@test.com", role="viewer", status="expired"
        )
    )
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def _client_as(test_db, user):
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


def test_invitations_api_flow(test_db, monkeypatch):
    """Owner invites (pending + accepted), lists, revokes; editor is denied."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "team")
    owner, ws = _make_workspace(test_db, "inv-api-owner@test.com")
    existing = _make_user(test_db, "inv-api-existing@test.com")
    base = f"/api/workspaces/{ws.id}/invitations"

    app, client = _client_as(test_db, owner)
    try:
        # Unknown email -> pending.
        pending = client.post(base, json={"email": "future@test.com"})
        assert pending.status_code == 201
        assert pending.json()["status"] == "pending"

        # Existing user -> accepted + membership visible via members API.
        accepted = client.post(
            base, json={"email": existing.email, "role": "editor"}
        )
        assert accepted.status_code == 201
        assert accepted.json()["status"] == "accepted"
        members = client.get(f"/api/workspaces/{ws.id}/members")
        assert existing.email in {m["email"] for m in members.json()["members"]}

        # Duplicate pending -> 409; owner email -> 400.
        dup = client.post(base, json={"email": "future@test.com"})
        assert dup.status_code == 409
        own = client.post(base, json={"email": owner.email})
        assert own.status_code == 400

        # Listing shows both, newest first.
        listing = client.get(base)
        assert listing.status_code == 200
        statuses = [i["status"] for i in listing.json()["invitations"]]
        assert statuses == ["accepted", "pending"]

        # Revoke the pending one; a second revoke conflicts.
        pending_id = pending.json()["id"]
        revoked = client.delete(f"{base}/{pending_id}")
        assert revoked.status_code == 204
        second = client.delete(f"{base}/{pending_id}")
        assert second.status_code == 409
        missing = client.delete(f"{base}/999999")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()

    # A non-owner (the newly added editor) cannot manage invitations.
    app, client = _client_as(test_db, existing)
    try:
        denied = client.post(base, json={"email": "z@test.com"})
        assert denied.status_code == 403
        denied_list = client.get(base)
        assert denied_list.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_invitations_api_requires_team_mode(test_db, monkeypatch):
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    owner, ws = _make_workspace(test_db, "inv-single@test.com")

    app, client = _client_as(test_db, owner)
    try:
        resp = client.post(
            f"/api/workspaces/{ws.id}/invitations", json={"email": "a@test.com"}
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_register_endpoint_accepts_pending_invitations(test_db, monkeypatch):
    """End-to-end: invite an unknown email, then register it -> membership."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "team")
    owner, ws = _make_workspace(test_db, "inv-reg-owner@test.com")
    invite_member(test_db, ws, "joiner@test.com", "editor", owner.id)

    from core.database import get_db
    from main import app

    def _override_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_db
    try:
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        client = TestClient(app)
        # The local venv's bcrypt backend is broken (passlib/bcrypt mismatch);
        # hashing is not what this test exercises — stub it.
        with patch(
            "api.models.user.pwd_context.hash",
            side_effect=lambda _pw: secrets.token_hex(16),
        ):
            resp = client.post(
                "/api/users/register",
                json={
                    "email": "Joiner@test.com",
                    "password": f"pw-{secrets.token_hex(8)}",
                },
            )
        assert resp.status_code == 201
        user_id = resp.json()["user"]["id"]

        membership = get_membership(test_db, ws.id, user_id)
        assert membership is not None and membership.role == "editor"
        invitation = test_db.query(WorkspaceInvitation).one()
        assert invitation.status == "accepted"
    finally:
        app.dependency_overrides.clear()
