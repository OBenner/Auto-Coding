"""
Predictive Scan Commands
=======================

CLI commands for predictive issue scanning (run scan, check status, CI/CD blocking)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from cli.utils import print_banner
from ui import (
    Icons,
    divider,
    icon,
    info,
    muted,
    print_header,
    success,
    warning,
)

# Try to import predictive scanner components
try:
    from analysis.predictive_scanner import PredictiveScanner, PredictiveScanResult
    from analysis.issue_tracker import IssueTracker
    PREDICTIVE_SCAN_AVAILABLE = True
except ImportError:
    PREDICTIVE_SCAN_AVAILABLE = False
    PredictiveScanner = None
    PredictiveScanResult = None
    IssueTracker = None


def handle_predictive_scan_command(
    project_dir: Path,
    spec_dir: Path | None = None,
    file_patterns: list[str] | None = None,
    run_llm: bool = True,
    output_json: bool = False,
    detect_bug: bool = True,
    detect_performance: bool = True,
    detect_code_smell: bool = True,
) -> int:
    """
    Handle the predictive scan command.

    Args:
        project_dir: Project root directory
        spec_dir: Optional spec directory for historical tracking
        file_patterns: Optional glob patterns to scan
        run_llm: Whether to run LLM analysis
        output_json: Whether to output results as JSON
        detect_bug: Whether to run bug detection
        detect_performance: Whether to run performance analysis
        detect_code_smell: Whether to run code smell detection

    Returns:
        0 on success, 1 if critical issues found, 2 on error
    """
    print_banner()
    print(f"\n{icon(Icons.SCANNING)} Predictive Issue Scan")
    print(f"Project: {project_dir}\n")

    if not PREDICTIVE_SCAN_AVAILABLE:
        print(
            warning(
                f"{icon(Icons.WARNING)} Predictive scanning not available. "
                "Please ensure analysis modules are installed."
            )
        )
        return 2

    try:
        # Initialize scanner
        scanner = PredictiveScanner(spec_dir)

        # Run scan
        print(info(f"{icon(Icons.INFO)} Running predictive scan..."))
        result = scanner.scan(
            project_dir=project_dir,
            file_patterns=file_patterns,
            run_bug_detection=detect_bug,
            run_performance_analysis=detect_performance,
            run_code_smell_detection=detect_code_smell,
            run_llm_analysis=run_llm,
            record_history=True,
        )

        # Output results
        if output_json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_scan_result(result)

        # Return exit code based on critical issues
        if result.summary.should_block_deployment:
            return 1
        return 0

    except Exception as e:
        print(warning(f"{icon(Icons.ERROR)} Error during scan: {e}"))
        return 2


def handle_predictive_scan_status_command(
    project_dir: Path,
    spec_dir: Path,
    days: int = 30,
) -> None:
    """
    Handle the predictive scan status command.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory path
        days: Number of days to analyze for trends
    """
    print_banner()
    print(f"\n{icon(Icons.INFO)} Predictive Scan Status")
    print(f"Project: {project_dir}")
    print(f"Spec: {spec_dir.name}\n")

    if not PREDICTIVE_SCAN_AVAILABLE:
        print(
            warning(
                f"{icon(Icons.WARNING)} Predictive scanning not available. "
                "Please ensure analysis modules are installed."
            )
        )
        return

    try:
        # Initialize issue tracker
        tracker = IssueTracker(spec_dir)

        # Get summary statistics
        print_header("Issue Summary")
        summary = tracker.get_summary()
        print(f"  Total Issues: {summary.total_issues}")
        print(f"  Resolved: {summary.resolved_count}")
        print(f"  Active: {summary.active_count}")
        print()

        # Get trends
        print_header(f"Trends (Last {days} Days)")
        trends = tracker.get_trends(days=days)

        if not trends:
            print(muted("  No trend data available"))
        else:
            for trend in trends[:10]:  # Show top 10
                direction_icon = {
                    "increasing": "📈",
                    "decreasing": "📉",
                    "stable": "➡️",
                }.get(trend.trend_direction, "•")

                print(
                    f"  {direction_icon} {trend.category} ({trend.severity}): "
                    f"{trend.count_7_days} issues (7d)"
                )
        print()

        # Get prevention effectiveness
        print_header("Prevention Effectiveness")
        effectiveness = tracker.calculate_prevention_effectiveness()
        print(f"  Prevention Rate: {effectiveness.prevention_rate:.1f}%")
        print(f"  Issues Prevented: {effectiveness.issues_prevented}")
        print(f"  Issues Detected: {effectiveness.total_detected}")
        print()

        # Get top categories
        print_header("Top Issue Categories")
        top_categories = tracker.get_top_categories(limit=5)
        for cat in top_categories:
            print(f"  • {cat['category']}: {cat['count']} issues")
        print()

    except Exception as e:
        print(warning(f"{icon(Icons.ERROR)} Error retrieving status: {e}"))


def handle_predictive_scan_check_command(
    project_dir: Path,
    spec_dir: Path | None = None,
    fail_on_high: bool = False,
) -> int:
    """
    Handle the predictive scan check command (for CI/CD blocking).

    Args:
        project_dir: Project root directory
        spec_dir: Optional spec directory for historical tracking
        fail_on_high: Whether to fail on high severity (default: critical only)

    Returns:
        0 if safe to deploy, 1 if should block, 2 on error
    """
    if not PREDICTIVE_SCAN_AVAILABLE:
        print(
            warning(
                f"{icon(Icons.WARNING)} Predictive scanning not available. "
                "Please ensure analysis modules are installed."
            ),
            file=sys.stderr,
        )
        return 2

    try:
        # Initialize scanner
        scanner = PredictiveScanner(spec_dir)

        # Run quick scan without LLM (faster for CI/CD)
        result = scanner.scan(
            project_dir=project_dir,
            run_llm_analysis=False,  # Skip LLM for faster CI/CD checks
            record_history=False,  # Don't record CI/CD checks in history
        )

        # Check for blocking issues
        if fail_on_high:
            blocking_severities = ["critical", "high"]
        else:
            blocking_severities = ["critical"]

        blocking_issues = [
            issue
            for issue in result.issues
            if issue.severity in blocking_severities
        ]

        if blocking_issues:
            print(
                warning(
                    f"{icon(Icons.WARNING)} Found {len(blocking_issues)} "
                    f"{'+' if fail_on_high else ''}blocking issue(s)"
                ),
                file=sys.stderr,
            )
            for issue in blocking_issues[:5]:  # Show first 5
                print(
                    f"  [{issue.severity.upper()}] {issue.title} "
                    f"({issue.file}:{issue.line})",
                    file=sys.stderr,
                )
            if len(blocking_issues) > 5:
                print(
                    f"  ... and {len(blocking_issues) - 5} more",
                    file=sys.stderr,
                )
            return 1

        # Safe to deploy
        print(
            success(f"{icon(Icons.SUCCESS)} No blocking issues - safe to deploy")
        )
        return 0

    except Exception as e:
        print(
            warning(f"{icon(Icons.ERROR)} Error during check: {e}"),
            file=sys.stderr,
        )
        return 2


def _print_scan_result(result: PredictiveScanResult) -> None:
    """
    Print predictive scan results in a formatted way.

    Args:
        result: PredictiveScanResult to display
    """
    # Print summary
    print_header("Scan Summary")
    print(f"  Total Issues: {result.summary.total_issues}")
    print(f"  Critical: {result.summary.critical_count}")
    print(f"  High: {result.summary.high_count}")
    print(f"  Medium: {result.summary.medium_count}")
    print(f"  Low: {result.summary.low_count}")
    print(f"  Duration: {result.scan_duration:.2f}s")
    if result.llm_enhanced:
        print(f"  LLM Analysis: {icon(Icons.SUCCESS)} Enhanced")
    print()

    # Print breakdown by type
    if result.summary.by_type:
        print_header("Issues by Type")
        for issue_type, count in result.summary.by_type.items():
            print(f"  {issue_type}: {count}")
        print()

    # Print top issues
    if result.issues:
        print_header("Top Issues")
        for issue in result.issues[:10]:  # Show top 10
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(issue.severity, "•")

            print(f"  {severity_icon} [{issue.severity.upper()}] {issue.title}")
            if issue.file:
                location = f"{issue.file}"
                if issue.line:
                    location += f":{issue.line}"
                print(muted(f"     Location: {location}"))
            if issue.description:
                print(muted(f"     {issue.description}"))
            if issue.auto_fix:
                print(success(f"     Auto-fix available"))
            print()

        if len(result.issues) > 10:
            print(muted(f"... and {len(result.issues) - 10} more issues"))
            print()

    # Print historical trends if available
    if result.historical_trends:
        print_header("Historical Trends")
        prevention_rate = result.historical_trends.get("prevention_rate", 0)
        print(f"  Prevention Rate: {prevention_rate:.1f}%")
        print()

    # Print deployment status
    if result.summary.should_block_deployment:
        print(
            warning(
                f"{icon(Icons.WARNING)} Deployment BLOCKED - "
                f"{result.summary.critical_count} critical issue(s) found"
            )
        )
    else:
        print(
            success(
                f"{icon(Icons.SUCCESS)} Deployment SAFE - "
                f"no blocking issues"
            )
        )
    print()

    # Print errors if any
    if result.scan_errors:
        print_header("Scan Errors")
        for error in result.scan_errors:
            print(warning(f"  {error}"))
        print()


def main() -> None:
    """
    Main entry point for predictive scan commands CLI.
    """
    parser = argparse.ArgumentParser(
        description="Predictive issue scanning for proactive code quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run predictive scan on current directory
  python -m cli.predictive_scan_commands scan

  # Run scan with specific file patterns
  python -m cli.predictive_scan_commands scan --file-patterns "**/*.py" "**/*.ts"

  # Run scan without LLM analysis (faster)
  python -m cli.predictive_scan_commands scan --no-llm

  # Run scan and output JSON
  python -m cli.predictive_scan_commands scan --json

  # Check status for a spec
  python -m cli.predictive_scan_commands status --spec-dir .auto-claude/specs/001-feature

  # CI/CD blocking check (exits 1 if critical issues found)
  python -m cli.predictive_scan_commands check --project-dir ./my-project

  # CI/CD check that also blocks on high severity
  python -m cli.predictive_scan_commands check --fail-on-high
        """,
    )

    parser.add_argument(
        "action",
        choices=["scan", "status", "check"],
        help="Action to perform",
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )

    parser.add_argument(
        "--spec-dir",
        type=Path,
        help="Spec directory for historical tracking",
    )

    parser.add_argument(
        "--file-patterns",
        nargs="+",
        help="Glob patterns to scan (e.g., '**/*.py')",
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM analysis (faster scan)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    parser.add_argument(
        "--no-bug",
        action="store_true",
        help="Disable bug detection",
    )

    parser.add_argument(
        "--no-performance",
        action="store_true",
        help="Disable performance analysis",
    )

    parser.add_argument(
        "--no-code-smell",
        action="store_true",
        help="Disable code smell detection",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze for trends (default: 30)",
    )

    parser.add_argument(
        "--fail-on-high",
        action="store_true",
        help="Fail CI/CD check on high severity (default: critical only)",
    )

    args = parser.parse_args()

    # Validate project_dir exists
    if not args.project_dir.exists():
        print(
            warning(f"{icon(Icons.WARNING)} Project directory not found: {args.project_dir}")
        )
        sys.exit(2)

    # Handle command
    if args.action == "scan":
        exit_code = handle_predictive_scan_command(
            project_dir=args.project_dir,
            spec_dir=args.spec_dir,
            file_patterns=args.file_patterns,
            run_llm=not args.no_llm,
            output_json=args.json,
            detect_bug=not args.no_bug,
            detect_performance=not args.no_performance,
            detect_code_smell=not args.no_code_smell,
        )
        sys.exit(exit_code)

    elif args.action == "status":
        if not args.spec_dir:
            print(
                warning(
                    f"{icon(Icons.WARNING)} --spec-dir required for 'status' action"
                )
            )
            sys.exit(2)

        if not args.spec_dir.exists():
            print(
                warning(f"{icon(Icons.WARNING)} Spec directory not found: {args.spec_dir}")
            )
            sys.exit(2)

        handle_predictive_scan_status_command(
            project_dir=args.project_dir,
            spec_dir=args.spec_dir,
            days=args.days,
        )

    elif args.action == "check":
        exit_code = handle_predictive_scan_check_command(
            project_dir=args.project_dir,
            spec_dir=args.spec_dir,
            fail_on_high=args.fail_on_high,
        )
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
