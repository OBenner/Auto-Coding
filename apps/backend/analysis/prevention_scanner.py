#!/usr/bin/env python3
"""
Prevention Scanner Module
==========================

Consolidates all proactive issue detection scanners for comprehensive analysis.
This module integrates security, performance, breaking changes, and architecture validation
to shift from reactive QA to proactive prevention.

The prevention scanner is used by:
- Planner Agent: To identify potential issues before implementation
- QA Reviewer: To validate code meets all quality standards

Usage:
    from analysis.prevention_scanner import PreventionScanner

    scanner = PreventionScanner()
    results = scanner.scan(project_dir, spec_dir)

    if results.should_block:
        print("Critical issues found - blocking implementation")
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Import individual scanners
from analysis.architecture_validator import (
    ArchitecturalAnalysisResult,
    ArchitectureValidator,
)
from analysis.breaking_change_detector import (
    BreakingChangeDetector,
    BreakingChangeResult,
)
from analysis.performance_analyzer import (
    PerformanceAnalysisResult,
    PerformanceAnalyzer,
)

# Import configuration
from analysis.prevention_config import PreventionConfig, load_prevention_config
from analysis.security_scanner import SecurityScanner, SecurityScanResult

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PreventionScanResult:
    """
    Consolidated result from all prevention scanners.

    Attributes:
        security: Security scan results
        performance: Performance analysis results
        breaking_changes: Breaking change detection results
        architecture: Architecture validation results
        scan_errors: List of errors during scanning
        has_critical_issues: Whether any critical issues were found across all scanners
        should_block: Whether these results should block implementation
        should_warn: Whether these results should warn the user
        summary: Human-readable summary of findings
    """

    security: SecurityScanResult | None = None
    performance: PerformanceAnalysisResult | None = None
    breaking_changes: BreakingChangeResult | None = None
    architecture: ArchitecturalAnalysisResult | None = None
    scan_errors: list[str] = field(default_factory=list)
    has_critical_issues: bool = False
    should_block: bool = False
    should_warn: bool = False
    summary: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# PREVENTION SCANNER
# =============================================================================


class PreventionScanner:
    """
    Consolidates all proactive issue detection operations.

    Integrates:
    - SecurityScanner for secrets and vulnerabilities
    - PerformanceAnalyzer for N+1 queries and performance issues
    - BreakingChangeDetector for API contract violations
    - ArchitectureValidator for pattern consistency
    """

    def __init__(self, config: PreventionConfig | None = None) -> None:
        """
        Initialize the prevention scanner with all sub-scanners.

        Args:
            config: Optional PreventionConfig (defaults to loading from environment)
        """
        self.config = config or load_prevention_config()
        self.security_scanner = SecurityScanner()
        self.performance_analyzer = PerformanceAnalyzer()
        self.breaking_change_detector = BreakingChangeDetector()
        self.architecture_validator = ArchitectureValidator()

    def scan(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        changed_files: list[str] | None = None,
        old_dir: Path | None = None,
    ) -> PreventionScanResult:
        """
        Run all applicable prevention scans based on configuration.

        Args:
            project_dir: Path to the project root
            spec_dir: Path to the spec directory (for storing results)
            changed_files: Optional list of files to scan (if None, scans all)
            old_dir: Path to old version for breaking change detection

        Returns:
            PreventionScanResult with all findings
        """
        project_dir = Path(project_dir)
        result = PreventionScanResult()

        # Run security scan
        if self.config.security_enabled:
            try:
                result.security = self.security_scanner.scan(
                    project_dir=project_dir,
                    spec_dir=spec_dir if self.config.save_reports else None,
                    changed_files=changed_files,
                )
            except Exception as e:
                error_msg = f"Security scan failed: {e}"
                result.scan_errors.append(error_msg)
                if self.config.fail_on_scan_error:
                    raise RuntimeError(error_msg) from e

        # Run performance analysis
        if self.config.performance_enabled:
            try:
                result.performance = self.performance_analyzer.analyze(
                    project_dir=project_dir,
                    spec_dir=spec_dir if self.config.save_reports else None,
                    changed_files=changed_files,
                )
            except Exception as e:
                error_msg = f"Performance analysis failed: {e}"
                result.scan_errors.append(error_msg)
                if self.config.fail_on_scan_error:
                    raise RuntimeError(error_msg) from e

        # Run breaking change detection (requires old version for comparison)
        if self.config.breaking_changes_enabled and old_dir:
            try:
                result.breaking_changes = self.breaking_change_detector.analyze(
                    old_dir=old_dir,
                    new_dir=project_dir,
                    spec_dir=spec_dir if self.config.save_reports else None,
                )
            except Exception as e:
                error_msg = f"Breaking change detection failed: {e}"
                result.scan_errors.append(error_msg)
                if self.config.fail_on_scan_error:
                    raise RuntimeError(error_msg) from e

        # Run architecture validation
        if self.config.architecture_enabled:
            try:
                result.architecture = self.architecture_validator.analyze(
                    project_dir=project_dir,
                    spec_dir=spec_dir if self.config.save_reports else None,
                    changed_files=changed_files,
                )
            except Exception as e:
                error_msg = f"Architecture validation failed: {e}"
                result.scan_errors.append(error_msg)
                if self.config.fail_on_scan_error:
                    raise RuntimeError(error_msg) from e

        # Aggregate results
        self._aggregate_results(result)

        # Save consolidated results if spec_dir provided
        if spec_dir:
            self._save_results(spec_dir, result)

        return result

    def _aggregate_results(self, result: PreventionScanResult) -> None:
        """
        Aggregate results from all scanners to determine overall status.

        Args:
            result: PreventionScanResult to populate with aggregated data
        """
        # Count issues by severity
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        total_issues = 0

        # Security issues
        if result.security:
            secrets = getattr(result.security, "secrets", [])
            vulnerabilities = getattr(result.security, "vulnerabilities", [])
            critical_count += len(secrets)
            critical_count += len(
                [v for v in vulnerabilities if v.severity == "critical"]
            )
            high_count += len([v for v in vulnerabilities if v.severity == "high"])
            medium_count += len([v for v in vulnerabilities if v.severity == "medium"])
            low_count += len([v for v in vulnerabilities if v.severity == "low"])
            total_issues += len(secrets) + len(vulnerabilities)

        # Performance issues
        if result.performance:
            perf_issues = getattr(result.performance, "issues", [])
            critical_count += len([i for i in perf_issues if i.severity == "critical"])
            high_count += len([i for i in perf_issues if i.severity == "high"])
            medium_count += len([i for i in perf_issues if i.severity == "medium"])
            low_count += len([i for i in perf_issues if i.severity == "low"])
            total_issues += len(perf_issues)

        # Breaking changes
        if result.breaking_changes:
            bc_changes = getattr(result.breaking_changes, "breaking_changes", [])
            critical_count += len([c for c in bc_changes if c.severity == "critical"])
            high_count += len([c for c in bc_changes if c.severity == "high"])
            medium_count += len([c for c in bc_changes if c.severity == "medium"])
            low_count += len([c for c in bc_changes if c.severity == "low"])
            total_issues += len(bc_changes)

        # Architecture issues
        if result.architecture:
            arch_issues = getattr(result.architecture, "issues", [])
            critical_count += len([i for i in arch_issues if i.severity == "critical"])
            high_count += len([i for i in arch_issues if i.severity == "high"])
            medium_count += len([i for i in arch_issues if i.severity == "medium"])
            low_count += len([i for i in arch_issues if i.severity == "low"])
            total_issues += len(arch_issues)

        # Determine overall status using config
        result.has_critical_issues = critical_count > 0 or high_count > 0
        result.should_block = self.config.should_block(critical_count, high_count)
        result.should_warn = self.config.should_warn(high_count, medium_count)

        # Build summary
        result.summary = {
            "total_issues": total_issues,
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "scanners_run": [],
            "scanners_with_issues": [],
        }

        # Track which scanners ran and found issues
        if result.security:
            result.summary["scanners_run"].append("security")
            if len(secrets) > 0 or len(vulnerabilities) > 0:
                result.summary["scanners_with_issues"].append("security")

        if result.performance:
            result.summary["scanners_run"].append("performance")
            if len(perf_issues) > 0:
                result.summary["scanners_with_issues"].append("performance")

        if result.breaking_changes:
            result.summary["scanners_run"].append("breaking_changes")
            if len(bc_changes) > 0:
                result.summary["scanners_with_issues"].append("breaking_changes")

        if result.architecture:
            result.summary["scanners_run"].append("architecture")
            if len(arch_issues) > 0:
                result.summary["scanners_with_issues"].append("architecture")

    def _save_results(self, spec_dir: Path, result: PreventionScanResult) -> None:
        """
        Save consolidated prevention scan results to spec directory.

        Args:
            spec_dir: Spec directory path
            result: Result to save
        """
        spec_dir = Path(spec_dir)
        spec_dir.mkdir(parents=True, exist_ok=True)

        output_file = spec_dir / "prevention_scan.json"

        data = {
            "summary": result.summary,
            "has_critical_issues": result.has_critical_issues,
            "should_block": result.should_block,
            "should_warn": result.should_warn,
            "scan_errors": result.scan_errors,
            "scanners": {},
        }

        # Include individual scanner results
        if result.security:
            data["scanners"]["security"] = {
                "secrets_found": len(result.security.secrets),
                "vulnerabilities_found": len(result.security.vulnerabilities),
                "has_critical_issues": result.security.has_critical_issues,
                "should_block_qa": result.security.should_block_qa,
            }

        if result.performance:
            data["scanners"]["performance"] = {
                "issues_found": len(result.performance.issues),
                "files_analyzed": result.performance.files_analyzed,
                "has_critical_issues": result.performance.has_critical_issues,
                "should_warn": result.performance.should_warn,
            }

        if result.breaking_changes:
            data["scanners"]["breaking_changes"] = {
                "changes_found": len(result.breaking_changes.breaking_changes),
                "files_analyzed": result.breaking_changes.files_analyzed,
                "has_breaking_changes": result.breaking_changes.has_breaking_changes,
                "should_block": result.breaking_changes.should_block,
            }

        if result.architecture:
            data["scanners"]["architecture"] = {
                "issues_found": len(result.architecture.issues),
                "patterns_found": len(result.architecture.patterns),
                "files_analyzed": result.architecture.files_analyzed,
                "has_critical_issues": result.architecture.has_critical_issues,
                "should_warn": result.architecture.should_warn,
            }

        # Atomic write: write to temp file first, then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=str(spec_dir), suffix=".tmp", prefix="prevention_scan_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, str(output_file))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def format_report(self, result: PreventionScanResult) -> str:
        """
        Format prevention scan results as a human-readable report.

        Args:
            result: Result to format

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("PROACTIVE ISSUE PREVENTION SCAN REPORT")
        lines.append("=" * 80)

        # Overall summary
        lines.append(f"\nTotal Issues Found: {result.summary.get('total_issues', 0)}")
        lines.append(f"  Critical: {result.summary.get('critical', 0)}")
        lines.append(f"  High:     {result.summary.get('high', 0)}")
        lines.append(f"  Medium:   {result.summary.get('medium', 0)}")
        lines.append(f"  Low:      {result.summary.get('low', 0)}")

        # Overall status
        if result.should_block:
            lines.append("\n🚫 CRITICAL ISSUES FOUND - BLOCKING IMPLEMENTATION")
        elif result.should_warn:
            lines.append("\n⚠️  HIGH/MEDIUM ISSUES FOUND - REVIEW RECOMMENDED")
        else:
            lines.append("\n✅ No critical issues detected")

        # Scanners run
        lines.append(
            f"\nScanners Run: {', '.join(result.summary.get('scanners_run', []))}"
        )
        scanners_with_issues = result.summary.get("scanners_with_issues", [])
        if scanners_with_issues:
            lines.append(f"Scanners With Issues: {', '.join(scanners_with_issues)}")

        # Individual scanner reports
        if result.security and (
            len(result.security.secrets) > 0 or len(result.security.vulnerabilities) > 0
        ):
            lines.append("\n" + "=" * 80)
            lines.append("SECURITY SCAN")
            lines.append("-" * 80)
            lines.append(f"Secrets Found: {len(result.security.secrets)}")
            lines.append(
                f"Vulnerabilities Found: {len(result.security.vulnerabilities)}"
            )
            if result.security.should_block_qa:
                lines.append("⚠️  Security issues will block QA approval")

        if result.performance and len(result.performance.issues) > 0:
            lines.append("\n" + "=" * 80)
            lines.append("PERFORMANCE ANALYSIS")
            lines.append("-" * 80)
            lines.append(f"Performance Issues: {len(result.performance.issues)}")
            lines.append(f"Files Analyzed: {result.performance.files_analyzed}")

            # Breakdown by issue type
            issue_types = {}
            for issue in result.performance.issues:
                issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
            for issue_type, count in issue_types.items():
                lines.append(f"  - {issue_type}: {count}")

        if (
            result.breaking_changes
            and len(result.breaking_changes.breaking_changes) > 0
        ):
            lines.append("\n" + "=" * 80)
            lines.append("BREAKING CHANGE DETECTION")
            lines.append("-" * 80)
            lines.append(
                f"Breaking Changes: {len(result.breaking_changes.breaking_changes)}"
            )
            lines.append(f"Files Analyzed: {result.breaking_changes.files_analyzed}")
            if result.breaking_changes.should_block:
                lines.append("🚫 Breaking changes will block deployment")

        if result.architecture and len(result.architecture.issues) > 0:
            lines.append("\n" + "=" * 80)
            lines.append("ARCHITECTURE VALIDATION")
            lines.append("-" * 80)
            lines.append(f"Architectural Issues: {len(result.architecture.issues)}")
            lines.append(f"Patterns Discovered: {len(result.architecture.patterns)}")
            lines.append(f"Files Analyzed: {result.architecture.files_analyzed}")

            # Show discovered patterns
            if result.architecture.patterns:
                lines.append("\nEstablished Patterns:")
                for pattern in result.architecture.patterns[:5]:  # Top 5 patterns
                    confidence = getattr(pattern, "confidence", None)
                    confidence_str = (
                        f"{confidence:.1%}"
                        if isinstance(confidence, (int, float))
                        else "N/A"
                    )
                    lines.append(
                        f"  - {pattern.pattern_type}: {pattern.pattern_name} "
                        f"(confidence: {confidence_str})"
                    )

        # Scan errors
        if result.scan_errors:
            lines.append("\n" + "=" * 80)
            lines.append("SCAN ERRORS:")
            for error in result.scan_errors:
                lines.append(f"  ❌ {error}")

        lines.append("\n" + "=" * 80)
        lines.append("\nFor detailed results, check individual scanner reports:")
        lines.append("  - security_scan.json")
        lines.append("  - performance_analysis.json")
        lines.append("  - breaking_changes.json")
        lines.append("  - architecture_analysis.json")
        lines.append("=" * 80)

        return "\n".join(lines)

    def format_summary(self, result: PreventionScanResult) -> str:
        """
        Format a brief summary of prevention scan results.

        Args:
            result: Result to format

        Returns:
            Brief summary string
        """
        summary_parts = []

        if result.should_block:
            summary_parts.append("🚫 CRITICAL issues detected")
        elif result.should_warn:
            summary_parts.append("⚠️  Issues detected")
        else:
            summary_parts.append("✅ No critical issues")

        summary_parts.append(
            f"[Total: {result.summary.get('total_issues', 0)} issues - "
            f"Critical: {result.summary.get('critical', 0)}, "
            f"High: {result.summary.get('high', 0)}, "
            f"Medium: {result.summary.get('medium', 0)}, "
            f"Low: {result.summary.get('low', 0)}]"
        )

        scanners_with_issues = result.summary.get("scanners_with_issues", [])
        if scanners_with_issues:
            summary_parts.append(f"Flagged by: {', '.join(scanners_with_issues)}")

        return " ".join(summary_parts)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def scan_for_issues(
    project_dir: Path,
    spec_dir: Path | None = None,
    changed_files: list[str] | None = None,
    old_dir: Path | None = None,
    run_security: bool = True,
    run_performance: bool = True,
    run_breaking_changes: bool = False,
    run_architecture: bool = True,
) -> PreventionScanResult:
    """
    Convenience function to run prevention scan.

    Args:
        project_dir: Path to project root
        spec_dir: Optional spec directory to save results
        changed_files: Optional list of files to scan
        old_dir: Optional path to old version for breaking change detection
        run_security: Whether to run security scanning
        run_performance: Whether to run performance analysis
        run_breaking_changes: Whether to run breaking change detection
        run_architecture: Whether to run architecture validation

    Returns:
        PreventionScanResult with all findings
    """
    config = PreventionConfig(
        security_enabled=run_security,
        performance_enabled=run_performance,
        breaking_changes_enabled=run_breaking_changes,
        architecture_enabled=run_architecture,
    )
    scanner = PreventionScanner(config=config)
    return scanner.scan(
        project_dir=project_dir,
        spec_dir=spec_dir,
        changed_files=changed_files,
        old_dir=old_dir,
    )


