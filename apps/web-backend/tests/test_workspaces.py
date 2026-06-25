"""Tests for workspace models and role-based access (C1).

Relies on the shared `test_db` fixture (in-memory SQLite with all tables created).
"""

import secrets

import pytest
from api.models.user import User
from api.models.workspace import Workspace, WorkspaceUser
from core.config import settings
from core.permissions import (
    WorkspaceRole,
    check_workspace_access,
    get_current_workspace,
    role_satisfies,
    user_role_in_workspace,
)
from fastapi import HTTPException
from services.workspace_service import (
    add_member,
    create_workspace,
    get_membership,
    get_or_create_personal_workspace,
    list_accessible_workspaces,
    list_workspace_members,
    remove_member,
    update_member_role,
)
from sqlalchemy.exc import IntegrityError


def _make_user(db, email: str) -> User:
    # Use a random throwaway hash (not a literal) directly: these tests exercise
    # workspace logic, not auth, so we avoid the bcrypt backend entirely.
    user = User(email=email, hashed_password=secrets.token_hex(16))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_workspace_membership_relationships(test_db):
    owner = _make_user(test_db, "owner@test.com")
    workspace = Workspace(name="Team A", owner_id=owner.id)
    test_db.add(workspace)
    test_db.commit()
    test_db.refresh(workspace)

    member = _make_user(test_db, "dev@test.com")
    membership = WorkspaceUser(
        workspace_id=workspace.id, user_id=member.id, role="editor"
    )
    test_db.add(membership)
    test_db.commit()
    test_db.refresh(membership)

    assert workspace.owner.email == "owner@test.com"
    assert len(workspace.members) == 1
    assert workspace.members[0].user.email == "dev@test.com"
    assert membership.workspace.name == "Team A"


def test_membership_is_unique_per_user(test_db):
    owner = _make_user(test_db, "o2@test.com")
    workspace = Workspace(name="WS", owner_id=owner.id)
    test_db.add(workspace)
    test_db.commit()
    test_db.refresh(workspace)

    test_db.add(
        WorkspaceUser(workspace_id=workspace.id, user_id=owner.id, role="owner")
    )
    test_db.commit()

    # A second membership for the same (workspace, user) violates the unique constraint.
    test_db.add(
        WorkspaceUser(workspace_id=workspace.id, user_id=owner.id, role="viewer")
    )

    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_role_hierarchy():
    assert role_satisfies(WorkspaceRole.OWNER, WorkspaceRole.EDITOR)
    assert role_satisfies(WorkspaceRole.EDITOR, WorkspaceRole.VIEWER)
    assert role_satisfies(WorkspaceRole.VIEWER, WorkspaceRole.VIEWER)
    assert not role_satisfies(WorkspaceRole.VIEWER, WorkspaceRole.EDITOR)
    assert not role_satisfies(WorkspaceRole.EDITOR, WorkspaceRole.OWNER)
    # Unknown roles never satisfy a requirement.
    assert not role_satisfies("bogus", WorkspaceRole.VIEWER)


def test_check_workspace_access(test_db):
    owner = _make_user(test_db, "owner3@test.com")
    workspace = Workspace(name="WS3", owner_id=owner.id)
    test_db.add(workspace)
    test_db.commit()
    test_db.refresh(workspace)

    member = _make_user(test_db, "editor@test.com")
    test_db.add(
        WorkspaceUser(workspace_id=workspace.id, user_id=member.id, role="editor")
    )
    test_db.commit()

    # An editor satisfies viewer + editor, but not owner.
    assert check_workspace_access(test_db, member.id, workspace.id, WorkspaceRole.VIEWER)
    assert check_workspace_access(test_db, member.id, workspace.id, WorkspaceRole.EDITOR)
    assert not check_workspace_access(
        test_db, member.id, workspace.id, WorkspaceRole.OWNER
    )

    # A non-member has no role and no access.
    outsider = _make_user(test_db, "outsider@test.com")
    assert user_role_in_workspace(test_db, outsider.id, workspace.id) is None
    assert not check_workspace_access(test_db, outsider.id, workspace.id)


