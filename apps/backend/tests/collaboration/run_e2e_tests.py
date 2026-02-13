#!/usr/bin/env python3
"""
Collaborative Editing E2E Test Runner
=====================================

This script runs end-to-end tests for the collaborative editing feature.

Usage:
    # Run all E2E tests
    python apps/backend/tests/collaboration/run_e2e_tests.py

    # Run specific test
    python apps/backend/tests/collaboration/run_e2e_tests.py -k test_content_sync

    # Run with verbose output
    python apps/backend/tests/collaboration/run_e2e_tests.py -v

    # Run with coverage
    python apps/backend/tests/collaboration/run_e2e_tests.py --cov
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(
    test_file: str | None = None,
    verbose: bool = False,
    coverage: bool = False,
    keyword: str | None = None,
):
    """Run the E2E tests.

    Args:
        test_file: Specific test file to run
        verbose: Enable verbose output
        coverage: Run with coverage reporting
        keyword: Filter tests by keyword
    """
    # Determine the test path
    backend_dir = Path(__file__).parent.parent.parent.parent
    tests_dir = backend_dir / "tests" / "collaboration"

    if not tests_dir.exists():
        print(f"ERROR: Tests directory not found: {tests_dir}")
        return 1

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=apps.backend.collaboration",
            "--cov-report=term-missing",
            "--cov-report=html",
        ])

    # Add test path
    if test_file:
        test_path = tests_dir / test_file
        cmd.append(str(test_path))
    else:
        cmd.append(str(tests_dir))

    # Add keyword filter
    if keyword:
        cmd.extend(["-k", keyword])

    # Add color output
    cmd.append("--color=yes")

    # Print command
    print("Running:", " ".join(cmd))
    print()

    # Run tests
    result = subprocess.run(cmd, cwd=backend_dir.parent.parent)

    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run collaborative editing E2E tests"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--cov",
        "--coverage",
        action="store_true",
        help="Run with coverage reporting",
    )
    parser.add_argument(
        "-k",
        "--keyword",
        help="Filter tests by keyword",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Specific test file to run",
    )

    args = parser.parse_args()

    return run_tests(
        test_file=args.file,
        verbose=args.verbose,
        coverage=args.coverage,
        keyword=args.keyword,
    )


if __name__ == "__main__":
    sys.exit(main())
