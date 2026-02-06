#!/usr/bin/env python3
"""
Import Chain Verification Test
================================

Verifies that CodeReviewService can be imported correctly within
the GitHub runner context. The service is designed to be used within
the runner.py context, not standalone.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# =============================================================================
# IMPORT CHAIN TESTS
# =============================================================================


class TestImportChain:
    """Tests for verifying import chain works in GitHub runner context."""

    def test_code_review_service_imports_in_runner_context(self):
        """Test that CodeReviewService imports when sys.path includes runner context."""
        # Get the backend directory
        backend_dir = (
            Path(__file__).parent.parent.parent / "apps" / "backend"
        )

        # Import should work when we add backend to sys.path
        original_path = sys.path.copy()
        try:
            sys.path.insert(0, str(backend_dir))

            # This should work in runner context
            from runners.github.services.code_review_service import (
                CodeReviewService,
            )

            assert (
                CodeReviewService is not None
            ), "CodeReviewService should import successfully"

        finally:
            sys.path = original_path

    def test_runner_command_help_works(self):
        """Test that the code-review-pr command help works."""
        backend_dir = (
            Path(__file__).parent.parent.parent / "apps" / "backend"
        )
        runner_script = backend_dir / "runners" / "github" / "runner.py"

        # Skip test if runner script doesn't exist
        if not runner_script.exists():
            pytest.skip("runner.py not found")

        # Try to run the help command
        result = subprocess.run(
            [sys.executable, str(runner_script), "code-review-pr", "--help"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # The command should either:
        # 1. Show help (exit code 0)
        # 2. Fail with a known error (but not import error)
        # We just want to verify the module can be loaded

        # Check that it's not an import error
        assert (
            "ImportError" not in result.stderr
        ), f"Import error detected: {result.stderr}"
        assert (
            "ModuleNotFoundError" not in result.stderr
        ), f"Module not found: {result.stderr}"

    def test_service_dependencies_available(self):
        """Test that service dependencies can be imported."""
        backend_dir = (
            Path(__file__).parent.parent.parent / "apps" / "backend"
        )

        original_path = sys.path.copy()
        try:
            sys.path.insert(0, str(backend_dir))

            # Import dependencies that CodeReviewService needs
            from analysis.security_scanner import SecurityScanner
            from runners.github.models import GitHubRunnerConfig, PRReviewFinding

            assert SecurityScanner is not None
            assert GitHubRunnerConfig is not None
            assert PRReviewFinding is not None

        finally:
            sys.path = original_path

    def test_import_from_runner_py_context(self):
        """Test importing as if we're inside runner.py."""
        backend_dir = (
            Path(__file__).parent.parent.parent / "apps" / "backend"
        )
        runners_dir = backend_dir / "runners" / "github"

        original_path = sys.path.copy()
        original_cwd = Path.cwd()

        try:
            # Simulate being in the runner.py context
            sys.path.insert(0, str(backend_dir))
            sys.path.insert(0, str(runners_dir))

            # Use absolute import path
            from runners.github.services.code_review_service import CodeReviewService

            assert CodeReviewService is not None

        finally:
            sys.path = original_path


# =============================================================================
# DOCUMENTATION TEST
# =============================================================================


class TestServiceDocumentation:
    """Tests for service documentation."""

    def test_service_has_usage_documentation(self):
        """Test that service file has usage documentation."""
        backend_dir = (
            Path(__file__).parent.parent.parent / "apps" / "backend"
        )
        service_file = (
            backend_dir / "runners" / "github" / "services" / "code_review_service.py"
        )

        if not service_file.exists():
            pytest.skip("code_review_service.py not found")

        content = service_file.read_text()

        # Should have documentation about usage
        assert "Usage:" in content or "usage:" in content.lower()

        # Should document the import pattern
        assert (
            "from runners.github.services.code_review_service import" in content
            or "CodeReviewService" in content
        )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def run_all_tests():
    """Run all tests using pytest."""
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))


if __name__ == "__main__":
    run_all_tests()
