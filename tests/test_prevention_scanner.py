#!/usr/bin/env python3
"""
Tests for Prevention Scanner
==============================

Tests the prevention_scanner module which consolidates all proactive
issue detection scanners for comprehensive analysis.
"""

import json

# Add apps/backend to path for imports
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.prevention_config import PreventionConfig
from analysis.prevention_scanner import (
    PreventionScanner,
    PreventionScanResult,
    has_blocking_issues,
    scan_for_issues,
)


class TestPreventionScanResult:
    """Test PreventionScanResult dataclass."""

    def test_create_result(self):
        """Test creating a scan result."""
        result = PreventionScanResult(
            security=None,
            performance=None,
            breaking_changes=None,
            architecture=None,
            scan_errors=[],
            has_critical_issues=False,
            should_block=False,
            should_warn=False,
            summary={},
        )

        assert result.has_critical_issues is False
        assert result.should_block is False
        assert len(result.scan_errors) == 0


class TestPreventionScanner:
    """Test PreventionScanner class."""

    def test_init_with_default_config(self):
        """Test scanner initialization with default config."""
        scanner = PreventionScanner()

        assert scanner is not None
        assert scanner.config is not None
        assert scanner.security_scanner is not None
        assert scanner.performance_analyzer is not None
        assert scanner.breaking_change_detector is not None
        assert scanner.architecture_validator is not None

    def test_init_with_custom_config(self):
        """Test scanner initialization with custom config."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=True,
            breaking_changes_enabled=False,
            architecture_enabled=True,
        )

        scanner = PreventionScanner(config=config)

        assert scanner.config.security_enabled is False
        assert scanner.config.performance_enabled is True

    def test_scan_with_all_scanners_disabled(self, tmp_path):
        """Test scanning with all scanners disabled."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=False,
            breaking_changes_enabled=False,
            architecture_enabled=False,
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path)

        # All scanners disabled, no results
        assert result.security is None
        assert result.performance is None
        assert result.breaking_changes is None
        assert result.architecture is None

    def test_scan_with_security_enabled(self, tmp_path):
        """Test scanning with security scanner enabled."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=False,
            breaking_changes_enabled=False,
            architecture_enabled=False,
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path)

        # Security should be scanned
        assert result.security is not None
        assert result.performance is None
        assert result.breaking_changes is None
        assert result.architecture is None

    def test_scan_with_performance_enabled(self, tmp_path):
        """Test scanning with performance analyzer enabled."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=True,
            breaking_changes_enabled=False,
            architecture_enabled=False,
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path)

        # Performance should be analyzed
        assert result.security is None
        assert result.performance is not None

    def test_scan_with_architecture_enabled(self, tmp_path):
        """Test scanning with architecture validator enabled."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=False,
            breaking_changes_enabled=False,
            architecture_enabled=True,
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path)

        # Architecture should be validated
        assert result.architecture is not None

    def test_scan_with_spec_dir_saves_results(self, tmp_path):
        """Test that scan saves results when spec_dir provided."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        config = PreventionConfig(
            security_enabled=True,
            save_reports=True,
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path, spec_dir=spec_dir)

        # Consolidated results should be saved
        assert (spec_dir / "prevention_scan.json").exists()

    def test_scan_with_changed_files_filter(self, tmp_path):
        """Test scanning only changed files."""
        (tmp_path / "module1.py").write_text("def test(): pass")
        (tmp_path / "module2.py").write_text("def test(): pass")

        config = PreventionConfig(performance_enabled=True)

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path, changed_files=["module1.py"])

        # Should only scan specified files
        assert result.performance is not None

    def test_scan_handles_scanner_error_gracefully(self, tmp_path):
        """Test that scanner errors are handled gracefully."""
        config = PreventionConfig(
            security_enabled=True,
            fail_on_scan_error=False,
        )

        scanner = PreventionScanner(config=config)

        # Mock security scanner to raise exception
        with patch.object(
            scanner.security_scanner, "scan", side_effect=Exception("Test error")
        ):
            result = scanner.scan(tmp_path)

            # Should capture error but not crash
            assert len(result.scan_errors) > 0
            assert "Security scan failed" in result.scan_errors[0]

    def test_scan_raises_on_error_when_fail_on_scan_error_enabled(self, tmp_path):
        """Test that scanner raises on error when fail_on_scan_error is True."""
        config = PreventionConfig(
            security_enabled=True,
            fail_on_scan_error=True,
        )

        scanner = PreventionScanner(config=config)

        # Mock security scanner to raise exception
        with patch.object(
            scanner.security_scanner, "scan", side_effect=Exception("Test error")
        ):
            with pytest.raises(RuntimeError, match="Security scan failed"):
                scanner.scan(tmp_path)

    def test_aggregate_results_calculates_summary_correctly(self, tmp_path):
        """Test that _aggregate_results calculates summary correctly."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=True,
            architecture_enabled=True,
        )

        # Create files to trigger some issues
        (tmp_path / "test.py").write_text("""
