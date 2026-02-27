"""
Spec Management API routes

Provides endpoints for listing and managing specs.
Specs and tasks are synonymous in Auto Code - this is an alias endpoint.
"""

import logging
from typing import Annotated

from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, status

from api.models.spec import (
    SpecDetail,
    SpecListResponse,
    SpecProgressDetail,
    SpecSummary,
)
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


@router.get("", response_model=SpecListResponse, status_code=status.HTTP_200_OK)
async def list_specs_endpoint(auth: Annotated[dict, Depends(require_auth)]):
    """
    List all specs in the project.

    Returns a list of all specs with their current status and progress.

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

        return SpecListResponse(specs=spec_list, total=len(spec_list))

    except Exception as e:
        logger.error(f"Error listing specs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list specs",
        )


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
