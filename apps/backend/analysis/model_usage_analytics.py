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
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from analysis.analytics_utils import (
    normalize_boundary,
    parse_timestamp,
)

logger = logging.getLogger(__name__)

# =============================================================================
# DATA MODELS
# =============================================================================


COST_PRECISION = 4  # Decimal places for cost rounding

# Project-level summary written next to the specs dir (.auto-claude/<filename>)
MODEL_USAGE_SUMMARY_FILENAME = "model_usage_summary.json"

# Shared token/cost field names for serialization
_USAGE_FIELDS = (
    "total_usage_count",
    "total_input_tokens",
    "total_output_tokens",
    "total_tokens",
)


def _usage_to_dict(obj: ModelMetrics | AgentMetrics) -> dict[str, Any]:
    """Return the common usage/cost fields as a serializable dict."""
    d: dict[str, Any] = {f: getattr(obj, f) for f in _USAGE_FIELDS}
    d["total_cost"] = round(obj.total_cost, COST_PRECISION)
    return d


def _usage_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Extract common usage/cost kwargs from a dict."""
    kwargs: dict[str, Any] = {f: data.get(f, 0) for f in _USAGE_FIELDS}
    kwargs["total_cost"] = data.get("total_cost", 0.0)
    return kwargs


def _optional_iso(data: dict[str, Any], key: str) -> datetime | None:
    """Parse an optional ISO datetime string from a dict."""
    val = data.get(key)
    return datetime.fromisoformat(val) if val else None


@dataclass
class ModelMetrics:
    """Metrics for a single AI model across all specs."""

    model: str
    provider: str = "unknown"
    total_usage_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    usage_by_agent: dict[str, int] = field(default_factory=dict)
    first_used: datetime | None = None
    last_used: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model": self.model,
            "provider": self.provider,
            **_usage_to_dict(self),
            "usage_by_agent": self.usage_by_agent,
            "first_used": self.first_used.isoformat() if self.first_used else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelMetrics:
        """Create from dictionary."""
        return cls(
            model=data["model"],
            provider=data.get("provider", "unknown"),
            **_usage_from_dict(data),
            usage_by_agent=data.get("usage_by_agent", {}),
            first_used=_optional_iso(data, "first_used"),
            last_used=_optional_iso(data, "last_used"),
        )

    @property
    def average_tokens_per_use(self) -> float:
        """Calculate average tokens per usage."""
        return (
            self.total_tokens / self.total_usage_count
            if self.total_usage_count
            else 0.0
        )

    @property
    def average_cost_per_use(self) -> float:
        """Calculate average cost per usage."""
        return (
            self.total_cost / self.total_usage_count if self.total_usage_count else 0.0
        )


@dataclass
class AgentMetrics:
    """Metrics for a single agent type across all specs."""

    agent_type: str
    total_usage_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    models_used: dict[str, int] = field(default_factory=dict)
    primary_model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_type": self.agent_type,
            **_usage_to_dict(self),
            "models_used": self.models_used,
            "primary_model": self.primary_model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentMetrics:
        """Create from dictionary."""
        return cls(
            agent_type=data["agent_type"],
            **_usage_from_dict(data),
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
    cost_by_phase: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        rnd = lambda v: round(v, COST_PRECISION)  # noqa: E731
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_specs": self.total_specs,
            "total_usage_records": self.total_usage_records,
            # The summary tracks records, not per-metric usage counts, so it
            # can't reuse _USAGE_FIELDS (whose total_usage_count doesn't exist
            # here) — serialize its token fields explicitly.
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": rnd(self.total_cost),
            "unique_models_used": self.unique_models_used,
            "unique_providers_used": self.unique_providers_used,
            "metrics_by_model": {
                k: v.to_dict() for k, v in self.metrics_by_model.items()
            },
            "metrics_by_agent": {
                k: v.to_dict() for k, v in self.metrics_by_agent.items()
            },
            "cost_by_model": {k: rnd(v) for k, v in self.cost_by_model.items()},
            "cost_by_agent": {k: rnd(v) for k, v in self.cost_by_agent.items()},
            "cost_by_phase": {k: rnd(v) for k, v in self.cost_by_phase.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelUsageSummary:
        """Create from dictionary."""
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
            metrics_by_model={
                k: ModelMetrics.from_dict(v)
                for k, v in data.get("metrics_by_model", {}).items()
            },
            metrics_by_agent={
                k: AgentMetrics.from_dict(v)
                for k, v in data.get("metrics_by_agent", {}).items()
            },
            cost_by_model=data.get("cost_by_model", {}),
            cost_by_agent=data.get("cost_by_agent", {}),
            cost_by_phase=data.get("cost_by_phase", {}),
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


_parse_timestamp = parse_timestamp
_normalize_boundary = normalize_boundary


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


def _accumulate_tokens(
    metric: ModelMetrics | AgentMetrics,
    input_tokens: int,
    output_tokens: int,
    cost: float,
) -> None:
    """Accumulate token and cost counters on a metrics object."""
    metric.total_usage_count += 1
    metric.total_input_tokens += input_tokens
    metric.total_output_tokens += output_tokens
    metric.total_tokens += input_tokens + output_tokens
    metric.total_cost += cost


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
    phase_costs: dict[str, float] = {}

    def _safe_int(val: Any) -> int:
        """Coerce a value to int, falling back to 0."""
        if val is None:
            return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def _safe_float(val: Any) -> float:
        """Coerce a value to float, falling back to 0.0."""
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    # Process each spec
    for spec_dir in specs_dir.iterdir():
        if not spec_dir.is_dir():
            continue

        # Extract cost records
        records = _extract_cost_records(spec_dir)
        if not records:
            continue

        spec_had_records = False

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

            spec_had_records = True
            all_timestamps.append(timestamp)
            total_usage_records += 1

            # Extract record data (coerce types for safety)
            model = record_dict.get("model", "unknown")
            provider = record_dict.get("provider", "unknown")
            agent_type = record_dict.get("agent_type", "unknown")
            input_tokens = _safe_int(record_dict.get("input_tokens", 0))
            output_tokens = _safe_int(record_dict.get("output_tokens", 0))
            cost = _safe_float(record_dict.get("cost", 0.0))

            # Key by (provider, model) to avoid collisions across providers
            model_key = f"{provider}:{model}"

            # Initialize model metrics if needed
            if model_key not in model_metrics:
                model_metrics[model_key] = ModelMetrics(model=model, provider=provider)
            model_metric = model_metrics[model_key]

            # Update model metrics
            _accumulate_tokens(model_metric, input_tokens, output_tokens, cost)
            model_metric.usage_by_agent[agent_type] = (
                model_metric.usage_by_agent.get(agent_type, 0) + 1
            )

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
            _accumulate_tokens(agent_metric, input_tokens, output_tokens, cost)
            agent_metric.models_used[model] = agent_metric.models_used.get(model, 0) + 1

            # Update phase cost breakdown (records predating the phase field
            # land in "unknown")
            phase = str(record_dict.get("phase") or "unknown")
            phase_costs[phase] = phase_costs.get(phase, 0.0) + cost

        # Only count spec if it had records passing filters
        if spec_had_records:
            total_specs += 1

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
        cost_by_phase=phase_costs,
    )


def write_model_usage_summary(project_dir: Path) -> Path | None:
    """
    Aggregate all-time model usage and persist the project-level summary.

    Writes `.auto-claude/model_usage_summary.json` atomically (temp file +
    replace) so concurrent readers never observe a torn file. Best-effort by
    design: cost accounting must never break a build, so failures are logged
    and swallowed.

    Args:
        project_dir: Path to project root

    Returns:
        Path to the written summary, or None when aggregation or write failed.
    """
    try:
        summary = aggregate_model_usage(project_dir)
        out_dir = project_dir / ".auto-claude"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / MODEL_USAGE_SUMMARY_FILENAME
        tmp_path = out_path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)
        os.replace(tmp_path, out_path)
        return out_path
    except Exception as exc:
        logger.warning("Failed to write model usage summary: %s", exc)
        return None


def _round_to_period_start(timestamp: datetime, granularity: str) -> datetime:
    """Round a timestamp to the start of the containing period."""
    if granularity == "weekly":
        days_since_monday = timestamp.weekday()
        return timestamp.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=days_since_monday
        )
    if granularity == "monthly":
        return timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # daily (default)
    return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)


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

    def _advance_period(dt: datetime, gran: str) -> datetime:
        """Advance a datetime by one period based on granularity."""
        if gran == "weekly":
            return dt + timedelta(weeks=1)
        if gran == "monthly":
            # Advance by one calendar month
            month = dt.month % 12 + 1
            year = dt.year + (1 if dt.month == 12 else 0)
            # Clamp day to valid range for target month
            import calendar

            max_day = calendar.monthrange(year, month)[1]
            day = min(dt.day, max_day)
            return dt.replace(year=year, month=month, day=day)
        # daily (default)
        return dt + timedelta(days=1)

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
            period_key = _round_to_period_start(timestamp, granularity)

            if period_key not in time_records:
                time_records[period_key] = []
            time_records[period_key].append(record_dict)

    # Generate trend data points
    current_date = start_date
    while current_date <= end_date:
        period_end = _advance_period(current_date, granularity)

        # Round to appropriate period boundary
        period_key = _round_to_period_start(current_date, granularity)

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
                    "total_cost": round(period_cost, COST_PRECISION),
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

        def _write_breakdown(
            writer: csv.writer,
            title: str,
            headers: list[str],
            items: dict[str, ModelMetrics | AgentMetrics],
            row_fn: object,
        ) -> None:
            """Write a sorted breakdown section to CSV."""
            writer.writerow([f"=== {title} ==="])
            writer.writerow(headers)
            for _key, m in sorted(
                items.items(), key=lambda x: x[1].total_cost, reverse=True
            ):
                writer.writerow(row_fn(m))  # type: ignore[operator]
            writer.writerow([])

        rnd = lambda v, p=COST_PRECISION: round(v, p)  # noqa: E731

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Summary section
            writer.writerow(["=== SUMMARY ==="])
            writer.writerow(["Metric", "Value"])
            for label, value in [
                ("Period Start", summary.period_start.isoformat()),
                ("Period End", summary.period_end.isoformat()),
                ("Total Specs", summary.total_specs),
                ("Total Usage Records", summary.total_usage_records),
                ("Total Tokens", summary.total_tokens),
                ("Total Cost ($)", rnd(summary.total_cost)),
                ("Unique Models", summary.unique_models_used),
            ]:
                writer.writerow([label, value])
            writer.writerow([])

            # Model breakdown
            _write_breakdown(
                writer,
                "MODEL BREAKDOWN",
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
                ],
                summary.metrics_by_model,
                lambda m: [
                    m.model,
                    m.provider,
                    m.total_usage_count,
                    m.total_input_tokens,
                    m.total_output_tokens,
                    m.total_tokens,
                    rnd(m.total_cost),
                    round(m.average_tokens_per_use, 1),
                    rnd(m.average_cost_per_use),
                ],
            )

            # Agent breakdown
            _write_breakdown(
                writer,
                "AGENT BREAKDOWN",
                [
                    "Agent Type",
                    "Usage Count",
                    "Input Tokens",
                    "Output Tokens",
                    "Total Tokens",
                    "Cost ($)",
                    "Primary Model",
                    "Models Used",
                ],
                summary.metrics_by_agent,
                lambda m: [
                    m.agent_type,
                    m.total_usage_count,
                    m.total_input_tokens,
                    m.total_output_tokens,
                    m.total_tokens,
                    rnd(m.total_cost),
                    m.primary_model or "N/A",
                    len(m.models_used),
                ],
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

    from analysis.analytics_utils import add_common_cli_args, parse_date_args

    parser = argparse.ArgumentParser(description="Model Usage Analytics Aggregator")
    parser.add_argument(
        "--get-summary", action="store_true", help="Get model usage summary"
    )
    parser.add_argument(
        "--get-trends", action="store_true", help="Get model usage trends over time"
    )
    parser.add_argument(
        "--export", action="store_true", help="Export model usage data to file"
    )
    add_common_cli_args(parser)

    args = parser.parse_args()
    project_dir = Path.cwd()
    start_date, end_date = parse_date_args(args)

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
