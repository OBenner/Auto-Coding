"""
Metrics Commands
================

CLI commands for viewing learning metrics and improvement trends
"""

import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from analysis.metrics_tracker import (
    get_detailed_metrics,
    get_improvement_trends,
    get_success_rate,
)
from ui import (
    Icons,
    box,
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


def show_learning_metrics(spec_dir: Path) -> None:
    """
    Display comprehensive learning metrics for a spec.

    Shows:
    - Success rates and QA iteration statistics
    - Improvement trends over time
    - Learning effectiveness metrics
    - Root causes identified and user corrections
    - Actionable recommendations

    Args:
        spec_dir: Spec directory path
    """
    print_banner()
    print(f"\n{icon(Icons.CHART)} Learning Metrics for: {spec_dir.name}\n")

    # Get comprehensive metrics
    detailed = get_detailed_metrics(spec_dir)
    success_metrics = detailed["success_metrics"]
    trend_metrics = detailed["trend_metrics"]
    learning_metrics = detailed.get("learning_metrics", {})
    issue_breakdown = detailed["issue_breakdown"]

    # === SUCCESS METRICS ===
    print_header("QA Iteration Success Metrics")
    print()

    if success_metrics["total_iterations"] == 0:
        print(info(f"{icon(Icons.INFO)} No QA iterations recorded yet"))
        print(muted("Run QA validation to start tracking metrics"))
        print()
        return

    # Success rates
    overall_pct = success_metrics["overall_success_rate"] * 100
    recent_pct = success_metrics["recent_success_rate"] * 100
    first_attempt_pct = success_metrics["first_attempt_success_rate"] * 100

    print_key_value("Overall Success Rate", f"{overall_pct:.1f}%")
    print_key_value("Recent Success Rate", f"{recent_pct:.1f}%")
    print_key_value("First Attempt Success", f"{first_attempt_pct:.1f}%")
    print_key_value(
        "Avg Iterations to Success",
        f"{success_metrics['average_iterations_to_success']:.1f}",
    )
    print()

    # Iteration counts
    print_key_value("Total Iterations", str(success_metrics["total_iterations"]))
    print_key_value("Approved", str(success_metrics["approved_iterations"]))
    print_key_value("Rejected", str(success_metrics["rejected_iterations"]))
    print_key_value("Errors", str(success_metrics["error_iterations"]))
    print()

    # === IMPROVEMENT TRENDS ===
    print(divider())
    print_header("Improvement Trends")
    print()

    trend = trend_metrics["trend"]
    success_trend_value = trend_metrics["success_rate_trend"]

    # Overall trend with icon
    if trend == "improving":
        trend_display = success(
            f"{icon(Icons.SUCCESS)} Improving (trend: +{success_trend_value:.1%})"
        )
    elif trend == "declining":
        trend_display = warning(
            f"{icon(Icons.WARNING)} Declining (trend: {success_trend_value:.1%})"
        )
    elif trend == "insufficient_data":
        trend_display = info(f"{icon(Icons.INFO)} Insufficient data for trend analysis")
    else:
        trend_display = info(
            f"{icon(Icons.INFO)} Stable (trend: {success_trend_value:+.1%})"
        )

    print_key_value("Overall Trend", trend_display)
    print_key_value("Recurring Issues", trend_metrics["recurring_issues_trend"].title())
    print_key_value(
        "Pattern Effectiveness", f"{trend_metrics['pattern_effectiveness']:.1%}"
    )
    print()

    # === LEARNING METRICS ===
    print(divider())
    print_header("Learning Effectiveness")
    print()

    root_causes = trend_metrics["root_causes_identified"]
    user_corrections = trend_metrics["user_corrections_applied"]

    print_key_value("Root Causes Identified", str(root_causes))
    print_key_value("User Corrections Applied", str(user_corrections))
    print_key_value(
        "Patterns Applied", str(learning_metrics.get("patterns_applied", 0))
    )
    print()

    # === ISSUE BREAKDOWN ===
    if issue_breakdown["total_issues"] > 0:
        print(divider())
        print_header("Issue Analysis")
        print()

        print_key_value("Total Issues Found", str(issue_breakdown["total_issues"]))
        print_key_value("Unique Issue Types", str(issue_breakdown["unique_types"]))
        print()

        # Top issue types
        if issue_breakdown["by_type"]:
            print(muted("Top Issue Types:"))
            for issue_type, count in sorted(
                issue_breakdown["by_type"].items(), key=lambda x: x[1], reverse=True
            )[:5]:
                print(f"  • {issue_type}: {count}")
            print()

        # Top files with issues
        if issue_breakdown["by_file"]:
            print(muted("Most Problematic Files:"))
            for file_path, count in list(issue_breakdown["by_file"].items())[:5]:
                print(f"  • {file_path}: {count} issues")
            print()

    # === RECOMMENDATIONS ===
    if trend_metrics["recommendations"]:
        print(divider())
        print_header("Recommendations")
        print()

        for rec in trend_metrics["recommendations"]:
            print(f"• {rec}")

        print()


def handle_metrics_command(spec_dir: Path) -> None:
    """
    Handle the --metrics command.

    Args:
        spec_dir: Spec directory path
    """
    show_learning_metrics(spec_dir)