def test_workspace_owner_has_owner_access_without_membership(test_db):
    # The single-user "Personal" workspace has an owner but no membership row;
    # access must still derive from Workspace.owner_id at owner level.
    owner = _make_user(test_db, "soleowner@test.com")
    workspace = Workspace(name="Personal", owner_id=owner.id)
    test_db.add(workspace)
    test_db.commit()
    test_db.refresh(workspace)

    # Precondition for this test's meaning: the owner has NO membership row, so
    # access must come from Workspace.owner_id (not an auto-created membership).
    assert (
        test_db.query(WorkspaceUser)
        .filter(
            WorkspaceUser.workspace_id == workspace.id,
            WorkspaceUser.user_id == owner.id,
        )
        .first()
        is None
    )
    assert user_role_in_workspace(test_db, owner.id, workspace.id) == WorkspaceRole.OWNER
    assert check_workspace_access(test_db, owner.id, workspace.id, WorkspaceRole.OWNER)


def test_invalid_role_is_rejected_by_db(test_db):
    # The CHECK constraint mirrors the WorkspaceRole closed set, so roles outside
    # {owner, editor, viewer} cannot be persisted.
    owner = _make_user(test_db, "ck@test.com")
    workspace = Workspace(name="WS-CK", owner_id=owner.id)
    test_db.add(workspace)
    test_db.commit()
    test_db.refresh(workspace)

    test_db.add(
        WorkspaceUser(workspace_id=workspace.id, user_id=owner.id, role="superadmin")
    )
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


# ---------------------------------------------------------------------------
# C2 — bootstrap, listing, and the get_current_workspace resolver
# ---------------------------------------------------------------------------


def test_get_or_create_personal_workspace_is_idempotent(test_db):
    user = _make_user(test_db, "personal@test.com")

    first = get_or_create_personal_workspace(test_db, user.id)
    second = get_or_create_personal_workspace(test_db, user.id)

    assert first.id == second.id
    assert first.name == "Personal"
    assert first.owner_id == user.id
    # No duplicate Personal workspace created on the second call.
    owned = test_db.query(Workspace).filter(Workspace.owner_id == user.id).all()
    assert len(owned) == 1


def test_list_accessible_workspaces_owned_and_member(test_db):
    user = _make_user(test_db, "lister@test.com")
    owned = create_workspace(test_db, owner_id=user.id, name="Mine")

    other = _make_user(test_db, "lister-other@test.com")
    member_ws = create_workspace(test_db, owner_id=other.id, name="Theirs")
    test_db.add(
        WorkspaceUser(workspace_id=member_ws.id, user_id=user.id, role="viewer")
    )
    test_db.commit()

    # A workspace the user neither owns nor belongs to must not appear.
    create_workspace(test_db, owner_id=other.id, name="Hidden")

    accessible = {w.id for w in list_accessible_workspaces(test_db, user.id)}
    assert accessible == {owned.id, member_ws.id}


def test_get_current_workspace_single_mode(test_db, monkeypatch):
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    user = _make_user(test_db, "single@test.com")

    # Resolves (and creates) the Personal workspace; workspace_id is ignored.
    ws = get_current_workspace(
        workspace_id=None, auth={"sub": str(user.id)}, db=test_db
    )
    assert ws.name == "Personal"
    assert ws.owner_id == user.id

    # Idempotent: a second resolve returns the same workspace.
    again = get_current_workspace(
        workspace_id=999, auth={"sub": str(user.id)}, db=test_db
    )
    assert again.id == ws.id


def test_get_current_workspace_team_mode(test_db, monkeypatch):
    monkeypatch.setattr(settings, "CLOUD_MODE", "team")
    owner = _make_user(test_db, "team-owner@test.com")
    workspace = create_workspace(test_db, owner_id=owner.id, name="Team")

    # The owner can resolve their workspace by id.
    got = get_current_workspace(
        workspace_id=workspace.id, auth={"sub": str(owner.id)}, db=test_db
    )
    assert got.id == workspace.id

    # team mode requires workspace_id -> 400 when omitted.
    with pytest.raises(HTTPException) as missing:
        get_current_workspace(
            workspace_id=None, auth={"sub": str(owner.id)}, db=test_db
        )
    assert missing.value.status_code == 400

    # A non-member is denied -> 403.
    outsider = _make_user(test_db, "team-outsider@test.com")
    with pytest.raises(HTTPException) as denied:
        get_current_workspace(
            workspace_id=workspace.id, auth={"sub": str(outsider.id)}, db=test_db
        )
    assert denied.value.status_code == 403