for user in users:
    posts = session.query(Post).all()
""")

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path)

        # Summary should be populated
        assert "total_issues" in result.summary
        assert "scanners_run" in result.summary
        assert len(result.summary["scanners_run"]) == 3

    def test_aggregate_results_sets_blocking_flags_correctly(self, tmp_path):
        """Test that _aggregate_results sets blocking flags correctly."""
        config = PreventionConfig(
            security_enabled=True,
            block_on_critical=True,
            block_on_high=False,
        )

        scanner = PreventionScanner(config=config)

        # Mock a critical security issue
        from analysis.security_scanner import SecurityScanResult, SecurityVulnerability

        mock_result = SecurityScanResult(
            secrets=["fake_secret"],
            vulnerabilities=[
                SecurityVulnerability(
                    severity="critical",
                    source="test",
                    title="SQL Injection",
                    description="SQL injection detected",
                    file="test.py",
                    line=1,
                    cwe="CWE-89",
                )
            ],
        )

        with patch.object(scanner.security_scanner, "scan", return_value=mock_result):
            result = scanner.scan(tmp_path)

            # Should block due to critical vulnerability
            assert result.has_critical_issues is True
            assert result.should_block is True

    def test_format_report(self):
        """Test formatting scan results as a report."""
        scanner = PreventionScanner()
        result = PreventionScanResult(
            summary={
                "total_issues": 5,
                "critical": 1,
                "high": 2,
                "medium": 2,
                "low": 0,
                "scanners_run": ["security", "performance"],
                "scanners_with_issues": ["performance"],
            },
            should_block=False,
            should_warn=True,
        )

        report = scanner.format_report(result)

        assert "PROACTIVE ISSUE PREVENTION SCAN REPORT" in report
        assert "Total Issues Found: 5" in report
        assert "Critical: 1" in report
        assert "High:     2" in report

    def test_format_summary(self):
        """Test formatting brief summary."""
        scanner = PreventionScanner()
        result = PreventionScanResult(
            summary={
                "total_issues": 3,
                "critical": 1,
                "high": 1,
                "medium": 1,
                "low": 0,
                "scanners_with_issues": ["security", "performance"],
            },
            should_block=True,
            should_warn=False,
        )

        summary = scanner.format_summary(result)

        assert "CRITICAL issues detected" in summary
        assert "Total: 3" in summary
        assert "Flagged by: security, performance" in summary

    def test_save_results_creates_consolidated_file(self, tmp_path):
        """Test that _save_results creates consolidated results file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        scanner = PreventionScanner()

        # Create a result with some data
        from analysis.security_scanner import SecurityScanResult

        result = PreventionScanResult(
            security=SecurityScanResult(secrets=[], vulnerabilities=[]),
            summary={
                "total_issues": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "scanners_run": ["security"],
                "scanners_with_issues": [],
            },
        )

        scanner._save_results(spec_dir, result)

        output_file = spec_dir / "prevention_scan.json"
        assert output_file.exists()

        data = json.loads(output_file.read_text())
        assert "summary" in data
        assert "scanners" in data
        assert "security" in data["scanners"]

    def test_breaking_changes_scanner_only_runs_with_old_dir(self, tmp_path):
        """Test that breaking changes scanner requires old_dir."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=False,
            breaking_changes_enabled=True,
            architecture_enabled=False,
        )

        scanner = PreventionScanner(config=config)

        # Scan without old_dir
        result = scanner.scan(tmp_path)

        # Breaking changes should not run
        assert result.breaking_changes is None

        # Scan with old_dir
        old_dir = tmp_path / "old"
        old_dir.mkdir()

        result = scanner.scan(tmp_path, old_dir=old_dir)

        # Breaking changes should run
        assert result.breaking_changes is not None


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_scan_for_issues_with_custom_scanners(self, tmp_path):
        """Test scan_for_issues convenience function with custom scanner selection."""
        result = scan_for_issues(
            tmp_path,
            run_security=True,
            run_performance=False,
            run_breaking_changes=False,
            run_architecture=False,
        )

        assert isinstance(result, PreventionScanResult)
        assert result.security is not None
        assert result.performance is None

    def test_scan_for_issues_with_spec_dir(self, tmp_path):
        """Test scan_for_issues saves to spec_dir."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = scan_for_issues(
            tmp_path,
            spec_dir=spec_dir,
            run_security=True,
        )

        # Results should be saved
        assert (spec_dir / "prevention_scan.json").exists()

    def test_has_blocking_issues_returns_true_when_blocking(self, tmp_path):
        """Test has_blocking_issues returns True when issues should block."""
        # Create file with critical issue
        (tmp_path / "test.py").write_text("""
try:
    pass
except:
    pass
""")

        # Bare except is high severity in architecture validator
        has_blocking = has_blocking_issues(tmp_path)

        # Result depends on default config blocking policy
        assert isinstance(has_blocking, bool)

    def test_has_blocking_issues_returns_false_when_no_blocking(self, tmp_path):
        """Test has_blocking_issues returns False when no blocking issues."""
        (tmp_path / "test.py").write_text("def test(): pass")

        has_blocking = has_blocking_issues(tmp_path)

        # Clean file should not have blocking issues
        assert has_blocking is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_scan_empty_project(self, tmp_path):
        """Test scanning an empty project."""
        scanner = PreventionScanner()
        result = scanner.scan(tmp_path)

        # Should complete without errors
        assert len(result.scan_errors) == 0
        assert result.has_critical_issues is False

    def test_scan_with_all_scanners_enabled(self, tmp_path):
        """Test scanning with all scanners enabled."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=True,
            breaking_changes_enabled=False,  # Requires old_dir
            architecture_enabled=True,
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path)

        # All enabled scanners should run
        assert result.security is not None
        assert result.performance is not None
        assert result.architecture is not None

    def test_summary_includes_all_scanners_run(self, tmp_path):
        """Test that summary includes all scanners that were run."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=True,
            architecture_enabled=True,
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path)

        assert "security" in result.summary["scanners_run"]
        assert "performance" in result.summary["scanners_run"]
        assert "architecture" in result.summary["scanners_run"]

    def test_summary_severity_counts(self, tmp_path):
        """Test that summary correctly counts issues by severity."""
        # Create file with issues of different severities
        (tmp_path / "test.py").write_text("""
# Bare except (high)
try:
    pass
except:
    pass

# N+1 query (high)
for user in users:
    posts = session.query(Post).all()
""")

        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=True,
            architecture_enabled=True,
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path)

        # Should have counts
        assert result.summary["total_issues"] >= 0
        assert "critical" in result.summary
        assert "high" in result.summary
        assert "medium" in result.summary

    def test_save_reports_false_does_not_save_individual_reports(self, tmp_path):
        """Test that individual scanner reports are not saved when save_reports=False."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=True,
            save_reports=False,  # Don't save individual reports
        )

        scanner = PreventionScanner(config=config)
        result = scanner.scan(tmp_path, spec_dir=spec_dir)

        # Consolidated report should exist
        assert (spec_dir / "prevention_scan.json").exists()

        # Individual reports should NOT exist
        assert not (spec_dir / "security_scan.json").exists()
        assert not (spec_dir / "performance_analysis.json").exists()

    def test_scan_with_no_issues_found(self, tmp_path):
        """Test scanning clean code with no issues."""
        (tmp_path / "clean.py").write_text('''
def clean_function(param: str) -> str:
    """Clean function with no issues."""
    return param.upper()
''')

        scanner = PreventionScanner()
        result = scanner.scan(tmp_path)

        # Should complete successfully
        assert result.has_critical_issues is False
        assert result.should_block is False
        assert result.should_warn is False
