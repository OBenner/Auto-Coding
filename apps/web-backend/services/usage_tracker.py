"""
Usage Tracking Service

Service layer for tracking API usage and rate limiting using Redis.
Provides methods to record requests, track usage metrics, and retrieve usage statistics.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, Optional, List
import redis
from core.config import settings

logger = logging.getLogger(__name__)


def _sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")


class UsageTracker:
    """
    Service for tracking API usage and rate limiting with Redis.

    Stores usage metrics per user, endpoint, and time period for billing
    and rate limiting purposes.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize usage tracker.

        Args:
            redis_client: Optional Redis client instance. If not provided,
                         creates a new connection using settings.
        """
        if redis_client:
            self.redis = redis_client
        else:
            # Create Redis connection from settings
            self.redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

        logger.info("Initialized UsageTracker with Redis connection")

    def _get_user_key(self, user_id: int, period: str = "daily") -> str:
        """
        Generate Redis key for user usage tracking.

        Args:
            user_id: User ID to track
            period: Time period ("hourly", "daily", "monthly")

        Returns:
            Redis key string
        """
        now = datetime.now(UTC)

        if period == "hourly":
            time_key = now.strftime("%Y-%m-%d-%H")
        elif period == "monthly":
            time_key = now.strftime("%Y-%m")
        else:  # daily
            time_key = now.strftime("%Y-%m-%d")

        return f"usage:user:{user_id}:{period}:{time_key}"

    def _get_endpoint_key(self, user_id: int, endpoint: str, period: str = "daily") -> str:
        """
        Generate Redis key for endpoint-specific usage tracking.

        Args:
            user_id: User ID to track
            endpoint: API endpoint path
            period: Time period ("hourly", "daily", "monthly")

        Returns:
            Redis key string
        """
        now = datetime.now(UTC)

        if period == "hourly":
            time_key = now.strftime("%Y-%m-%d-%H")
        elif period == "monthly":
            time_key = now.strftime("%Y-%m")
        else:  # daily
            time_key = now.strftime("%Y-%m-%d")

        # Sanitize endpoint for Redis key
        safe_endpoint = endpoint.replace("/", ":").strip(":")

        return f"usage:endpoint:{user_id}:{safe_endpoint}:{period}:{time_key}"

    def record_request(
        self,
        user_id: int,
        endpoint: str,
        method: str = "GET",
        status_code: int = 200
    ) -> bool:
        """
        Record an API request for usage tracking.

        Args:
            user_id: User ID making the request
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP response status code

        Returns:
            True if successfully recorded, False otherwise
        """
        try:
            # Increment user request counters for different periods
            for period in ["hourly", "daily", "monthly"]:
                user_key = self._get_user_key(user_id, period)
                endpoint_key = self._get_endpoint_key(user_id, endpoint, period)

                # Use pipeline for atomic operations
                pipe = self.redis.pipeline()

                # Increment total requests
                pipe.hincrby(user_key, "total_requests", 1)

                # Increment endpoint-specific requests
                pipe.hincrby(endpoint_key, f"{method}_requests", 1)

                # Track status codes
                pipe.hincrby(user_key, f"status_{status_code}", 1)

                # Set expiration (7 days for hourly, 90 days for daily, 1 year for monthly)
                if period == "hourly":
                    pipe.expire(user_key, 7 * 24 * 60 * 60)  # 7 days
                    pipe.expire(endpoint_key, 7 * 24 * 60 * 60)
                elif period == "daily":
                    pipe.expire(user_key, 90 * 24 * 60 * 60)  # 90 days
                    pipe.expire(endpoint_key, 90 * 24 * 60 * 60)
                else:  # monthly
                    pipe.expire(user_key, 365 * 24 * 60 * 60)  # 1 year
                    pipe.expire(endpoint_key, 365 * 24 * 60 * 60)

                pipe.execute()

            logger.debug(
                f"Recorded request for user {_sanitize_log(str(user_id))}: {method} {endpoint} -> {status_code}"
            )

            return True

        except redis.RedisError as e:
            logger.error(f"Failed to record request in Redis: {e}")
            return False

    def get_user_usage(
        self,
        user_id: int,
        period: str = "daily",
        days_back: int = 7
    ) -> List[Dict]:
        """
        Get usage statistics for a user over time.

        Args:
            user_id: User ID to query
            period: Time period ("hourly", "daily", "monthly")
            days_back: Number of days to look back

        Returns:
            List of dictionaries with usage data per time period
        """
        try:
            results = []
            now = datetime.now(UTC)

            for i in range(days_back):
                if period == "hourly":
                    time_key = (now - timedelta(hours=i)).strftime("%Y-%m-%d-%H")
                elif period == "monthly":
                    time_key = (now - timedelta(days=i*30)).strftime("%Y-%m")
                else:  # daily
                    time_key = (now - timedelta(days=i)).strftime("%Y-%m-%d")

                key = f"usage:user:{user_id}:{period}:{time_key}"
                data = self.redis.hgetall(key)

                if data:
                    results.append({
                        "period": time_key,
                        "total_requests": int(data.get("total_requests", 0)),
                        "metrics": data
                    })

            logger.info(f"Retrieved usage data for user {_sanitize_log(str(user_id))} ({len(results)} periods)")

            return results

        except redis.RedisError as e:
            logger.error(f"Failed to get user usage from Redis: {e}")
            return []

    def get_endpoint_stats(
        self,
        user_id: int,
        endpoint: str,
        period: str = "daily"
    ) -> Dict:
        """
        Get usage statistics for a specific endpoint.

        Args:
            user_id: User ID to query
            endpoint: API endpoint path
            period: Time period ("hourly", "daily", "monthly")

        Returns:
            Dictionary with endpoint usage statistics
        """
        try:
            endpoint_key = self._get_endpoint_key(user_id, endpoint, period)
            data = self.redis.hgetall(endpoint_key)

            if not data:
                return {
                    "endpoint": endpoint,
                    "period": period,
                    "requests": 0,
                    "methods": {}
                }

            # Parse method-specific request counts
            methods = {}
            total_requests = 0

            for key, value in data.items():
                if key.endswith("_requests"):
                    method = key.replace("_requests", "")
                    count = int(value)
                    methods[method] = count
                    total_requests += count

            result = {
                "endpoint": endpoint,
                "period": period,
                "total_requests": total_requests,
                "methods": methods
            }

            logger.debug(f"Retrieved endpoint stats for {endpoint}: {total_requests} requests")

            return result

        except redis.RedisError as e:
            logger.error(f"Failed to get endpoint stats from Redis: {e}")
            return {
                "endpoint": endpoint,
                "period": period,
                "requests": 0,
                "methods": {},
                "error": str(e)
            }

    def check_rate_limit(
        self,
        user_id: int,
        limit: int = 1000,
        period: str = "hourly"
    ) -> tuple[bool, int]:
        """
        Check if user has exceeded rate limit.

        Args:
            user_id: User ID to check
            limit: Maximum requests allowed in period
            period: Time period ("hourly", "daily", "monthly")

        Returns:
            Tuple of (is_allowed, current_count)
        """
        try:
            user_key = self._get_user_key(user_id, period)
            current_count = int(self.redis.hget(user_key, "total_requests") or 0)

            is_allowed = current_count < limit

            logger.debug(
                f"Rate limit check for user {_sanitize_log(str(user_id))}: "
                f"{current_count}/{limit} ({period})"
            )

            return is_allowed, current_count

        except redis.RedisError as e:
            logger.error(f"Failed to check rate limit in Redis: {e}")
            # On error, allow the request (fail open)
            return True, 0

    def reset_user_usage(self, user_id: int, period: str = "daily") -> bool:
        """
        Reset usage counters for a user (admin function).

        Args:
            user_id: User ID to reset
            period: Time period to reset ("hourly", "daily", "monthly")

        Returns:
            True if successfully reset, False otherwise
        """
        try:
            user_key = self._get_user_key(user_id, period)
            self.redis.delete(user_key)

            logger.info(f"Reset usage for user {_sanitize_log(str(user_id))} ({period})")

            return True

        except redis.RedisError as e:
            logger.error(f"Failed to reset user usage in Redis: {e}")
            return False

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            self.redis.ping()
            return True
        except redis.RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False
