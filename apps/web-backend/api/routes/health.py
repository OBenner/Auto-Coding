"""
Health Check API routes

Provides liveness, readiness, and detailed health check endpoints
for monitoring and orchestration systems (e.g., Kubernetes, load balancers).
"""

import logging
import os
import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Record startup time so uptime can be reported
_START_TIME: float = time.time()

# Create router for health endpoints (no auth required for health checks)
router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    """Response from the liveness endpoint"""

    status: Literal["alive"] = Field("alive", description="Always 'alive' when process is running")


class ReadinessResponse(BaseModel):
    """Response from the readiness endpoint"""

    status: Literal["ready", "not_ready"] = Field(..., description="Readiness status")
    reason: str | None = Field(None, description="Reason if not ready")


class ComponentHealth(BaseModel):
    """Health status for an individual component"""

    status: Literal["ok", "degraded", "unavailable"] = Field(..., description="Component status")
    detail: str | None = Field(None, description="Optional detail message")


class DetailedHealthResponse(BaseModel):
    """Response from the detailed health endpoint"""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall service health"
    )
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="Seconds since server startup")
    headless_mode: bool = Field(..., description="Whether the server is running in headless/daemon mode")
    components: dict[str, ComponentHealth] = Field(
        default_factory=dict, description="Per-component health details"
    )


def _check_agent_runner() -> ComponentHealth:
    """Check whether the agent runner service is importable and operational."""
    try:
        from services.agent_runner import get_task_status  # noqa: F401

        return ComponentHealth(status="ok")
    except Exception as exc:  # pragma: no cover
        logger.warning("agent_runner health check failed: %s", exc)
        return ComponentHealth(status="unavailable", detail=str(exc))


def _check_specs_dir() -> ComponentHealth:
    """Check whether the specs directory is accessible."""
    try:
        from api.routes.shared import get_specs_dir

        specs_dir = get_specs_dir()
        if specs_dir.exists():
            return ComponentHealth(status="ok", detail=str(specs_dir))
        # Directory missing is not fatal – specs may not have been created yet
        return ComponentHealth(status="degraded", detail="specs directory does not exist yet")
    except Exception as exc:  # pragma: no cover
        logger.warning("specs_dir health check failed: %s", exc)
        return ComponentHealth(status="unavailable", detail=str(exc))


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description=(
        "Returns HTTP 200 whenever the process is alive. "
        "Intended for use as a Kubernetes/load-balancer liveness probe."
    ),
)
async def liveness() -> LivenessResponse:
    """
    Liveness probe – confirms the process is running.

    Returns HTTP 200 with ``{"status": "alive"}`` as long as the server
    process is up and the event loop is responding.  This endpoint never
    returns a non-200 response under normal circumstances; a failure to
    reach it indicates the process has crashed or is hung.

    Example:
        ```bash
        curl http://localhost:8000/health/live
        # Returns: {"status": "alive"}
        ```
    """
    return LivenessResponse()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Returns HTTP 200 when the server is ready to handle requests. "
        "Returns HTTP 503 with a reason when critical dependencies are unavailable."
    ),
)
async def readiness() -> ReadinessResponse:
    """
    Readiness probe – confirms the server can handle traffic.

    Checks that critical service dependencies (e.g. the agent runner) are
    initialised and responsive.  Returns HTTP 200 when ready, or HTTP 503
    with a descriptive ``reason`` field when not ready.

    Example:
        ```bash
        curl -i http://localhost:8000/health/ready
        # 200: {"status": "ready", "reason": null}
        # 503: {"status": "not_ready", "reason": "agent_runner unavailable"}
        ```
    """
    from fastapi import HTTPException
    from fastapi import status as http_status

    agent_health = _check_agent_runner()
    if agent_health.status == "unavailable":
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ReadinessResponse(
                status="not_ready",
                reason=f"agent_runner unavailable: {agent_health.detail}",
            ).model_dump(),
        )

    return ReadinessResponse(status="ready")


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health report",
    description=(
        "Returns a comprehensive health report including uptime, headless mode status, "
        "and per-component health checks."
    ),
)
async def detailed_health() -> DetailedHealthResponse:
    """
    Detailed health report – full diagnostic information.

    Aggregates individual component health checks and returns an overall
    service status.  Useful for dashboards, alerting, and debugging.

    Overall status rules:
    - ``healthy``  – all components are ``ok``
    - ``degraded`` – at least one component is ``degraded`` but none are ``unavailable``
    - ``unhealthy`` – at least one component is ``unavailable``

    Example:
        ```bash
        curl http://localhost:8000/health/detailed
        # Returns:
        # {
        #   "status": "healthy",
        #   "version": "1.0.0",
        #   "uptime_seconds": 42.3,
        #   "headless_mode": false,
        #   "components": {
        #     "agent_runner": {"status": "ok", "detail": null},
        #     "specs_dir": {"status": "ok", "detail": "/path/to/specs"}
        #   }
        # }
        ```
    """
    components: dict[str, ComponentHealth] = {
        "agent_runner": _check_agent_runner(),
        "specs_dir": _check_specs_dir(),
    }

    statuses = {c.status for c in components.values()}
    if "unavailable" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    headless_mode = (
        os.getenv("HEADLESS", "false").lower() == "true"
        or os.getenv("AUTO_CLAUDE_HEADLESS", "false").lower() == "true"
    )

    return DetailedHealthResponse(
        status=overall,
        version="1.0.0",
        uptime_seconds=round(time.time() - _START_TIME, 2),
        headless_mode=headless_mode,
        components=components,
    )
