"""
Shared Test Validation Utilities
=================================

Common validation logic for Python test files (pytest/e2e).
Used by both test_generator.py and e2e_generator.py.
"""

import asyncio
import logging
import subprocess
from pathlib import Path

from ui import print_status

logger = logging.getLogger(__name__)


async def validate_python_tests(
    test_files: list[Path], project_dir: Path, label: str = "pytest"
) -> bool:
    """
    Validate that generated Python tests are syntactically correct.

    Checks Python syntax with compile() and uses pytest --collect-only
    to verify tests can be collected without errors. Runs subprocess calls
    in a thread to avoid blocking the event loop.

    Args:
        test_files: List of generated test file paths (relative to project_dir)
        project_dir: Project root directory
        label: Label for status messages (e.g. "pytest", "E2E")

    Returns:
        True if all tests are valid, False otherwise
    """
    if not test_files:
        logger.warning(f"No {label} test files to validate")
        return False

    print()
    print_status(f"Validating generated {label} tests...", "progress")

    for test_file in test_files:
        file_path = project_dir / test_file
        if not file_path.exists():
            print_status(f"Test file not found: {test_file}", "error")
            return False

        # Check Python syntax
        try:
            source = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
            compile(source, str(file_path), "exec")
            print_status(f"Syntax valid: {test_file.name}", "success")
        except SyntaxError as e:
            print_status(f"Syntax error in {test_file}: {e}", "error")
            return False

        # Check if pytest can collect tests (non-blocking)
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["pytest", str(file_path), "--collect-only", "-q"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Allow conftest.py with no collected tests (fixtures only)
            if result.returncode != 0 and file_path.name != "conftest.py":
                print_status(f"pytest collection failed for {test_file}", "error")
                logger.debug(f"pytest output: {result.stdout}\n{result.stderr}")
                return False
            print_status(f"pytest collection OK: {test_file.name}", "success")
        except subprocess.TimeoutExpired:
            print_status(f"pytest collection timeout for {test_file}", "error")
            return False
        except FileNotFoundError:
            logger.warning("pytest not found - skipping collection validation")
            print_status("pytest not available - syntax check only", "warning")
            continue

    print_status(f"All generated {label} tests are valid", "success")
    return True
