"""Tests for workspace models and role-based access (C1).

Relies on the shared `test_db` fixture (in-memory SQLite with all tables created).
"""

import secrets

import pytest
from api.models.user import User
from api.models.workspace import Workspace, WorkspaceUser
from core.permissions import (
    WorkspaceRole,
    check_workspace_access,
    role_satisfies,
    user_role_in_workspace,
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
