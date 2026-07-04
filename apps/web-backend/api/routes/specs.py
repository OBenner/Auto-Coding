"""
Spec Management API routes

Provides endpoints for listing and managing specs.
Specs and tasks are synonymous in Auto Code - this is an alias endpoint.
"""

import logging
from typing import Annotated

from core.config import settings
from core.database import get_db
from core.permissions import (
    WorkspaceRole,
    check_workspace_access,
    current_user_id,
    get_current_workspace,
)
from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, Query, status
from services.spec_index import get_spec_record, sync_specs_index_safely
from services.workspace_service import get_or_create_personal_workspace
from sqlalchemy.orm import Session

from api.models.spec import (
    SpecDetail,
    SpecListResponse,
    SpecProgressDetail,
    SpecSummary,
)
from api.models.spec_record import SpecAuditEntryResponse, SpecAuditResponse
from api.models.workspace import Workspace
from api.routes.shared import (
    build_item_detail,
    count_subtasks_detailed,
    find_spec_dir,
    get_progress_percentage,
    list_specs,
    sanitize_log,
)

logger = logging.getLogger(__name__)


# Create router for spec endpoints
router = APIRouter(prefix="/api/specs", tags=["specs"])


def _resolve_index_workspace(
    auth: dict, db: Session, workspace_id: int | None
) -> int | None:
    """Workspace to sync the spec index into, or None to skip syncing.

    Listing is a read: legacy tokens (non-numeric ``sub``) and team mode
    without an explicit ``workspace_id`` skip the index sync instead of
    failing. An explicit ``workspace_id`` without access is still a hard 403.
    """
    user_id = current_user_id(auth)
    if user_id is None:
        return None
    if settings.CLOUD_MODE == "single":
        return get_or_create_personal_workspace(db, user_id).id
    if workspace_id is None:
        return None
    if not check_workspace_access(db, user_id, workspace_id, WorkspaceRole.VIEWER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient workspace permissions",
        )
    return workspace_id


@router.get("", response_model=SpecListResponse, status_code=status.HTTP_200_OK)
def list_specs_endpoint(
    auth: dict = Depends(require_auth),
    db: Session = Depends(get_db),
    workspace_id: int | None = Query(
        None, description="Workspace for the spec index sync (team mode)"
    ),
):
    """
    List all specs in the project.

    Returns a list of all specs with their current status and progress. The
    filesystem is the source of truth; as a side effect the listing is mirrored
    into the workspace's spec index (C4) so changes are audited — best-effort,
    never blocking the listing. Plain ``def``: FS + DB work stays off the loop.

    Returns:
        SpecListResponse with list of specs and total count

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/specs \
             -H "Authorization: Bearer <token>" \
             -H "Content-Type: application/json"
        # Returns: {"specs": [...], "total": 5}
        ```
    """
    try:
        # Get specs
        specs = list_specs()

        # Convert to API response format
        spec_list = [
            SpecSummary(
                number=spec["number"],
                name=spec["name"],
                folder=spec["folder"],
                status=spec["status"],
                progress=spec["progress"],
                has_build=spec.get("has_build", False),
            )
            for spec in specs
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing specs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list specs",
        )

    # Mirror the FS listing into the workspace's spec index (audit trail).
    sync_workspace_id = _resolve_index_workspace(auth, db, workspace_id)
    if sync_workspace_id is not None:
        sync_specs_index_safely(db, sync_workspace_id, specs)

    return SpecListResponse(specs=spec_list, total=len(spec_list))


@router.get("/health", status_code=status.HTTP_200_OK)
async def specs_health():
    """
    Health check for specs API.

    Returns basic status information about the specs API endpoint.

    Returns:
        Dictionary with status and configuration info
    """
    return {
        "status": "ok",
        "endpoint": "specs",
    }


@router.get("/{spec_id}/progress", status_code=status.HTTP_200_OK)
async def get_spec_progress(spec_id: str, auth: Annotated[dict, Depends(require_auth)]):
    """
    Get progress statistics for a specific spec.

    Args:
        spec_id: Spec number (e.g., "001") or full folder name (e.g., "001-feature")
        auth: Authentication token claims (required)

    Returns:
        Dictionary with completed, in_progress, pending, failed, total, percentage
    """
    spec_folder = find_spec_dir(spec_id)

    if spec_folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spec {spec_id} not found",
        )

    counts = count_subtasks_detailed(spec_folder)
    percentage = get_progress_percentage(spec_folder)

    return {
        "completed": counts["completed"],
        "in_progress": counts["in_progress"],
        "pending": counts["pending"],
        "failed": counts["failed"],
        "total": counts["total"],
        "percentage": percentage,
    }


@router.get("/{spec_id}/audit", response_model=SpecAuditResponse)
def get_spec_audit(
    spec_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Max entries to return"),
):
    """Audit trail of one spec's observed changes (newest first), per workspace.

    ``spec_id`` is the folder name ("001-feature") or the bare number ("001").
    Entries are recorded by the listing sync (C4); the FS remains the source of
    truth for spec content. Plain ``def``: blocking DB work runs in the
    threadpool.
    """
    record = get_spec_record(db, workspace.id, spec_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec is not indexed in this workspace",
        )
    entries = sorted(record.audit_entries, key=lambda e: e.id, reverse=True)[:limit]
    return SpecAuditResponse(
        folder=record.folder,
        workspace_id=record.workspace_id,
        entries=[SpecAuditEntryResponse.model_validate(e) for e in entries],
    )


@router.get("/{spec_id}", response_model=SpecDetail, status_code=status.HTTP_200_OK)
async def get_spec_detail(spec_id: str, auth: Annotated[dict, Depends(require_auth)]):
    """
    Get detailed information for a specific spec.

    Args:
        spec_id: Spec number (e.g., "001") or full folder name (e.g., "001-feature")

    Returns:
        SpecDetail with complete spec information including spec content

    Raises:
        HTTPException: 404 if spec not found, 500 for other errors

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/specs/001 \
             -H "Authorization: Bearer <token>" \
             -H "Content-Type: application/json"
        # Returns: {"number": "001", "name": "feature", ...}
        ```
    """
    try:
        data = build_item_detail(spec_id, "Spec")
        progress_data = data.pop("progress")
        return SpecDetail(progress=SpecProgressDetail(**progress_data), **data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting spec detail for {sanitize_log(spec_id)}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get spec detail",
        )
