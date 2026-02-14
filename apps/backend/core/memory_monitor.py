"""
Memory Monitor & Session Bounds
================================

Provides memory pressure detection and session growth limits to prevent
OOM conditions during long-running agent sessions.
"""

import gc
import logging
import os
from enum import Enum

logger = logging.getLogger(__name__)

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    _PSUTIL_AVAILABLE = False


class MemoryPressure(Enum):
    """Memory pressure levels."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class MemoryMonitor:
    """Monitors process memory usage and triggers GC when needed."""

    def __init__(
        self,
        max_memory_mb: float = 2048.0,
        warning_threshold: float = 0.8,
    ) -> None:
        self._max_memory_mb = max_memory_mb
        self._warning_threshold = warning_threshold
        self._process: psutil.Process | None = None  # type: ignore[name-defined]

        if _PSUTIL_AVAILABLE:
            try:
                self._process = psutil.Process(os.getpid())
            except (psutil.Error, OSError):
                logger.debug("Could not create psutil Process handle")

    def get_usage_mb(self) -> float:
        """Return current process RSS in megabytes, or -1 if unavailable."""
        if self._process is None:
            return -1.0
        try:
            mem = self._process.memory_info()
            return mem.rss / (1024.0 * 1024.0)
        except Exception:  # noqa: BLE001 — psutil can raise various exceptions
            return -1.0

    def check_pressure(self) -> MemoryPressure:
        """Check the current memory pressure level."""
        usage = self.get_usage_mb()
        if usage < 0:
            return MemoryPressure.NORMAL  # Can't measure — assume OK

        ratio = usage / self._max_memory_mb
        if ratio >= 1.0:
            return MemoryPressure.CRITICAL
        if ratio >= self._warning_threshold:
            return MemoryPressure.WARNING
        return MemoryPressure.NORMAL

    def should_gc(self) -> bool:
        """Return True when garbage collection should be triggered."""
        pressure = self.check_pressure()
        return pressure in (MemoryPressure.WARNING, MemoryPressure.CRITICAL)

    def maybe_gc(self) -> bool:
        """Run gc.collect() if memory pressure warrants it. Returns True if GC ran."""
        if self.should_gc():
            gc.collect()
            logger.debug(
                "GC triggered at %.1f MB (limit %.1f MB)",
                self.get_usage_mb(),
                self._max_memory_mb,
            )
            return True
        return False


class SessionBounds:
    """Hard caps on session growth to prevent runaway agents."""

    MAX_ROUNDS: int = 100
    MAX_MESSAGES: int = 500

    @classmethod
    def check(cls, round_count: int, message_count: int) -> bool:
        """Return True if the session should be stopped."""
        return round_count >= cls.MAX_ROUNDS or message_count >= cls.MAX_MESSAGES

    @classmethod
    def reason(cls, round_count: int, message_count: int) -> str:
        """Return a human-readable reason if bounds are exceeded."""
        parts: list[str] = []
        if round_count >= cls.MAX_ROUNDS:
            parts.append(f"rounds ({round_count}/{cls.MAX_ROUNDS})")
        if message_count >= cls.MAX_MESSAGES:
            parts.append(f"messages ({message_count}/{cls.MAX_MESSAGES})")
        if parts:
            return f"Session exceeded safety bounds: {', '.join(parts)}"
        return ""
