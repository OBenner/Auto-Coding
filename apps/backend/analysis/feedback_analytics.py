"""
Feedback Analytics Aggregator
==============================

Aggregates user feedback across all specs to provide insights into
agent performance, user satisfaction, and areas for improvement.

Provides analytics on:
- Feedback distribution (accepted/rejected/modified)
- Satisfaction scores and ratings
- Sentiment trends
- Top issues and complaints
- Improvement tracking
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
class FeedbackMetrics:
    """
    Metrics for a single feedback item.

    Captures key feedback attributes for individual submissions.
    """

    feedback_id: str
    spec_id: str | None = None
    spec_name: str | None = None

    # Feedback details
    feedback_type: str = "accepted"  # accepted, rejected, modified
    agent_type: str = "coder"  # planner, coder, qa_reviewer, qa_fixer
    task_description: str = ""
    rating: int | None = None  # 0-5 or None

    # Sentiment analysis (from sentiment_analyzer.py)
    sentiment: str | None = None  # positive, negative, neutral
    sentiment_confidence: float = 0.0
    category: str | None = None  # feature_request, bug_report, praise, complaint
    severity: str | None = None  # low, medium, high (for negative feedback)

    # Timestamps
    created_at: datetime | None = None

    # Context
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feedback_id": self.feedback_id,
            "spec_id": self.spec_id,
            "spec_name": self.spec_name,
            "feedback_type": self.feedback_type,
            "agent_type": self.agent_type,
            "task_description": self.task_description,
            "rating": self.rating,
            "sentiment": self.sentiment,
            "sentiment_confidence": self.sentiment_confidence,
            "category": self.category,
            "severity": self.severity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedbackMetrics:
        """Create from dictionary."""
        return cls(
            feedback_id=data["feedback_id"],
            spec_id=data.get("spec_id"),
            spec_name=data.get("spec_name"),
            feedback_type=data.get("feedback_type", "accepted"),
            agent_type=data.get("agent_type", "coder"),
            task_description=data.get("task_description", ""),
            rating=data.get("rating"),
            sentiment=data.get("sentiment"),
            sentiment_confidence=data.get("sentiment_confidence", 0.0),
            category=data.get("category"),
            severity=data.get("severity"),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            context=data.get("context", {}),
        )

    @property
    def is_positive(self) -> bool:
        """Check if feedback is positive."""
        return self.feedback_type == "accepted" or (
            self.rating is not None and self.rating >= 4
        )

    @property
    def is_negative(self) -> bool:
        """Check if feedback is negative."""
        return self.feedback_type == "rejected" or (
            self.rating is not None and self.rating <= 2
        )


@dataclass
class FeedbackSummary:
    """
    Aggregated feedback metrics across all specs.

    Provides high-level insights into user satisfaction and agent performance.
    """

    # Time period
    period_start: datetime
    period_end: datetime

    # Overall metrics
    total_feedback: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    modified_count: int = 0

    # Ratings
    average_rating: float | None = None
    total_ratings: int = 0

    # Sentiment distribution
    positive_sentiment_count: int = 0
    negative_sentiment_count: int = 0
    neutral_sentiment_count: int = 0

    # Breakdown by agent type
    feedback_by_agent: dict[str, int] = field(default_factory=dict)
    ratings_by_agent: dict[str, float] = field(default_factory=dict)

    # Top issues (from negative feedback)
    top_issues: list[dict[str, Any]] = field(default_factory=list)

    # Top categories
    feedback_by_category: dict[str, int] = field(default_factory=dict)

    # Satisfaction metrics
    satisfaction_rate: float = 0.0  # Percentage of positive feedback
    net_promoter_score: float | None = None  # NPS calculation if using 0-10 ratings

    # Detailed feedback list
    feedback_items: list[FeedbackMetrics] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_feedback": self.total_feedback,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "modified_count": self.modified_count,
            "average_rating": round(self.average_rating, 2)
            if self.average_rating is not None
            else None,
            "total_ratings": self.total_ratings,
            "positive_sentiment_count": self.positive_sentiment_count,
            "negative_sentiment_count": self.negative_sentiment_count,
            "neutral_sentiment_count": self.neutral_sentiment_count,
            "feedback_by_agent": self.feedback_by_agent,
            "ratings_by_agent": {
                agent: round(rating, 2) for agent, rating in self.ratings_by_agent.items()
            },
            "top_issues": self.top_issues,
            "feedback_by_category": self.feedback_by_category,
            "satisfaction_rate": round(self.satisfaction_rate, 3),
            "net_promoter_score": round(self.net_promoter_score, 2)
            if self.net_promoter_score is not None
            else None,
            "feedback_items": [item.to_dict() for item in self.feedback_items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedbackSummary:
        """Create from dictionary."""
        return cls(
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
            total_feedback=data.get("total_feedback", 0),
            accepted_count=data.get("accepted_count", 0),
            rejected_count=data.get("rejected_count", 0),
            modified_count=data.get("modified_count", 0),
            average_rating=data.get("average_rating"),
            total_ratings=data.get("total_ratings", 0),
            positive_sentiment_count=data.get("positive_sentiment_count", 0),
            negative_sentiment_count=data.get("negative_sentiment_count", 0),
            neutral_sentiment_count=data.get("neutral_sentiment_count", 0),
            feedback_by_agent=data.get("feedback_by_agent", {}),
            ratings_by_agent=data.get("ratings_by_agent", {}),
            top_issues=data.get("top_issues", []),
            feedback_by_category=data.get("feedback_by_category", {}),
            satisfaction_rate=data.get("satisfaction_rate", 0.0),
            net_promoter_score=data.get("net_promoter_score"),
            feedback_items=[
                FeedbackMetrics.from_dict(item) for item in data.get("feedback_items", [])
            ],
        )


# =============================================================================
# FEEDBACK COLLECTION
# =============================================================================


async def collect_feedback_from_graphiti(
    project_dir: Path,
    spec_dir: Path | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[FeedbackMetrics]:
    """
    Collect feedback from Graphiti memory.

    Args:
        project_dir: Project directory
        spec_dir: Optional spec directory (if None, collect all project feedback)
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of FeedbackMetrics
    """
    from integrations.graphiti.queries_pkg.graphiti import GraphitiMemory
    from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_USER_FEEDBACK

    feedback_list = []

    try:
        # Initialize Graphiti memory
        memory = GraphitiMemory(spec_dir or project_dir, project_dir)

        # Query feedback episodes
        # For now, we use search with a broad query to get all feedback
        # TODO: Add a dedicated get_episodes_by_type method to Graphiti
        query = "user feedback ratings comments"
        results = await memory.search(query, max_results=1000)

        # Filter for user_feedback episodes
        for result in results:
            # Check if this is a feedback episode
            if not isinstance(result, dict):
                continue

            episode_data = result.get("episode", {})
            if episode_data.get("episode_type") != EPISODE_TYPE_USER_FEEDBACK:
                continue

            # Extract feedback data
            feedback_data = episode_data.get("_user_feedback", {})
            if not feedback_data:
                continue

            # Create FeedbackMetrics
            feedback_id = result.get("id", str(len(feedback_list)))
            created_at_str = result.get("created_at")
            created_at = (
                datetime.fromisoformat(created_at_str)
                if created_at_str
                else datetime.now(UTC)
            )

            # Apply date filters
            if start_date and created_at < start_date:
                continue
            if end_date and created_at > end_date:
                continue

            # Extract sentiment if available
            sentiment_data = feedback_data.get("sentiment", {})

            feedback = FeedbackMetrics(
                feedback_id=feedback_id,
                spec_id=feedback_data.get("spec_id"),
                spec_name=feedback_data.get("spec_name"),
                feedback_type=feedback_data.get("feedback_type", "accepted"),
                agent_type=feedback_data.get("agent_type", "coder"),
                task_description=feedback_data.get("task_description", ""),
                rating=feedback_data.get("rating"),
                sentiment=sentiment_data.get("sentiment"),
                sentiment_confidence=sentiment_data.get("confidence", 0.0),
                category=sentiment_data.get("category"),
                severity=sentiment_data.get("severity"),
                created_at=created_at,
                context=feedback_data.get("context", {}),
            )

            feedback_list.append(feedback)

        await memory.close()

    except Exception as e:
        # If Graphiti fails, return empty list (graceful degradation)
        import logging

        logging.warning(f"Failed to collect feedback from Graphiti: {e}")
        return []

    return feedback_list


def collect_feedback_from_files(
    project_dir: Path,
    spec_dir: Path | None = None,
) -> list[FeedbackMetrics]:
    """
    Collect feedback from local files (fallback if Graphiti unavailable).

    Args:
        project_dir: Project directory
        spec_dir: Optional spec directory

    Returns:
        List of FeedbackMetrics
    """
    feedback_list = []

    # Look for feedback files in .auto-claude/feedback/ or similar
    feedback_dir = project_dir / ".auto-claude" / "feedback"
    if not feedback_dir.exists():
        return []

    try:
        for feedback_file in feedback_dir.glob("*.json"):
            with open(feedback_file) as f:
                data = json.load(f)

            # Create FeedbackMetrics from file data
            feedback = FeedbackMetrics.from_dict(data)
            feedback_list.append(feedback)

    except Exception as e:
        import logging

        logging.warning(f"Failed to collect feedback from files: {e}")

    return feedback_list


# =============================================================================
# AGGREGATION
# =============================================================================


def aggregate_feedback(
    feedback_items: list[FeedbackMetrics],
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> FeedbackSummary:
    """
    Aggregate feedback metrics into summary.

    Args:
        feedback_items: List of feedback items to aggregate
        period_start: Start of period (defaults to earliest feedback)
        period_end: End of period (defaults to now)

    Returns:
        FeedbackSummary with aggregated metrics
    """
    if not feedback_items:
        now = datetime.now(UTC)
        return FeedbackSummary(
            period_start=period_start or now - timedelta(days=30),
            period_end=period_end or now,
        )

    # Determine period
    if period_start is None:
        dates = [f.created_at for f in feedback_items if f.created_at]
        period_start = min(dates) if dates else datetime.now(UTC) - timedelta(days=30)

    if period_end is None:
        period_end = datetime.now(UTC)

    # Initialize summary
    summary = FeedbackSummary(
        period_start=period_start,
        period_end=period_end,
        feedback_items=feedback_items,
    )

    # Count by type
    summary.total_feedback = len(feedback_items)
    summary.accepted_count = sum(
        1 for f in feedback_items if f.feedback_type == "accepted"
    )
    summary.rejected_count = sum(
        1 for f in feedback_items if f.feedback_type == "rejected"
    )
    summary.modified_count = sum(
        1 for f in feedback_items if f.feedback_type == "modified"
    )

    # Calculate average rating
    ratings = [f.rating for f in feedback_items if f.rating is not None]
    if ratings:
        summary.average_rating = sum(ratings) / len(ratings)
        summary.total_ratings = len(ratings)

    # Count sentiment
    summary.positive_sentiment_count = sum(
        1 for f in feedback_items if f.sentiment == "positive"
    )
    summary.negative_sentiment_count = sum(
        1 for f in feedback_items if f.sentiment == "negative"
    )
    summary.neutral_sentiment_count = sum(
        1 for f in feedback_items if f.sentiment == "neutral"
    )

    # Breakdown by agent type
    agent_counts = defaultdict(int)
    agent_ratings = defaultdict(list)
    for feedback in feedback_items:
        agent_counts[feedback.agent_type] += 1
        if feedback.rating is not None:
            agent_ratings[feedback.agent_type].append(feedback.rating)

    summary.feedback_by_agent = dict(agent_counts)
    summary.ratings_by_agent = {
        agent: sum(ratings) / len(ratings)
        for agent, ratings in agent_ratings.items()
        if ratings
    }

    # Breakdown by category
    category_counts = defaultdict(int)
    for feedback in feedback_items:
        if feedback.category:
            category_counts[feedback.category] += 1
    summary.feedback_by_category = dict(category_counts)

    # Top issues (negative feedback with severity)
    negative_items = [
        f
        for f in feedback_items
        if f.is_negative or f.sentiment == "negative"
    ]
    # Sort by severity (high > medium > low) and then by date
    severity_order = {"high": 0, "medium": 1, "low": 2, None: 3}
    sorted_issues = sorted(
        negative_items,
        key=lambda f: (
            severity_order.get(f.severity, 3),
            f.created_at or datetime.min.replace(tzinfo=UTC),
        ),
        reverse=True,
    )

    summary.top_issues = [
        {
            "task": f.task_description[:200],
            "agent_type": f.agent_type,
            "severity": f.severity,
            "category": f.category,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in sorted_issues[:10]  # Top 10 issues
    ]

    # Calculate satisfaction rate
    positive_count = sum(1 for f in feedback_items if f.is_positive)
    if summary.total_feedback > 0:
        summary.satisfaction_rate = positive_count / summary.total_feedback

    # Calculate NPS (if using 0-10 scale ratings)
    # NPS = % promoters (9-10) - % detractors (0-6)
    if ratings and max(ratings) >= 9:  # Looks like 0-10 scale
        promoters = sum(1 for r in ratings if r >= 9)
        detractors = sum(1 for r in ratings if r <= 6)
        summary.net_promoter_score = (
            (promoters - detractors) / len(ratings)
        ) * 100

    return summary


# =============================================================================
# PUBLIC API
# =============================================================================


async def get_feedback_summary(
    project_dir: Path,
    spec_dir: Path | None = None,
    days: int = 30,
) -> FeedbackSummary:
    """
    Get feedback summary for a time period.

    This is the main entry point for feedback analytics.

    Args:
        project_dir: Project directory
        spec_dir: Optional spec directory (if None, get all project feedback)
        days: Number of days to include (default 30)

    Returns:
        FeedbackSummary with aggregated metrics

    Example:
        >>> summary = await get_feedback_summary(Path("."), days=7)
        >>> print(f"Satisfaction: {summary.satisfaction_rate:.1%}")
        >>> print(f"Avg Rating: {summary.average_rating}/5")
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    # Try Graphiti first
    feedback_items = await collect_feedback_from_graphiti(
        project_dir, spec_dir, start_date, end_date
    )

    # Fallback to file-based collection
    if not feedback_items:
        feedback_items = collect_feedback_from_files(project_dir, spec_dir)

    return aggregate_feedback(feedback_items, start_date, end_date)


