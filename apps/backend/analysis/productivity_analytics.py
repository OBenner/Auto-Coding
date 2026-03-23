"""
Productivity Analytics Aggregator
==================================

Aggregates productivity metrics across all specs to provide insights into
Auto-Claude's value and effectiveness.

Provides analytics on:
- Total specs completed
- Time saved through automation
- Success rates and trends
- Breakdown by complexity and type
- Export functionality for external analysis
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from analysis.analytics_utils import (
    normalize_boundary,
    parse_timestamp,
)

# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SpecMetrics:
    """
    Metrics for a single spec.

    Captures key performance indicators for one build.
    """

    spec_id: str
    spec_name: str
    workflow_type: str = "feature"  # feature, bug, refactor, etc.
    complexity: str = "standard"  # simple, standard, complex
    status: str = "pending"  # pending, in_progress, completed, failed

    # Time tracking
    created_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    # Subtask metrics
    total_subtasks: int = 0
    completed_subtasks: int = 0
    failed_subtasks: int = 0

    # QA metrics
    qa_iterations: int = 0
    qa_status: str = "pending"

    # Session metrics
    unique_sessions: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "spec_id": self.spec_id,
            "spec_name": self.spec_name,
            "workflow_type": self.workflow_type,
            "complexity": self.complexity,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_seconds": self.duration_seconds,
            "total_subtasks": self.total_subtasks,
            "completed_subtasks": self.completed_subtasks,
            "failed_subtasks": self.failed_subtasks,
            "qa_iterations": self.qa_iterations,
            "qa_status": self.qa_status,
            "unique_sessions": self.unique_sessions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecMetrics:
        """Create from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            spec_name=data["spec_name"],
            workflow_type=data.get("workflow_type", "feature"),
            complexity=data.get("complexity", "standard"),
            status=data.get("status", "pending"),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            duration_seconds=data.get("duration_seconds", 0.0),
            total_subtasks=data.get("total_subtasks", 0),
            completed_subtasks=data.get("completed_subtasks", 0),
            failed_subtasks=data.get("failed_subtasks", 0),
            qa_iterations=data.get("qa_iterations", 0),
            qa_status=data.get("qa_status", "pending"),
            unique_sessions=data.get("unique_sessions", 0),
        )

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate (0.0 to 1.0)."""
        if self.total_subtasks == 0:
            return 0.0
        return self.completed_subtasks / self.total_subtasks

    @property
    def is_completed(self) -> bool:
        """Check if spec is completed."""
        return self.status == "completed" or (
            self.total_subtasks > 0
            and self.completed_subtasks == self.total_subtasks
            and self.qa_status == "approved"
        )


@dataclass
class ProductivitySummary:
    """
    Aggregated productivity metrics across all specs.

    Provides high-level insights into Auto-Claude's effectiveness.
    """

    # Time period
    period_start: datetime
    period_end: datetime

    # Overall metrics
    total_specs: int = 0
    completed_specs: int = 0
    in_progress_specs: int = 0
    failed_specs: int = 0

    # Time savings (estimated)
    total_time_saved_hours: float = 0.0
    total_build_time_hours: float = 0.0

    # Success metrics
    average_success_rate: float = 0.0
    first_attempt_success_rate: float = 0.0

    # Breakdown by type
    specs_by_type: dict[str, int] = field(default_factory=dict)
    specs_by_complexity: dict[str, int] = field(default_factory=dict)

    # Productivity metrics
    average_subtasks_per_spec: float = 0.0
    average_qa_iterations: float = 0.0
    total_subtasks_completed: int = 0

    # Detailed spec list
    specs: list[SpecMetrics] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_specs": self.total_specs,
            "completed_specs": self.completed_specs,
            "in_progress_specs": self.in_progress_specs,
            "failed_specs": self.failed_specs,
            "total_time_saved_hours": round(self.total_time_saved_hours, 2),
            "total_build_time_hours": round(self.total_build_time_hours, 2),
            "average_success_rate": round(self.average_success_rate, 3),
            "first_attempt_success_rate": round(self.first_attempt_success_rate, 3),
            "specs_by_type": self.specs_by_type,
            "specs_by_complexity": self.specs_by_complexity,
            "average_subtasks_per_spec": round(self.average_subtasks_per_spec, 1),
            "average_qa_iterations": round(self.average_qa_iterations, 1),
            "total_subtasks_completed": self.total_subtasks_completed,
            "specs": [spec.to_dict() for spec in self.specs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductivitySummary:
        """Create from dictionary."""
        return cls(
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
            total_specs=data.get("total_specs", 0),
            completed_specs=data.get("completed_specs", 0),
            in_progress_specs=data.get("in_progress_specs", 0),
            failed_specs=data.get("failed_specs", 0),
            total_time_saved_hours=data.get("total_time_saved_hours", 0.0),
            total_build_time_hours=data.get("total_build_time_hours", 0.0),
            average_success_rate=data.get("average_success_rate", 0.0),
            first_attempt_success_rate=data.get("first_attempt_success_rate", 0.0),
            specs_by_type=data.get("specs_by_type", {}),
            specs_by_complexity=data.get("specs_by_complexity", {}),
            average_subtasks_per_spec=data.get("average_subtasks_per_spec", 0.0),
            average_qa_iterations=data.get("average_qa_iterations", 0.0),
            total_subtasks_completed=data.get("total_subtasks_completed", 0),
            specs=[SpecMetrics.from_dict(s) for s in data.get("specs", [])],
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


_parse_timestamp = parse_timestamp
_normalize_boundary = normalize_boundary


def _count_unique_sessions(plan: dict[str, Any]) -> int:
    """
    Count unique session IDs across all subtasks.

    Args:
        plan: Implementation plan dict

    Returns:
        Number of unique sessions
    """
    session_ids = set()

    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            session_id = subtask.get("session_id")
            if session_id:
                session_ids.add(session_id)

    return len(session_ids)


def _estimate_time_saved(spec_metrics: SpecMetrics) -> float:
    """
    Estimate time saved by AI automation (in hours).

    Uses industry benchmarks:
    - Simple spec: ~2-4 hours manual work
    - Standard spec: ~8-16 hours manual work
    - Complex spec: ~24-40 hours manual work

    Returns conservative estimate based on completed subtasks.

    Args:
        spec_metrics: Spec metrics

    Returns:
        Estimated time saved in hours
    """
    # Time estimates per subtask (hours) based on complexity
    time_per_subtask = {
        "simple": 0.5,  # 30 minutes per subtask
        "standard": 1.5,  # 1.5 hours per subtask
        "complex": 3.0,  # 3 hours per subtask
    }

    subtask_time = time_per_subtask.get(spec_metrics.complexity, 1.5)

    # Conservative estimate: only count completed subtasks
    estimated_manual_hours = spec_metrics.completed_subtasks * subtask_time

    # AI build time
    ai_build_hours = spec_metrics.duration_seconds / 3600

    # Time saved = manual time - AI time (but never negative)
    return max(0.0, estimated_manual_hours - ai_build_hours)


def _extract_spec_metrics(spec_dir: Path) -> SpecMetrics | None:
    """
    Extract metrics from a single spec directory.

    Args:
        spec_dir: Path to spec directory

    Returns:
        SpecMetrics object or None if invalid
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return None

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        # Extract basic info
        spec_id = spec_dir.name
        spec_name = plan.get("feature", spec_id)
        workflow_type = plan.get("workflow_type", "feature")

        # Determine complexity from plan or spec metadata
        complexity = "standard"  # default
        # Try to infer from subtask count
        total_subtasks = sum(
            len(phase.get("subtasks", [])) for phase in plan.get("phases", [])
        )
        if total_subtasks <= 3:
            complexity = "simple"
        elif total_subtasks >= 10:
            complexity = "complex"

        # Count subtasks by status
        completed_subtasks = 0
        failed_subtasks = 0
        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                status = subtask.get("status", "pending")
                if status == "completed":
                    completed_subtasks += 1
                elif status == "failed":
                    failed_subtasks += 1

        # Determine overall status
        plan_status = plan.get("status", "pending")
        if plan_status == "completed" or (
            total_subtasks > 0 and completed_subtasks == total_subtasks
        ):
            status = "completed"
        elif completed_subtasks > 0 or any(
            subtask.get("status") == "in_progress"
            for phase in plan.get("phases", [])
            for subtask in phase.get("subtasks", [])
        ):
            status = "in_progress"
        else:
            status = "pending"

        # Time tracking
        created_at = _parse_timestamp(plan.get("created_at"))
        updated_at = _parse_timestamp(plan.get("updated_at"))

        # Calculate duration
        completed_at = None
        duration_seconds = 0.0
        if created_at:
            if status == "completed" and updated_at:
                completed_at = updated_at
                duration_seconds = (completed_at - created_at).total_seconds()
            elif status == "in_progress":
                # In-progress: duration so far
                duration_seconds = (datetime.now(UTC) - created_at).total_seconds()

        # QA metrics
        qa_signoff = plan.get("qa_signoff") or {}
        qa_iterations = qa_signoff.get("qa_session", 0)
        qa_status = qa_signoff.get("status", "pending")

        # Session count
        unique_sessions = _count_unique_sessions(plan)

        return SpecMetrics(
            spec_id=spec_id,
            spec_name=spec_name,
            workflow_type=workflow_type,
            complexity=complexity,
            status=status,
            created_at=created_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            total_subtasks=total_subtasks,
            completed_subtasks=completed_subtasks,
            failed_subtasks=failed_subtasks,
            qa_iterations=qa_iterations,
            qa_status=qa_status,
            unique_sessions=unique_sessions,
        )

    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


