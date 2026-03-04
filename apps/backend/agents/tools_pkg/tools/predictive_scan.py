"""
Predictive Scan Tools
====================

Tools for running predictive code quality scans and tracking historical trends.
"""

import json
import logging
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None

try:
    from analysis.predictive_scanner import PredictiveScanner, PredictiveScanResult
except ImportError:
    logging.warning("PredictiveScanner not available")
    PredictiveScanner = None
    PredictiveScanResult = None


def _format_scan_result(result: Any, show_issues: bool = True) -> str:
    """
    Format scan result for display.

    Args:
        result: PredictiveScanResult object
        show_issues: Whether to include individual issues

    Returns:
        Formatted text
    """
    if not result:
        return "No scan results available"

    summary = result.get("summary", {})

    output = f"""Predictive Scan Results
=====================

Summary:
--------
Total Issues: {summary.get("total_issues", 0)}
Critical: {summary.get("critical_count", 0)}
High: {summary.get("high_count", 0)}
Medium: {summary.get("medium_count", 0)}
Low: {summary.get("low_count", 0)}

Blocking Deployment: {summary.get("should_block_deployment", False)}
Prevention Rate: {summary.get("prevention_rate", 0):.1%}
Scan Duration: {result.get("scan_duration", 0):.2f}s

By Type:
--------
"""

    # Add breakdown by type
    by_type = summary.get("by_type", {})
    if by_type:
        for issue_type, count in by_type.items():
            output += f"  {issue_type}: {count}\n"
    else:
        output += "  (none)\n"

    # Add top categories
    top_categories = summary.get("top_categories", [])
    if top_categories:
        output += "\nTop Categories:\n---------------\n"
        for cat in top_categories[:5]:
            output += f"  {cat['category']}: {cat['count']}\n"

    # Add individual issues if requested
    if show_issues:
        issues = result.get("issues", [])
        if issues:
            output += f"\nIssues ({len(issues)}):\n"
            for i, issue in enumerate(issues[:20], 1):  # Show first 20
                severity = issue.get("severity", "unknown").upper()
                category = issue.get("category", "unknown")
                title = issue.get("title", "No title")
                file = issue.get("file", "")
                line = issue.get("line", "")

                output += f"\n  {i}. [{severity}] {category}: {title}\n"

                if file:
                    output += f"     File: {file}:{line}\n"

                # Show LLM analysis if available
                llm_analysis = issue.get("llm_analysis", {})
                if llm_analysis:
                    priority = llm_analysis.get("priority", "unknown")
                    impact = llm_analysis.get("impact", "unknown")
                    effort = llm_analysis.get("effort", "unknown")
                    output += f"     Priority: {priority} | Impact: {impact} | Effort: {effort}\n"

                # Show auto-fix if available
                auto_fix = issue.get("auto_fix", {})
                if auto_fix:
                    fix_desc = auto_fix.get("description", "N/A")
                    output += f"     Auto-fix: {fix_desc}\n"

            if len(issues) > 20:
                output += f"\n  ... and {len(issues) - 20} more issues\n"

    # Add scan errors if any
    scan_errors = result.get("scan_errors", [])
    if scan_errors:
        output += f"\nScan Errors ({len(scan_errors)}):\n"
        for error in scan_errors:
            output += f"  - {error}\n"

    return output


