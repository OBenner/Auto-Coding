"""
Agent Performance Analytics Service
====================================

Tracks and analyzes agent performance across all specs.
Provides metrics on success rates, completion times, error patterns, and quality.

Components:
- AnalyticsService: Main service for aggregating and analyzing spec data
- MetricsSummary: Performance metrics aggregated from all specs
- AgentStats: Per-agent-type statistics

Usage:
    # Create analytics service
    service = AnalyticsService(specs_dir=Path(".auto-claude/specs"))

    # Get overall metrics
    summary = service.get_metrics_summary()

    # Get agent-specific stats
    stats = service.get_agent_stats()

    # Get trend data
    trends = service.get_trend_data(days=30)
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass
class AgentStats:
    """Statistics for a specific agent type."""

    agent_type: str
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    avg_completion_time: float = 0.0  # in seconds
    error_patterns: dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_attempts / self.total_attempts) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_type": self.agent_type,
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": round(self.success_rate, 2),
            "total_cost": round(self.total_cost, 2),
            "total_tokens": self.total_tokens,
            "avg_completion_time": round(self.avg_completion_time, 2),
            "error_patterns": self.error_patterns,
        }


@dataclass
class TaskComplexityStats:
    """Statistics grouped by task complexity."""

    complexity: str
    total_tasks: int = 0
    successful_tasks: int = 0
    avg_completion_time: float = 0.0
    avg_cost: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "complexity": self.complexity,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "success_rate": round(self.success_rate, 2),
            "avg_completion_time": round(self.avg_completion_time, 2),
            "avg_cost": round(self.avg_cost, 2),
        }


@dataclass
class QAStats:
    """QA reviewer statistics."""

    total_reviews: int = 0
    approved: int = 0
    rejected: int = 0
    common_issues: dict[str, int] = field(default_factory=dict)

    @property
    def rejection_rate(self) -> float:
        """Calculate rejection rate percentage."""
        if self.total_reviews == 0:
            return 0.0
        return (self.rejected / self.total_reviews) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_reviews": self.total_reviews,
            "approved": self.approved,
            "rejected": self.rejected,
            "rejection_rate": round(self.rejection_rate, 2),
            "common_issues": self.common_issues,
        }


@dataclass
class MetricsSummary:
    """Overall metrics summary."""

    total_specs: int = 0
    completed_specs: int = 0
    failed_specs: int = 0
    in_progress_specs: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    agent_stats: dict[str, AgentStats] = field(default_factory=dict)
    complexity_stats: dict[str, TaskComplexityStats] = field(default_factory=dict)
    qa_stats: QAStats = field(default_factory=QAStats)
    last_updated: str = ""

    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate percentage."""
        if self.total_specs == 0:
            return 0.0
        return (self.completed_specs / self.total_specs) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_specs": self.total_specs,
            "completed_specs": self.completed_specs,
            "failed_specs": self.failed_specs,
            "in_progress_specs": self.in_progress_specs,
            "overall_success_rate": round(self.overall_success_rate, 2),
            "total_cost": round(self.total_cost, 2),
            "total_tokens": self.total_tokens,
            "agent_stats": {
                name: stats.to_dict() for name, stats in self.agent_stats.items()
            },
            "complexity_stats": {
                name: stats.to_dict() for name, stats in self.complexity_stats.items()
            },
            "qa_stats": self.qa_stats.to_dict(),
            "last_updated": self.last_updated,
        }


@dataclass
class TrendDataPoint:
    """Single data point in trend analysis."""

    date: str
    success_rate: float
    total_tasks: int
    total_cost: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date,
            "success_rate": round(self.success_rate, 2),
            "total_tasks": self.total_tasks,
            "total_cost": round(self.total_cost, 2),
        }


