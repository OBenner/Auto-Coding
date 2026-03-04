#!/usr/bin/env python3
"""
Predictive Scanner Module
==========================

Integrates all detection modules (bug, performance, code smell) with LLM-based
analysis to provide comprehensive predictive issue detection. This module serves
as the main entry point for proactive code quality analysis.

The predictive scanner is used by:
- QA Agent: To verify code quality before approval
- CI/CD Pipeline: To block PRs with critical issues
- Developer Tools: To provide proactive code quality feedback
- Analytics: To track prevention effectiveness over time

Usage:
    from analysis.predictive_scanner import PredictiveScanner

    scanner = PredictiveScanner()
    results = scanner.scan(project_dir, spec_dir)

    if results.has_critical_issues:
        print("Critical issues found - blocking deployment")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Check for Claude SDK availability
try:
    __import__("claude_agent_sdk")
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# Import detection modules
try:
    from analysis.bug_detector import BugDetector
    from analysis.code_smell_detector import CodeSmellDetector
    from analysis.performance_analyzer import PerformanceAnalyzer
except ImportError:
    logger.warning("Detection modules not available")
    BugDetector = None
    PerformanceAnalyzer = None
    CodeSmellDetector = None

# Import issue tracker
try:
    from analysis.issue_tracker import IssueTracker
except ImportError:
    logger.warning("IssueTracker not available")
    IssueTracker = None

from core.auth import get_auth_token

# Default model for LLM analysis (fast and cost-effective)
DEFAULT_ANALYSIS_MODEL = "claude-haiku-4-5-20251001"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PredictiveIssue:
    """
    Represents a predictive issue found during scanning.

    Attributes:
        issue_type: Type of issue (bug, performance, code_smell)
        severity: Severity level (critical, high, medium, low)
        category: Category/subtype (e.g., "NoneType error", "N+1 query")
        source: Which detector found this issue
        title: Short title of the issue
        description: Detailed description
        file: File where issue was found
        line: Line number (if applicable)
        code_snippet: Code fragment causing the issue
        suggestion: Suggested fix or mitigation
        confidence: Confidence score (0.0 to 1.0)
        llm_analysis: Enhanced analysis from LLM (if available)
        auto_fix: Auto-generated code fix (if available)
    """

    issue_type: str  # bug, performance, code_smell
    severity: str  # critical, high, medium, low
    category: str  # Subtype for grouping
    source: str  # bug_detector, performance_analyzer, code_smell_detector
    title: str
    description: str
    file: str | None = None
    line: int | None = None
    code_snippet: str | None = None
    suggestion: str | None = None
    confidence: float = 0.8
    llm_analysis: dict[str, Any] | None = None
    auto_fix: dict[str, Any] | None = None


@dataclass
class ScanSummary:
    """
    Summary statistics for a predictive scan.

    Attributes:
        total_issues: Total number of issues found
        critical_count: Number of critical issues
        high_count: Number of high severity issues
        medium_count: Number of medium severity issues
        low_count: Number of low severity issues
        by_type: Breakdown by issue type
        by_category: Breakdown by category
        has_critical_issues: Whether any critical issues were found
        should_block_deployment: Whether these results should block deployment
        prevention_rate: Estimated prevention rate (from IssueTracker)
        top_categories: Top issue categories by count
    """

    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    has_critical_issues: bool = False
    should_block_deployment: bool = False
    prevention_rate: float = 0.0
    top_categories: list[dict[str, int]] = field(default_factory=list)


@dataclass
class PredictiveScanResult:
    """
    Result of a predictive scan.

    Attributes:
        issues: List of detected predictive issues
        summary: Summary statistics
        scan_errors: List of errors during scanning
        scan_duration: Time taken for scan (seconds)
        llm_enhanced: Whether LLM analysis was performed
        historical_trends: Historical issue trends (from IssueTracker)
    """

    issues: list[PredictiveIssue] = field(default_factory=list)
    summary: ScanSummary = field(default_factory=ScanSummary)
    scan_errors: list[str] = field(default_factory=list)
    scan_duration: float = 0.0
    llm_enhanced: bool = False
    historical_trends: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# PREDICTIVE SCANNER
# =============================================================================


class PredictiveScanner:
    """
    Consolidates all predictive scanning operations.

    Integrates:
    - BugDetector for runtime error detection
    - PerformanceAnalyzer for performance issue detection
    - CodeSmellDetector for code quality analysis
    - IssueTracker for historical tracking and trends
    - LLM analysis for enhanced insights (optional)
    """

    # Severity thresholds for blocking deployment
    BLOCKING_SEVERITIES = ["critical", "high"]

    def __init__(self, spec_dir: Path | None = None):
        """
        Initialize the predictive scanner.

        Args:
            spec_dir: Optional spec directory for IssueTracker storage
        """
        self._detectors_available: bool = (
            BugDetector is not None
            and PerformanceAnalyzer is not None
            and CodeSmellDetector is not None
        )

        # Initialize detectors
        self._bug_detector = BugDetector() if BugDetector else None
        self._performance_analyzer = (
            PerformanceAnalyzer() if PerformanceAnalyzer else None
        )
        self._code_smell_detector = CodeSmellDetector() if CodeSmellDetector else None

        # Initialize issue tracker
        self._issue_tracker = (
            IssueTracker(spec_dir) if (IssueTracker and spec_dir) else None
        )

    def scan(
        self,
        project_dir: Path,
        file_patterns: list[str] | None = None,
        run_bug_detection: bool = True,
        run_performance_analysis: bool = True,
        run_code_smell_detection: bool = True,
        run_llm_analysis: bool = True,
        record_history: bool = True,
    ) -> PredictiveScanResult:
        """
        Run comprehensive predictive scan.

        Args:
            project_dir: Path to the project root
            file_patterns: Optional list of glob patterns to scan (e.g., ["**/*.py"])
            run_bug_detection: Whether to run bug detection
            run_performance_analysis: Whether to run performance analysis
            run_code_smell_detection: Whether to run code smell detection
            run_llm_analysis: Whether to enhance results with LLM analysis
            record_history: Whether to record results in IssueTracker

        Returns:
            PredictiveScanResult with all findings
        """
        import time

        project_dir = Path(project_dir)
        start_time = time.time()

        result = PredictiveScanResult()

        if not self._detectors_available:
            result.scan_errors.append("Detection modules not available")
            return result

        # Collect files to scan
        files_to_scan = self._collect_files(project_dir, file_patterns)

        if not files_to_scan:
            result.scan_errors.append("No files found to scan")
            return result

        # Run bug detection
        if run_bug_detection and self._bug_detector:
            self._run_bug_detection(files_to_scan, result)

        # Run performance analysis
        if run_performance_analysis and self._performance_analyzer:
            self._run_performance_analysis(files_to_scan, result)

        # Run code smell detection
        if run_code_smell_detection and self._code_smell_detector:
            self._run_code_smell_detection(files_to_scan, result)

        # Calculate summary
        result.summary = self._calculate_summary(result.issues)

        # Run LLM analysis if enabled and available
        if run_llm_analysis and self._is_llm_analysis_enabled():
            try:
                self._run_llm_analysis(result)
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")
                result.scan_errors.append(f"LLM analysis error: {str(e)}")

        # Generate auto-fixes if enabled and available
        if run_llm_analysis and self._is_llm_analysis_enabled():
            try:
                self._generate_auto_fixes(result)
            except Exception as e:
                logger.warning(f"Auto-fix generation failed: {e}")
                result.scan_errors.append(f"Auto-fix generation error: {str(e)}")

        # Load historical trends if issue tracker available
        if self._issue_tracker:
            try:
                result.historical_trends = self._get_historical_trends()
            except Exception as e:
                logger.warning(f"Failed to load historical trends: {e}")

        # Record in history
        if record_history and self._issue_tracker:
            try:
                self._record_scan_results(result)
            except Exception as e:
                logger.warning(f"Failed to record scan results: {e}")

        result.scan_duration = time.time() - start_time

        return result

    def _collect_files(
        self, project_dir: Path, file_patterns: list[str] | None
    ) -> list[Path]:
        """
        Collect files to scan based on patterns.

        Args:
            project_dir: Project root directory
            file_patterns: Optional glob patterns

        Returns:
            List of file paths to scan
        """
        if file_patterns:
            files = []
            for pattern in file_patterns:
                files.extend(project_dir.glob(pattern))
            return files

        # Default: scan all Python files
        return list(project_dir.glob("**/*.py"))

    def _run_bug_detection(
        self, files: list[Path], result: PredictiveScanResult
    ) -> None:
        """Run bug detection on all files."""
        if not self._bug_detector:
            return

        try:
            for file_path in files:
                try:
                    detection_result = self._bug_detector.detect_issues(file_path)

                    # Convert to PredictiveIssue
                    for issue_dict in detection_result.get("issues", []):
                        issue = PredictiveIssue(
                            issue_type="bug",
                            severity=issue_dict.get("severity", "medium"),
                            category=issue_dict.get("bug_type", "unknown"),
                            source="bug_detector",
                            title=issue_dict.get("message", "Unknown bug"),
                            description=issue_dict.get("message", ""),
                            file=str(file_path),
                            line=issue_dict.get("lineno"),
                            code_snippet=issue_dict.get("code_snippet"),
                            suggestion=issue_dict.get("suggestion"),
                            confidence=issue_dict.get("confidence", 0.8),
                        )
                        result.issues.append(issue)

                except Exception as e:
                    result.scan_errors.append(
                        f"Bug detection failed for {file_path}: {str(e)}"
                    )

        except Exception as e:
            result.scan_errors.append(f"Bug detection error: {str(e)}")

    def _run_performance_analysis(
        self, files: list[Path], result: PredictiveScanResult
    ) -> None:
        """Run performance analysis on all files."""
        if not self._performance_analyzer:
            return

        try:
            for file_path in files:
                try:
                    analysis_result = self._performance_analyzer.analyze_file(file_path)

                    # Convert to PredictiveIssue
                    for issue_dict in analysis_result.get("issues", []):
                        issue = PredictiveIssue(
                            issue_type="performance",
                            severity=issue_dict.get("severity", "medium"),
                            category=issue_dict.get("issue_type", "unknown"),
                            source="performance_analyzer",
                            title=issue_dict.get(
                                "message", "Unknown performance issue"
                            ),
                            description=issue_dict.get("message", ""),
                            file=str(file_path),
                            line=issue_dict.get("lineno"),
                            code_snippet=issue_dict.get("code_snippet"),
                            suggestion=issue_dict.get("suggestion"),
                            confidence=issue_dict.get("confidence", 0.8),
                        )
                        result.issues.append(issue)

                except Exception as e:
                    result.scan_errors.append(
                        f"Performance analysis failed for {file_path}: {str(e)}"
                    )

        except Exception as e:
            result.scan_errors.append(f"Performance analysis error: {str(e)}")

    def _run_code_smell_detection(
        self, files: list[Path], result: PredictiveScanResult
    ) -> None:
        """Run code smell detection on all files."""
        if not self._code_smell_detector:
            return

        try:
            for file_path in files:
                try:
                    analysis_result = self._code_smell_detector.analyze_file(file_path)

                    # Convert to PredictiveIssue
                    for issue_dict in analysis_result.get("issues", []):
                        issue = PredictiveIssue(
                            issue_type="code_smell",
                            severity=issue_dict.get("severity", "medium"),
                            category=issue_dict.get("smell_type", "unknown"),
                            source="code_smell_detector",
                            title=issue_dict.get("message", "Unknown code smell"),
                            description=issue_dict.get("message", ""),
                            file=str(file_path),
                            line=issue_dict.get("lineno"),
                            code_snippet=issue_dict.get("code_snippet"),
                            suggestion=issue_dict.get("suggestion"),
                            confidence=issue_dict.get("confidence", 0.8),
                        )
                        result.issues.append(issue)

                except Exception as e:
                    result.scan_errors.append(
                        f"Code smell detection failed for {file_path}: {str(e)}"
                    )

        except Exception as e:
            result.scan_errors.append(f"Code smell detection error: {str(e)}")

    def _calculate_summary(self, issues: list[PredictiveIssue]) -> ScanSummary:
        """Calculate summary statistics from issues."""
        summary = ScanSummary()

        summary.total_issues = len(issues)

        # Count by severity
        for issue in issues:
            if issue.severity == "critical":
                summary.critical_count += 1
            elif issue.severity == "high":
                summary.high_count += 1
            elif issue.severity == "medium":
                summary.medium_count += 1
            elif issue.severity == "low":
                summary.low_count += 1

        # Breakdown by type
        summary.by_type = {}
        for issue in issues:
            summary.by_type[issue.issue_type] = (
                summary.by_type.get(issue.issue_type, 0) + 1
            )

        # Breakdown by category
        summary.by_category = {}
        for issue in issues:
            summary.by_category[issue.category] = (
                summary.by_category.get(issue.category, 0) + 1
            )

        # Top categories
        summary.top_categories = [
            {"category": cat, "count": count}
            for cat, count in sorted(
                summary.by_category.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        # Determine if should block
        summary.has_critical_issues = summary.critical_count > 0
        summary.should_block_deployment = any(
            issue.severity in self.BLOCKING_SEVERITIES for issue in issues
        )

        # Load prevention rate from issue tracker
        if self._issue_tracker:
            try:
                effectiveness = self._issue_tracker.calculate_prevention_effectiveness(
                    days=30
                )
                summary.prevention_rate = effectiveness.prevention_rate
            except Exception:
                pass  # Intentionally suppress - fallback to default prevention rate

        return summary

    def _is_llm_analysis_enabled(self) -> bool:
        """Check if LLM analysis is enabled."""
        if not SDK_AVAILABLE:
            return False
        if not get_auth_token():
            return False
        enabled_str = os.environ.get("PREDICTIVE_ANALYSIS_ENABLED", "true").lower()
        return enabled_str in ("true", "1", "yes")

    def _run_llm_analysis(self, result: PredictiveScanResult) -> None:
        """
        Enhance issues with LLM analysis.

        Args:
            result: Scan result to enhance
        """
        if not SDK_AVAILABLE:
            return

        # Run async analysis synchronously
        import asyncio

        try:
            asyncio.run(_run_analysis_async(result.issues))
            result.llm_enhanced = True
        except Exception as e:
            logger.warning(f"LLM analysis execution failed: {e}")

    def _generate_auto_fixes(self, result: PredictiveScanResult) -> None:
        """
        Generate auto-fix suggestions for issues.

        Args:
            result: Scan result to generate fixes for
        """
        if not SDK_AVAILABLE:
            return

        # Filter issues that should have auto-fixes
        fixable_issues = [i for i in result.issues if self._should_generate_fix(i)]

        if not fixable_issues:
            logger.info("No fixable issues found for auto-fix generation")
            return

        # Run async fix generation synchronously
        import asyncio

        try:
            asyncio.run(_generate_fixes_async(fixable_issues))
            logger.info(f"Generated auto-fixes for {len(fixable_issues)} issues")
        except Exception as e:
            logger.warning(f"Auto-fix generation failed: {e}")
            result.scan_errors.append(f"Auto-fix generation error: {str(e)}")

    def _should_generate_fix(self, issue: PredictiveIssue) -> bool:
        """
        Determine if an issue should have an auto-fix generated.

        Args:
            issue: Issue to evaluate

        Returns:
            True if auto-fix should be generated
        """
        # Require code snippet to generate fix
        if not issue.code_snippet:
            return False

        # Require file and line number
        if not issue.file or not issue.line:
            return False

        # Focus on critical and high severity issues
        if issue.severity not in ("critical", "high"):
            return False

        # Categories that are well-suited for auto-fixes
        fixable_categories = {
            # Bugs
            "NoneType error",
            "IndexError",
            "KeyError",
            "Division by zero",
            "Missing error handling",
            # Performance
            "N+1 query",
            # Code smells
            "Long function",
            "Deep nesting",
        }

        return issue.category in fixable_categories

    def _get_historical_trends(self) -> dict[str, Any]:
        """Get historical issue trends from IssueTracker."""
        if not self._issue_tracker:
            return {}

        try:
            trends = self._issue_tracker.get_trends(days=30)
            return {
                "trends": [
                    {
                        "category": t.category,
                        "severity": t.severity,
                        "count_7_days": t.count_7_days,
                        "count_30_days": t.count_30_days,
                        "trend_direction": t.trend_direction,
                        "change_percentage": t.change_percentage,
                    }
                    for t in trends
                ],
                "summary": asdict(self._issue_tracker.get_summary()),
            }
        except Exception as e:
            logger.warning(f"Failed to get historical trends: {e}")
            return {}

    def _record_scan_results(self, result: PredictiveScanResult) -> None:
        """Record scan results in IssueTracker."""
        if not self._issue_tracker:
            return

        try:
            # Convert PredictiveIssue to IssueRecord format
            issue_records = []
            for issue in result.issues:
                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "issue_type": issue.issue_type,
                    "severity": issue.severity,
                    "source": issue.source,
                    "title": issue.title,
                    "description": issue.description,
                    "file": issue.file,
                    "line": issue.line,
                    "category": issue.category,
                    "resolved": False,
                }
                issue_records.append(record)

            # Group by (issue_type, source) since record_issues requires these
            grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
            for record in issue_records:
                key = (record["issue_type"], record["source"])
                grouped.setdefault(key, []).append(record)
            for (issue_type, source), records in grouped.items():
                self._issue_tracker.record_issues(records, issue_type, source)
        except Exception as e:
            logger.warning(f"Failed to record scan results: {e}")

    def to_dict(self, result: PredictiveScanResult) -> dict[str, Any]:
        """
        Convert result to dictionary for JSON serialization.

        Args:
            result: PredictiveScanResult to convert

        Returns:
            Dictionary representation
        """
        return {
            "issues": [
                {
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "category": i.category,
                    "source": i.source,
                    "title": i.title,
                    "description": i.description,
                    "file": i.file,
                    "line": i.line,
                    "code_snippet": i.code_snippet,
                    "suggestion": i.suggestion,
                    "confidence": i.confidence,
                    "llm_analysis": i.llm_analysis,
                    "auto_fix": i.auto_fix,
                }
                for i in result.issues
            ],
            "summary": {
                "total_issues": result.summary.total_issues,
                "critical_count": result.summary.critical_count,
                "high_count": result.summary.high_count,
                "medium_count": result.summary.medium_count,
                "low_count": result.summary.low_count,
                "by_type": result.summary.by_type,
                "by_category": result.summary.by_category,
                "has_critical_issues": result.summary.has_critical_issues,
                "should_block_deployment": result.summary.should_block_deployment,
                "prevention_rate": result.summary.prevention_rate,
                "top_categories": result.summary.top_categories,
            },
            "scan_errors": result.scan_errors,
            "scan_duration": result.scan_duration,
            "llm_enhanced": result.llm_enhanced,
            "historical_trends": result.historical_trends,
        }


# =============================================================================
# LLM ANALYSIS (Async)
# =============================================================================


async def _run_analysis_async(issues: list[PredictiveIssue]) -> None:
    """
    Run LLM analysis on issues asynchronously.

    Args:
        issues: List of issues to enhance with LLM analysis
    """
    from core.auth import ensure_claude_code_oauth_token
    from core.simple_client import create_simple_client

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    model = os.environ.get("PREDICTIVE_ANALYZER_MODEL", DEFAULT_ANALYSIS_MODEL)

    # Build prompt from issues
    prompt = _build_analysis_prompt(issues)

    try:
        client = create_simple_client(
            agent_type="predictive_analyzer",
            model=model,
            system_prompt=(
                "You are a predictive code analysis expert. You analyze code quality issues "
                "to provide enhanced insights, prioritize fixes, and suggest specific refactoring. "
                "Always respond with valid JSON only, no markdown formatting or explanations."
            ),
            cwd=None,
        )

        async with client:
            await client.query(prompt)

            # Collect the response
            response_text = ""
            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        if type(block).__name__ == "TextBlock" and hasattr(
                            block, "text"
                        ):
                            if block.text:
                                response_text += block.text

            if response_text.strip():
                enhanced_data = _parse_analysis_response(response_text)
                if enhanced_data:
                    # Merge LLM insights back into issues
                    _merge_llm_insights(issues, enhanced_data)

    except Exception as e:
        logger.warning(f"LLM analysis failed: {e}")


def _build_analysis_prompt(issues: list[PredictiveIssue]) -> str:
    """Build the prompt for LLM analysis."""
    prompt_file = Path(__file__).parent / "prompts" / "predictive_analysis.md"

    if prompt_file.exists():
        base_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        base_prompt = "Analyze these code quality issues and provide enhanced insights."

    # Format issues for prompt
    issues_text = "\n".join(
        f"- [{i.severity.upper()}] {i.category}: {i.title}\n"
        f"  File: {i.file}:{i.line}\n"
        f"  Description: {i.description}\n"
        f"  Suggestion: {i.suggestion or 'None'}"
        for i in issues[:50]  # Limit to first 50 issues for context
    )

    return f"""{base_prompt}

