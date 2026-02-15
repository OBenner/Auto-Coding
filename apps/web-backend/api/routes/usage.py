"""
Usage API routes

Provides endpoints for viewing usage statistics and metrics.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from services.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


def _sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")


# Create router for usage endpoints
router = APIRouter(prefix="/api/usage", tags=["usage"])


# Pydantic models for API responses
class UsagePeriodStats(BaseModel):
    """Usage statistics for a specific time period"""

    period: str = Field(..., description="Time period identifier (e.g., '2026-02-04')")
    total_requests: int = Field(
        default=0, description="Total number of requests in this period"
    )
    metrics: dict = Field(
        default_factory=dict, description="Additional metrics for this period"
    )


class EndpointStats(BaseModel):
    """Usage statistics for a specific endpoint"""

    endpoint: str = Field(..., description="API endpoint path")
    period: str = Field(..., description="Time period (hourly, daily, monthly)")
    total_requests: int = Field(
        default=0, description="Total requests to this endpoint"
    )
    methods: dict[str, int] = Field(
        default_factory=dict, description="Request counts by HTTP method"
    )


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics"""

    user_id: int | None = Field(None, description="User ID (if authenticated)")
    period: str = Field(..., description="Time period type (hourly, daily, monthly)")
    days_back: int = Field(default=7, description="Number of days/periods included")
    usage_data: list[UsagePeriodStats] = Field(
        default_factory=list, description="Usage data over time"
    )
    total_requests: int = Field(
        default=0, description="Total requests across all periods"
    )
    redis_healthy: bool = Field(
        default=True, description="Redis connection health status"
    )


class UsageDashboardResponse(BaseModel):
    """Response model for usage dashboard overview"""

    total_requests_today: int = Field(default=0, description="Total requests today")
    total_requests_this_month: int = Field(
        default=0, description="Total requests this month"
    )
    endpoints: list[EndpointStats] = Field(
        default_factory=list, description="Top endpoints by usage"
    )
    redis_healthy: bool = Field(
        default=True, description="Redis connection health status"
    )


def get_usage_tracker() -> UsageTracker:
    """
    Dependency to get UsageTracker instance.

    Returns:
        UsageTracker instance
    """
    return UsageTracker()


@router.get("", status_code=status.HTTP_200_OK)
async def usage_info():
    """
    Basic usage endpoint for health check and info.

    Returns basic information about the usage tracking system.

    Returns:
        Dictionary with status and info

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/usage \
             -H "Content-Type: application/json"
        # Returns: {"status": "ok", "service": "usage-tracking"}
        ```
    """
    return {
        "status": "ok",
        "service": "usage-tracking",
        "description": "API usage tracking and analytics",
    }


@router.get("/stats", status_code=status.HTTP_200_OK, response_model=UsageStatsResponse)
async def get_usage_stats(
    user_id: int | None = Query(
        None, description="User ID to query (defaults to 1 for demo)"
    ),
    period: str = Query("daily", description="Time period: hourly, daily, or monthly"),
    days_back: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    tracker: UsageTracker = Depends(get_usage_tracker),
):
    """
    Get usage statistics for a user over time.

    Returns detailed usage metrics including request counts per period,
    status codes, and other tracked metrics.

    Args:
        user_id: User ID to query (defaults to 1 for demo purposes)
        period: Time period granularity (hourly, daily, monthly)
        days_back: Number of time periods to retrieve (1-90)
        tracker: UsageTracker dependency injection

    Returns:
        UsageStatsResponse with usage data

    Example:
        ```bash
        curl -X GET "http://localhost:8000/api/usage/stats?user_id=1&period=daily&days_back=7" \
             -H "Content-Type: application/json"
        ```
    """
    try:
        # Validate period parameter
        if period not in ["hourly", "daily", "monthly"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid period: {period}. Must be hourly, daily, or monthly",
            )

        # Check Redis health
        redis_healthy = tracker.health_check()
        if not redis_healthy:
            logger.warning("Redis connection unhealthy, returning empty stats")
            return UsageStatsResponse(
                user_id=user_id,
                period=period,
                days_back=days_back,
                usage_data=[],
                total_requests=0,
                redis_healthy=False,
            )

        # Default to user_id 1 for demo purposes if not provided
        if user_id is None:
            user_id = 1
            logger.info("No user_id provided, defaulting to user_id=1 for demo")

        # Fetch usage data from tracker
        usage_data = tracker.get_user_usage(
            user_id=user_id, period=period, days_back=days_back
        )

        # Convert to Pydantic models
        usage_periods = [
            UsagePeriodStats(
                period=item["period"],
                total_requests=item["total_requests"],
                metrics=item["metrics"],
            )
            for item in usage_data
        ]

        # Calculate total requests
        total_requests = sum(item.total_requests for item in usage_periods)

        logger.info(
            f"Retrieved usage stats for user {_sanitize_log(str(user_id))}: "
            f"{total_requests} total requests over {len(usage_periods)} periods"
        )

        return UsageStatsResponse(
            user_id=user_id,
            period=period,
            days_back=days_back,
            usage_data=usage_periods,
            total_requests=total_requests,
            redis_healthy=redis_healthy,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching usage stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch usage statistics: {str(e)}",
        )