class AnalyticsService:
    """
    Service for analyzing agent performance across all specs.

    Aggregates data from multiple sources:
    - cost_report.json: Token usage and costs
    - attempt_history.json: Retry attempts and stuck subtasks
    - implementation_plan.json: Subtask status and completion
    - qa_report.md: QA review results

    Args:
        specs_dir: Path to specs directory (e.g., .auto-claude/specs)
    """

    def __init__(self, specs_dir: Path):
        """Initialize analytics service."""
        self.specs_dir = Path(specs_dir)

    def _get_all_spec_dirs(self) -> list[Path]:
        """Get all spec directories."""
        if not self.specs_dir.exists():
            return []

        # Get all directories in specs folder
        return [
            d
            for d in self.specs_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def _load_json_file(self, file_path: Path) -> dict[str, Any] | None:
        """Load JSON file with error handling."""
        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _parse_cost_report(self, spec_dir: Path) -> dict[str, Any]:
        """Parse cost_report.json from a spec directory."""
        cost_file = spec_dir / "cost_report.json"
        data = self._load_json_file(cost_file)

        if not data:
            return {"total_cost": 0.0, "total_tokens": 0, "agent_usage": {}}

        total_cost = data.get("total_cost", 0.0)
        records = data.get("records", [])

        # Aggregate by agent type
        agent_usage = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "count": 0})
        total_tokens = 0

        for record in records:
            agent_type = record.get("agent_type", "unknown")
            cost = record.get("cost", 0.0)
            input_tokens = record.get("input_tokens", 0)
            output_tokens = record.get("output_tokens", 0)
            tokens = input_tokens + output_tokens

            agent_usage[agent_type]["cost"] += cost
            agent_usage[agent_type]["tokens"] += tokens
            agent_usage[agent_type]["count"] += 1
            total_tokens += tokens

        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "agent_usage": dict(agent_usage),
        }

    def _parse_attempt_history(self, spec_dir: Path) -> dict[str, Any]:
        """Parse attempt_history.json from a spec directory.

        Supports both legacy and new locations:
          - <spec_dir>/attempt_history.json
          - <spec_dir>/memory/attempt_history.json
        """
        # Preferred new location
        memory_dir = spec_dir / "memory"
        attempt_file = memory_dir / "attempt_history.json"
        data = self._load_json_file(attempt_file)

        if not data:
            # Fallback: legacy location at spec root
            legacy_file = spec_dir / "attempt_history.json"
            data = self._load_json_file(legacy_file)

        if not data:
            return {"subtasks": {}, "stuck_subtasks": []}

        return {
            "subtasks": data.get("subtasks", {}),
            "stuck_subtasks": data.get("stuck_subtasks", []),
        }

    def _parse_implementation_plan(self, spec_dir: Path) -> dict[str, Any]:
        """Parse implementation_plan.json from a spec directory."""
        plan_file = spec_dir / "implementation_plan.json"
        data = self._load_json_file(plan_file)

        if not data:
            return {
                "status": "unknown",
                "phases": [],
                "complexity": "unknown",
            }

        # Count subtask statuses
        total_subtasks = 0
        completed_subtasks = 0
        failed_subtasks = 0

        for phase in data.get("phases", []):
            for subtask in phase.get("subtasks", []):
                total_subtasks += 1
                status = subtask.get("status", "pending")
                if status == "completed":
                    completed_subtasks += 1
                elif status == "failed":
                    failed_subtasks += 1

        return {
            "status": data.get("status", "unknown"),
            "phases": data.get("phases", []),
            "total_subtasks": total_subtasks,
            "completed_subtasks": completed_subtasks,
            "failed_subtasks": failed_subtasks,
            "complexity": data.get("complexity", "unknown"),
        }

    def _parse_qa_report(self, spec_dir: Path) -> dict[str, Any]:
        """Parse qa_report.md from a spec directory."""
        qa_file = spec_dir / "qa_report.md"

        if not qa_file.exists():
            return {"status": "not_reviewed", "issues": []}

        try:
            with open(qa_file, encoding="utf-8") as f:
                content = f.read()

            # Check for approval/rejection
            if "✅ APPROVED" in content or "APPROVED" in content:
                status = "approved"
            elif "❌ REJECTED" in content or "REJECTED" in content:
                status = "rejected"
            else:
                status = "in_review"

            # Extract issues (look for bullet points or numbered lists)
            issues = []
            issue_pattern = r"(?:^|\n)(?:[-*]|\d+\.)\s+(.+?)(?=\n|$)"
            matches = re.findall(issue_pattern, content, re.MULTILINE)
            issues = [m.strip() for m in matches if len(m.strip()) > 10]

            return {
                "status": status,
                "issues": issues,
            }
        except (OSError, UnicodeDecodeError):
            return {"status": "error", "issues": []}

    def _extract_complexity(self, spec_dir: Path) -> str:
        """Extract task complexity from spec name or implementation plan."""
        # Try from implementation plan first
        plan_data = self._parse_implementation_plan(spec_dir)
        complexity = plan_data.get("complexity", "unknown")
        if complexity != "unknown":
            return complexity

        # Fallback: infer from spec name or default to "standard"
        spec_name = spec_dir.name.lower()
        if any(word in spec_name for word in ["simple", "quick", "fix"]):
            return "simple"
        elif any(word in spec_name for word in ["complex", "refactor", "migration"]):
            return "complex"
        else:
            return "standard"

    def get_metrics_summary(self) -> MetricsSummary:
        """
        Get overall metrics summary across all specs.

        Returns:
            MetricsSummary with aggregated metrics
        """
        summary = MetricsSummary(last_updated=datetime.utcnow().isoformat() + "Z")

        spec_dirs = self._get_all_spec_dirs()
        summary.total_specs = len(spec_dirs)

        for spec_dir in spec_dirs:
            # Parse all data sources
            cost_data = self._parse_cost_report(spec_dir)
            attempt_data = self._parse_attempt_history(spec_dir)
            plan_data = self._parse_implementation_plan(spec_dir)
            qa_data = self._parse_qa_report(spec_dir)

            # Update spec status counts
            status = plan_data["status"]
            if status == "completed":
                summary.completed_specs += 1
            elif status == "failed":
                summary.failed_specs += 1
            elif status in ["in_progress", "pending"]:
                summary.in_progress_specs += 1

            # Update cost and token totals
            summary.total_cost += cost_data["total_cost"]
            summary.total_tokens += cost_data["total_tokens"]

            # Update agent stats
            attempt_subtasks = attempt_data.get("subtasks", {})

            for agent_type, usage in cost_data["agent_usage"].items():
                if agent_type not in summary.agent_stats:
                    summary.agent_stats[agent_type] = AgentStats(agent_type=agent_type)

                stats = summary.agent_stats[agent_type]
                stats.total_attempts += usage["count"]
                stats.total_cost += usage["cost"]
                stats.total_tokens += usage["tokens"]

                # Prefer attempt_history for per-agent outcome data
                agent_attempts = attempt_subtasks.get(agent_type)
                if isinstance(agent_attempts, list):
                    for attempt in agent_attempts:
                        outcome = attempt.get("status") or attempt.get("outcome")
                        if outcome == "success":
                            stats.successful_attempts += 1
                        elif outcome in {"failed", "error"}:
                            stats.failed_attempts += 1
                else:
                    # Fallback: align successes/failures with usage count
                    if plan_data["failed_subtasks"] > 0:
                        stats.failed_attempts += usage["count"]
                    elif plan_data["completed_subtasks"] > 0:
                        stats.successful_attempts += usage["count"]

            # Update complexity stats
            complexity = self._extract_complexity(spec_dir)
            if complexity not in summary.complexity_stats:
                summary.complexity_stats[complexity] = TaskComplexityStats(
                    complexity=complexity
                )

            comp_stats = summary.complexity_stats[complexity]
            comp_stats.total_tasks += 1
            comp_stats.avg_cost += cost_data["total_cost"]

            if status == "completed":
                comp_stats.successful_tasks += 1

            # Update QA stats
            if qa_data["status"] != "not_reviewed":
                summary.qa_stats.total_reviews += 1
                if qa_data["status"] == "approved":
                    summary.qa_stats.approved += 1
                elif qa_data["status"] == "rejected":
                    summary.qa_stats.rejected += 1

                # Count common issues
                for issue in qa_data["issues"]:
                    # Extract issue category (first few words)
                    category = " ".join(issue.split()[:3])
                    summary.qa_stats.common_issues[category] = (
                        summary.qa_stats.common_issues.get(category, 0) + 1
                    )

        # Calculate averages for complexity stats
        for comp_stats in summary.complexity_stats.values():
            if comp_stats.total_tasks > 0:
                comp_stats.avg_cost /= comp_stats.total_tasks

        return summary

    def get_agent_stats(self) -> dict[str, AgentStats]:
        """
        Get statistics broken down by agent type.

        Returns:
            Dictionary mapping agent type to AgentStats
        """
        summary = self.get_metrics_summary()
        return summary.agent_stats

    def get_trend_data(self, days: int = 30) -> list[TrendDataPoint]:
        """
        Get trend data for the last N days.

        Args:
            days: Number of days to include in trend analysis

        Returns:
            List of TrendDataPoint for each day
        """
        # Group specs by date (using last_updated or created_at)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        daily_data = defaultdict(lambda: {"total": 0, "completed": 0, "cost": 0.0})

        spec_dirs = self._get_all_spec_dirs()

        for spec_dir in spec_dirs:
            plan_data = self._parse_implementation_plan(spec_dir)
            cost_data = self._parse_cost_report(spec_dir)

            # Try to get date from plan metadata
            plan_file = spec_dir / "implementation_plan.json"
            plan_json = self._load_json_file(plan_file)
            if not plan_json:
                continue

            # Get date from updated_at or metadata
            date_str = plan_json.get("updated_at") or plan_json.get("metadata", {}).get(
                "created_at"
            )

            # Parse spec date, falling back to filesystem mtime
            spec_date = None
            if date_str:
                try:
                    spec_date = datetime.fromisoformat(
                        str(date_str).replace("Z", "+00:00")
                    )
                except (TypeError, ValueError):
                    pass

            if spec_date is None:
                try:
                    mtime = plan_file.stat().st_mtime
                except OSError:
                    try:
                        mtime = spec_dir.stat().st_mtime
                    except OSError:
                        continue
                spec_date = datetime.fromtimestamp(mtime, tz=timezone.utc)

            # Ensure spec_date is timezone-aware UTC for comparison
            if spec_date.tzinfo is None:
                spec_date = spec_date.replace(tzinfo=timezone.utc)
            else:
                spec_date = spec_date.astimezone(timezone.utc)

            if spec_date < cutoff_date:
                continue

            # Group by date (YYYY-MM-DD)
            date_key = spec_date.strftime("%Y-%m-%d")

            daily_data[date_key]["total"] += 1
            daily_data[date_key]["cost"] += cost_data["total_cost"]

            if plan_data["status"] == "completed":
                daily_data[date_key]["completed"] += 1

        # Convert to TrendDataPoint list
        trend_points = []
        for date_key in sorted(daily_data.keys()):
            data = daily_data[date_key]
            success_rate = (
                (data["completed"] / data["total"]) * 100 if data["total"] > 0 else 0.0
            )
            trend_points.append(
                TrendDataPoint(
                    date=date_key,
                    success_rate=success_rate,
                    total_tasks=data["total"],
                    total_cost=data["cost"],
                )
            )

        return trend_points

    def get_analytics_report(self) -> dict[str, Any]:
        """
        Get comprehensive analytics report.

        Returns:
            Dictionary with all analytics data
        """
        summary = self.get_metrics_summary()
        trends = self.get_trend_data(days=30)

        return {
            "summary": summary.to_dict(),
            "trends": [t.to_dict() for t in trends],
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