def has_blocking_issues(project_dir: Path) -> bool:
    """
    Quick check if project has blocking issues.

    Args:
        project_dir: Path to project root

    Returns:
        True if any blocking issues found
    """
    scanner = PreventionScanner()
    result = scanner.scan(project_dir)
    return result.should_block


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Run proactive issue prevention scan")
    parser.add_argument("project_dir", type=Path, help="Path to project root")
    parser.add_argument("--spec-dir", type=Path, help="Path to spec directory")
    parser.add_argument(
        "--old-dir", type=Path, help="Path to old version for breaking change detection"
    )
    parser.add_argument("--no-security", action="store_true", help="Skip security scan")
    parser.add_argument(
        "--no-performance", action="store_true", help="Skip performance analysis"
    )
    parser.add_argument(
        "--breaking-changes",
        action="store_true",
        help="Enable breaking change detection (requires --old-dir)",
    )
    parser.add_argument(
        "--no-architecture", action="store_true", help="Skip architecture validation"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--summary", action="store_true", help="Show brief summary only"
    )

    args = parser.parse_args()

    config = PreventionConfig(
        security_enabled=not args.no_security,
        performance_enabled=not args.no_performance,
        breaking_changes_enabled=args.breaking_changes,
        architecture_enabled=not args.no_architecture,
    )
    scanner = PreventionScanner(config=config)
    result = scanner.scan(
        project_dir=args.project_dir,
        spec_dir=args.spec_dir,
        old_dir=args.old_dir,
    )

    if args.json:
        # Output full JSON results
        data = {
            "summary": result.summary,
            "has_critical_issues": result.has_critical_issues,
            "should_block": result.should_block,
            "should_warn": result.should_warn,
            "scan_errors": result.scan_errors,
        }
        print(json.dumps(data, indent=2))
    elif args.summary:
        print(scanner.format_summary(result))
    else:
        print(scanner.format_report(result))

    # Exit with error code if blocking issues found
    if result.should_block:
        exit(1)


if __name__ == "__main__":
    main()
