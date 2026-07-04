"""Tests for workspace-scoped repository links (C6): service and API.

Relies on the shared `test_db` fixture (in-memory SQLite with all tables created).
"""

import secrets

from api.models.repository import GitRepository, RepositoryCreateRequest
from api.models.user import User
from api.models.workspace import WorkspaceUser
from core.config import settings
from services.repository_service import (
    get_repository,
    link_repository,
    list_repositories,
)
from services.workspace_service import create_workspace


def _make_user(db, email: str) -> User:
    # Random throwaway hash: these tests exercise repo links, not auth.
    user = User(email=email, hashed_password=secrets.token_hex(16))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_workspace(db, email: str):
    user = _make_user(db, email)
    return user, create_workspace(db, owner_id=user.id, name="WS")


def _request(name="auto-code", token=None):
    # Random throwaway token (never a literal): Sonar S6418 reads hard-coded
    # defaults as secrets, and these tests only need *a* value to track.
    return RepositoryCreateRequest(
        provider="github",
        repository_url=f"https://github.com/acme/{name}",
        repository_name=name,
        repository_owner="acme",
        access_token=token or f"tok-{secrets.token_hex(12)}",
    )


def test_link_and_list_scoped_by_workspace(test_db):
    user_a, ws_a = _make_workspace(test_db, "repo-a@test.com")
    user_b, ws_b = _make_workspace(test_db, "repo-b@test.com")

    linked = link_repository(test_db, ws_a.id, user_a.id, _request("one"))
    link_repository(test_db, ws_b.id, user_b.id, _request("two"))

    assert linked.workspace_id == ws_a.id
    mine = list_repositories(test_db, ws_a.id)
    assert [r.repository_name for r in mine] == ["one"]
    # Cross-workspace lookup by id misses.
    assert get_repository(test_db, ws_b.id, linked.id) is None
    assert get_repository(test_db, ws_a.id, linked.id) is not None


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


def test_repositories_api_lifecycle_single_mode(test_db, monkeypatch):
    """Link -> list -> delete in single mode; tokens never leave the API."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "single")
    user = _make_user(test_db, "repo-api@test.com")

    app, client = _client_as(test_db, user)
    try:
        secret = f"tok-{secrets.token_hex(12)}"
        body = {
            "provider": "github",
            "repository_url": "https://github.com/acme/auto-code",
            "repository_name": "auto-code",
            "repository_owner": "acme",
            "access_token": secret,
        }
        created = client.post("/api/repositories", json=body)
        assert created.status_code == 201
        payload = created.json()
        assert payload["repository_name"] == "auto-code"
        assert payload["workspace_id"] is not None
        # No token material in any response.
        assert "access_token" not in payload
        assert "refresh_token" not in payload
        assert secret not in created.text

        listed = client.get("/api/repositories")
        assert listed.status_code == 200
        assert [r["id"] for r in listed.json()["repositories"]] == [payload["id"]]
        assert secret not in listed.text

        deleted = client.delete(f"/api/repositories/{payload['id']}")
        assert deleted.status_code == 204
        assert client.get("/api/repositories").json()["repositories"] == []
    finally:
        app.dependency_overrides.clear()


def test_repositories_api_cross_workspace_isolation(test_db, monkeypatch):
    """Team mode: a foreign workspace's repos are invisible and undeletable."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "team")
    owner_a, ws_a = _make_workspace(test_db, "repo-t-a@test.com")
    owner_b, ws_b = _make_workspace(test_db, "repo-t-b@test.com")
    foreign = link_repository(test_db, ws_b.id, owner_b.id, _request("secret-repo"))

    app, client = _client_as(test_db, owner_a)
    try:
        listed = client.get(f"/api/repositories?workspace_id={ws_a.id}")
        assert listed.status_code == 200
        assert listed.json()["repositories"] == []

        # Deleting another workspace's repo through my workspace context -> 404.
        resp = client.delete(
            f"/api/repositories/{foreign.id}?workspace_id={ws_a.id}"
        )
        assert resp.status_code == 404
        assert test_db.query(GitRepository).filter_by(id=foreign.id).count() == 1

        # And I can't use their workspace context at all -> 403.
        resp = client.get(f"/api/repositories?workspace_id={ws_b.id}")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_repositories_api_viewer_cannot_mutate(test_db, monkeypatch):
    """Team mode: a viewer can list but not link/unlink (403)."""
    monkeypatch.setattr(settings, "CLOUD_MODE", "team")
    owner, ws = _make_workspace(test_db, "repo-v-owner@test.com")
    viewer = _make_user(test_db, "repo-v-viewer@test.com")
    test_db.add(WorkspaceUser(workspace_id=ws.id, user_id=viewer.id, role="viewer"))
    test_db.commit()
    linked = link_repository(test_db, ws.id, owner.id, _request("shared"))

    app, client = _client_as(test_db, viewer)
    try:
        listed = client.get(f"/api/repositories?workspace_id={ws.id}")
        assert listed.status_code == 200
        assert [r["id"] for r in listed.json()["repositories"]] == [linked.id]

        body = {
            "provider": "github",
            "repository_url": "https://github.com/acme/x",
            "repository_name": "x",
            "repository_owner": "acme",
            "access_token": f"tok-{secrets.token_hex(4)}",
        }
        denied_link = client.post(
            f"/api/repositories?workspace_id={ws.id}", json=body
        )
        assert denied_link.status_code == 403
        denied_unlink = client.delete(
            f"/api/repositories/{linked.id}?workspace_id={ws.id}"
        )
        assert denied_unlink.status_code == 403
    finally:
        app.dependency_overrides.clear()
