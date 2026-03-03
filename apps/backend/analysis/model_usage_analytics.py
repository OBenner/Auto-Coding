"""
Model Usage Analytics Aggregator
================================

Aggregates model usage metrics across all specs to provide insights into
AI model consumption and costs.

Provides analytics on:
- Total tokens and cost per model
- Usage breakdown by agent type
- Model popularity and trends
- Cost distribution across models
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
class ModelMetrics:
    """
    Metrics for a single AI model.

    Captures usage statistics for one model across all specs.
    """

    model: str
    provider: str = "anthropic"

    # Usage metrics
    total_usage_count: int = 0  # Number of times this model was used
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0

    # Cost metrics
    total_cost: float = 0.0

    # Agent breakdown
    usage_by_agent: dict[str, int] = field(default_factory=dict)  # agent_type -> count

    # Time period
    first_used: datetime | None = None
    last_used: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model": self.model,
            "provider": self.provider,
            "total_usage_count": self.total_usage_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "usage_by_agent": self.usage_by_agent,
            "first_used": self.first_used.isoformat() if self.first_used else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelMetrics:
        """Create from dictionary."""
        return cls(
            model=data["model"],
            provider=data.get("provider", "anthropic"),
            total_usage_count=data.get("total_usage_count", 0),
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            usage_by_agent=data.get("usage_by_agent", {}),
            first_used=datetime.fromisoformat(data["first_used"])
            if data.get("first_used")
            else None,
            last_used=datetime.fromisoformat(data["last_used"])
            if data.get("last_used")
            else None,
        )

    @property
    def average_tokens_per_use(self) -> float:
        """Calculate average tokens per usage."""
        if self.total_usage_count == 0:
            return 0.0
        return self.total_tokens / self.total_usage_count

    @property
    def average_cost_per_use(self) -> float:
        """Calculate average cost per usage."""
        if self.total_usage_count == 0:
            return 0.0
        return self.total_cost / self.total_usage_count


@dataclass
class AgentMetrics:
    """
    Metrics for a single agent type.

    Captures model usage patterns for one agent type.
    """

    agent_type: str

    # Usage metrics
    total_usage_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0

    # Model breakdown
    models_used: dict[str, int] = field(default_factory=dict)  # model -> count
    primary_model: str | None = None  # Most frequently used model

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_type": self.agent_type,
            "total_usage_count": self.total_usage_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "models_used": self.models_used,
            "primary_model": self.primary_model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentMetrics:
        """Create from dictionary."""
        return cls(
            agent_type=data["agent_type"],
            total_usage_count=data.get("total_usage_count", 0),
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            models_used=data.get("models_used", {}),
            primary_model=data.get("primary_model"),
        )


@dataclass
class ModelUsageSummary:
    """
    Aggregated model usage metrics across all specs.

    Provides high-level insights into AI model consumption.
    """

    # Time period
    period_start: datetime
    period_end: datetime

    # Overall metrics
    total_specs: int = 0
    total_usage_records: int = 0

    # Token and cost metrics
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0

    # Model diversity
    unique_models_used: int = 0
    unique_providers_used: int = 0

    # Breakdowns
    metrics_by_model: dict[str, ModelMetrics] = field(default_factory=dict)
    metrics_by_agent: dict[str, AgentMetrics] = field(default_factory=dict)

    # Cost distribution
    cost_by_model: dict[str, float] = field(default_factory=dict)
    cost_by_agent: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_specs": self.total_specs,
            "total_usage_records": self.total_usage_records,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "unique_models_used": self.unique_models_used,
            "unique_providers_used": self.unique_providers_used,
            "metrics_by_model": {
                model: metrics.to_dict()
                for model, metrics in self.metrics_by_model.items()
            },
            "metrics_by_agent": {
                agent: metrics.to_dict()
                for agent, metrics in self.metrics_by_agent.items()
            },
            "cost_by_model": {
                model: round(cost, 4) for model, cost in self.cost_by_model.items()
            },
            "cost_by_agent": {
                agent: round(cost, 4) for agent, cost in self.cost_by_agent.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelUsageSummary:
        """Create from dictionary."""
        metrics_by_model = {
            model: ModelMetrics.from_dict(metrics)
            for model, metrics in data.get("metrics_by_model", {}).items()
        }
        metrics_by_agent = {
            agent: AgentMetrics.from_dict(metrics)
            for agent, metrics in data.get("metrics_by_agent", {}).items()
        }

        return cls(
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
            total_specs=data.get("total_specs", 0),
            total_usage_records=data.get("total_usage_records", 0),
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            unique_models_used=data.get("unique_models_used", 0),
            unique_providers_used=data.get("unique_providers_used", 0),
            metrics_by_model=metrics_by_model,
            metrics_by_agent=metrics_by_agent,
            cost_by_model=data.get("cost_by_model", {}),
            cost_by_agent=data.get("cost_by_agent", {}),
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


def _extract_cost_records(spec_dir: Path) -> list[dict[str, Any]]:
    """
    Extract cost records from a spec's cost_report.json.

    Args:
        spec_dir: Path to spec directory

    Returns:
        List of usage record dictionaries
    """
    cost_file = spec_dir / "cost_report.json"
    if not cost_file.exists():
        return []

    try:
        with open(cost_file, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("records", [])
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []


# =============================================================================
# PUBLIC API
# =============================================================================


def aggregate_model_usage(
    project_dir: Path,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ModelUsageSummary:
    """
    Aggregate model usage metrics across all specs.

    Args:
        project_dir: Path to project root
        start_date: Optional start date filter (inclusive)
        end_date: Optional end date filter (inclusive)

    Returns:
        ModelUsageSummary with aggregated metrics
    """
    # Normalize boundaries to UTC-aware datetimes
    start_date = _normalize_boundary(start_date)
    end_date = _normalize_boundary(end_date)

    # Locate specs directory
    specs_dir = project_dir / ".auto-claude" / "specs"
    if not specs_dir.exists():
        # Return empty summary
        return ModelUsageSummary(
            period_start=start_date or datetime.now(UTC),
            period_end=end_date or datetime.now(UTC),
        )

    # Track all records and their timestamps for period determination
    all_timestamps: list[datetime] = []
    total_specs = 0
    total_usage_records = 0

    # Aggregation containers
    model_metrics: dict[str, ModelMetrics] = {}
    agent_metrics: dict[str, AgentMetrics] = {}

    # Process each spec
    for spec_dir in specs_dir.iterdir():
        if not spec_dir.is_dir():
            continue

        # Extract cost records
        records = _extract_cost_records(spec_dir)
        if not records:
            continue

        total_specs += 1

        # Process each record
        for record_dict in records:
            # Parse timestamp
            timestamp = _parse_timestamp(record_dict.get("timestamp"))
            if not timestamp:
                continue

            # Apply date filters
            if start_date and timestamp < start_date:
                continue
            if end_date and timestamp > end_date:
                continue

            all_timestamps.append(timestamp)
            total_usage_records += 1

            # Extract record data
            model = record_dict.get("model", "unknown")
            provider = record_dict.get("provider", "anthropic")
            agent_type = record_dict.get("agent_type", "unknown")
            input_tokens = record_dict.get("input_tokens", 0)
            output_tokens = record_dict.get("output_tokens", 0)
            cost = record_dict.get("cost", 0.0)

            # Initialize model metrics if needed
            if model not in model_metrics:
                model_metrics[model] = ModelMetrics(model=model, provider=provider)
            model_metric = model_metrics[model]

            # Update model metrics
            model_metric.total_usage_count += 1
            model_metric.total_input_tokens += input_tokens
            model_metric.total_output_tokens += output_tokens
            model_metric.total_tokens += input_tokens + output_tokens
            model_metric.total_cost += cost

            # Update agent usage for this model
            if agent_type not in model_metric.usage_by_agent:
                model_metric.usage_by_agent[agent_type] = 0
            model_metric.usage_by_agent[agent_type] += 1

            # Update first/last used
            if model_metric.first_used is None or timestamp < model_metric.first_used:
                model_metric.first_used = timestamp
            if model_metric.last_used is None or timestamp > model_metric.last_used:
                model_metric.last_used = timestamp

            # Initialize agent metrics if needed
            if agent_type not in agent_metrics:
                agent_metrics[agent_type] = AgentMetrics(agent_type=agent_type)
            agent_metric = agent_metrics[agent_type]

            # Update agent metrics
            agent_metric.total_usage_count += 1
            agent_metric.total_input_tokens += input_tokens
            agent_metric.total_output_tokens += output_tokens
            agent_metric.total_tokens += input_tokens + output_tokens
            agent_metric.total_cost += cost

            # Update model usage for this agent
            if model not in agent_metric.models_used:
                agent_metric.models_used[model] = 0
            agent_metric.models_used[model] += 1

    # Determine primary model for each agent
    for agent_metric in agent_metrics.values():
        if agent_metric.models_used:
            agent_metric.primary_model = max(
                agent_metric.models_used.items(), key=lambda x: x[1]
            )[0]

    # Determine period
    if all_timestamps:
        period_start = start_date or min(all_timestamps)
        period_end = end_date or max(all_timestamps)
    else:
        period_start = start_date or datetime.now(UTC)
        period_end = end_date or datetime.now(UTC)

    # Calculate totals
    total_input_tokens = sum(m.total_input_tokens for m in model_metrics.values())
    total_output_tokens = sum(m.total_output_tokens for m in model_metrics.values())
    total_tokens = sum(m.total_tokens for m in model_metrics.values())
    total_cost = sum(m.total_cost for m in model_metrics.values())

    # Calculate unique counts
    unique_models_used = len(model_metrics)
    unique_providers_used = len(set(m.provider for m in model_metrics.values()))

    # Build cost breakdowns
    cost_by_model = {model: m.total_cost for model, m in model_metrics.items()}
    cost_by_agent = {agent: m.total_cost for agent, m in agent_metrics.items()}

    return ModelUsageSummary(
        period_start=period_start,
        period_end=period_end,
        total_specs=total_specs,
        total_usage_records=total_usage_records,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_tokens=total_tokens,
        total_cost=total_cost,
        unique_models_used=unique_models_used,
        unique_providers_used=unique_providers_used,
        metrics_by_model=model_metrics,
        metrics_by_agent=agent_metrics,
        cost_by_model=cost_by_model,
        cost_by_agent=cost_by_agent,
    )


def get_model_usage_trends(
    project_dir: Path, window_days: int = 30, granularity: str = "daily"
) -> list[dict[str, Any]]:
    """
    Get model usage trends over time.

    Args:
        project_dir: Path to project root
        window_days: Number of days to look back
        granularity: Time granularity - "daily", "weekly", or "monthly"

    Returns:
        List of time-series data points with metrics
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=window_days)

    # Get all usage in window
    # Group usage by time period
    trends = []

    if granularity == "daily":
        period_delta = timedelta(days=1)
    elif granularity == "weekly":
        period_delta = timedelta(weeks=1)
    elif granularity == "monthly":
        period_delta = timedelta(days=30)
    else:
        period_delta = timedelta(days=1)

    # Collect all records with timestamps for grouping
    specs_dir = project_dir / ".auto-claude" / "specs"
    if not specs_dir.exists():
        return trends

    # Build time-indexed records
    time_records: dict[datetime, list[dict[str, Any]]] = {}

    for spec_dir in specs_dir.iterdir():
        if not spec_dir.is_dir():
            continue

        records = _extract_cost_records(spec_dir)
        for record_dict in records:
            timestamp = _parse_timestamp(record_dict.get("timestamp"))
            if not timestamp:
                continue

            # Filter to window
            if timestamp < start_date or timestamp > end_date:
                continue

            # Round timestamp to period start
            if granularity == "daily":
                period_key = timestamp.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            elif granularity == "weekly":
                # Round to Monday
                days_since_monday = timestamp.weekday()
                period_key = timestamp.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=days_since_monday)
            else:  # monthly
                period_key = timestamp.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )

            if period_key not in time_records:
                time_records[period_key] = []
            time_records[period_key].append(record_dict)

    # Generate trend data points
    current_date = start_date
    while current_date <= end_date:
        period_end = current_date + period_delta

        # Round to appropriate period boundary
        if granularity == "daily":
            period_key = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == "weekly":
            days_since_monday = current_date.weekday()
            period_key = current_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=days_since_monday)
        else:
            period_key = current_date.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )

        # Get records for this period
        period_records = time_records.get(period_key, [])

        if period_records:
            # Aggregate metrics for this period
            period_tokens = sum(
                r.get("input_tokens", 0) + r.get("output_tokens", 0)
                for r in period_records
            )
            period_cost = sum(r.get("cost", 0.0) for r in period_records)
            period_models = len(set(r.get("model", "unknown") for r in period_records))

            # Count by model
            model_counts: dict[str, int] = defaultdict(int)
            for record in period_records:
                model_counts[record.get("model", "unknown")] += 1

            trends.append(
                {
                    "date": current_date.isoformat(),
                    "total_usage_records": len(period_records),
                    "total_tokens": period_tokens,
                    "total_cost": round(period_cost, 4),
                    "unique_models": period_models,
                    "most_used_model": max(model_counts.items(), key=lambda x: x[1])[0]
                    if model_counts
                    else None,
                }
            )

        current_date = period_end

    return trends


