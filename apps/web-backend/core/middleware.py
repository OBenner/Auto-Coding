"""
Usage Tracking Middleware

FastAPI middleware for tracking API usage and rate limiting.
Records request metrics to Redis for usage analytics and billing.
"""

import logging
import time
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status

from services.usage_tracker import UsageTracker
from core.config import settings

logger = logging.getLogger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API usage and enforce rate limits.

    Records all API requests to Redis for usage analytics and billing.
    Optionally enforces rate limits per user if enabled.
    """

    def __init__(
        self,
        app,
        usage_tracker: Optional[UsageTracker] = None,
        rate_limit_enabled: bool = False,
        rate_limit_requests: int = 1000,
        rate_limit_period: str = "hourly"
    ):
        """
        Initialize usage tracking middleware.

        Args:
            app: FastAPI application instance
            usage_tracker: Optional UsageTracker instance. Creates one if not provided.
            rate_limit_enabled: Whether to enforce rate limits
            rate_limit_requests: Maximum requests per period (if rate limiting enabled)
            rate_limit_period: Rate limit period ("hourly", "daily", "monthly")
        """
        super().__init__(app)

        # Initialize usage tracker
        if usage_tracker:
            self.usage_tracker = usage_tracker
        else:
            try:
                self.usage_tracker = UsageTracker()
                logger.info("Initialized UsageTracker in middleware")
            except Exception as e:
                logger.error(f"Failed to initialize UsageTracker: {e}")
                self.usage_tracker = None

        self.rate_limit_enabled = rate_limit_enabled
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_period = rate_limit_period

        logger.info(
            f"UsageTrackingMiddleware initialized "
            f"(rate_limit_enabled={rate_limit_enabled})"
        )

    def _get_user_id_from_request(self, request: Request) -> Optional[int]:
        """
        Extract user ID from request (from JWT token or session).

        Args:
            request: FastAPI request object

        Returns:
            User ID if authenticated, None otherwise
        """
        # Check if user is attached to request (set by auth dependency)
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # For unauthenticated requests, use a default ID or None
        # In production, you might want to track anonymous usage differently
        return None

    def _should_track_endpoint(self, path: str) -> bool:
        """
        Determine if endpoint should be tracked.

        Excludes health checks, metrics endpoints, and static files.

        Args:
            path: Request path

        Returns:
            True if endpoint should be tracked
        """
        # Exclude specific paths from tracking
        excluded_paths = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
        }

        # Exact match for excluded paths
        if path in excluded_paths:
            return False

        # Exclude paths that start with certain prefixes
        excluded_prefixes = ["/static/", "/assets/"]
        if any(path.startswith(prefix) for prefix in excluded_prefixes):
            return False

        return True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request, track usage, and enforce rate limits.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip tracking for excluded endpoints
        if not self._should_track_endpoint(request.url.path):
            return await call_next(request)

        # Skip if usage tracker is not available
        if not self.usage_tracker:
            logger.debug("UsageTracker not available, skipping tracking")
            return await call_next(request)

        # Get user ID (if authenticated)
        user_id = self._get_user_id_from_request(request)

        # If no user ID and tracking requires authentication, skip
        if user_id is None:
            # For unauthenticated requests, we can still track with a sentinel value
            # or skip tracking entirely based on requirements
            # For now, skip tracking if no user
            return await call_next(request)

        # Check rate limit before processing request
        if self.rate_limit_enabled:
            try:
                is_allowed, current_count = self.usage_tracker.check_rate_limit(
                    user_id=user_id,
                    limit=self.rate_limit_requests,
                    period=self.rate_limit_period
                )

                if not is_allowed:
                    logger.warning(
                        f"Rate limit exceeded for user {user_id}: "
                        f"{current_count}/{self.rate_limit_requests} ({self.rate_limit_period})"
                    )

                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": "Rate limit exceeded",
                            "limit": self.rate_limit_requests,
                            "period": self.rate_limit_period,
                            "current": current_count
                        }
                    )
            except Exception as e:
                logger.error(f"Error checking rate limit: {e}")
                # On error, allow the request (fail open)

        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Record request in usage tracker
        try:
            self.usage_tracker.record_request(
                user_id=user_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code
            )

            logger.debug(
                f"Tracked request: user={user_id} {request.method} {request.url.path} "
                f"-> {response.status_code} ({process_time:.3f}s)"
            )

        except Exception as e:
            logger.error(f"Failed to record request: {e}")
            # Don't fail the request if tracking fails

        # Add custom headers for debugging (optional, can be disabled in production)
        if settings.DEBUG:
            response.headers["X-Process-Time"] = str(process_time)
            if user_id:
                response.headers["X-User-Id"] = str(user_id)

        return response
