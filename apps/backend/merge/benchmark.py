"""
Merge Benchmark Comparison
===========================

Compares semantic merge resolution accuracy against text-only baseline.

This module provides:
- Benchmark data structures for tracking semantic vs text-only merges
- Comparison metrics to measure accuracy improvement
- Statistical analysis to validate the 40% improvement target
- Storage and retrieval of benchmark results
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .types import MergeDecision, MergeResult

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """
    Result from a single benchmark comparison.

    Compares semantic merge outcome against text-only baseline
    for a specific file or merge operation.
    """

    # Identification
    benchmark_id: str  # Unique identifier
    file_path: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Semantic merge outcome
    semantic_decision: MergeDecision = MergeDecision.NEEDS_HUMAN_REVIEW
    semantic_conflicts_resolved: int = 0
    semantic_conflicts_remaining: int = 0
    semantic_ai_calls: int = 0
    semantic_success: bool = False

    # Text-only baseline outcome (standard git merge)
    textual_conflicts_detected: int = 0
    textual_conflicts_remaining: int = 0
    textual_success: bool = False

    # Accuracy metrics
    accuracy_improvement: float = 0.0  # Percentage improvement (0.0 to 1.0+)
    conflicts_avoided: int = 0  # How many conflicts semantic avoided
    resolution_quality_score: float = 0.0  # 0.0 to 1.0

    # Additional context
    merge_strategy_used: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "benchmark_id": self.benchmark_id,
            "file_path": self.file_path,
            "timestamp": self.timestamp.isoformat(),
            "semantic_decision": self.semantic_decision.value,
            "semantic_conflicts_resolved": self.semantic_conflicts_resolved,
            "semantic_conflicts_remaining": self.semantic_conflicts_remaining,
            "semantic_ai_calls": self.semantic_ai_calls,
            "semantic_success": self.semantic_success,
            "textual_conflicts_detected": self.textual_conflicts_detected,
            "textual_conflicts_remaining": self.textual_conflicts_remaining,
            "textual_success": self.textual_success,
            "accuracy_improvement": self.accuracy_improvement,
            "conflicts_avoided": self.conflicts_avoided,
            "resolution_quality_score": self.resolution_quality_score,
            "merge_strategy_used": self.merge_strategy_used,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkResult:
        """Create from dictionary."""
        return cls(
            benchmark_id=data["benchmark_id"],
            file_path=data["file_path"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            semantic_decision=MergeDecision(data["semantic_decision"]),
            semantic_conflicts_resolved=data.get("semantic_conflicts_resolved", 0),
            semantic_conflicts_remaining=data.get("semantic_conflicts_remaining", 0),
            semantic_ai_calls=data.get("semantic_ai_calls", 0),
            semantic_success=data.get("semantic_success", False),
            textual_conflicts_detected=data.get("textual_conflicts_detected", 0),
            textual_conflicts_remaining=data.get("textual_conflicts_remaining", 0),
            textual_success=data.get("textual_success", False),
            accuracy_improvement=data.get("accuracy_improvement", 0.0),
            conflicts_avoided=data.get("conflicts_avoided", 0),
            resolution_quality_score=data.get("resolution_quality_score", 0.0),
            merge_strategy_used=data.get("merge_strategy_used", ""),
            notes=data.get("notes", ""),
        )

    @property
    def improvement_percentage(self) -> float:
        """Get accuracy improvement as a percentage (0-100+)."""
        return self.accuracy_improvement * 100.0


@dataclass
class BenchmarkSummary:
    """
    Aggregated benchmark statistics across multiple comparisons.

    Provides overall metrics for semantic vs text-only merge performance.
    """

    # Time period
    period_start: datetime
    period_end: datetime

    # Overall metrics
    total_benchmarks: int = 0
    files_benchmarked: list[str] = field(default_factory=list)

    # Semantic merge performance
    semantic_successes: int = 0
    semantic_failures: int = 0
    total_semantic_conflicts_resolved: int = 0
    total_semantic_conflicts_remaining: int = 0

    # Text-only baseline performance
    textual_successes: int = 0
    textual_failures: int = 0
    total_textual_conflicts: int = 0

    # Accuracy comparison
    average_accuracy_improvement: float = 0.0
    median_accuracy_improvement: float = 0.0
    min_accuracy_improvement: float = 0.0
    max_accuracy_improvement: float = 0.0
    total_conflicts_avoided: int = 0

    # Target validation
    meets_40_percent_target: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_benchmarks": self.total_benchmarks,
            "files_benchmarked": self.files_benchmarked,
            "semantic_successes": self.semantic_successes,
            "semantic_failures": self.semantic_failures,
            "total_semantic_conflicts_resolved": self.total_semantic_conflicts_resolved,
            "total_semantic_conflicts_remaining": self.total_semantic_conflicts_remaining,
            "textual_successes": self.textual_successes,
            "textual_failures": self.textual_failures,
            "total_textual_conflicts": self.total_textual_conflicts,
            "average_accuracy_improvement": self.average_accuracy_improvement,
            "median_accuracy_improvement": self.median_accuracy_improvement,
            "min_accuracy_improvement": self.min_accuracy_improvement,
            "max_accuracy_improvement": self.max_accuracy_improvement,
            "total_conflicts_avoided": self.total_conflicts_avoided,
            "meets_40_percent_target": self.meets_40_percent_target,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkSummary:
        """Create from dictionary."""
        return cls(
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
            total_benchmarks=data.get("total_benchmarks", 0),
            files_benchmarked=data.get("files_benchmarked", []),
            semantic_successes=data.get("semantic_successes", 0),
            semantic_failures=data.get("semantic_failures", 0),
            total_semantic_conflicts_resolved=data.get(
                "total_semantic_conflicts_resolved", 0
            ),
            total_semantic_conflicts_remaining=data.get(
                "total_semantic_conflicts_remaining", 0
            ),
            textual_successes=data.get("textual_successes", 0),
            textual_failures=data.get("textual_failures", 0),
            total_textual_conflicts=data.get("total_textual_conflicts", 0),
            average_accuracy_improvement=data.get("average_accuracy_improvement", 0.0),
            median_accuracy_improvement=data.get("median_accuracy_improvement", 0.0),
            min_accuracy_improvement=data.get("min_accuracy_improvement", 0.0),
            max_accuracy_improvement=data.get("max_accuracy_improvement", 0.0),
            total_conflicts_avoided=data.get("total_conflicts_avoided", 0),
            meets_40_percent_target=data.get("meets_40_percent_target", False),
        )

    @property
    def semantic_success_rate(self) -> float:
        """Calculate semantic merge success rate (0.0 to 1.0)."""
        if self.total_benchmarks == 0:
            return 0.0
        return self.semantic_successes / self.total_benchmarks

    @property
    def textual_success_rate(self) -> float:
        """Calculate text-only baseline success rate (0.0 to 1.0)."""
        if self.total_benchmarks == 0:
            return 0.0
        return self.textual_successes / self.total_benchmarks

    @property
    def improvement_percentage(self) -> float:
        """Get average improvement as percentage (0-100+)."""
        return self.average_accuracy_improvement * 100.0


def calculate_accuracy_improvement(
    semantic_result: MergeResult, textual_conflicts: int
) -> float:
    """
    Calculate accuracy improvement from semantic vs text-only merge.

    Accuracy improvement is measured as the reduction in conflicts that
    require human intervention.

    Args:
        semantic_result: The result from semantic merge
        textual_conflicts: Number of conflicts from text-only merge

    Returns:
        Accuracy improvement as float (0.0 to 1.0+)
        - 0.0 = no improvement
        - 0.4 = 40% improvement (target)
        - 1.0 = 100% improvement (perfect)
    """
    # Text-only baseline: how many conflicts need manual resolution
    if textual_conflicts == 0:
        # No conflicts to begin with, semantic merge doesn't help
        return 0.0

    # Semantic approach: how many conflicts still need manual review
    semantic_remaining = len(semantic_result.conflicts_remaining)

    # Calculate improvement: (baseline - semantic) / baseline
    conflicts_avoided = textual_conflicts - semantic_remaining
    improvement = conflicts_avoided / textual_conflicts

    return max(0.0, improvement)  # Ensure non-negative


def compare_semantic_vs_textual(
    semantic_result: MergeResult, textual_conflicts: int, file_path: str
) -> BenchmarkResult:
    """
    Compare semantic merge result against text-only baseline.

    Creates a benchmark result that tracks the performance difference
    between semantic merge and standard git merge.

    Args:
        semantic_result: Result from semantic merge operation
        textual_conflicts: Number of conflicts from standard git merge
        file_path: Path to the file being merged

    Returns:
        BenchmarkResult with comparison metrics
    """
    # Generate unique benchmark ID
    benchmark_id = (
        f"bench_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    )

    # Calculate accuracy improvement
    accuracy_improvement = calculate_accuracy_improvement(
        semantic_result, textual_conflicts
    )

    # Determine conflicts avoided
    semantic_remaining = len(semantic_result.conflicts_remaining)
    conflicts_avoided = max(0, textual_conflicts - semantic_remaining)

    # Calculate resolution quality score (0.0 to 1.0)
    # Based on how well semantic merge resolved conflicts
    total_conflicts = len(semantic_result.conflicts_resolved) + len(
        semantic_result.conflicts_remaining
    )
    if total_conflicts > 0:
        quality_score = len(semantic_result.conflicts_resolved) / total_conflicts
    else:
        quality_score = 1.0  # No conflicts = perfect

    # Determine success status
    semantic_success = semantic_result.decision in {
        MergeDecision.AUTO_MERGED,
        MergeDecision.AI_MERGED,
    }
    textual_success = textual_conflicts == 0

    return BenchmarkResult(
        benchmark_id=benchmark_id,
        file_path=file_path,
        timestamp=datetime.now(),
        semantic_decision=semantic_result.decision,
        semantic_conflicts_resolved=len(semantic_result.conflicts_resolved),
        semantic_conflicts_remaining=len(semantic_result.conflicts_remaining),
        semantic_ai_calls=semantic_result.ai_calls_made,
        semantic_success=semantic_success,
        textual_conflicts_detected=textual_conflicts,
        textual_conflicts_remaining=textual_conflicts,
        textual_success=textual_success,
        accuracy_improvement=accuracy_improvement,
        conflicts_avoided=conflicts_avoided,
        resolution_quality_score=quality_score,
        merge_strategy_used="semantic",
        notes=semantic_result.explanation,
    )


def aggregate_benchmark_results(
    results: list[BenchmarkResult],
) -> BenchmarkSummary:
    """
    Aggregate multiple benchmark results into summary statistics.

    Args:
        results: List of benchmark results to aggregate

    Returns:
        BenchmarkSummary with aggregated metrics
    """
    if not results:
        # Return empty summary
        now = datetime.now()
        return BenchmarkSummary(period_start=now, period_end=now)

    # Determine time period
    timestamps = [r.timestamp for r in results]
    period_start = min(timestamps)
    period_end = max(timestamps)

    # Count successes and failures
    semantic_successes = sum(1 for r in results if r.semantic_success)
    semantic_failures = len(results) - semantic_successes
    textual_successes = sum(1 for r in results if r.textual_success)
    textual_failures = len(results) - textual_successes

    # Aggregate conflicts
    total_semantic_resolved = sum(r.semantic_conflicts_resolved for r in results)
    total_semantic_remaining = sum(r.semantic_conflicts_remaining for r in results)
    total_textual_conflicts = sum(r.textual_conflicts_detected for r in results)
    total_conflicts_avoided = sum(r.conflicts_avoided for r in results)

    # Calculate accuracy improvements
    improvements = [r.accuracy_improvement for r in results]
    average_improvement = sum(improvements) / len(improvements)
    sorted_improvements = sorted(improvements)
    median_improvement = sorted_improvements[len(sorted_improvements) // 2]
    min_improvement = min(improvements)
    max_improvement = max(improvements)

    # Check if meets 40% target
    meets_target = average_improvement >= 0.4

    return BenchmarkSummary(
        period_start=period_start,
        period_end=period_end,
        total_benchmarks=len(results),
        files_benchmarked=[r.file_path for r in results],
        semantic_successes=semantic_successes,
        semantic_failures=semantic_failures,
        total_semantic_conflicts_resolved=total_semantic_resolved,
        total_semantic_conflicts_remaining=total_semantic_remaining,
        textual_successes=textual_successes,
        textual_failures=textual_failures,
        total_textual_conflicts=total_textual_conflicts,
        average_accuracy_improvement=average_improvement,
        median_accuracy_improvement=median_improvement,
        min_accuracy_improvement=min_improvement,
        max_accuracy_improvement=max_improvement,
        total_conflicts_avoided=total_conflicts_avoided,
        meets_40_percent_target=meets_target,
    )


class BenchmarkStore:
    """
    Persistent storage for benchmark results.

    Responsibilities:
    - Save benchmark results to disk
    - Load historical benchmark data
    - Generate aggregate summaries
    """

    def __init__(self, storage_dir: Path | str):
        """
        Initialize benchmark storage.

        Args:
            storage_dir: Directory for benchmark data (.auto-claude/)
        """
        self.storage_dir = Path(storage_dir).resolve()
        self.benchmarks_dir = self.storage_dir / "benchmarks"
        self.results_file = self.benchmarks_dir / "results.json"
        self.summary_file = self.benchmarks_dir / "summary.json"

        # Ensure directories exist
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)

    def save_result(self, result: BenchmarkResult) -> None:
        """
        Save a benchmark result to storage.

        Args:
            result: Benchmark result to save
        """
        # Load existing results
        results = self.load_all_results()

        # Append new result
        results.append(result)

        # Save back to disk
        self._write_results(results)

        # Update summary
        summary = aggregate_benchmark_results(results)
        self._write_summary(summary)

        logger.info(
            f"Saved benchmark result {result.benchmark_id} "
            f"(improvement: {result.improvement_percentage:.1f}%)"
        )

    def load_all_results(self) -> list[BenchmarkResult]:
        """
        Load all benchmark results from storage.

        Returns:
            List of benchmark results (empty if no results exist)
        """
        if not self.results_file.exists():
            return []

        try:
            with open(self.results_file, encoding="utf-8") as f:
                data = json.load(f)
                return [BenchmarkResult.from_dict(r) for r in data]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load benchmark results: {e}")
            return []

    def load_summary(self) -> BenchmarkSummary | None:
        """
        Load the current benchmark summary.

        Returns:
            BenchmarkSummary if available, None otherwise
        """
        if not self.summary_file.exists():
            return None

        try:
            with open(self.summary_file, encoding="utf-8") as f:
                data = json.load(f)
                return BenchmarkSummary.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load benchmark summary: {e}")
            return None

    def clear_results(self) -> None:
        """Clear all benchmark results and summary."""
        if self.results_file.exists():
            self.results_file.unlink()
        if self.summary_file.exists():
            self.summary_file.unlink()
        logger.info("Cleared all benchmark results")

    def _write_results(self, results: list[BenchmarkResult]) -> None:
        """Write results to disk."""
        with open(self.results_file, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, indent=2)

    def _write_summary(self, summary: BenchmarkSummary) -> None:
        """Write summary to disk."""
        with open(self.summary_file, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)
