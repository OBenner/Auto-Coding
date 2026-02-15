"""
Feedback Commands
=================

CLI commands for viewing user feedback analytics and improvement tracking
"""

import sys
from pathlib import Path

# Add apps/backend/ to sys.path so that sibling packages (analysis/, ui/, etc.)
# can be imported when this module is loaded via relative imports from cli/.
# This is the established pattern across all CLI modules in this project.
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from analysis.feedback_analytics import (
    export_feedback_summary,
    get_feedback_summary,
    get_feedback_trends,
)
from ui import (
    Icons,
    divider,
    icon,
    info,
    muted,
    print_header,
    print_key_value,
    success,
    warning,
)

from .utils import print_banner


async def feedback_dashboard(project_dir: Path, days: int = 30) -> None:
    """
    Display comprehensive feedback analytics dashboard.

    Shows:
    - Overall feedback metrics (accepted, rejected, modified)
    - Satisfaction scores and ratings
    - Sentiment distribution
    - Breakdown by agent type
    - Top issues and complaints
    - Recommendations and insights

    Args:
        project_dir: Project directory path
        days: Number of days to analyze (default 30)
    """
    print_banner()
    print(f"\n{icon(Icons.CHART)} User Feedback Dashboard (Last {days} days)\n")

    # Get comprehensive analytics
    summary = await get_feedback_summary(project_dir, days=days)

    # === OVERALL METRICS ===
    print_header("Overall Metrics")
    print()

    if summary.total_feedback == 0:
        print(info(f"{icon(Icons.INFO)} No feedback collected yet"))
        print(muted("Feedback will appear here after users rate agent outputs"))
        print()
        return

    print_key_value("Total Feedback", str(summary.total_feedback))
    print_key_value("Accepted", success(str(summary.accepted_count)))
    print_key_value("Modified", warning(str(summary.modified_count)))
    print_key_value("Rejected", str(summary.rejected_count))
    print()

    # === SATISFACTION METRICS ===
    print(divider())
    print_header("Satisfaction Metrics")
    print()

    satisfaction_pct = (summary.satisfaction_rate or 0.0) * 100
    print_key_value(
        "Satisfaction Rate",
        success(f"{satisfaction_pct:.1f}%")
        if satisfaction_pct >= 70
        else warning(f"{satisfaction_pct:.1f}%"),
    )

    if summary.average_rating is not None:
        rating_display = f"{summary.average_rating:.1f}/5"
        if summary.average_rating >= 4.0:
            rating_display = success(rating_display)
        elif summary.average_rating < 3.0:
            rating_display = warning(rating_display)
        print_key_value("Average Rating", rating_display)
        print_key_value("Total Ratings", str(summary.total_ratings))

    if summary.net_promoter_score is not None:
        nps_display = f"{summary.net_promoter_score:.0f}"
        if summary.net_promoter_score >= 50:
            nps_display = success(nps_display)
        elif summary.net_promoter_score < 0:
            nps_display = warning(nps_display)
        print_key_value("Net Promoter Score", nps_display)

    print()

    # === SENTIMENT DISTRIBUTION ===
    pos = int(summary.positive_sentiment_count or 0)
    neg = int(summary.negative_sentiment_count or 0)
    neu = int(summary.neutral_sentiment_count or 0)

    if pos or neg or neu:
        print(divider())
        print_header("Sentiment Distribution")
        print()

        total_sentiment = pos + neg + neu

        if total_sentiment > 0:
            pos_pct = (pos / total_sentiment) * 100
            neg_pct = (neg / total_sentiment) * 100
            neu_pct = (neu / total_sentiment) * 100

            print_key_value(
                "Positive",
                success(f"{pos} ({pos_pct:.1f}%)"),
            )
            print_key_value("Neutral", f"{neu} ({neu_pct:.1f}%)")
            print_key_value(
                "Negative",
                warning(f"{neg} ({neg_pct:.1f}%)"),
            )

        print()

    # === BREAKDOWN BY AGENT TYPE ===
    if summary.feedback_by_agent:
        print(divider())
        print_header("Feedback by Agent Type")
        print()

        for agent_type, count in sorted(
            summary.feedback_by_agent.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / summary.total_feedback) * 100
            rating_info = ""
            if agent_type in summary.ratings_by_agent:
                rating = summary.ratings_by_agent[agent_type]
                rating_info = f" (avg rating: {rating:.1f}/5)"
            print(f"  • {agent_type.title()}: {count} ({pct:.1f}%){rating_info}")

        print()

    # === BREAKDOWN BY CATEGORY ===
    if summary.feedback_by_category:
        print(divider())
        print_header("Feedback by Category")
        print()

        for category, count in sorted(
            summary.feedback_by_category.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / summary.total_feedback) * 100
            print(f"  • {category.replace('_', ' ').title()}: {count} ({pct:.1f}%)")

        print()

    # === TOP ISSUES ===
    if summary.top_issues:
        print(divider())
        print_header("Top Issues (Negative Feedback)")
        print()

        for i, issue in enumerate(summary.top_issues[:5], 1):  # Show top 5
            severity = issue.get("severity", "unknown")
            severity_icon = (
                "🔴" if severity == "high" else "🟡" if severity == "medium" else "⚪"
            )
            agent = issue.get("agent_type", "unknown")
            task = issue.get("task", "No description")[:100]

            print(f"{severity_icon} {i}. [{agent}] {task}")
            if issue.get("category"):
                print(f"   Category: {issue['category'].replace('_', ' ').title()}")
            print()

    # === INSIGHTS & RECOMMENDATIONS ===
    print(divider())
    print_header("Insights")
    print()

    # Generate insights based on metrics
    if summary.total_feedback < 10:
        print(
            info("• Not enough feedback yet for meaningful insights (need 10+ samples)")
        )
    else:
        # Satisfaction insights
        if satisfaction_pct >= 80:
            print(success(f"• Excellent satisfaction rate ({satisfaction_pct:.1f}%)"))
        elif satisfaction_pct < 60:
            print(
                warning(
                    f"• Low satisfaction rate ({satisfaction_pct:.1f}%) - review recent issues"
                )
            )

        # Rating insights
        if summary.average_rating is not None:
            if summary.average_rating >= 4.5:
                print(
                    success(
                        f"• Outstanding average rating ({summary.average_rating:.1f}/5)"
                    )
                )
            elif summary.average_rating < 3.0:
                print(
                    warning(
                        f"• Below-average rating ({summary.average_rating:.1f}/5) - investigate top issues"
                    )
                )

        # Agent-specific insights
        if summary.ratings_by_agent:
            best_agent = max(summary.ratings_by_agent.items(), key=lambda x: x[1])
            worst_agent = min(summary.ratings_by_agent.items(), key=lambda x: x[1])

            if best_agent[1] - worst_agent[1] > 1.0:
                print(
                    info(
                        f"• {best_agent[0]} performing best ({best_agent[1]:.1f}/5), "
                        f"{worst_agent[0]} needs attention ({worst_agent[1]:.1f}/5)"
                    )
                )

        # Category insights
        if summary.feedback_by_category:
            top_category = max(summary.feedback_by_category.items(), key=lambda x: x[1])
            if (
                top_category[0] == "bug_report"
                and top_category[1] > summary.total_feedback * 0.3
            ):
                print(
                    warning(
                        f"• High bug report rate ({top_category[1]} reports) - focus on quality improvements"
                    )
                )
            elif (
                top_category[0] == "feature_request"
                and top_category[1] > summary.total_feedback * 0.3
            ):
                print(
                    info(
                        f"• Many feature requests ({top_category[1]}) - users are actively engaged"
                    )
                )

    print()


