"""
Resource Usage Tracking
=======================

Tracks CPU, memory, and time usage for agent execution phases.
Provides metrics for real-time progress visualization in the frontend.
"""

import os
import time
from typing import TypedDict

_HAS_PSUTIL = False
try:
    import psutil

    _HAS_PSUTIL = True
except ImportError:
    pass


class ResourceMetrics(TypedDict, total=False):
    """Resource usage metrics."""

    cpu_percent: float
    memory_mb: float
    memory_percent: float
    elapsed_seconds: float


class ResourceTracker:
    """
    Tracks resource usage (CPU, memory, time) for agent processes.

    Example:
        tracker = ResourceTracker()
        # ... do work ...
        metrics = tracker.get_metrics()
        print(f"CPU: {metrics['cpu_percent']}%, Memory: {metrics['memory_mb']}MB")
    """

    def __init__(self) -> None:
        """Initialize resource tracker."""
        self._start_time = time.time()
        self._process = None

        if _HAS_PSUTIL:
            try:
                self._process = psutil.Process(os.getpid())
                # Initialize CPU percent (first call always returns 0.0)
                self._process.cpu_percent(interval=None)
            except (psutil.Error, OSError):
                self._process = None

    def get_metrics(self) -> ResourceMetrics:
        """
        Get current resource usage metrics.

        Returns:
            Dictionary with cpu_percent, memory_mb, memory_percent, elapsed_seconds
            Returns partial metrics if psutil unavailable or errors occur
        """
        metrics: ResourceMetrics = {}

        # Always track elapsed time (no dependencies)
        try:
            metrics["elapsed_seconds"] = time.time() - self._start_time
        except (OSError, ValueError):
            metrics["elapsed_seconds"] = 0.0

        # Track CPU and memory if psutil available
        if self._process is not None:
            try:
                # Get CPU percent (non-blocking)
                cpu = self._process.cpu_percent(interval=None)
                if cpu is not None and cpu >= 0:
                    metrics["cpu_percent"] = round(cpu, 1)
            except (psutil.Error, OSError, ValueError):
                pass

            try:
                # Get memory info
                mem_info = self._process.memory_info()
                memory_bytes = mem_info.rss
                memory_mb = memory_bytes / (1024 * 1024)
                metrics["memory_mb"] = round(memory_mb, 1)

                # Get memory percent if available
                mem_percent = self._process.memory_percent()
                if mem_percent is not None and mem_percent >= 0:
                    metrics["memory_percent"] = round(mem_percent, 1)
            except (psutil.Error, OSError, ValueError, AttributeError):
                pass

        return metrics

    def reset(self) -> None:
        """Reset the elapsed time counter."""
        self._start_time = time.time()
        if self._process is not None:
            try:
                # Reset CPU percent baseline
                self._process.cpu_percent(interval=None)
            except (psutil.Error, OSError):
                pass


# Global tracker instance for convenience
_global_tracker: ResourceTracker | None = None


def get_global_tracker() -> ResourceTracker:
    """
    Get or create global resource tracker instance.

    Returns:
        Shared ResourceTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ResourceTracker()
    return _global_tracker


def reset_global_tracker() -> None:
    """Reset the global resource tracker."""
    global _global_tracker
    if _global_tracker is not None:
        _global_tracker.reset()
    else:
        _global_tracker = ResourceTracker()
