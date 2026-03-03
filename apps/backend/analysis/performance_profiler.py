"""
Performance Profiler
====================

Analyzes runtime performance, memory usage, and identifies bottlenecks in Python code.
Provides performance metrics, optimization suggestions, and tracks improvements over time.

The performance profiler supports:
- Runtime profiling with cProfile
- Memory profiling with tracemalloc
- Bottleneck identification
- Performance trend tracking
- Optimization suggestions
- Before/after comparisons
"""

from __future__ import annotations

import cProfile
import io
import json
import logging
import pstats
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Top N functions to report in profiling results
TOP_FUNCTIONS_COUNT = 20

# Memory snapshot comparison threshold (bytes)
MEMORY_THRESHOLD_BYTES = 1024  # 1 KB

# Performance history file name
PERFORMANCE_HISTORY_FILE = "performance_history.json"

# Bottleneck thresholds
BOTTLENECK_TIME_THRESHOLD = 0.1  # seconds (100ms)
BOTTLENECK_MEMORY_THRESHOLD = 1024 * 1024  # 1 MB


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class FunctionProfile:
    """
    Performance profile for a single function.

    Attributes:
        name: Function name (module:function)
        calls: Number of times called
        total_time: Total time spent in function (seconds)
        cumulative_time: Cumulative time including subcalls (seconds)
        time_per_call: Average time per call (seconds)
        percent_time: Percentage of total execution time
    """

    name: str
    calls: int
    total_time: float
    cumulative_time: float
    time_per_call: float
    percent_time: float


@dataclass
class MemoryProfile:
    """
    Memory usage profile.

    Attributes:
        current_bytes: Current memory usage in bytes
        peak_bytes: Peak memory usage in bytes
        top_allocations: List of top memory allocations
        total_allocated: Total memory allocated during profiling
    """

    current_bytes: int
    peak_bytes: int
    top_allocations: list[dict[str, Any]] = field(default_factory=list)
    total_allocated: int = 0


@dataclass
class Bottleneck:
    """
    Identified performance bottleneck.

    Attributes:
        location: Function/location name
        type: Bottleneck type (runtime/memory)
        severity: Severity level (high/medium/low)
        metric: Metric value (time in seconds or memory in bytes)
        suggestion: Optimization suggestion
        impact: Estimated impact of fixing (high/medium/low)
    """

    location: str
    type: str  # "runtime" or "memory"
    severity: str  # "high", "medium", "low"
    metric: float  # seconds or bytes
    suggestion: str
    impact: str  # "high", "medium", "low"


@dataclass
class ProfileResult:
    """
    Complete profiling result.

    Attributes:
        timestamp: When profiling was performed
        duration: Total profiling duration (seconds)
        function_profiles: List of function performance profiles
        memory_profile: Memory usage profile
        bottlenecks: List of identified bottlenecks
        summary: Summary statistics
        suggestions: List of optimization suggestions
    """

    timestamp: str
    duration: float
    function_profiles: list[FunctionProfile] = field(default_factory=list)
    memory_profile: MemoryProfile | None = None
    bottlenecks: list[Bottleneck] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)


# =============================================================================
# PERFORMANCE PROFILER
# =============================================================================