def export_model_usage_data(
    summary: ModelUsageSummary, output_path: Path, format: str = "json"
) -> None:
    """
    Export model usage data to file.

    Args:
        summary: ModelUsageSummary to export
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

            # Write summary section
            writer.writerow(["=== SUMMARY ==="])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Period Start", summary.period_start.isoformat()])
            writer.writerow(["Period End", summary.period_end.isoformat()])
            writer.writerow(["Total Specs", summary.total_specs])
            writer.writerow(["Total Usage Records", summary.total_usage_records])
            writer.writerow(["Total Tokens", summary.total_tokens])
            writer.writerow(["Total Cost ($)", round(summary.total_cost, 4)])
            writer.writerow(["Unique Models", summary.unique_models_used])
            writer.writerow([])

            # Write model breakdown
            writer.writerow(["=== MODEL BREAKDOWN ==="])
            writer.writerow(
                [
                    "Model",
                    "Provider",
                    "Usage Count",
                    "Input Tokens",
                    "Output Tokens",
                    "Total Tokens",
                    "Cost ($)",
                    "Avg Tokens/Use",
                    "Avg Cost/Use ($)",
                ]
            )

            for model, metrics in sorted(
                summary.metrics_by_model.items(),
                key=lambda x: x[1].total_cost,
                reverse=True,
            ):
                writer.writerow(
                    [
                        model,
                        metrics.provider,
                        metrics.total_usage_count,
                        metrics.total_input_tokens,
                        metrics.total_output_tokens,
                        metrics.total_tokens,
                        round(metrics.total_cost, 4),
                        round(metrics.average_tokens_per_use, 1),
                        round(metrics.average_cost_per_use, 4),
                    ]
                )

            writer.writerow([])

            # Write agent breakdown
            writer.writerow(["=== AGENT BREAKDOWN ==="])
            writer.writerow(
                [
                    "Agent Type",
                    "Usage Count",
                    "Input Tokens",
                    "Output Tokens",
                    "Total Tokens",
                    "Cost ($)",
                    "Primary Model",
                    "Models Used",
                ]
            )

            for agent, metrics in sorted(
                summary.metrics_by_agent.items(),
                key=lambda x: x[1].total_cost,
                reverse=True,
            ):
                writer.writerow(
                    [
                        agent,
                        metrics.total_usage_count,
                        metrics.total_input_tokens,
                        metrics.total_output_tokens,
                        metrics.total_tokens,
                        round(metrics.total_cost, 4),
                        metrics.primary_model or "N/A",
                        len(metrics.models_used),
                    ]
                )
    else:
        raise ValueError(f"Unsupported export format: {format}")


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main() -> None:
    """CLI entry point for model usage analytics."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Model Usage Analytics Aggregator")
    parser.add_argument(
        "--get-summary",
        action="store_true",
        help="Get model usage summary",
    )
    parser.add_argument(
        "--get-trends",
        action="store_true",
        help="Get model usage trends over time",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export model usage data to file",
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
        summary = aggregate_model_usage(project_dir, start_date, end_date)
        print(json.dumps(summary.to_dict(), indent=2))

    elif args.get_trends:
        trends = get_model_usage_trends(project_dir, args.window_days, args.granularity)
        print(json.dumps(trends, indent=2))

    elif args.export:
        # Get summary data
        summary = aggregate_model_usage(project_dir, start_date, end_date)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            # Auto-generate path in analytics directory
            analytics_dir = project_dir / ".auto-claude" / "analytics"
            analytics_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"model_usage_export_{timestamp}.{args.format}"
            output_path = analytics_dir / filename

        # Export data
        export_model_usage_data(summary, output_path, args.format)

        # Return result as JSON
        result = {
            "success": True,
            "output_path": str(output_path.resolve()),
            "format": args.format,
            "total_usage_records": summary.total_usage_records,
            "total_models": summary.unique_models_used,
        }
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