## CODE QUALITY ISSUES TO ANALYZE

{issues_text if issues_text else "(No issues found)"}

Total issues: {len(issues)}

Now provide your analysis as JSON only.
"""


def _parse_analysis_response(response_text: str) -> dict[str, Any] | None:
    """Parse the LLM response."""
    text = response_text.strip()

    if not text:
        return None

    # Handle markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM analysis JSON")
        return None


def _merge_llm_insights(
    issues: list[PredictiveIssue], enhanced_data: dict[str, Any]
) -> None:
    """Merge LLM insights back into issues."""
    # Match enhanced insights to issues by category and file
    insights_by_category = enhanced_data.get("insights_by_category", {})

    for issue in issues:
        category_insights = insights_by_category.get(issue.category, {})
        if category_insights:
            issue.llm_analysis = {
                "priority": category_insights.get("priority", "medium"),
                "effort": category_insights.get("effort", "medium"),
                "impact": category_insights.get("impact", "medium"),
                "enhanced_suggestion": category_insights.get("enhanced_suggestion"),
            }


# =============================================================================
# AUTO-FIX GENERATION (Async)
# =============================================================================


async def _generate_fixes_async(issues: list[PredictiveIssue]) -> None:
    """
    Generate auto-fixes for issues asynchronously.

    Args:
        issues: List of issues to generate fixes for
    """
    from core.auth import ensure_claude_code_oauth_token
    from core.simple_client import create_simple_client

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    model = os.environ.get("AUTO_FIX_MODEL", DEFAULT_ANALYSIS_MODEL)

    # Generate fixes for each issue
    for issue in issues:
        try:
            # Build prompt for this specific issue
            prompt = _build_fix_prompt(issue)

            client = create_simple_client(
                agent_type="auto_fix_generator",
                model=model,
                system_prompt=(
                    "You are a code fix generation expert. You analyze code quality issues "
                    "and generate specific, ready-to-apply code fixes. "
                    "Always respond with valid JSON only, no markdown formatting or explanations."
                ),
                cwd=None,
            )

            async with client:
                await client.query(prompt)

                # Collect the response
                response_text = ""
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__
                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            if type(block).__name__ == "TextBlock" and hasattr(
                                block, "text"
                            ):
                                if block.text:
                                    response_text += block.text

                if response_text.strip():
                    fix_data = _parse_fix_response(response_text)
                    if fix_data:
                        issue.auto_fix = fix_data
                        logger.debug(
                            f"Generated auto-fix for {issue.category} at {issue.file}:{issue.line}"
                        )

        except Exception as e:
            logger.warning(
                f"Auto-fix generation failed for {issue.file}:{issue.line}: {e}"
            )


def _build_fix_prompt(issue: PredictiveIssue) -> str:
    """
    Build the prompt for auto-fix generation.

    Args:
        issue: Issue to generate fix for

    Returns:
        Full prompt text
    """
    prompt_file = Path(__file__).parent / "prompts" / "auto_fix_generation.md"

    if prompt_file.exists():
        base_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        base_prompt = "Generate a code fix for this issue."

    # Format issue for prompt
    issue_context = f"""