def export_feedback_summary(
    summary: FeedbackSummary,
    output_path: Path,
    format: str = "json",
) -> None:
    """
    Export feedback summary to file.

    Args:
        summary: FeedbackSummary to export
        output_path: Output file path
        format: Export format ("json" or "csv")

    Raises:
        ValueError: If format is not supported
    """
    if format == "json":
        with open(output_path, "w") as f:
            json.dump(summary.to_dict(), f, indent=2)
    elif format == "csv":
        import csv

        with open(output_path, "w", newline="") as f:
            # Export summary metrics
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Feedback", summary.total_feedback])
            writer.writerow(["Accepted", summary.accepted_count])
            writer.writerow(["Rejected", summary.rejected_count])
            writer.writerow(["Modified", summary.modified_count])
            writer.writerow(["Average Rating", summary.average_rating or "N/A"])
            writer.writerow(
                ["Satisfaction Rate", f"{summary.satisfaction_rate:.1%}"]
            )
            writer.writerow(
                [
                    "Net Promoter Score",
                    summary.net_promoter_score
                    if summary.net_promoter_score is not None
                    else "N/A",
                ]
            )
    else:
        raise ValueError(f"Unsupported export format: {format}")


def get_feedback_trends(
    feedback_items: list[FeedbackMetrics],
    interval: str = "day",
) -> dict[str, list[dict[str, Any]]]:
    """
    Get feedback trends over time.

    Args:
        feedback_items: List of feedback items
        interval: Time interval ("day", "week", "month")

    Returns:
        Dictionary with trend data by interval
    """
    from collections import defaultdict

    trends = defaultdict(lambda: {"accepted": 0, "rejected": 0, "modified": 0})

    for feedback in feedback_items:
        if not feedback.created_at:
            continue

        # Determine bucket based on interval
        if interval == "day":
            bucket = feedback.created_at.date().isoformat()
        elif interval == "week":
            # ISO week number
            bucket = f"{feedback.created_at.year}-W{feedback.created_at.isocalendar()[1]:02d}"
        elif interval == "month":
            bucket = f"{feedback.created_at.year}-{feedback.created_at.month:02d}"
        else:
            bucket = feedback.created_at.date().isoformat()

        trends[bucket][feedback.feedback_type] += 1

    # Convert to sorted list
    sorted_trends = sorted(trends.items())
    return {
        "interval": interval,
        "data": [
            {"period": period, **counts} for period, counts in sorted_trends
        ],
    }
