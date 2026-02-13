"""
Cost Analytics Aggregator
========================

Aggregates cost metrics across all specs to provide insights into
AI API usage and spending.

Provides analytics on:
- Total API costs across all specs
- Cost breakdown by agent type
- Cost breakdown by model
- Token usage statistics
- Cost trends over time
- Export functionality for external analysis
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SpecCostMetrics:
    """
    Cost metrics for a single spec.

    Captures key cost indicators for one build.
    """

    spec_id: str
    spec_name: str

    # Cost tracking
    total_cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Breakdowns
    cost_by_agent: dict[str, float] = field(default_factory=dict)
    cost_by_model: dict[str, float] = field(default_factory=dict)

    # Session count
    session_count: int = 0

    # Time period
    first_session: datetime | None = None
    last_session: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "spec_id": self.spec_id,
            "spec_name": self.spec_name,
            "total_cost": self.total_cost,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_by_agent": self.cost_by_agent,
            "cost_by_model": self.cost_by_model,
            "session_count": self.session_count,
            "first_session": self.first_session.isoformat()
            if self.first_session
            else None,
            "last_session": self.last_session.isoformat()
            if self.last_session
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecCostMetrics:
        """Create from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            spec_name=data["spec_name"],
            total_cost=data.get("total_cost", 0.0),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            cost_by_agent=data.get("cost_by_agent", {}),
            cost_by_model=data.get("cost_by_model", {}),
            session_count=data.get("session_count", 0),
            first_session=datetime.fromisoformat(data["first_session"])
            if data.get("first_session")
            else None,
            last_session=datetime.fromisoformat(data["last_session"])
            if data.get("last_session")
            else None,
        )

    @property
    def average_cost_per_session(self) -> float:
        """Calculate average cost per session."""
        if self.session_count == 0:
            return 0.0
        return self.total_cost / self.session_count

    @property
    def cost_per_million_tokens(self) -> float:
        """Calculate cost per million tokens."""
        if self.total_tokens == 0:
            return 0.0
        return (self.total_cost / self.total_tokens) * 1_000_000