## CODE ISSUE TO FIX

Issue Type: {issue.issue_type}
Severity: {issue.severity}
Category: {issue.category}
File: {issue.file}
Line: {issue.line}
Title: {issue.title}
Description: {issue.description}
Code Snippet:
```
{issue.code_snippet}
```
Current Suggestion: {issue.suggestion or "None"}
"""

    return f"""{base_prompt}

{issue_context}

Now generate the auto-fix JSON for this issue.
"""


def _parse_fix_response(response_text: str) -> dict[str, Any] | None:
    """
    Parse the auto-fix response from LLM.

    Args:
        response_text: Raw LLM response

    Returns:
        Parsed fix dict or None if parsing failed
    """
    text = response_text.strip()

    if not text:
        return None

    # Handle markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        fix_data = json.loads(text)

        # Validate required fields
        required_fields = [
            "fix_type",
            "original_code",
            "fixed_code",
            "description",
            "applies_to_line",
            "scope",
            "confidence",
        ]
        for field in required_fields:
            if field not in fix_data:
                logger.warning(f"Missing required field in auto-fix: {field}")
                return None

        return fix_data

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse auto-fix JSON: {e}")
        return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def scan_for_issues(
    project_dir: Path,
    spec_dir: Path | None = None,
    file_patterns: list[str] | None = None,
) -> PredictiveScanResult:
    """
    Convenience function to run predictive scan.

    Args:
        project_dir: Path to project root
        spec_dir: Optional spec directory for historical tracking
        file_patterns: Optional glob patterns to scan

    Returns:
        PredictiveScanResult with all findings
    """
    scanner = PredictiveScanner(spec_dir)
    return scanner.scan(project_dir, file_patterns)


def has_critical_issues(project_dir: Path) -> bool:
    """
    Quick check if project has critical issues.

    Args:
        project_dir: Path to project root

    Returns:
        True if any critical issues found
    """
    scanner = PredictiveScanner()
    result = scanner.scan(project_dir, run_llm_analysis=False)
    return result.summary.has_critical_issues


def generate_auto_fix(issue: PredictiveIssue) -> dict[str, Any] | None:
    """
    Generate auto-fix for a specific issue.

    Args:
        issue: Issue to generate fix for

    Returns:
        Auto-fix dict or None if generation failed
    """
    if not SDK_AVAILABLE:
        logger.warning("Claude SDK not available for auto-fix generation")
        return None

    if not get_auth_token():
        logger.warning("No authentication token for auto-fix generation")
        return None

    import asyncio

    try:
        asyncio.run(_generate_fixes_async([issue]))
        return issue.auto_fix
    except Exception as e:
        logger.warning(f"Auto-fix generation failed: {e}")
        return None


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Run predictive code quality scans")
    parser.add_argument("project_dir", type=Path, help="Path to project root")
    parser.add_argument("--spec-dir", type=Path, help="Path to spec directory")
    parser.add_argument(
        "--patterns",
        nargs="+",
        help="Glob patterns to scan (e.g., '**/*.py')",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM analysis",
    )

    args = parser.parse_args()

    scanner = PredictiveScanner(args.spec_dir)
    result = scanner.scan(
        args.project_dir,
        file_patterns=args.patterns,
        run_llm_analysis=not args.no_llm,
    )

    if args.json:
        print(json.dumps(scanner.to_dict(result), indent=2))
    else:
        print(f"Issues Found: {result.summary.total_issues}")
        print(f"Critical: {result.summary.critical_count}")
        print(f"High: {result.summary.high_count}")
        print(f"Medium: {result.summary.medium_count}")
        print(f"Low: {result.summary.low_count}")
        print(f"Has Critical Issues: {result.summary.has_critical_issues}")
        print(f"Should Block Deployment: {result.summary.should_block_deployment}")
        print(f"Prevention Rate: {result.summary.prevention_rate:.1%}")
        print(f"Scan Duration: {result.scan_duration:.2f}s")

        if result.summary.top_categories:
            print("\nTop Categories:")
            for cat in result.summary.top_categories[:5]:
                print(f"  - {cat['category']}: {cat['count']}")

        if result.issues:
            print(f"\nIssues ({len(result.issues)}):")
            for issue in result.issues[:20]:  # Show first 20
                print(f"  [{issue.severity.upper()}] {issue.category}: {issue.title}")
                if issue.file:
                    print(f"    File: {issue.file}:{issue.line or ''}")
                if issue.llm_analysis:
                    print(
                        f"    Priority: {issue.llm_analysis.get('priority', 'unknown')}"
                    )
                if issue.auto_fix:
                    print(
                        f"    Auto-fix available: {issue.auto_fix.get('description', 'N/A')}"
                    )

        if result.scan_errors:
            print(f"\nScan Errors ({len(result.scan_errors)}):")
            for error in result.scan_errors:
                print(f"  - {error}")


if __name__ == "__main__":
    main()