@router.get(
    "/dashboard", status_code=status.HTTP_200_OK, response_model=UsageDashboardResponse
)
async def get_usage_dashboard(
    user_id: int | None = Query(
        None, description="User ID to query (defaults to 1 for demo)"
    ),
    tracker: UsageTracker = Depends(get_usage_tracker),
):
    """
    Get usage dashboard overview.

    Returns a high-level overview of usage statistics including
    today's requests, monthly totals, and top endpoints.

    Args:
        user_id: User ID to query (defaults to 1 for demo purposes)
        tracker: UsageTracker dependency injection

    Returns:
        UsageDashboardResponse with dashboard data

    Example:
        ```bash
        curl -X GET "http://localhost:8000/api/usage/dashboard?user_id=1" \
             -H "Content-Type: application/json"
        ```
    """
    try:
        # Check Redis health
        redis_healthy = tracker.health_check()
        if not redis_healthy:
            logger.warning("Redis connection unhealthy, returning empty dashboard")
            return UsageDashboardResponse(
                total_requests_today=0,
                total_requests_this_month=0,
                endpoints=[],
                redis_healthy=False,
            )

        # Default to user_id 1 for demo purposes if not provided
        if user_id is None:
            user_id = 1
            logger.info("No user_id provided, defaulting to user_id=1 for demo")

        # Get today's usage
        daily_usage = tracker.get_user_usage(
            user_id=user_id, period="daily", days_back=1
        )
        total_requests_today = daily_usage[0]["total_requests"] if daily_usage else 0

        # Get monthly usage
        monthly_usage = tracker.get_user_usage(
            user_id=user_id, period="monthly", days_back=1
        )
        total_requests_this_month = (
            monthly_usage[0]["total_requests"] if monthly_usage else 0
        )

        logger.info(
            f"Dashboard stats for user {_sanitize_log(str(user_id))}: "
            f"{total_requests_today} today, {total_requests_this_month} this month"
        )

        return UsageDashboardResponse(
            total_requests_today=total_requests_today,
            total_requests_this_month=total_requests_this_month,
            endpoints=[],  # Endpoint breakdown can be added later
            redis_healthy=redis_healthy,
        )

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard data: {str(e)}",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def usage_health_check(tracker: UsageTracker = Depends(get_usage_tracker)):
    """
    Check health of usage tracking system (Redis connection).

    Returns:
        Dictionary with health status

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/usage/health \
             -H "Content-Type: application/json"
        ```
    """
    try:
        redis_healthy = tracker.health_check()

        return {
            "status": "healthy" if redis_healthy else "unhealthy",
            "redis": "connected" if redis_healthy else "disconnected",
            "service": "usage-tracking",
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "redis": "error",
            "service": "usage-tracking",
        }