@dataclass
class CostSummary:
    """
    Aggregated cost metrics across all specs.

    Provides high-level insights into AI API spending.
    """

    # Time period
    period_start: datetime
    period_end: datetime

    # Overall metrics
    total_specs: int = 0
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_sessions: int = 0

    # Cost breakdowns
    cost_by_agent: dict[str, float] = field(default_factory=dict)
    cost_by_model: dict[str, float] = field(default_factory=dict)

    # Cost per spec
    average_cost_per_spec: float = 0.0
    median_cost_per_spec: float = 0.0

    # Token efficiency
    average_cost_per_million_tokens: float = 0.0
    average_tokens_per_session: float = 0.0

    # Detailed spec list
    specs: list[SpecCostMetrics] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_specs": self.total_specs,
            "total_cost": round(self.total_cost, 4),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_sessions": self.total_sessions,
            "cost_by_agent": {
                k: round(v, 4) for k, v in self.cost_by_agent.items()
            },
            "cost_by_model": {
                k: round(v, 4) for k, v in self.cost_by_model.items()
            },
            "average_cost_per_spec": round(self.average_cost_per_spec, 4),
            "median_cost_per_spec": round(self.median_cost_per_spec, 4),
            "average_cost_per_million_tokens": round(
                self.average_cost_per_million_tokens, 4
            ),
            "average_tokens_per_session": round(self.average_tokens_per_session, 1),
            "specs": [spec.to_dict() for spec in self.specs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CostSummary:
        """Create from dictionary."""
        return cls(
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
            total_specs=data.get("total_specs", 0),
            total_cost=data.get("total_cost", 0.0),
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            total_sessions=data.get("total_sessions", 0),
            cost_by_agent=data.get("cost_by_agent", {}),
            cost_by_model=data.get("cost_by_model", {}),
            average_cost_per_spec=data.get("average_cost_per_spec", 0.0),
            median_cost_per_spec=data.get("median_cost_per_spec", 0.0),
            average_cost_per_million_tokens=data.get(
                "average_cost_per_million_tokens", 0.0
            ),
            average_tokens_per_session=data.get("average_tokens_per_session", 0.0),
            specs=[SpecCostMetrics.from_dict(s) for s in data.get("specs", [])],
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp string to timezone-aware UTC datetime.

    Returns None for invalid or missing timestamps.
    """
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(ts)

        # Ensure timezone-aware in UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        else:
            dt = dt.astimezone(UTC)
        return dt
    except (ValueError, AttributeError):
        return None


def _normalize_boundary(dt: datetime | None) -> datetime | None:
    """Normalize start/end boundary datetimes to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _extract_spec_cost_metrics(spec_dir: Path) -> SpecCostMetrics | None:
    """
    Extract cost metrics from a single spec directory.

    Args:
        spec_dir: Path to spec directory

    Returns:
        SpecCostMetrics object or None if no cost data
    """
    # Check for cost_report.json
    cost_report_file = spec_dir / "cost_report.json"
    if not cost_report_file.exists():
        return None

    # Check for implementation_plan.json for spec name
    plan_file = spec_dir / "implementation_plan.json"

    try:
        # Load cost data
        with open(cost_report_file, encoding="utf-8") as f:
            cost_data = json.load(f)

        # Load spec name from plan if available
        spec_name = spec_dir.name
        if plan_file.exists():
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)
                spec_name = plan.get("feature", spec_dir.name)

        # Extract records
        records = cost_data.get("records", [])

        if not records:
            return SpecCostMetrics(
                spec_id=spec_dir.name,
                spec_name=spec_name,
                session_count=0,
            )

        # Aggregate metrics from records
        total_cost = 0.0
        input_tokens = 0
        output_tokens = 0
        cost_by_agent: dict[str, float] = defaultdict(float)
        cost_by_model: dict[str, float] = defaultdict(float)

        timestamps: list[datetime] = []

        for record in records:
            cost = record.get("cost", 0.0)
            agent_type = record.get("agent_type", "unknown")
            model = record.get("model", "unknown")

            total_cost += cost
            input_tokens += record.get("input_tokens", 0)
            output_tokens += record.get("output_tokens", 0)

            cost_by_agent[agent_type] += cost
            cost_by_model[model] += cost

            # Parse timestamp
            ts = _parse_timestamp(record.get("timestamp"))
            if ts:
                timestamps.append(ts)

        total_tokens = input_tokens + output_tokens

        # Determine time range
        first_session = min(timestamps) if timestamps else None
        last_session = max(timestamps) if timestamps else None

        return SpecCostMetrics(
            spec_id=spec_dir.name,
            spec_name=spec_name,
            total_cost=total_cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_by_agent=dict(cost_by_agent),
            cost_by_model=dict(cost_by_model),
            session_count=len(records),
            first_session=first_session,
            last_session=last_session,
        )

    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _calculate_median(values: list[float]) -> float:
    """Calculate median of a list of values."""
    if not values:
        return 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)

    if n % 2 == 0:
        # Even number of elements: average of middle two
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
    else:
        # Odd number of elements: middle element
        return sorted_values[n // 2]


# =============================================================================
# PUBLIC API
# =============================================================================


def aggregate_cost_metrics(
    project_dir: Path,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CostSummary:
    """
    Aggregate cost metrics across all specs.

    Args:
        project_dir: Path to project root
        start_date: Optional start date filter (inclusive)
        end_date: Optional end date filter (inclusive)

    Returns:
        CostSummary with aggregated metrics
    """
    # Normalize boundaries to UTC-aware datetimes
    start_date = _normalize_boundary(start_date)
    end_date = _normalize_boundary(end_date)

    # Locate specs directory
    specs_dir = project_dir / ".auto-claude" / "specs"
    if not specs_dir.exists():
        # Return empty summary
        return CostSummary(
            period_start=start_date or datetime.now(UTC),
            period_end=end_date or datetime.now(UTC),
        )

    # Collect all spec cost metrics
    all_specs: list[SpecCostMetrics] = []
    for spec_dir in specs_dir.iterdir():
        if not spec_dir.is_dir():
            continue

        spec_metrics = _extract_spec_cost_metrics(spec_dir)
        if not spec_metrics:
            continue

        # Apply date filters (use last session date)
        if (
            start_date
            and spec_metrics.last_session
            and spec_metrics.last_session < start_date
        ):
            continue
        if (
            end_date
            and spec_metrics.last_session
            and spec_metrics.last_session > end_date
        ):
            continue

        all_specs.append(spec_metrics)

    # Determine period
    if not all_specs:
        period_start = start_date or datetime.now(UTC)
        period_end = end_date or datetime.now(UTC)
    else:
        # Use first and last session dates across all specs
        first_sessions = [
            s.first_session for s in all_specs if s.first_session
        ]
        last_sessions = [s.last_session for s in all_specs if s.last_session]

        if first_sessions and last_sessions:
            period_start = start_date or min(first_sessions)
            period_end = end_date or max(last_sessions)
        else:
            period_start = start_date or datetime.now(UTC)
            period_end = end_date or datetime.now(UTC)

    # Calculate aggregate metrics
    total_specs = len(all_specs)
    total_cost = sum(s.total_cost for s in all_specs)
    total_input_tokens = sum(s.input_tokens for s in all_specs)
    total_output_tokens = sum(s.output_tokens for s in all_specs)
    total_tokens = sum(s.total_tokens for s in all_specs)
    total_sessions = sum(s.session_count for s in all_specs)

    # Cost breakdowns
    cost_by_agent: dict[str, float] = defaultdict(float)
    cost_by_model: dict[str, float] = defaultdict(float)

    for spec in all_specs:
        for agent, cost in spec.cost_by_agent.items():
            cost_by_agent[agent] += cost
        for model, cost in spec.cost_by_model.items():
            cost_by_model[model] += cost

    # Cost per spec
    if total_specs > 0:
        average_cost_per_spec = total_cost / total_specs
        spec_costs = [s.total_cost for s in all_specs]
        median_cost_per_spec = _calculate_median(spec_costs)
    else:
        average_cost_per_spec = 0.0
        median_cost_per_spec = 0.0

    # Token efficiency
    if total_tokens > 0:
        average_cost_per_million_tokens = (total_cost / total_tokens) * 1_000_000
    else:
        average_cost_per_million_tokens = 0.0

    if total_sessions > 0:
        average_tokens_per_session = total_tokens / total_sessions
    else:
        average_tokens_per_session = 0.0

    return CostSummary(
        period_start=period_start,
        period_end=period_end,
        total_specs=total_specs,
        total_cost=total_cost,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_tokens=total_tokens,
        total_sessions=total_sessions,
        cost_by_agent=dict(cost_by_agent),
        cost_by_model=dict(cost_by_model),
        average_cost_per_spec=average_cost_per_spec,
        median_cost_per_spec=median_cost_per_spec,
        average_cost_per_million_tokens=average_cost_per_million_tokens,
        average_tokens_per_session=average_tokens_per_session,
        specs=all_specs,
    )


def get_cost_trends(
    project_dir: Path, window_days: int = 30, granularity: str = "daily"
) -> list[dict[str, Any]]:
    """
    Get cost trends over time.

    Args:
        project_dir: Path to project root
        window_days: Number of days to look back
        granularity: Time granularity - "daily", "weekly", or "monthly"

    Returns:
        List of time-series data points with cost metrics
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=window_days)

    # Get all specs in window
    summary = aggregate_cost_metrics(project_dir, start_date, end_date)

    # Group costs by time period
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

        # Filter specs that had sessions in this period
        period_specs = [
            s
            for s in summary.specs
            if s.last_session
            and current_date <= s.last_session < period_end
        ]

        if period_specs:
            period_cost = sum(s.total_cost for s in period_specs)
            period_tokens = sum(s.total_tokens for s in period_specs)
            period_sessions = sum(s.session_count for s in period_specs)

            trends.append(
                {
                    "date": current_date.isoformat(),
                    "total_cost": round(period_cost, 4),
                    "total_tokens": period_tokens,
                    "total_sessions": period_sessions,
                    "specs_count": len(period_specs),
                }
            )

        current_date = period_end

    return trends


def export_cost_data(
    summary: CostSummary, output_path: Path, format: str = "json"
) -> None:
    """
    Export cost data to file.

    Args:
        summary: CostSummary to export
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
                    "Total Cost ($)",
                    "Input Tokens",
                    "Output Tokens",
                    "Total Tokens",
                    "Session Count",
                    "Cost/Session ($)",
                    "Cost/1M Tokens ($)",
                    "First Session",
                    "Last Session",
                ]
            )

            # Data rows
            for spec in summary.specs:
                writer.writerow(
                    [
                        spec.spec_id,
                        spec.spec_name,
                        round(spec.total_cost, 4),
                        spec.input_tokens,
                        spec.output_tokens,
                        spec.total_tokens,
                        spec.session_count,
                        round(spec.average_cost_per_session, 4),
                        round(spec.cost_per_million_tokens, 4),
                        spec.first_session.isoformat() if spec.first_session else "",
                        spec.last_session.isoformat() if spec.last_session else "",
                    ]
                )

            # Add summary row at bottom
            writer.writerow([])
            writer.writerow(
                [
                    "TOTAL",
                    f"{summary.total_specs} specs",
                    round(summary.total_cost, 4),
                    summary.total_input_tokens,
                    summary.total_output_tokens,
                    summary.total_tokens,
                    summary.total_sessions,
                    "",
                    round(summary.average_cost_per_million_tokens, 4),
                    summary.period_start.isoformat(),
                    summary.period_end.isoformat(),
                ]
            )
    else:
        raise ValueError(f"Unsupported export format: {format}")


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main() -> None:
    """CLI entry point for cost analytics."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Cost Analytics Aggregator")
    parser.add_argument(
        "--get-summary",
        action="store_true",
        help="Get cost summary",
    )
    parser.add_argument(
        "--get-trends",
        action="store_true",
        help="Get cost trends over time",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export cost data to file",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Export format (default: json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: auto-generated in analytics dir)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date filter (ISO format)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date filter (ISO format)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Number of days to look back for trends (default: 30)",
    )
    parser.add_argument(
        "--granularity",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Time granularity for trends (default: daily)",
    )

    args = parser.parse_args()

    # Determine project directory (current working directory)
    project_dir = Path.cwd()

    # Parse date filters
    start_date = None
    end_date = None
    if args.start_date:
        try:
            start_date = datetime.fromisoformat(args.start_date)
        except ValueError:
            print(
                f"Error: Invalid start date format: {args.start_date}",
                file=sys.stderr,
            )
            sys.exit(1)

    if args.end_date:
        try:
            end_date = datetime.fromisoformat(args.end_date)
        except ValueError:
            print(
                f"Error: Invalid end date format: {args.end_date}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Execute requested operation
    if args.get_summary:
        summary = aggregate_cost_metrics(project_dir, start_date, end_date)
        print(json.dumps(summary.to_dict(), indent=2))

    elif args.get_trends:
        trends = get_cost_trends(project_dir, args.window_days, args.granularity)
        print(json.dumps(trends, indent=2))

    elif args.export:
        # Get summary data
        summary = aggregate_cost_metrics(project_dir, start_date, end_date)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            # Auto-generate path in analytics directory
            analytics_dir = project_dir / ".auto-claude" / "analytics"
            analytics_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"cost_export_{timestamp}.{args.format}"
            output_path = analytics_dir / filename

        # Export data
        export_cost_data(summary, output_path, args.format)

        # Return result as JSON
        result = {
            "success": True,
            "output_path": str(output_path.resolve()),
            "format": args.format,
            "total_specs": summary.total_specs,
            "total_cost": round(summary.total_cost, 4),
        }
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
