"""
Resource Manager Service

Service layer for per-user quota enforcement and process resource limits.
Provides methods to check quotas, track resource consumption, and enforce
limits for multi-tenant isolation in headless server mode.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

import redis
from core.config import settings

logger = logging.getLogger(__name__)


def _sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")


@dataclass
class UserQuota:
    """Quota configuration for a user tier."""

    max_concurrent_agents: int = 3
    max_daily_agent_runs: int = 50
    max_agent_run_duration_seconds: int = 3600  # 1 hour
    max_worktrees: int = 10
    max_memory_mb: int = 2048
    max_cpu_percent: float = 80.0
    max_storage_mb: int = 5120  # 5 GB


# Default quota tiers
QUOTA_TIERS: dict[str, UserQuota] = {
    "free": UserQuota(
        max_concurrent_agents=1,
        max_daily_agent_runs=10,
        max_agent_run_duration_seconds=1800,  # 30 minutes
        max_worktrees=3,
        max_memory_mb=512,
        max_cpu_percent=50.0,
        max_storage_mb=1024,  # 1 GB
    ),
    "standard": UserQuota(
        max_concurrent_agents=3,
        max_daily_agent_runs=50,
        max_agent_run_duration_seconds=3600,  # 1 hour
        max_worktrees=10,
        max_memory_mb=2048,
        max_cpu_percent=80.0,
        max_storage_mb=5120,  # 5 GB
    ),
    "premium": UserQuota(
        max_concurrent_agents=10,
        max_daily_agent_runs=200,
        max_agent_run_duration_seconds=7200,  # 2 hours
        max_worktrees=50,
        max_memory_mb=8192,
        max_cpu_percent=95.0,
        max_storage_mb=20480,  # 20 GB
    ),
}


@dataclass
class ResourceUsage:
    """Current resource usage snapshot for a user."""

    user_id: int
    concurrent_agents: int = 0
    daily_agent_runs: int = 0
    active_worktrees: int = 0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    storage_mb: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class QuotaExceededError(Exception):
    """Raised when a user exceeds their resource quota."""

    def __init__(self, resource: str, current: float, limit: float, user_id: int):
        self.resource = resource
        self.current = current
        self.limit = limit
        self.user_id = user_id
        super().__init__(
            f"User {user_id} exceeded {resource} quota: {current}/{limit}"
        )


class ResourceManager:
    """
    Service for per-user quota enforcement and process resource limits.

    Tracks resource consumption per user and enforces configurable quotas
    to ensure fair multi-tenant resource allocation in headless server mode.
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        """
        Initialize resource manager.

        Args:
            redis_client: Optional Redis client instance. If not provided,
                         creates a new connection using settings.
        """
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

        logger.info("Initialized ResourceManager with Redis connection")

    def _get_quota_key(self, user_id: int) -> str:
        """Generate Redis key for user quota tier storage."""
        return f"resource:quota_tier:{user_id}"

    def _get_concurrent_agents_key(self, user_id: int) -> str:
        """Generate Redis key for tracking concurrent agents."""
        return f"resource:concurrent_agents:{user_id}"

    def _get_daily_runs_key(self, user_id: int) -> str:
        """Generate Redis key for daily agent run counter."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"resource:daily_runs:{user_id}:{today}"

    def _get_worktrees_key(self, user_id: int) -> str:
        """Generate Redis key for tracking active worktrees."""
        return f"resource:worktrees:{user_id}"

    def get_user_quota(self, user_id: int) -> UserQuota:
        """
        Get quota configuration for a user.

        Args:
            user_id: User ID to retrieve quota for

        Returns:
            UserQuota instance with the user's limits
        """
        try:
            tier_key = self._get_quota_key(user_id)
            tier = self.redis.get(tier_key) or "standard"

            quota = QUOTA_TIERS.get(str(tier), QUOTA_TIERS["standard"])
            logger.debug(
                f"Retrieved quota tier '{_sanitize_log(str(tier))}' "
                f"for user {_sanitize_log(str(user_id))}"
            )
            return quota

        except redis.RedisError as e:
            logger.error(f"Failed to get quota tier from Redis: {e}")
            return QUOTA_TIERS["standard"]

    def set_user_quota_tier(self, user_id: int, tier: str) -> bool:
        """
        Set the quota tier for a user (admin function).

        Args:
            user_id: User ID to update
            tier: Quota tier name ("free", "standard", "premium")

        Returns:
            True if successfully set, False otherwise
        """
        if tier not in QUOTA_TIERS:
            logger.warning(
                f"Invalid quota tier '{_sanitize_log(tier)}' for user "
                f"{_sanitize_log(str(user_id))}"
            )
            return False

        try:
            tier_key = self._get_quota_key(user_id)
            self.redis.set(tier_key, tier)

            logger.info(
                f"Set quota tier '{_sanitize_log(tier)}' for user "
                f"{_sanitize_log(str(user_id))}"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to set quota tier in Redis: {e}")
            return False

    def get_resource_usage(self, user_id: int) -> ResourceUsage:
        """
        Get current resource usage for a user.

        Args:
            user_id: User ID to query

        Returns:
            ResourceUsage snapshot for the user
        """
        try:
            concurrent_key = self._get_concurrent_agents_key(user_id)
            daily_key = self._get_daily_runs_key(user_id)
            worktrees_key = self._get_worktrees_key(user_id)

            pipe = self.redis.pipeline()
            pipe.get(concurrent_key)
            pipe.get(daily_key)
            pipe.get(worktrees_key)
            results = pipe.execute()

            concurrent_agents = int(results[0] or 0)
            daily_agent_runs = int(results[1] or 0)
            active_worktrees = int(results[2] or 0)

            usage = ResourceUsage(
                user_id=user_id,
                concurrent_agents=concurrent_agents,
                daily_agent_runs=daily_agent_runs,
                active_worktrees=active_worktrees,
            )

            logger.debug(
                f"Resource usage for user {_sanitize_log(str(user_id))}: "
                f"{concurrent_agents} agents, {daily_agent_runs} daily runs, "
                f"{active_worktrees} worktrees"
            )

            return usage

        except redis.RedisError as e:
            logger.error(f"Failed to get resource usage from Redis: {e}")
            return ResourceUsage(user_id=user_id)

    def check_agent_quota(self, user_id: int) -> tuple[bool, str]:
        """
        Check if a user can start a new agent run.

        Validates both concurrent agent limit and daily run limit.

        Args:
            user_id: User ID to check

        Returns:
            Tuple of (is_allowed, reason). reason is empty string if allowed.
        """
        try:
            quota = self.get_user_quota(user_id)
            usage = self.get_resource_usage(user_id)

            if usage.concurrent_agents >= quota.max_concurrent_agents:
                reason = (
                    f"Concurrent agent limit reached: "
                    f"{usage.concurrent_agents}/{quota.max_concurrent_agents}"
                )
                logger.warning(
                    f"User {_sanitize_log(str(user_id))} exceeded concurrent agents: "
                    f"{usage.concurrent_agents}/{quota.max_concurrent_agents}"
                )
                return False, reason

            if usage.daily_agent_runs >= quota.max_daily_agent_runs:
                reason = (
                    f"Daily agent run limit reached: "
                    f"{usage.daily_agent_runs}/{quota.max_daily_agent_runs}"
                )
                logger.warning(
                    f"User {_sanitize_log(str(user_id))} exceeded daily runs: "
                    f"{usage.daily_agent_runs}/{quota.max_daily_agent_runs}"
                )
                return False, reason

            return True, ""

        except redis.RedisError as e:
            logger.error(f"Failed to check agent quota in Redis: {e}")
            # On error, allow the request (fail open)
            return True, ""

    def check_worktree_quota(self, user_id: int) -> tuple[bool, str]:
        """
        Check if a user can create a new worktree.

        Args:
            user_id: User ID to check

        Returns:
            Tuple of (is_allowed, reason). reason is empty string if allowed.
        """
        try:
            quota = self.get_user_quota(user_id)
            usage = self.get_resource_usage(user_id)

            if usage.active_worktrees >= quota.max_worktrees:
                reason = (
                    f"Worktree limit reached: "
                    f"{usage.active_worktrees}/{quota.max_worktrees}"
                )
                logger.warning(
                    f"User {_sanitize_log(str(user_id))} exceeded worktrees: "
                    f"{usage.active_worktrees}/{quota.max_worktrees}"
                )
                return False, reason

            return True, ""

        except redis.RedisError as e:
            logger.error(f"Failed to check worktree quota in Redis: {e}")
            return True, ""

    def acquire_agent_slot(self, user_id: int) -> bool:
        """
        Acquire a concurrent agent slot for a user, incrementing the counter.

        Should be called when an agent run starts. Pair with
        release_agent_slot() when the run completes.

        Args:
            user_id: User ID acquiring the slot

        Returns:
            True if slot acquired successfully, False otherwise
        """
        try:
            is_allowed, reason = self.check_agent_quota(user_id)
            if not is_allowed:
                logger.warning(
                    f"Agent slot denied for user {_sanitize_log(str(user_id))}: "
                    f"{_sanitize_log(reason)}"
                )
                return False

            concurrent_key = self._get_concurrent_agents_key(user_id)
            daily_key = self._get_daily_runs_key(user_id)

            pipe = self.redis.pipeline()
            pipe.incr(concurrent_key)
            pipe.incr(daily_key)
            # Daily counter expires at end of day (86400 seconds)
            pipe.expire(daily_key, 86400)
            pipe.execute()

            logger.info(
                f"Acquired agent slot for user {_sanitize_log(str(user_id))}"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to acquire agent slot in Redis: {e}")
            return False

    def release_agent_slot(self, user_id: int) -> bool:
        """
        Release a concurrent agent slot for a user, decrementing the counter.

        Should be called when an agent run completes or fails.

        Args:
            user_id: User ID releasing the slot

        Returns:
            True if slot released successfully, False otherwise
        """
        try:
            concurrent_key = self._get_concurrent_agents_key(user_id)
            current = int(self.redis.get(concurrent_key) or 0)

            if current <= 0:
                logger.warning(
                    f"Attempted to release agent slot for user "
                    f"{_sanitize_log(str(user_id))} but count is already 0"
                )
                return False

            self.redis.decr(concurrent_key)

            logger.info(
                f"Released agent slot for user {_sanitize_log(str(user_id))}"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to release agent slot in Redis: {e}")
            return False

    def acquire_worktree_slot(self, user_id: int) -> bool:
        """
        Acquire a worktree slot for a user, incrementing the counter.

        Should be called when a worktree is created. Pair with
        release_worktree_slot() when the worktree is removed.

        Args:
            user_id: User ID acquiring the worktree slot

        Returns:
            True if slot acquired successfully, False otherwise
        """
        try:
            is_allowed, reason = self.check_worktree_quota(user_id)
            if not is_allowed:
                logger.warning(
                    f"Worktree slot denied for user {_sanitize_log(str(user_id))}: "
                    f"{_sanitize_log(reason)}"
                )
                return False

            worktrees_key = self._get_worktrees_key(user_id)
            self.redis.incr(worktrees_key)

            logger.info(
                f"Acquired worktree slot for user {_sanitize_log(str(user_id))}"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to acquire worktree slot in Redis: {e}")
            return False

    def release_worktree_slot(self, user_id: int) -> bool:
        """
        Release a worktree slot for a user, decrementing the counter.

        Should be called when a worktree is deleted.

        Args:
            user_id: User ID releasing the worktree slot

        Returns:
            True if slot released successfully, False otherwise
        """
        try:
            worktrees_key = self._get_worktrees_key(user_id)
            current = int(self.redis.get(worktrees_key) or 0)

            if current <= 0:
                logger.warning(
                    f"Attempted to release worktree slot for user "
                    f"{_sanitize_log(str(user_id))} but count is already 0"
                )
                return False

            self.redis.decr(worktrees_key)

            logger.info(
                f"Released worktree slot for user {_sanitize_log(str(user_id))}"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to release worktree slot in Redis: {e}")
            return False

    def reset_user_resources(self, user_id: int) -> bool:
        """
        Reset all resource counters for a user (admin function).

        Args:
            user_id: User ID to reset

        Returns:
            True if successfully reset, False otherwise
        """
        try:
            concurrent_key = self._get_concurrent_agents_key(user_id)
            daily_key = self._get_daily_runs_key(user_id)
            worktrees_key = self._get_worktrees_key(user_id)

            pipe = self.redis.pipeline()
            pipe.delete(concurrent_key)
            pipe.delete(daily_key)
            pipe.delete(worktrees_key)
            pipe.execute()

            logger.info(
                f"Reset all resource counters for user {_sanitize_log(str(user_id))}"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to reset user resources in Redis: {e}")
            return False

    def get_quota_summary(self, user_id: int) -> dict:
        """
        Get a summary of quota limits and current usage for a user.

        Args:
            user_id: User ID to query

        Returns:
            Dictionary with quota limits, current usage, and remaining capacity
        """
        try:
            quota = self.get_user_quota(user_id)
            usage = self.get_resource_usage(user_id)

            tier_key = self._get_quota_key(user_id)
            tier = self.redis.get(tier_key) or "standard"

            summary = {
                "user_id": user_id,
                "tier": tier,
                "concurrent_agents": {
                    "current": usage.concurrent_agents,
                    "limit": quota.max_concurrent_agents,
                    "remaining": max(
                        0, quota.max_concurrent_agents - usage.concurrent_agents
                    ),
                },
                "daily_agent_runs": {
                    "current": usage.daily_agent_runs,
                    "limit": quota.max_daily_agent_runs,
                    "remaining": max(
                        0, quota.max_daily_agent_runs - usage.daily_agent_runs
                    ),
                },
                "worktrees": {
                    "current": usage.active_worktrees,
                    "limit": quota.max_worktrees,
                    "remaining": max(0, quota.max_worktrees - usage.active_worktrees),
                },
                "limits": {
                    "max_agent_run_duration_seconds": quota.max_agent_run_duration_seconds,
                    "max_memory_mb": quota.max_memory_mb,
                    "max_cpu_percent": quota.max_cpu_percent,
                    "max_storage_mb": quota.max_storage_mb,
                },
                "timestamp": usage.timestamp.isoformat(),
            }

            logger.debug(
                f"Retrieved quota summary for user {_sanitize_log(str(user_id))}"
            )
            return summary

        except redis.RedisError as e:
            logger.error(f"Failed to get quota summary from Redis: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
            }

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
