"""
Spec Management API routes

Provides endpoints for listing and managing specs.
Specs and tasks are synonymous in Auto Code - this is an alias endpoint.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from api.models.spec import (
    SpecDetail,
    SpecListResponse,
    SpecProgressDetail,
    SpecSummary,
)
from api.routes.shared import (
    count_subtasks_detailed,
    find_spec_dir,
    get_progress_percentage,
    get_specs_dir,
    list_specs,
    sanitize_log,
)

logger = logging.getLogger(__name__)


# Create router for spec endpoints
router = APIRouter(prefix="/api/specs", tags=["specs"])


@router.get("", response_model=SpecListResponse, status_code=status.HTTP_200_OK)
async def list_specs_endpoint():
    """
    List all specs in the project.

    Returns a list of all specs with their current status and progress.

    Returns:
        SpecListResponse with list of specs and total count

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/specs \
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
    specs_dir = get_specs_dir()

    return {
        "status": "ok",
        "endpoint": "specs",
        "specs_dir_exists": specs_dir.exists(),
    }


@router.get("/{spec_id}", response_model=SpecDetail, status_code=status.HTTP_200_OK)
async def get_spec_detail(spec_id: str):
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
             -H "Content-Type: application/json"
        # Returns: {"number": "001", "name": "feature", ...}
        ```
    """
    try:
        spec_dir = find_spec_dir(spec_id)

        # Check if spec exists
        if spec_dir is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec {spec_id} not found",
            )

        spec_file = spec_dir / "spec.md"
        if not spec_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec {spec_id} not found",
            )

        # Get spec content
        try:
            spec_content = spec_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read spec content: {e}")
            spec_content = None

        # Parse folder name to get number and name
        folder_name = spec_dir.name
        parts = folder_name.split("-", 1)
        number = parts[0] if len(parts) > 0 else spec_id
        name = parts[1] if len(parts) > 1 else "unknown"

        # Get progress details
        progress_detail = count_subtasks_detailed(spec_dir)
        percentage = get_progress_percentage(spec_dir)

        # Determine status
        if progress_detail["total"] == 0:
            spec_status = "pending"
        elif progress_detail["completed"] == progress_detail["total"]:
            spec_status = "complete"
        elif progress_detail["in_progress"] > 0 or progress_detail["completed"] > 0:
            spec_status = "in_progress"
        else:
            spec_status = "initialized"

        # Check for active build
        has_build = (spec_dir / "implementation_plan.json").exists()

        return SpecDetail(
            number=number,
            name=name,
            folder=folder_name,
            status=spec_status,
            progress=SpecProgressDetail(
                completed=progress_detail["completed"],
                in_progress=progress_detail["in_progress"],
                pending=progress_detail["pending"],
                failed=progress_detail["failed"],
                total=progress_detail["total"],
                percentage=percentage,
            ),
            has_build=has_build,
            spec_content=spec_content,
        )

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
