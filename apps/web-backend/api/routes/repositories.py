"""
Repository link management API (Track C — C6).

Connect Git repositories to the current workspace so agents can work in them.
Listing needs >= viewer; linking/unlinking needs >= editor. OAuth tokens are
accepted on link, stored server-side, and never returned by any endpoint
(RepositoryResponse deliberately has no token fields).
"""

import logging

from core.database import get_db
from core.permissions import (
    WorkspaceRole,
    current_user_id,
    get_current_workspace,
    role_satisfies,
    user_role_in_workspace,
)
from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, status
from services.repository_service import (
    get_repository,
    link_repository,
    list_repositories,
    unlink_repository,
)
from sqlalchemy.orm import Session

from api.models.repository import (
    RepositoryCreateRequest,
    RepositoryListResponse,
    RepositoryResponse,
)
from api.models.workspace import Workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


def _require_editor(db: Session, auth: dict, workspace: Workspace) -> int:
    """403 unless the caller has >= editor in the workspace; returns user id.

    get_current_workspace already guarantees a numeric sub and >= viewer; this
    raises the bar for mutations.
    """
    user_id = current_user_id(auth)
    role = (
        user_role_in_workspace(db, user_id, workspace.id)
        if user_id is not None
        else None
    )
    if role is None or not role_satisfies(role, WorkspaceRole.EDITOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient workspace permissions",
        )
    return user_id


@router.get("", response_model=RepositoryListResponse)
def list_workspace_repositories(
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """List the current workspace's linked repositories (no token fields)."""
    repositories = [
        RepositoryResponse.model_validate(r)
        for r in list_repositories(db, workspace.id)
    ]
    return RepositoryListResponse(repositories=repositories)


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def link_workspace_repository(
    request: RepositoryCreateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Link a repository (with its OAuth credentials) into the current workspace.

    Requires >= editor. The token is stored server-side for agent use and is
    never returned.
    """
    user_id = _require_editor(db, auth, workspace)
    repository = link_repository(db, workspace.id, user_id, request)
    return RepositoryResponse.model_validate(repository)


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_workspace_repository(
    repository_id: int,
    workspace: Workspace = Depends(get_current_workspace),
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Unlink a repository from the current workspace. Requires >= editor."""
    _require_editor(db, auth, workspace)
    repository = get_repository(db, workspace.id, repository_id)
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    unlink_repository(db, repository)
