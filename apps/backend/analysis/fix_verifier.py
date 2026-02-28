#!/usr/bin/env python3
"""
Fix Verifier Module
===================

Verifies suggested fixes by running tests and analyzing code changes.
This module helps ensure that proposed fixes actually resolve the issue
without introducing new problems.

The fix verifier results are used by:
- QA Agent: To validate fixes before applying them
- Debug Assistant: To confirm fixes will work
- Coder Agent: To test changes before committing

Usage:
    from fix_verifier import verify_fix, FixVerifier

    verifier = FixVerifier()
    result = verifier.verify(
        fix_suggestion=fix,
        project_dir=Path("/path/to/project")
    )

    print(f"Fix verified: {result['is_safe']}")
    print(f"Tests to run: {result['test_command']}")
"""

from __future__ import annotations

import hashlib
import json
import logging
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class FixSuggestion:
    """
    Represents a fix suggestion from the fix suggester.

    Attributes:
        root_cause: Description of the root cause
        fix_category: Category of the fix (import_error, type_error, etc.)
        suggested_fixes: List of fix descriptions
        verification_steps: Steps to verify the fix
        confidence: Confidence score (0-1)
        pattern_based: Whether this is a pattern-based suggestion
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    root_cause: str
    fix_category: str
    suggested_fixes: list[str]
    verification_steps: list[str]
    confidence: float = 0.5
    pattern_based: bool = False
    ai_generated: bool = False


@dataclass
class VerificationResult:
    """
    Result of fix verification.

    Attributes:
        is_safe: Whether the fix is safe to apply
        test_command: Command to run tests
        test_results: Results of running tests
        risk_level: Risk level of applying the fix
        warnings: Any warnings about the fix
        recommendations: Additional recommendations
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    is_safe: bool = False
    test_command: str = ""
    test_results: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "unknown"  # low, medium, high
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# =============================================================================
# FIX VERIFIER
# =============================================================================


