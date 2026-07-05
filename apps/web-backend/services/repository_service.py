"""
Workspace-scoped repository links (Track C — C6).

Persists which Git repositories are connected to a workspace (with the OAuth
credentials the agent will use to work in them). All reads filter by
workspace_id and all writes set it — the tenant boundary owns its repos.
OAuth tokens are stored server-side only and never leave through the API.
"""

import logging

from api.models.repository import GitRepository, RepositoryCreateRequest
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def link_repository(
    db: Session,
    workspace_id: int,
    user_id: int,
    request: RepositoryCreateRequest,
) -> GitRepository:
    """Persist a repository link into the workspace (token stays server-side)."""
    repository = GitRepository(
        user_id=user_id,
        workspace_id=workspace_id,
        provider=request.provider,
        repository_url=request.repository_url,
        repository_name=request.repository_name,
        repository_owner=request.repository_owner,
        access_token=request.access_token,
        refresh_token=request.refresh_token,
        token_expires_at=request.token_expires_at,
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)
    logger.info(
        "Linked repository id=%s to workspace_id=%s", repository.id, workspace_id
    )
    return repository


def list_repositories(db: Session, workspace_id: int) -> list[GitRepository]:
    """All repository links belonging to the workspace (oldest first)."""
    return (
        db.query(GitRepository)
        .filter(GitRepository.workspace_id == workspace_id)
        .order_by(GitRepository.id.asc())
        .all()
    )


def get_repository(
    db: Session, workspace_id: int, repository_id: int
) -> GitRepository | None:
    """One repository link, only if it belongs to the workspace."""
    return (
        db.query(GitRepository)
        .filter(
            GitRepository.id == repository_id,
            GitRepository.workspace_id == workspace_id,
        )
        .first()
    )


def unlink_repository(db: Session, repository: GitRepository) -> None:
    """Delete a repository link (and its stored credentials)."""
    db.delete(repository)
    db.commit()
