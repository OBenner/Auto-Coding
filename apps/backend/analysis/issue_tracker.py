#!/usr/bin/env python3
"""
Issue Tracker Module
====================

Tracks historical issues for predictive analysis and prevention effectiveness.
Stores issues over time to identify patterns, measure improvement, and provide
insights into code quality trends.

The issue tracker is used by:
- PredictiveScanner: To analyze historical patterns
- QA Agent: To track prevention effectiveness
- Analytics: To provide metrics on code quality over time

Usage:
    from analysis.issue_tracker import IssueTracker

    tracker = IssueTracker(spec_dir)
    tracker.record_issues(scan_results)
    trends = tracker.get_trends(days=30)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class IssueRecord:
    """
    Represents a single issue record at a point in time.

    Attributes:
        timestamp: When this issue was recorded
        issue_type: Type of issue (bug, performance, code_smell, security)
        severity: Severity level (critical, high, medium, low)
        source: Which detector found this issue
        title: Short title of the issue
        description: Detailed description
        file: File where issue was found
        line: Line number (if applicable)
        category: Category/subtype (e.g., "NoneType error", "N+1 query")
        resolved: Whether this issue has been resolved
        resolved_at: When this issue was resolved (if applicable)
    """

    timestamp: str  # ISO format timestamp
    issue_type: str  # bug, performance, code_smell, security
    severity: str  # critical, high, medium, low
    source: str  # bug_detector, performance_analyzer, etc.
    title: str
    description: str
    file: str | None = None
    line: int | None = None
    category: str | None = None  # Subtype for grouping
    resolved: bool = False
    resolved_at: str | None = None  # ISO format timestamp


@dataclass
class IssueTrend:
    """
    Represents a trend in issue occurrence over time.

    Attributes:
        category: Issue category
        severity: Severity level
        count_7_days: Count in last 7 days
        count_30_days: Count in last 30 days
        count_90_days: Count in last 90 days
        trend_direction: Direction of trend (increasing, decreasing, stable)
        change_percentage: Percentage change from previous period
    """

    category: str
    severity: str
    count_7_days: int
    count_30_days: int
    count_90_days: int
    trend_direction: str  # increasing, decreasing, stable
    change_percentage: float


@dataclass
class IssueSummary:
    """
    Summary statistics for issues.

    Attributes:
        total_issues: Total number of issues
        critical_count: Number of critical issues
        high_count: Number of high issues
        medium_count: Number of medium issues
        low_count: Number of low issues
        by_type: Breakdown by issue type
        by_category: Breakdown by category
        resolved_count: Number of resolved issues
        unresolved_count: Number of unresolved issues
    """

    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    by_type: dict[str, int]
    by_category: dict[str, int]
    resolved_count: int
    unresolved_count: int


@dataclass
class PreventionEffectiveness:
    """
    Metrics for measuring prevention effectiveness.

    Attributes:
        period_start: Start of analysis period
        period_end: End of analysis period
        issues_prevented: Estimated number of issues prevented
        issues_found: Number of issues found
        prevention_rate: Percentage of issues prevented
        accuracy: Accuracy of predictions (if available)
        false_positive_rate: Rate of false positives
    """

    period_start: str
    period_end: str
    issues_prevented: int
    issues_found: int
    prevention_rate: float
    accuracy: float | None = None
    false_positive_rate: float | None = None


# =============================================================================
# ISSUE TRACKER
# =============================================================================


class IssueTracker:
    """
    Tracks historical issues for predictive analysis.

    Features:
    - Record issues from various detectors
    - Query historical data
    - Calculate trends and patterns
    - Measure prevention effectiveness
    """

    def __init__(self, storage_dir: Path) -> None:
        """
        Initialize the issue tracker.

        Args:
            storage_dir: Directory to store issue history
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._issues_file = self.storage_dir / "issue_history.json"
        self._issues: list[IssueRecord] = []
        self._load_issues()

    def record_issues(
        self,
        issues: list[dict[str, Any]],
        issue_type: str,
        source: str,
    ) -> int:
        """
        Record issues from a scan.

        Args:
            issues: List of issue dictionaries
            issue_type: Type of issues (bug, performance, code_smell, security)
            source: Source detector

        Returns:
            Number of issues recorded
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        recorded = 0

        for issue in issues:
            try:
                record = IssueRecord(
                    timestamp=timestamp,
                    issue_type=issue_type,
                    severity=issue.get("severity", "medium").lower(),
                    source=source,
                    title=issue.get("title", "Unknown issue"),
                    description=issue.get("description", ""),
                    file=issue.get("file"),
                    line=issue.get("line"),
                    category=issue.get("category"),
                )
                self._issues.append(record)
                recorded += 1
            except Exception as e:
                logger.warning(f"Failed to record issue: {e}")

        self._save_issues()
        return recorded

    def record_single_issue(
        self,
        issue_type: str,
        severity: str,
        source: str,
        title: str,
        description: str,
        file: str | None = None,
        line: int | None = None,
        category: str | None = None,
    ) -> None:
        """
        Record a single issue.

        Args:
            issue_type: Type of issue
            severity: Severity level
            source: Source detector
            title: Issue title
            description: Issue description
            file: File path
            line: Line number
            category: Issue category
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        record = IssueRecord(
            timestamp=timestamp,
            issue_type=issue_type,
            severity=severity.lower(),
            source=source,
            title=title,
            description=description,
            file=file,
            line=line,
            category=category,
        )

        self._issues.append(record)
        self._save_issues()

    def mark_resolved(
        self,
        file: str,
        line: int | None = None,
        category: str | None = None,
    ) -> int:
        """
        Mark issues as resolved.

        Args:
            file: File where issue was found
            line: Line number (optional, for more specific matching)
            category: Issue category (optional, for more specific matching)

        Returns:
            Number of issues marked as resolved
        """
        resolved = 0
        resolved_at = datetime.now(timezone.utc).isoformat()

        for issue in self._issues:
            if issue.resolved:
                continue

            # Check if this issue matches
            if issue.file != file:
                continue

            if line is not None and issue.line != line:
                continue

            if category is not None and issue.category != category:
                continue

            # Mark as resolved
            issue.resolved = True
            issue.resolved_at = resolved_at
            resolved += 1

        if resolved > 0:
            self._save_issues()

        return resolved

    def get_issues(
        self,
        issue_type: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        resolved: bool | None = None,
        days: int | None = None,
        limit: int | None = None,
    ) -> list[IssueRecord]:
        """
        Query issues with optional filters.

        Args:
            issue_type: Filter by issue type
            severity: Filter by severity
            category: Filter by category
            resolved: Filter by resolution status
            days: Only include issues from last N days
            limit: Maximum number of issues to return

        Returns:
            List of matching issues
        """
        issues = self._issues.copy()

        # Filter by type
        if issue_type:
            issues = [i for i in issues if i.issue_type == issue_type]

        # Filter by severity
        if severity:
            issues = [i for i in issues if i.severity == severity.lower()]

        # Filter by category
        if category:
            issues = [i for i in issues if i.category == category]

        # Filter by resolution status
        if resolved is not None:
            issues = [i for i in issues if i.resolved == resolved]

        # Filter by time
        if days:
            cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
            issues = [
                i
                for i in issues
                if datetime.fromisoformat(i.timestamp).timestamp() >= cutoff
            ]

        # Sort by timestamp (newest first)
        issues.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        if limit:
            issues = issues[:limit]

        return issues

    def get_summary(self, days: int | None = None) -> IssueSummary:
        """
        Get summary statistics for issues.

        Args:
            days: Only include issues from last N days (None = all time)

        Returns:
            IssueSummary with statistics
        """
        issues = self.get_issues(days=days)

        # Count by severity
        critical = sum(1 for i in issues if i.severity == "critical")
        high = sum(1 for i in issues if i.severity == "high")
        medium = sum(1 for i in issues if i.severity == "medium")
        low = sum(1 for i in issues if i.severity == "low")

        # Count by type
        by_type: dict[str, int] = {}
        for issue in issues:
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1

        # Count by category
        by_category: dict[str, int] = {}
        for issue in issues:
            if issue.category:
                by_category[issue.category] = by_category.get(issue.category, 0) + 1

        # Count resolved vs unresolved
        resolved = sum(1 for i in issues if i.resolved)
        unresolved = len(issues) - resolved

        return IssueSummary(
            total_issues=len(issues),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            by_type=by_type,
            by_category=by_category,
            resolved_count=resolved,
            unresolved_count=unresolved,
        )

    def get_trends(
        self,
        days: int = 30,
        category: str | None = None,
        severity: str | None = None,
    ) -> list[IssueTrend]:
        """
        Calculate trends for issues over time.

        Args:
            days: Analysis period in days
            category: Filter by category (optional)
            severity: Filter by severity (optional)

        Returns:
            List of IssueTrend objects
        """
        # Get issues for different time periods
        issues_7 = self.get_issues(days=7, category=category, severity=severity)
        issues_30 = self.get_issues(days=30, category=category, severity=severity)
        issues_90 = self.get_issues(days=90, category=category, severity=severity)

        # Group by category and severity
        groups: dict[tuple[str, str], dict[str, list[IssueRecord]]] = {}

        for issue in issues_90:
            key = (issue.category or "uncategorized", issue.severity)
            if key not in groups:
                groups[key] = {"7": [], "30": [], "90": []}

            # Add to appropriate period buckets
            issue_time = datetime.fromisoformat(issue.timestamp).timestamp()
            now = datetime.now(timezone.utc).timestamp()

            if now - issue_time <= 7 * 86400:
                groups[key]["7"].append(issue)
            if now - issue_time <= 30 * 86400:
                groups[key]["30"].append(issue)
            groups[key]["90"].append(issue)

        # Calculate trends
        trends = []
        for (cat, sev), buckets in groups.items():
            count_7 = len(buckets["7"])
            count_30 = len(buckets["30"])
            count_90 = len(buckets["90"])

            # Calculate trend direction
            if count_7 > count_30 * 1.2:
                direction = "increasing"
                change = ((count_7 - count_30) / max(count_30, 1)) * 100
            elif count_7 < count_30 * 0.8:
                direction = "decreasing"
                change = ((count_30 - count_7) / max(count_30, 1)) * 100
            else:
                direction = "stable"
                change = 0.0

            trends.append(
                IssueTrend(
                    category=cat,
                    severity=sev,
                    count_7_days=count_7,
                    count_30_days=count_30,
                    count_90_days=count_90,
                    trend_direction=direction,
                    change_percentage=change,
                )
            )

        # Sort by count (most concerning first)
        trends.sort(key=lambda x: x.count_7_days, reverse=True)

        return trends

    def calculate_prevention_effectiveness(
        self,
        days: int = 30,
    ) -> PreventionEffectiveness:
        """
        Calculate prevention effectiveness metrics.

        Args:
            days: Analysis period in days

        Returns:
            PreventionEffectiveness metrics
        """
        issues = self.get_issues(days=days)

        # Calculate resolved issues as "prevented"
        resolved = sum(1 for i in issues if i.resolved)
        total = len(issues)

        prevention_rate = (resolved / max(total, 1)) * 100 if total > 0 else 0.0

        period_end = datetime.now(timezone.utc)
        period_start = period_end.timestamp() - (days * 86400)

        return PreventionEffectiveness(
            period_start=datetime.fromtimestamp(period_start, timezone.utc).isoformat(),
            period_end=period_end.isoformat(),
            issues_prevented=resolved,
            issues_found=total,
            prevention_rate=prevention_rate,
        )

    def get_top_categories(
        self,
        days: int = 30,
        limit: int = 10,
    ) -> list[tuple[str, int]]:
        """
        Get top issue categories by frequency.

        Args:
            days: Analysis period in days
            limit: Maximum number of categories to return

        Returns:
            List of (category, count) tuples
        """
        issues = self.get_issues(days=days)

        category_counts: dict[str, int] = {}
        for issue in issues:
            cat = issue.category or "uncategorized"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Sort by count
        sorted_categories = sorted(
            category_counts.items(), key=lambda x: x[1], reverse=True
        )

        return sorted_categories[:limit]

    def _load_issues(self) -> None:
        """Load issues from storage."""
        if not self._issues_file.exists():
            return

        try:
            with open(self._issues_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._issues = [
                IssueRecord(
                    timestamp=record["timestamp"],
                    issue_type=record["issue_type"],
                    severity=record["severity"],
                    source=record["source"],
                    title=record["title"],
                    description=record["description"],
                    file=record.get("file"),
                    line=record.get("line"),
                    category=record.get("category"),
                    resolved=record.get("resolved", False),
                    resolved_at=record.get("resolved_at"),
                )
                for record in data
            ]

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to load issues: {e}")
            self._issues = []

    def _save_issues(self) -> None:
        """Save issues to storage."""
        data = [
            {
                "timestamp": issue.timestamp,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "source": issue.source,
                "title": issue.title,
                "description": issue.description,
                "file": issue.file,
                "line": issue.line,
                "category": issue.category,
                "resolved": issue.resolved,
                "resolved_at": issue.resolved_at,
            }
            for issue in self._issues
        ]

        with open(self._issues_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def to_dict(self, summary: IssueSummary) -> dict[str, Any]:
        """
        Convert summary to dictionary for JSON serialization.

        Args:
            summary: IssueSummary to convert

        Returns:
            Dictionary representation
        """
        return {
            "total_issues": summary.total_issues,
            "critical_count": summary.critical_count,
            "high_count": summary.high_count,
            "medium_count": summary.medium_count,
            "low_count": summary.low_count,
            "by_type": summary.by_type,
            "by_category": summary.by_category,
            "resolved_count": summary.resolved_count,
            "unresolved_count": summary.unresolved_count,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_tracker(spec_dir: Path) -> IssueTracker:
    """
    Get or create an issue tracker for the spec.

    Args:
        spec_dir: Path to spec directory

    Returns:
        IssueTracker instance
    """
    storage_dir = Path(spec_dir) / "issue_tracking"
    return IssueTracker(storage_dir)


def record_scan_results(
    spec_dir: Path,
    scan_results: dict[str, Any],
    source: str,
) -> int:
    """
    Record scan results from a detector.

    Args:
        spec_dir: Path to spec directory
        scan_results: Results dict with 'issues' key
        source: Source detector name

    Returns:
        Number of issues recorded
    """
    tracker = get_tracker(spec_dir)
    issues = scan_results.get("issues", [])

    # Determine issue type from source
    issue_type_map = {
        "bug_detector": "bug",
        "performance_analyzer": "performance",
        "code_smell_detector": "code_smell",
        "security_scanner": "security",
    }

    issue_type = issue_type_map.get(source, "unknown")

    return tracker.record_issues(issues, issue_type, source)


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Track and analyze issues")
    parser.add_argument("spec_dir", type=Path, help="Path to spec directory")
    parser.add_argument("--summary", action="store_true", help="Show summary")
    parser.add_argument("--trends", action="store_true", help="Show trends")
    parser.add_argument("--days", type=int, default=30, help="Analysis period in days")
    parser.add_argument("--type", help="Filter by issue type")
    parser.add_argument("--severity", help="Filter by severity")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    tracker = get_tracker(args.spec_dir)

    if args.summary:
        summary = tracker.get_summary(days=args.days)
        if args.json:
            print(json.dumps(tracker.to_dict(summary), indent=2))
        else:
            print(f"Issue Summary (Last {args.days} days):")
            print(f"  Total Issues: {summary.total_issues}")
            print(f"  Critical: {summary.critical_count}")
            print(f"  High: {summary.high_count}")
            print(f"  Medium: {summary.medium_count}")
            print(f"  Low: {summary.low_count}")
            print(f"  Resolved: {summary.resolved_count}")
            print(f"  Unresolved: {summary.unresolved_count}")

            if summary.by_type:
                print(f"\nBy Type:")
                for issue_type, count in summary.by_type.items():
                    print(f"  {issue_type}: {count}")

            if summary.by_category:
                print(f"\nTop Categories:")
                for cat, count in list(summary.by_category.items())[:5]:
                    print(f"  {cat}: {count}")

    elif args.trends:
        trends = tracker.get_trends(days=args.days, category=args.type, severity=args.severity)

        if args.json:
            print(json.dumps([t.__dict__ for t in trends], indent=2))
        else:
            print(f"Issue Trends (Last {args.days} days):")
            for trend in trends[:10]:
                direction_icon = "↑" if trend.trend_direction == "increasing" else "↓" if trend.trend_direction == "decreasing" else "→"
                print(f"  {trend.category} [{trend.severity}] {direction_icon}")
                print(f"    7d: {trend.count_7_days} | 30d: {trend.count_30_days} | 90d: {trend.count_90_days}")
                if trend.change_percentage != 0:
                    print(f"    Change: {trend.change_percentage:+.1f}%")
    else:
        # List recent issues
        issues = tracker.get_issues(days=args.days, type=args.type, severity=args.severity, limit=20)

        if args.json:
            print(json.dumps([i.__dict__ for i in issues], indent=2))
        else:
            print(f"Recent Issues (Last {args.days} days):")
            for issue in issues:
                status = "✓" if issue.resolved else "✗"
                print(f"  {status} [{issue.severity.upper()}] {issue.title}")
                if issue.file:
                    print(f"    {issue.file}:{issue.line or '?'}")
                if issue.category:
                    print(f"    Category: {issue.category}")


if __name__ == "__main__":
    main()