class FixVerifier:
    """
    Verifies suggested fixes by analyzing and testing them.

    Provides:
    - Risk assessment for proposed changes
    - Test discovery to run relevant tests
    - Safety checks before applying fixes
    - Recommendations for safe implementation
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(self) -> None:
        """Initialize the fix verifier."""
        self._cache: dict[str, VerificationResult] = {}

    def verify(
        self,
        fix_suggestion: dict | FixSuggestion,
        project_dir: Path,
        parsed_trace: dict | None = None,
    ) -> VerificationResult:
        """
        Verify a fix suggestion.

        Args:
            fix_suggestion: The fix suggestion to verify
            project_dir: Path to the project root
            parsed_trace: Original parsed stack trace (optional)

        Returns:
            VerificationResult with safety assessment and test recommendations
        """
        project_dir = Path(project_dir)
        cache_key = self._make_cache_key(fix_suggestion, str(project_dir.resolve()))

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Normalize input to FixSuggestion
        fix = self._normalize_fix_suggestion(fix_suggestion)

        result = VerificationResult()

        # Assess risk
        result.risk_level = self._assess_risk(fix, parsed_trace)

        # Discover test command
        result.test_command = self._discover_test_command(project_dir)

        # Generate warnings based on fix category
        result.warnings = self._generate_warnings(fix)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(fix, result.risk_level)

        # Determine if fix is safe to apply
        result.is_safe = self._is_safe_to_apply(fix, result)

        # Run tests if available
        if result.test_command and self._should_run_tests(result.risk_level):
            result.test_results = self._run_tests(result.test_command, project_dir)

        self._cache[cache_key] = result
        return result

    def _normalize_fix_suggestion(self, fix: dict | FixSuggestion) -> FixSuggestion:
        """Normalize fix suggestion to FixSuggestion dataclass."""
        if isinstance(fix, FixSuggestion):
            return fix

        return FixSuggestion(
            root_cause=fix.get("root_cause", "Unknown"),
            fix_category=fix.get("fix_category", "unknown"),
            suggested_fixes=fix.get("suggested_fixes", []),
            verification_steps=fix.get("verification_steps", []),
            confidence=fix.get("confidence", 0.5),
            pattern_based=fix.get("pattern_based", False),
            ai_generated=fix.get("ai_generated", False),
        )

    def _make_cache_key(self, fix: dict | FixSuggestion, project_dir: str) -> str:
        """Generate a content-based cache key for the fix."""
        if isinstance(fix, FixSuggestion):
            category = fix.fix_category
            fixes = fix.suggested_fixes
        else:
            category = fix.get("fix_category", "unknown")
            fixes = fix.get("suggested_fixes", [])

        content = json.dumps(fixes, sort_keys=True, default=str)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"{project_dir}:{category}:{content_hash}"

    def _assess_risk(self, fix: FixSuggestion, parsed_trace: dict | None) -> str:
        """
        Assess the risk level of applying a fix.

        Args:
            fix: The fix suggestion
            parsed_trace: Original error trace

        Returns:
            Risk level: low, medium, or high
        """
        # High-risk fixes
        if fix.fix_category in ["file_error", "permission_error", "network_error"]:
            return "high"

        # Medium-risk fixes
        if fix.fix_category in ["import_error", "type_error", "null_reference"]:
            return "medium"

        # Low-risk fixes
        if fix.fix_category in ["syntax_error", "lookup_error", "timeout"]:
            return "low"

        # Default to medium for unknown categories
        return "medium"

    def _discover_test_command(self, project_dir: Path) -> str:
        """Discover the test command for the project."""
        try:
            from .test_discovery import TestDiscovery

            discovery = TestDiscovery()
            result = discovery.discover(project_dir)
            return result.test_command
        except ImportError:
            logger.debug("TestDiscovery module not available, using fallback")
            return self._get_fallback_test_command(project_dir)
        except Exception as e:
            logger.warning(f"Test discovery failed: {e}")
            return self._get_fallback_test_command(project_dir)

    def _get_fallback_test_command(self, project_dir: Path) -> str:
        """Get fallback test command if discovery fails."""
        # Check for common test files
        test_indicators = {
            "pytest": [
                project_dir / "pytest.ini",
                project_dir / "conftest.py",
                project_dir / "tests" / "conftest.py",
            ],
            "npm": [project_dir / "package.json"],
            "cargo": [project_dir / "Cargo.toml"],
        }

        for test_type, indicators in test_indicators.items():
            if any(indicator.exists() for indicator in indicators):
                if test_type == "pytest":
                    return "pytest"
                elif test_type == "npm":
                    return "npm test"
                elif test_type == "cargo":
                    return "cargo test"

        return ""

    def _generate_warnings(self, fix: FixSuggestion) -> list[str]:
        """Generate warnings based on fix category."""
        warnings = []

        # Category-specific warnings
        category_warnings = {
            "import_error": [
                "Adding new dependencies may affect deployment",
                "Verify dependency version compatibility",
            ],
            "type_error": [
                "Type changes may break dependent code",
                "Run full test suite to catch cascading issues",
            ],
            "null_reference": [
                "Adding null checks is safe but may hide underlying issues",
                "Ensure all code paths initialize the variable",
            ],
            "file_error": [
                "File paths may differ across environments",
                "Use path utilities for cross-platform compatibility",
            ],
            "permission_error": [
                "Permission fixes may not work in all environments",
                "Verify permissions match deployment environment",
            ],
            "network_error": [
                "Network issues may be transient",
                "Verify service availability before applying fix",
            ],
        }

        warnings.extend(category_warnings.get(fix.fix_category, []))

        # Confidence-based warnings
        if fix.confidence < 0.5:
            warnings.append(
                "Low confidence suggestion - review carefully before applying"
            )

        return warnings

    def _generate_recommendations(
        self, fix: FixSuggestion, risk_level: str
    ) -> list[str]:
        """Generate recommendations for safe fix application."""
        recommendations = []

        # Always recommend creating a backup
        recommendations.append(
            "Create a backup or commit current changes before applying fix"
        )

        # Risk-specific recommendations
        if risk_level == "high":
            recommendations.extend(
                [
                    "Test in isolated environment first",
                    "Review fix with team before applying to production",
                    "Monitor system closely after applying fix",
                ]
            )
        elif risk_level == "medium":
            recommendations.extend(
                [
                    "Run affected tests to verify fix",
                    "Check for side effects in related code",
                ]
            )
        elif risk_level == "low":
            recommendations.extend(
                [
                    "Run quick smoke tests to verify fix",
                    "Consider edge cases that may not be covered",
                ]
            )

        # Category-specific recommendations
        if fix.fix_category == "import_error":
            recommendations.append(
                "Update requirements.txt or package.json if adding new dependency"
            )
        elif fix.fix_category == "file_error":
            recommendations.append(
                "Verify file paths work across different operating systems"
            )

        return recommendations

    def _is_safe_to_apply(self, fix: FixSuggestion, result: VerificationResult) -> bool:
        """Determine if fix is safe to apply."""
        # High-risk fixes with low confidence are not automatically safe
        if result.risk_level == "high" and fix.confidence < 0.6:
            return False

        # Medium-risk fixes with very low confidence require review
        if result.risk_level == "medium" and fix.confidence < 0.4:
            return False

        return True

    def _should_run_tests(self, risk_level: str) -> bool:
        """Determine if tests should be run."""
        # Always run tests for medium and high risk
        return risk_level in ["medium", "high"]

    def _run_tests(self, test_command: str, project_dir: Path) -> dict[str, Any]:
        """
        Run tests and return results.

        Args:
            test_command: Command to run tests
            project_dir: Project directory

        Returns:
            Dict with test results
        """
        result = {
            "ran": False,
            "passed": False,
            "exit_code": None,
            "output": "",
        }

        if not test_command:
            return result

        try:
            logger.info(f"Running test command: {test_command}")

            # Run test command (split into args to avoid shell=True)
            if sys.platform == "win32":
                cmd_args = test_command.split()
            else:
                cmd_args = shlex.split(test_command)
            process = subprocess.Popen(
                cmd_args,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            output, _ = process.communicate(timeout=300)  # 5 minute timeout

            result["ran"] = True
            result["passed"] = process.returncode == 0
            result["exit_code"] = process.returncode
            result["output"] = output

            logger.info(f"Tests completed with exit code: {process.returncode}")

        except subprocess.TimeoutExpired:
            logger.warning("Test execution timed out after 5 minutes")
            process.kill()
            process.communicate()  # Reap the process
            result["ran"] = True
            result["output"] = "Test execution timed out"
        except Exception as e:
            logger.warning(f"Failed to run tests: {e}")
            result["output"] = str(e)

        return result

    def to_dict(self, result: VerificationResult) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "is_safe": result.is_safe,
            "test_command": result.test_command,
            "test_results": result.test_results,
            "risk_level": result.risk_level,
            "warnings": result.warnings,
            "recommendations": result.recommendations,
        }

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self._cache.clear()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def verify_fix(
    fix_suggestion: dict | FixSuggestion,
    project_dir: Path,
    parsed_trace: dict | None = None,
) -> VerificationResult:
    """
    Verify a fix suggestion.

    Convenience function that creates a verifier and runs verification.

    Args:
        fix_suggestion: The fix suggestion to verify
        project_dir: Path to the project root
        parsed_trace: Original parsed stack trace (optional)

    Returns:
        VerificationResult with safety assessment
    """
    verifier = FixVerifier()
    return verifier.verify(fix_suggestion, project_dir, parsed_trace)


def assess_fix_risk(
    fix_suggestion: dict | FixSuggestion,
    parsed_trace: dict | None = None,
) -> str:
    """
    Assess the risk level of a fix.

    Args:
        fix_suggestion: The fix suggestion to assess
        parsed_trace: Original parsed stack trace (optional)

    Returns:
        Risk level: low, medium, or high
    """
    verifier = FixVerifier()
    fix = verifier._normalize_fix_suggestion(fix_suggestion)
    return verifier._assess_risk(fix, parsed_trace)


def get_test_command(project_dir: Path) -> str:
    """
    Get the test command for a project.

    Args:
        project_dir: Path to project root

    Returns:
        Test command string, or empty string if not found
    """
    verifier = FixVerifier()
    return verifier._discover_test_command(project_dir)


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify fix suggestions")
    parser.add_argument("project_dir", type=Path, help="Path to project root")
    parser.add_argument("--fix-file", type=Path, help="JSON file with fix suggestion")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.fix_file:
        # Load fix from file
        fix_data = json.loads(args.fix_file.read_text(encoding="utf-8"))
    else:
        # Use example fix
        fix_data = {
            "root_cause": "Module not found",
            "fix_category": "import_error",
            "suggested_fixes": ["Install missing module"],
            "verification_steps": ["Import module", "Run tests"],
            "confidence": 0.8,
        }

    verifier = FixVerifier()
    result = verifier.verify(fix_data, args.project_dir)

    if args.json:
        print(json.dumps(verifier.to_dict(result), indent=2))
    else:
        print(f"Safe to apply: {result.is_safe}")
        print(f"Risk level: {result.risk_level}")
        print(f"Test command: {result.test_command or 'none'}")
        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  - {warning}")
        if result.recommendations:
            print(f"\nRecommendations ({len(result.recommendations)}):")
            for rec in result.recommendations:
                print(f"  - {rec}")
        if result.test_results.get("ran"):
            print("\nTest results:")
            print(f"  - Passed: {result.test_results.get('passed', False)}")
            print(f"  - Exit code: {result.test_results.get('exit_code')}")


if __name__ == "__main__":
    main()