def test_workspaces_api_endpoints(test_db, monkeypatch):
    """End-to-end HTTP test of the workspaces router (single mode)."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    from core.database import get_db
    from core.security import require_auth
    from fastapi.testclient import TestClient
    from main import app

    user = _make_user(test_db, "apiuser@test.com")

    def _override_db():
        yield test_db

    def _override_auth():
        return {"sub": str(user.id), "email": user.email}

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_auth] = _override_auth
    try:
        client = TestClient(app)

        # No workspaces owned yet.
        resp = client.get("/api/workspaces")
        assert resp.status_code == 200
        assert resp.json()["workspaces"] == []
        assert resp.json()["cloud_mode"] == "single"

        # Resolving the current workspace bootstraps "Personal" (owner role).
        resp = client.get("/api/workspaces/current")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Personal"
        assert resp.json()["role"] == "owner"

        # Creating a workspace returns it with owner role.
        resp = client.post("/api/workspaces", json={"name": "Team X"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Team X"
        assert resp.json()["role"] == "owner"

        # The list now contains both workspaces.
        resp = client.get("/api/workspaces")
        names = {w["name"] for w in resp.json()["workspaces"]}
        assert names == {"Personal", "Team X"}
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# C2 (cont.) — workspace member management
# ---------------------------------------------------------------------------


def test_member_service_crud(test_db):
    owner = _make_user(test_db, "ms-owner@test.com")
    ws = create_workspace(test_db, owner_id=owner.id, name="WS")
    member = _make_user(test_db, "ms-member@test.com")

    m = add_member(test_db, ws.id, member.id, "viewer")
    assert m.role == "viewer"
    assert get_membership(test_db, ws.id, member.id) is not None
    assert [x.user_id for x in list_workspace_members(test_db, ws.id)] == [member.id]

    update_member_role(test_db, m, "editor")
    assert get_membership(test_db, ws.id, member.id).role == "editor"

    remove_member(test_db, m)
    assert get_membership(test_db, ws.id, member.id) is None
    assert list_workspace_members(test_db, ws.id) == []


def test_workspace_members_api(test_db, monkeypatch):
    """End-to-end HTTP test of member management + require_workspace_access."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "team")
    from core.database import get_db
    from core.security import require_auth
    from fastapi.testclient import TestClient
    from main import app

    owner = _make_user(test_db, "mapi-owner@test.com")
    member = _make_user(test_db, "mapi-member@test.com")
    workspace = create_workspace(test_db, owner_id=owner.id, name="Team")
    base = f"/api/workspaces/{workspace.id}/members"

    # A mutable holder lets us switch the acting user mid-test.
    auth_holder = {"sub": str(owner.id), "email": owner.email}

    def _override_db():
        yield test_db

    def _override_auth():
        return auth_holder

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_auth] = _override_auth
    try:
        client = TestClient(app)

        # Initially only the owner is a member.
        resp = client.get(base)
        assert resp.status_code == 200
        assert [m["role"] for m in resp.json()["members"]] == ["owner"]

        # Owner adds a member.
        resp = client.post(base, json={"user_id": member.id, "role": "viewer"})
        assert resp.status_code == 201
        assert resp.json() == {
            "user_id": member.id,
            "email": member.email,
            "role": "viewer",
        }

        # Duplicate add -> 409; adding the owner -> 400.
        dup = client.post(base, json={"user_id": member.id})
        assert dup.status_code == 409
        add_owner = client.post(base, json={"user_id": owner.id, "role": "editor"})
        assert add_owner.status_code == 400

        # Listing now shows owner + member.
        resp = client.get(base)
        assert {m["email"] for m in resp.json()["members"]} == {
            owner.email,
            member.email,
        }

        # Owner promotes the member to editor.
        resp = client.patch(f"{base}/{member.id}", json={"role": "editor"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "editor"

        # A non-owner (the editor) cannot mutate members -> 403, but can list.
        auth_holder["sub"] = str(member.id)
        denied = client.post(base, json={"user_id": owner.id})
        assert denied.status_code == 403
        listed = client.get(base)
        assert listed.status_code == 200

        # Owner removes the member.
        auth_holder["sub"] = str(owner.id)
        removed = client.delete(f"{base}/{member.id}")
        assert removed.status_code == 204
        resp = client.get(base)
        assert [m["role"] for m in resp.json()["members"]] == ["owner"]
    finally:
        app.dependency_overrides.clear()