class PerformanceProfiler:
    """
    Profiles Python code performance and identifies optimization opportunities.

    Supports:
    - Runtime profiling with cProfile
    - Memory profiling with tracemalloc
    - Bottleneck detection
    - Performance tracking over time
    - Optimization suggestions
    """

    def __init__(self, spec_dir: Path | str | None = None):
        """
        Initialize performance profiler.

        Args:
            spec_dir: Optional spec directory for storing performance history
        """
        self.spec_dir = Path(spec_dir) if spec_dir else None
        self._profiler: cProfile.Profile | None = None
        self._memory_tracking = False

    def start_profiling(self, enable_memory: bool = True) -> None:
        """
        Start performance profiling.

        Args:
            enable_memory: Whether to enable memory profiling
        """
        # Start wall-clock timer for accurate duration measurement
        self._start_time = time.perf_counter()

        # Start CPU profiling
        self._profiler = cProfile.Profile()
        self._profiler.enable()

        # Start memory profiling if requested
        if enable_memory:
            tracemalloc.start()
            self._memory_tracking = True

    def stop_profiling(self) -> ProfileResult:
        """
        Stop profiling and return results.

        Returns:
            ProfileResult with profiling data
        """
        # Stop wall-clock timer
        self._end_time = time.perf_counter()

        # Stop CPU profiling
        if self._profiler:
            self._profiler.disable()

        # Get function profiles
        function_profiles = self._extract_function_profiles()

        # Get memory profile
        memory_profile = None
        if self._memory_tracking:
            memory_profile = self._extract_memory_profile()
            tracemalloc.stop()
            self._memory_tracking = False

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(function_profiles, memory_profile)

        # Generate suggestions
        suggestions = self._generate_suggestions(bottlenecks)

        # Create result (use wall-clock time for duration, not sum of top N functions)
        wall_duration = (
            self._end_time - self._start_time
            if hasattr(self, "_end_time")
            else sum(fp.total_time for fp in function_profiles)
        )
        result = ProfileResult(
            timestamp=datetime.now(UTC).isoformat(),
            duration=round(wall_duration, 4),
            function_profiles=function_profiles,
            memory_profile=memory_profile,
            bottlenecks=bottlenecks,
            summary=self._create_summary(function_profiles, memory_profile),
            suggestions=suggestions,
        )

        # Save to history
        if self.spec_dir:
            self._save_to_history(result)

        return result

    def profile_function(
        self, func: Callable, *args, enable_memory: bool = True, **kwargs
    ) -> tuple[Any, ProfileResult]:
        """
        Profile a single function call.

        Args:
            func: Function to profile
            *args: Function arguments
            enable_memory: Whether to enable memory profiling
            **kwargs: Function keyword arguments

        Returns:
            Tuple of (function_result, profile_result)
        """
        self.start_profiling(enable_memory=enable_memory)

        try:
            result = func(*args, **kwargs)
        finally:
            profile = self.stop_profiling()

        return result, profile

    def _extract_function_profiles(self) -> list[FunctionProfile]:
        """Extract function performance profiles from cProfile data."""
        if not self._profiler:
            return []

        # Get stats
        stream = io.StringIO()
        stats = pstats.Stats(self._profiler, stream=stream)

        # Explicitly sort by cumulative time (pstats.sort_stats only affects printing,
        # not the dict order of stats.stats)
        sorted_items = sorted(
            stats.stats.items(),
            key=lambda kv: kv[1][3],  # ct (cumulative time)
            reverse=True,
        )

        # Extract top functions
        profiles = []
        total_time = sum(tt for (cc, nc, tt, ct, callers) in stats.stats.values())

        for func_key, (cc, nc, tt, ct, callers) in sorted_items[:TOP_FUNCTIONS_COUNT]:
            # Format function name
            filename, line, func_name = func_key
            if filename == "~":
                name = func_name
            else:
                name = f"{Path(filename).name}:{func_name}"

            # Calculate metrics
            time_per_call = tt / cc if cc > 0 else 0.0
            percent_time = (tt / total_time * 100) if total_time > 0 else 0.0

            profiles.append(
                FunctionProfile(
                    name=name,
                    calls=cc,
                    total_time=round(tt, 4),
                    cumulative_time=round(ct, 4),
                    time_per_call=round(time_per_call, 6),
                    percent_time=round(percent_time, 2),
                )
            )

        return profiles

    def _extract_memory_profile(self) -> MemoryProfile:
        """Extract memory usage profile from tracemalloc."""
        current, peak = tracemalloc.get_traced_memory()

        # Get top allocations
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")

        allocations = []
        total_allocated = 0

        for stat in top_stats[:TOP_FUNCTIONS_COUNT]:
            allocations.append(
                {
                    "file": str(stat.traceback.format()[0])
                    if stat.traceback
                    else "unknown",
                    "size_bytes": stat.size,
                    "size_mb": round(stat.size / (1024 * 1024), 2),
                    "count": stat.count,
                }
            )
            total_allocated += stat.size

        return MemoryProfile(
            current_bytes=current,
            peak_bytes=peak,
            top_allocations=allocations,
            total_allocated=total_allocated,
        )

    def _identify_bottlenecks(
        self,
        function_profiles: list[FunctionProfile],
        memory_profile: MemoryProfile | None,
    ) -> list[Bottleneck]:
        """Identify performance bottlenecks."""
        bottlenecks = []

        # Runtime bottlenecks
        for profile in function_profiles:
            if profile.total_time >= BOTTLENECK_TIME_THRESHOLD:
                severity = self._calculate_severity(
                    profile.total_time, BOTTLENECK_TIME_THRESHOLD
                )

                suggestion = self._suggest_runtime_optimization(profile)

                bottlenecks.append(
                    Bottleneck(
                        location=profile.name,
                        type="runtime",
                        severity=severity,
                        metric=profile.total_time,
                        suggestion=suggestion,
                        impact=severity,  # Impact matches severity for now
                    )
                )

        # Memory bottlenecks
        if memory_profile:
            for alloc in memory_profile.top_allocations:
                if alloc["size_bytes"] >= BOTTLENECK_MEMORY_THRESHOLD:
                    severity = self._calculate_severity(
                        alloc["size_bytes"], BOTTLENECK_MEMORY_THRESHOLD
                    )

                    bottlenecks.append(
                        Bottleneck(
                            location=alloc["file"],
                            type="memory",
                            severity=severity,
                            metric=alloc["size_bytes"],
                            suggestion=self._suggest_memory_optimization(alloc),
                            impact=severity,
                        )
                    )

        return bottlenecks

    def _calculate_severity(self, value: float, threshold: float) -> str:
        """Calculate severity level based on threshold multiplier."""
        multiplier = value / threshold

        if multiplier >= 10:
            return "high"
        elif multiplier >= 3:
            return "medium"
        else:
            return "low"

    def _suggest_runtime_optimization(self, profile: FunctionProfile) -> str:
        """Suggest runtime optimization for a function."""
        suggestions = []

        if profile.calls > 1000:
            suggestions.append("Consider caching or memoization")

        if profile.time_per_call > 0.01:
            suggestions.append(
                "Function is slow per call - review algorithm complexity"
            )

        if profile.percent_time > 20:
            suggestions.append(
                "Function dominates execution time - prioritize optimization"
            )

        return " | ".join(suggestions) if suggestions else "Review and optimize logic"

    def _suggest_memory_optimization(self, alloc: dict[str, Any]) -> str:
        """Suggest memory optimization."""
        size_mb = alloc["size_mb"]

        if size_mb > 100:
            return "Large allocation - consider streaming or chunking data"
        elif size_mb > 10:
            return "Moderate allocation - review data structures and cleanup"
        else:
            return "Small allocation - may be optimizable if called frequently"

    def _generate_suggestions(self, bottlenecks: list[Bottleneck]) -> list[str]:
        """Generate overall optimization suggestions."""
        suggestions = []

        # High severity bottlenecks
        high_severity = [b for b in bottlenecks if b.severity == "high"]
        if high_severity:
            suggestions.append(
                f"Found {len(high_severity)} high-severity bottlenecks - prioritize these"
            )

        # Runtime issues
        runtime_bottlenecks = [b for b in bottlenecks if b.type == "runtime"]
        if runtime_bottlenecks:
            suggestions.append(
                f"Runtime optimization needed in {len(runtime_bottlenecks)} locations"
            )

        # Memory issues
        memory_bottlenecks = [b for b in bottlenecks if b.type == "memory"]
        if memory_bottlenecks:
            suggestions.append(
                f"Memory optimization needed in {len(memory_bottlenecks)} locations"
            )

        if not bottlenecks:
            suggestions.append("No significant bottlenecks detected")

        return suggestions

    def _create_summary(
        self,
        function_profiles: list[FunctionProfile],
        memory_profile: MemoryProfile | None,
    ) -> dict[str, Any]:
        """Create summary statistics."""
        summary = {
            "total_functions": len(function_profiles),
            "total_calls": sum(fp.calls for fp in function_profiles),
            "total_time": round(sum(fp.total_time for fp in function_profiles), 4),
        }

        if function_profiles:
            summary["slowest_function"] = function_profiles[0].name
            summary["slowest_time"] = function_profiles[0].total_time

        if memory_profile:
            summary["peak_memory_mb"] = round(
                memory_profile.peak_bytes / (1024 * 1024), 2
            )
            summary["current_memory_mb"] = round(
                memory_profile.current_bytes / (1024 * 1024), 2
            )

        return summary

    def _save_to_history(self, result: ProfileResult) -> None:
        """Save profiling result to history file."""
        if not self.spec_dir:
            return

        history_file = self.spec_dir / PERFORMANCE_HISTORY_FILE

        # Load existing history
        history: list[dict[str, Any]] = []
        if history_file.exists():
            try:
                with open(history_file, encoding="utf-8") as f:
                    history = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Failed to read existing performance history '%s': %s",
                    history_file,
                    exc,
                )
                history = []

        # Add new result (convert to dict)
        history.append(self._result_to_dict(result))

        # Save updated history
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except OSError as exc:
            logger.warning(
                "Failed to write performance history '%s': %s",
                history_file,
                exc,
            )

    def _result_to_dict(self, result: ProfileResult) -> dict[str, Any]:
        """Convert ProfileResult to dictionary."""
        return {
            "timestamp": result.timestamp,
            "duration": result.duration,
            "function_profiles": [
                {
                    "name": fp.name,
                    "calls": fp.calls,
                    "total_time": fp.total_time,
                    "cumulative_time": fp.cumulative_time,
                    "time_per_call": fp.time_per_call,
                    "percent_time": fp.percent_time,
                }
                for fp in result.function_profiles
            ],
            "memory_profile": (
                {
                    "current_bytes": result.memory_profile.current_bytes,
                    "peak_bytes": result.memory_profile.peak_bytes,
                    "total_allocated": result.memory_profile.total_allocated,
                    "top_allocations": result.memory_profile.top_allocations,
                }
                if result.memory_profile
                else None
            ),
            "bottlenecks": [
                {
                    "location": b.location,
                    "type": b.type,
                    "severity": b.severity,
                    "metric": b.metric,
                    "suggestion": b.suggestion,
                    "impact": b.impact,
                }
                for b in result.bottlenecks
            ],
            "summary": result.summary,
            "suggestions": result.suggestions,
        }

    def get_performance_history(self) -> list[dict[str, Any]]:
        """
        Get performance profiling history.

        Returns:
            List of historical profiling results
        """
        if not self.spec_dir:
            return []

        history_file = self.spec_dir / PERFORMANCE_HISTORY_FILE

        if not history_file.exists():
            return []

        try:
            with open(history_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return []

    def compare_results(
        self, before: ProfileResult, after: ProfileResult
    ) -> dict[str, Any]:
        """
        Compare two profiling results (before/after optimization).

        Args:
            before: Profile before optimization
            after: Profile after optimization

        Returns:
            Comparison metrics showing improvement
        """
        comparison = {
            "runtime_improvement": 0.0,
            "memory_improvement": 0.0,
            "bottlenecks_fixed": 0,
            "overall_improvement": "none",
        }

        # Runtime comparison
        before_time = before.duration
        after_time = after.duration

        if before_time > 0:
            runtime_improvement = (before_time - after_time) / before_time * 100
            comparison["runtime_improvement"] = round(runtime_improvement, 2)

        # Memory comparison
        if before.memory_profile and after.memory_profile:
            before_mem = before.memory_profile.peak_bytes
            after_mem = after.memory_profile.peak_bytes

            if before_mem > 0:
                memory_improvement = (before_mem - after_mem) / before_mem * 100
                comparison["memory_improvement"] = round(memory_improvement, 2)

        # Bottlenecks comparison
        before_bottlenecks = len(before.bottlenecks)
        after_bottlenecks = len(after.bottlenecks)
        comparison["bottlenecks_fixed"] = max(0, before_bottlenecks - after_bottlenecks)

        # Overall assessment
        if (
            comparison["runtime_improvement"] > 10
            or comparison["memory_improvement"] > 10
        ):
            comparison["overall_improvement"] = "significant"
        elif (
            comparison["runtime_improvement"] > 5
            or comparison["memory_improvement"] > 5
        ):
            comparison["overall_improvement"] = "moderate"
        elif (
            comparison["runtime_improvement"] > 0
            or comparison["memory_improvement"] > 0
        ):
            comparison["overall_improvement"] = "minor"

        return comparison


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def profile_code_string(code: str, enable_memory: bool = True) -> ProfileResult:
    """
    Profile a code string.

    WARNING: This executes arbitrary Python code via exec(). Callers are
    responsible for ensuring ``code`` is trusted. The code is executed in
    an isolated namespace to prevent mutation of the module's global state.

    Args:
        code: Python code to profile (must be trusted)
        enable_memory: Whether to enable memory profiling

    Returns:
        ProfileResult with profiling data
    """
    profiler = PerformanceProfiler()
    profiler.start_profiling(enable_memory=enable_memory)

    try:
        # Execute in isolated namespace to prevent global state mutation
        exec_globals: dict[str, Any] = {
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }
        exec_locals: dict[str, Any] = {}
        exec(code, exec_globals, exec_locals)  # noqa: S102
    finally:
        result = profiler.stop_profiling()

    return result


def get_performance_trends(spec_dir: Path | str) -> dict[str, Any]:
    """
    Analyze performance trends over time.

    Args:
        spec_dir: Spec directory with performance history

    Returns:
        Trend analysis with improvement metrics
    """
    profiler = PerformanceProfiler(spec_dir)
    history = profiler.get_performance_history()

    if len(history) < 2:
        return {
            "trend": "insufficient_data",
            "data_points": len(history),
            "message": "Need at least 2 profiling runs to analyze trends",
        }

    # Calculate trends
    runtimes = [r["duration"] for r in history]
    memories = [
        r["memory_profile"]["peak_bytes"] for r in history if r.get("memory_profile")
    ]

    trends = {
        "trend": "stable",
        "data_points": len(history),
        "runtime_trend": "stable",
        "memory_trend": "stable" if memories else "no_data",
    }

    # Runtime trend
    if len(runtimes) >= 2:
        first_half_avg = sum(runtimes[: len(runtimes) // 2]) / (len(runtimes) // 2)
        second_half_avg = sum(runtimes[len(runtimes) // 2 :]) / (
            len(runtimes) - len(runtimes) // 2
        )

        if second_half_avg < first_half_avg * 0.9:
            trends["runtime_trend"] = "improving"
        elif second_half_avg > first_half_avg * 1.1:
            trends["runtime_trend"] = "declining"

    # Memory trend
    if len(memories) >= 2:
        first_half_avg = sum(memories[: len(memories) // 2]) / (len(memories) // 2)
        second_half_avg = sum(memories[len(memories) // 2 :]) / (
            len(memories) - len(memories) // 2
        )

        if second_half_avg < first_half_avg * 0.9:
            trends["memory_trend"] = "improving"
        elif second_half_avg > first_half_avg * 1.1:
            trends["memory_trend"] = "declining"

    # Overall trend
    if trends["runtime_trend"] == "improving" or trends["memory_trend"] == "improving":
        trends["trend"] = "improving"
    elif (
        trends["runtime_trend"] == "declining" or trends["memory_trend"] == "declining"
    ):
        trends["trend"] = "declining"

    return trends