def create_predictive_scan_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create predictive scan tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of predictive scan tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    if not PredictiveScanner:
        logging.warning("PredictiveScanner not available, tools not created")
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: run_predictive_scan
    # -------------------------------------------------------------------------
    @tool(
        "run_predictive_scan",
        "Run a predictive code quality scan on the project. Detects bugs, performance issues, and code smells before deployment.",
        {
            "file_patterns": str,
            "run_bug_detection": str,
            "run_performance_analysis": str,
            "run_code_smell_detection": str,
            "run_llm_analysis": str,
        },
    )
    async def run_predictive_scan(args: dict[str, Any]) -> dict[str, Any]:
        """
        Run predictive scan on the project.

        Args (from args dict):
            file_patterns: JSON array of glob patterns (e.g., '["**/*.py"]')
            run_bug_detection: "true"/"false" to enable/disable bug detection
            run_performance_analysis: "true"/"false" to enable/disable performance analysis
            run_code_smell_detection: "true"/"false" to enable/disable code smell detection
            run_llm_analysis: "true"/"false" to enable/disable LLM enhancement

        Returns:
            Scan results with issues and summary
        """
        try:
            # Parse arguments
            file_patterns_str = args.get("file_patterns", "[]")
            run_bug_detection = args.get("run_bug_detection", "true").lower() in (
                "true",
                "1",
                "yes",
            )
            run_performance_analysis = args.get(
                "run_performance_analysis", "true"
            ).lower() in ("true", "1", "yes")
            run_code_smell_detection = args.get(
                "run_code_smell_detection", "true"
            ).lower() in ("true", "1", "yes")
            run_llm_analysis = args.get("run_llm_analysis", "true").lower() in (
                "true",
                "1",
                "yes",
            )

            # Parse file patterns
            try:
                file_patterns = (
                    json.loads(file_patterns_str) if file_patterns_str else None
                )
            except json.JSONDecodeError:
                file_patterns = None

            # Create scanner and run scan
            scanner = PredictiveScanner(spec_dir)
            result = scanner.scan(
                project_dir,
                file_patterns=file_patterns,
                run_bug_detection=run_bug_detection,
                run_performance_analysis=run_performance_analysis,
                run_code_smell_detection=run_code_smell_detection,
                run_llm_analysis=run_llm_analysis,
            )

            # Convert to dict
            result_dict = scanner.to_dict(result)

            # Format for display
            formatted_output = _format_scan_result(result_dict)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": formatted_output,
                    }
                ]
            }

        except Exception as e:
            logging.exception("Error running predictive scan")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error running predictive scan: {e}",
                    }
                ]
            }

    tools.append(run_predictive_scan)

    # -------------------------------------------------------------------------
    # Tool: get_predictive_scan_history
    # -------------------------------------------------------------------------
    @tool(
        "get_predictive_scan_history",
        "Get historical predictive scan trends and statistics from IssueTracker. Use this to track code quality improvements over time.",
        {"days": str},
    )
    async def get_predictive_scan_history(args: dict[str, Any]) -> dict[str, Any]:
        """
        Get historical predictive scan trends.

        Args (from args dict):
            days: Number of days to look back (default: 30)

        Returns:
            Historical trends, top categories, and prevention statistics
        """
        try:
            # Parse days argument
            days_str = args.get("days", "30")
            try:
                days = int(days_str)
            except ValueError:
                days = 30

            # Create scanner and get historical data
            scanner = PredictiveScanner(spec_dir)

            if not scanner._issue_tracker:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "IssueTracker not available. Historical tracking requires spec_dir to be initialized.",
                        }
                    ]
                }

            # Get trends
            trends = scanner._issue_tracker.get_trends(days=days)

            # Get summary
            summary = scanner._issue_tracker.get_summary()

            # Get prevention effectiveness
            effectiveness = scanner._issue_tracker.calculate_prevention_effectiveness(
                days=days
            )

            # Format output
            output = f"""Predictive Scan History ({days} days)
===================================

Summary:
--------
Total Issues Recorded: {summary.get("total_issues", 0)}
Resolved Issues: {summary.get("resolved_issues", 0)}
Active Issues: {summary.get("active_issues", 0)}

Prevention Effectiveness:
-------------------------
Prevention Rate: {effectiveness.prevention_rate:.1%}
Issues Prevented: {effectiveness.issues_prevented}
Total Issues Found: {effectiveness.issues_found}
Period: {effectiveness.period_start} to {effectiveness.period_end}

Top Categories:
---------------
"""

            # Get top categories by count
            top_categories = scanner._issue_tracker.get_top_categories(limit=10)
            if top_categories:
                for i, cat in enumerate(top_categories, 1):
                    output += f"  {i}. {cat['category']} ({cat['count']} issues)\n"
            else:
                output += "  (no categories found)\n"

            # Add trends
            if trends:
                output += "\nTrends:\n-------\n"
                for trend in trends[:10]:  # Show top 10 trends
                    direction_icon = (
                        "📈"
                        if trend.trend_direction == "increasing"
                        else "📉"
                        if trend.trend_direction == "decreasing"
                        else "➡"
                    )
                    output += (
                        f"\n  {direction_icon} {trend.category} ({trend.severity})\n"
                    )
                    output += f"     Last 7 days: {trend.count_7_days} | Last 30 days: {trend.count_30_days}\n"
                    if trend.change_percentage is not None:
                        change_str = (
                            f"+{trend.change_percentage:.1f}%"
                            if trend.change_percentage > 0
                            else f"{trend.change_percentage:.1f}%"
                        )
                        output += f"     Change: {change_str}\n"

            return {
                "content": [
                    {
                        "type": "text",
                        "text": output,
                    }
                ]
            }

        except Exception as e:
            logging.exception("Error getting predictive scan history")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error getting predictive scan history: {e}",
                    }
                ]
            }

    tools.append(get_predictive_scan_history)

    # -------------------------------------------------------------------------
    # Tool: has_critical_issues
    # -------------------------------------------------------------------------
    @tool(
        "has_critical_issues",
        "Quick check if the project has critical issues that should block deployment. Use this before merging code or deploying.",
        {},
    )
    async def has_critical_issues(args: dict[str, Any]) -> dict[str, Any]:
        """
        Quick check for critical issues.

        Returns:
            Boolean indicating if critical issues were found
        """
        try:
            # Create scanner and run quick scan (no LLM for speed)
            scanner = PredictiveScanner(spec_dir)
            result = scanner.scan(
                project_dir,
                run_llm_analysis=False,  # Skip LLM for quick check
            )

            has_critical = result.summary.has_critical_issues
            should_block = result.summary.should_block_deployment

            output = f"""Critical Issues Check
====================

Has Critical Issues: {has_critical}
Should Block Deployment: {should_block}

Summary:
--------
Total Issues: {result.summary.total_issues}
Critical: {result.summary.critical_count}
High: {result.summary.high_count}
Medium: {result.summary.medium_count}
Low: {result.summary.low_count}

"""

            if has_critical:
                output += (
                    "⚠️  CRITICAL ISSUES FOUND - Review required before deployment!\n\n"
                )
                # Show critical issues
                critical_issues = [i for i in result.issues if i.severity == "critical"]
                if critical_issues:
                    output += "Critical Issues:\n"
                    for i, issue in enumerate(critical_issues[:10], 1):
                        output += f"\n  {i}. [{issue.severity.upper()}] {issue.category}: {issue.title}\n"
                        if issue.file:
                            output += f"     File: {issue.file}:{issue.line or ''}\n"
                        if issue.description:
                            output += f"     Description: {issue.description}\n"
            else:
                output += "✅ No critical issues found. Code is ready for deployment.\n"

            return {
                "content": [
                    {
                        "type": "text",
                        "text": output,
                    }
                ]
            }

        except Exception as e:
            logging.exception("Error checking for critical issues")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error checking for critical issues: {e}",
                    }
                ]
            }

    tools.append(has_critical_issues)

    return tools