# =============================================================================
# PUBLIC API
# =============================================================================


def aggregate_productivity_metrics(
    project_dir: Path,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ProductivitySummary:
    """
    Aggregate productivity metrics across all specs.

    Args:
        project_dir: Path to project root
        start_date: Optional start date filter (inclusive)
        end_date: Optional end date filter (inclusive)

    Returns:
        ProductivitySummary with aggregated metrics
    """
    # Normalize boundaries to UTC-aware datetimes to avoid naive/aware comparison
    start_date = _normalize_boundary(start_date)
    end_date = _normalize_boundary(end_date)

    # Locate specs directory
    specs_dir = project_dir / ".auto-claude" / "specs"
    if not specs_dir.exists():
        # Return empty summary
        return ProductivitySummary(
            period_start=start_date or datetime.now(UTC),
            period_end=end_date or datetime.now(UTC),
        )

    # Collect all spec metrics
    all_specs: list[SpecMetrics] = []
    for spec_dir in specs_dir.iterdir():
        if not spec_dir.is_dir():
            continue

        spec_metrics = _extract_spec_metrics(spec_dir)
        if not spec_metrics:
            continue

        # Apply date filters
        if (
            start_date
            and spec_metrics.created_at
            and spec_metrics.created_at < start_date
        ):
            continue
        if end_date and spec_metrics.created_at and spec_metrics.created_at > end_date:
            continue

        all_specs.append(spec_metrics)

    # Determine period
    if not all_specs:
        period_start = start_date or datetime.now(UTC)
        period_end = end_date or datetime.now(UTC)
    else:
        spec_dates = [s.created_at for s in all_specs if s.created_at]
        if spec_dates:
            period_start = start_date or min(spec_dates)
            period_end = end_date or max(spec_dates)
        else:
            period_start = start_date or datetime.now(UTC)
            period_end = end_date or datetime.now(UTC)

    # Calculate aggregate metrics
    total_specs = len(all_specs)
    completed_specs = sum(1 for s in all_specs if s.is_completed)
    in_progress_specs = sum(1 for s in all_specs if s.status == "in_progress")
    failed_specs = sum(1 for s in all_specs if s.status == "failed")

    # Time savings
    total_time_saved_hours = sum(_estimate_time_saved(s) for s in all_specs)
    total_build_time_hours = sum(s.duration_seconds / 3600 for s in all_specs)

    # Success rates
    if completed_specs > 0:
        # First attempt success: QA approved on first iteration
        first_attempt_success = sum(
            1 for s in all_specs if s.is_completed and s.qa_iterations <= 1
        )
        first_attempt_success_rate = first_attempt_success / completed_specs
    else:
        first_attempt_success_rate = 0.0

    if total_specs > 0:
        average_success_rate = completed_specs / total_specs
    else:
        average_success_rate = 0.0

    # Breakdowns
    specs_by_type: dict[str, int] = defaultdict(int)
    specs_by_complexity: dict[str, int] = defaultdict(int)
    for spec in all_specs:
        specs_by_type[spec.workflow_type] += 1
        specs_by_complexity[spec.complexity] += 1

    # Productivity metrics
    total_subtasks_completed = sum(s.completed_subtasks for s in all_specs)
    average_subtasks_per_spec = (
        total_subtasks_completed / total_specs if total_specs > 0 else 0.0
    )

    total_qa_iterations = sum(s.qa_iterations for s in all_specs)
    average_qa_iterations = (
        total_qa_iterations / completed_specs if completed_specs > 0 else 0.0
    )

    return ProductivitySummary(
        period_start=period_start,
        period_end=period_end,
        total_specs=total_specs,
        completed_specs=completed_specs,
        in_progress_specs=in_progress_specs,
        failed_specs=failed_specs,
        total_time_saved_hours=total_time_saved_hours,
        total_build_time_hours=total_build_time_hours,
        average_success_rate=average_success_rate,
        first_attempt_success_rate=first_attempt_success_rate,
        specs_by_type=dict(specs_by_type),
        specs_by_complexity=dict(specs_by_complexity),
        average_subtasks_per_spec=average_subtasks_per_spec,
        average_qa_iterations=average_qa_iterations,
        total_subtasks_completed=total_subtasks_completed,
        specs=all_specs,
    )


def get_productivity_trends(
    project_dir: Path, window_days: int = 30, granularity: str = "daily"
) -> list[dict[str, Any]]:
    """
    Get productivity trends over time.

    Args:
        project_dir: Path to project root
        window_days: Number of days to look back
        granularity: Time granularity - "daily", "weekly", or "monthly"

    Returns:
        List of time-series data points with metrics
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=window_days)

    # Get all specs in window
    summary = aggregate_productivity_metrics(project_dir, start_date, end_date)

    # Group specs by time period
    trends = []

    if granularity == "daily":
        period_delta = timedelta(days=1)
    elif granularity == "weekly":
        period_delta = timedelta(weeks=1)
    elif granularity == "monthly":
        period_delta = timedelta(days=30)
    else:
        period_delta = timedelta(days=1)

    current_date = start_date
    while current_date <= end_date:
        period_end = current_date + period_delta

        # Filter specs in this period
        period_specs = [
            s
            for s in summary.specs
            if s.created_at and current_date <= s.created_at < period_end
        ]

        if period_specs:
            completed = sum(1 for s in period_specs if s.is_completed)
            time_saved = sum(_estimate_time_saved(s) for s in period_specs)

            trends.append(
                {
                    "date": current_date.isoformat(),
                    "total_specs": len(period_specs),
                    "completed_specs": completed,
                    "time_saved_hours": round(time_saved, 2),
                    "success_rate": round(
                        completed / len(period_specs) if period_specs else 0.0, 3
                    ),
                }
            )

        current_date = period_end

    return trends


def export_productivity_data(
    summary: ProductivitySummary, output_path: Path, format: str = "json"
) -> None:
    """
    Export productivity data to file.

    Args:
        summary: ProductivitySummary to export
        output_path: Path to output file
        format: Export format - "json" or "csv"
    """
    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)

    elif format == "csv":
        import csv

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "Spec ID",
                    "Spec Name",
                    "Type",
                    "Complexity",
                    "Status",
                    "Created At",
                    "Completed At",
                    "Duration (hours)",
                    "Total Subtasks",
                    "Completed Subtasks",
                    "QA Iterations",
                    "Completion Rate",
                ]
            )

            # Data rows
            for spec in summary.specs:
                writer.writerow(
                    [
                        spec.spec_id,
                        spec.spec_name,
                        spec.workflow_type,
                        spec.complexity,
                        spec.status,
                        spec.created_at.isoformat() if spec.created_at else "",
                        spec.completed_at.isoformat() if spec.completed_at else "",
                        round(spec.duration_seconds / 3600, 2),
                        spec.total_subtasks,
                        spec.completed_subtasks,
                        spec.qa_iterations,
                        round(spec.completion_rate, 3),
                    ]
                )
    else:
        raise ValueError(f"Unsupported export format: {format}")


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main() -> None:
    """CLI entry point for productivity analytics."""
    import argparse
    import sys

    from analysis.analytics_utils import add_common_cli_args, parse_date_args

    parser = argparse.ArgumentParser(description="Productivity Analytics Aggregator")
    parser.add_argument(
        "--get-summary", action="store_true", help="Get productivity summary"
    )
    parser.add_argument(
        "--get-trends", action="store_true", help="Get productivity trends over time"
    )
    parser.add_argument(
        "--export", action="store_true", help="Export productivity data to file"
    )
    add_common_cli_args(parser)

    args = parser.parse_args()
    project_dir = Path.cwd()
    start_date, end_date = parse_date_args(args)

    # Execute requested operation
    if args.get_summary:
        summary = aggregate_productivity_metrics(project_dir, start_date, end_date)
        print(json.dumps(summary.to_dict(), indent=2))

    elif args.get_trends:
        trends = get_productivity_trends(
            project_dir, args.window_days, args.granularity
        )
        print(json.dumps(trends, indent=2))

    elif args.export:
        # Get summary data
        summary = aggregate_productivity_metrics(project_dir, start_date, end_date)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            # Auto-generate path in analytics directory
            analytics_dir = project_dir / ".auto-claude" / "analytics"
            analytics_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"productivity_export_{timestamp}.{args.format}"
            output_path = analytics_dir / filename

        # Export data
        export_productivity_data(summary, output_path, args.format)

        # Return result as JSON
        result = {
            "success": True,
            "output_path": str(output_path.resolve()),
            "format": args.format,
            "total_specs": summary.total_specs,
        }
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