async def show_feedback_trends(
    project_dir: Path, days: int = 30, interval: str = "day"
) -> None:
    """
    Display feedback trends over time.

    Args:
        project_dir: Project directory path
        days: Number of days to analyze
        interval: Time interval - "day", "week", or "month"
    """
    print_banner()
    print(f"\n{icon(Icons.CHART)} Feedback Trends ({interval.title()})\n")

    # Get feedback summary
    summary = await get_feedback_summary(project_dir, days=days)

    if summary.total_feedback == 0:
        print(info(f"{icon(Icons.INFO)} No feedback data available"))
        print()
        return

    # Get trends
    trends_data = get_feedback_trends(summary.feedback_items, interval=interval)

    print_header("Feedback Trends Over Time")
    print()

    if not trends_data["data"]:
        print(info("No trend data available"))
        print()
        return

    # Display trend data
    print(
        f"{'Period':<20} {'Accepted':>10} {'Modified':>10} {'Rejected':>10} {'Total':>10}"
    )
    print("─" * 62)

    for entry in trends_data["data"]:
        period = entry["period"]
        accepted = entry["accepted"]
        modified = entry["modified"]
        rejected = entry["rejected"]
        total = accepted + modified + rejected

        print(f"{period:<20} {accepted:>10} {modified:>10} {rejected:>10} {total:>10}")

    print()

    # Summary statistics
    print_header("Trend Summary")
    print()

    total_periods = len(trends_data["data"])
    avg_per_period = summary.total_feedback / total_periods if total_periods > 0 else 0

    print_key_value("Total Periods", str(total_periods))
    print_key_value("Avg Feedback/Period", f"{avg_per_period:.1f}")

    # Check if feedback is increasing or decreasing
    if len(trends_data["data"]) >= 2:
        first_half = trends_data["data"][: len(trends_data["data"]) // 2]
        second_half = trends_data["data"][len(trends_data["data"]) // 2 :]

        first_half_total = sum(
            e["accepted"] + e["modified"] + e["rejected"] for e in first_half
        )
        second_half_total = sum(
            e["accepted"] + e["modified"] + e["rejected"] for e in second_half
        )

        if second_half_total > first_half_total * 1.2:
            print_key_value("Trend", success("📈 Increasing engagement"))
        elif second_half_total < first_half_total * 0.8:
            print_key_value("Trend", warning("📉 Decreasing engagement"))
        else:
            print_key_value("Trend", "→ Stable")

    print()


async def export_feedback_data(
    project_dir: Path,
    output_path: Path,
    days: int = 30,
    format: str = "json",
) -> None:
    """
    Export feedback data to file.

    Args:
        project_dir: Project directory path
        output_path: Output file path
        days: Number of days to include
        format: Export format ("json" or "csv")
    """
    print_banner()
    print(f"\n{icon(Icons.SAVE)} Exporting Feedback Data\n")

    # Get feedback summary
    summary = await get_feedback_summary(project_dir, days=days)

    if summary.total_feedback == 0:
        print(warning(f"{icon(Icons.WARNING)} No feedback data to export"))
        print()
        return

    # Export
    try:
        export_feedback_summary(summary, output_path, format=format)
        print(
            success(
                f"✓ Exported {summary.total_feedback} feedback items to {output_path}"
            )
        )
        print()
        print_key_value("Format", format.upper())
        print_key_value("Period", f"{days} days")
        print_key_value("Total Items", str(summary.total_feedback))
        print()
    except Exception as e:
        print(warning(f"{icon(Icons.WARNING)} Export failed: {e}"))
        print()
