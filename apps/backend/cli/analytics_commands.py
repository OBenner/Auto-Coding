"""
Analytics Commands
==================

CLI commands for viewing productivity analytics and metrics across all specs
"""

import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from analysis.productivity_analytics import (
    aggregate_productivity_metrics,
    export_productivity_data,
    get_productivity_trends,
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


def show_productivity_analytics(project_dir: Path) -> None:
    """
    Display comprehensive productivity analytics across all specs.

    Shows:
    - Overall productivity metrics (specs completed, time saved, success rates)
    - Breakdown by spec type and complexity
    - Productivity statistics (subtasks, QA iterations)
    - Recommendations and insights

    Args:
        project_dir: Project directory path
    """
    print_banner()
    print(f"\n{icon(Icons.CHART)} Productivity Analytics\n")

    # Get comprehensive analytics
    summary = aggregate_productivity_metrics(project_dir)

    # === OVERALL METRICS ===
    print_header("Overall Metrics")
    print()

    if summary.total_specs == 0:
        print(info(f"{icon(Icons.INFO)} No specs found yet"))
        print(muted("Create specs to start tracking productivity metrics"))
        print()
        return

    # Success rates
    success_pct = summary.average_success_rate * 100
    first_attempt_pct = summary.first_attempt_success_rate * 100

    print_key_value("Total Specs", str(summary.total_specs))
    print_key_value("Completed", str(summary.completed_specs))
    print_key_value("In Progress", str(summary.in_progress_specs))
    print_key_value("Failed", str(summary.failed_specs))
    print()

    print_key_value("Success Rate", f"{success_pct:.1f}%")
    print_key_value("First Attempt Success", f"{first_attempt_pct:.1f}%")
    print()

    # === TIME SAVINGS ===
    print(divider())
    print_header("Time Savings")
    print()

    print_key_value(
        "Total Time Saved",
        success(f"{summary.total_time_saved_hours:.1f} hours"),
    )
    print_key_value("AI Build Time", f"{summary.total_build_time_hours:.1f} hours")

    if summary.total_build_time_hours > 0:
        efficiency = (
            summary.total_time_saved_hours / summary.total_build_time_hours
        ) * 100
        print_key_value("Efficiency Gain", f"{efficiency:.1f}%")

    print()

    # === BREAKDOWN BY TYPE ===
    if summary.specs_by_type:
        print(divider())
        print_header("Breakdown by Type")
        print()

        for spec_type, count in sorted(
            summary.specs_by_type.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / summary.total_specs) * 100
            print(f"  • {spec_type.title()}: {count} ({pct:.1f}%)")

        print()

    # === BREAKDOWN BY COMPLEXITY ===
    if summary.specs_by_complexity:
        print(divider())
        print_header("Breakdown by Complexity")
        print()

        for complexity, count in sorted(
            summary.specs_by_complexity.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / summary.total_specs) * 100
            print(f"  • {complexity.title()}: {count} ({pct:.1f}%)")

        print()

    # === PRODUCTIVITY STATISTICS ===
    print(divider())
    print_header("Productivity Statistics")
    print()

    print_key_value(
        "Total Subtasks Completed",
        str(summary.total_subtasks_completed),
    )
    print_key_value(
        "Avg Subtasks per Spec",
        f"{summary.average_subtasks_per_spec:.1f}",
    )
    print_key_value(
        "Avg QA Iterations",
        f"{summary.average_qa_iterations:.1f}",
    )
    print()

    # === RECOMMENDATIONS ===
    print(divider())
    print_header("Insights")
    print()

    # Generate insights
    if summary.average_qa_iterations > 3.0:
        print(
            warning(
                f"• High QA iteration rate ({summary.average_qa_iterations:.1f}) - consider more detailed specs"
            )
        )
    elif summary.average_qa_iterations < 1.5 and summary.completed_specs > 5:
        print(
            success(
                f"• Excellent QA performance ({summary.average_qa_iterations:.1f} iterations avg)"
            )
        )

    if summary.first_attempt_success_rate > 0.7:
        print(
            success(f"• Strong first-attempt success rate ({first_attempt_pct:.1f}%)")
        )
    elif summary.first_attempt_success_rate < 0.3 and summary.completed_specs > 5:
        print(
            warning(
                f"• Low first-attempt success rate ({first_attempt_pct:.1f}%) - review spec quality"
            )
        )

    if summary.total_time_saved_hours > 0:
        print(
            info(
                f"• Estimated productivity gain: {summary.total_time_saved_hours:.1f} hours"
            )
        )

    print()


def show_productivity_trends(project_dir: Path, days: int, granularity: str) -> None:
    """
    Display productivity trends over time.

    Args:
        project_dir: Project directory path
        days: Number of days to look back
        granularity: Time granularity - "daily", "weekly", or "monthly"
    """
    print_banner()
    print(f"\n{icon(Icons.CHART)} Productivity Trends ({granularity.title()})\n")

    # Get trends
    trends = get_productivity_trends(
        project_dir, window_days=days, granularity=granularity
    )

    if not trends:
        print(info(f"{icon(Icons.INFO)} No data for the specified time period"))
        print(muted(f"No specs found in the last {days} days"))
        print()
        return

    print_header(f"Last {days} Days")
    print()

    # Display trends
    for trend in trends:
        date_str = trend["date"][:10]  # Just the date part
        specs = trend["total_specs"]
        completed = trend["completed_specs"]
        time_saved = trend["time_saved_hours"]
        success_rate = trend["success_rate"] * 100

        print(f"{muted(date_str)}:")
        print(
            f"  Specs: {specs} | Completed: {completed} | Success: {success_rate:.1f}%"
        )
        print(f"  Time Saved: {time_saved:.1f}h")
        print()


def export_analytics(project_dir: Path, output_path: Path, format: str) -> None:
    """
    Export productivity analytics to file.

    Args:
        project_dir: Project directory path
        output_path: Path to output file
        format: Export format - "json" or "csv"
    """
    print_banner()
    print(f"\n{icon(Icons.SAVE)} Exporting Analytics\n")

    # Get analytics summary
    summary = aggregate_productivity_metrics(project_dir)

    if summary.total_specs == 0:
        print(warning(f"{icon(Icons.WARNING)} No specs found to export"))
        print()
        return

    # Export
    try:
        export_productivity_data(summary, output_path, format=format)
        print(success(f"{icon(Icons.SUCCESS)} Exported to: {output_path}"))
        print()
        print(muted(f"Total specs exported: {summary.total_specs}"))
        print(muted(f"Format: {format.upper()}"))
        print()
    except Exception as e:
        print(warning(f"{icon(Icons.WARNING)} Export failed: {e}"))
        print()


def handle_analytics_command(
    project_dir: Path,
    trends: bool = False,
    days: int = 30,
    granularity: str = "daily",
    export_path: Path | None = None,
    export_format: str = "json",
) -> None:
    """
    Handle the --analytics command.

    Args:
        project_dir: Project directory path
        trends: Show trends over time
        days: Number of days for trends
        granularity: Time granularity for trends
        export_path: Optional path to export analytics
        export_format: Export format - "json" or "csv"
    """
    if export_path:
        export_analytics(project_dir, export_path, export_format)
    elif trends:
        show_productivity_trends(project_dir, days, granularity)
    else:
        show_productivity_analytics(project_dir)
