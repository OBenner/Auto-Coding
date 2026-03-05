"""
Fixture Generator Agent Module
================================

AI agent that generates pytest fixtures and test data factories based on code analysis.
Creates reusable fixtures for unit and integration tests following pytest best practices.

Generated fixtures support:
- Basic data fixtures for common test scenarios
- Factory fixtures for customizable test instances
- Mock fixtures for external dependencies
- Setup/teardown fixtures for test isolation
"""

import json
import logging
from pathlib import Path
from typing import Any

from task_logger import LogPhase
from ui import (
    print_key_value,
    print_status,
)

from ._generator_base import log_generator_result, run_generator_session
from ._validation import validate_python_tests

logger = logging.getLogger(__name__)


async def validate_fixture_files(fixture_files: list[Path], project_dir: Path) -> bool:
    """
    Validate that generated fixture files are syntactically correct.

    Uses Python syntax check to verify fixtures can be imported.
    Runs subprocess calls in a thread to avoid blocking the event loop.

    Args:
        fixture_files: List of generated fixture file paths
        project_dir: Project root directory

    Returns:
        True if all fixtures are valid, False otherwise
    """
    return await validate_python_tests(fixture_files, project_dir, label="Fixture")


async def generate_fixtures(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run Fixture Generator Agent session to generate pytest fixtures and test data.

    Creates reusable fixtures that support unit and integration tests with realistic
    test data, mocks, and setup/teardown patterns.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results (classes, functions, models)
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - generated_files: List of generated fixture file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
        - framework: Test framework used ("pytest-fixtures")
    """
    # Count entities that need fixtures
    classes_count = len(analysis_results.get("classes", []))
    functions_count = len(analysis_results.get("functions", []))
    models_count = len(analysis_results.get("models", []))

    starting_message = f"""You are the Fixture Generator Agent. Your task is to generate pytest fixtures and test data factories for comprehensive test coverage.

## Code Analysis Results

{json.dumps(analysis_results, indent=2)}

## Your Task

1. Read the spec.md to understand what was implemented
2. Review the implementation_plan.json to see what modules were built
3. Study existing fixtures in tests/conftest.py (if it exists)
4. Identify data structures that need fixtures (classes, models, configs)
5. Generate fixture files with reusable test data and mocks
6. Follow the project's fixture conventions
7. Create fixtures for both happy path and error scenarios

## Fixture Patterns to Use

Your fixtures should include:
- **Simple data fixtures**: Provide basic test data instances
- **Factory fixtures**: Allow customizable test instance creation
- **Mock fixtures**: Mock external dependencies (APIs, databases, file system)
- **Parametrized fixtures**: Support multiple test scenarios
- **Setup/teardown fixtures**: Handle test isolation and cleanup

## File Organization

Place fixtures in appropriate locations:
- **tests/conftest.py**: Shared fixtures used across multiple test files
- **tests/fixtures/<category>.py**: Organize large fixture sets by category
- **tests/test_<module>.py**: Test-specific fixtures directly in test files

Generate fixtures that make writing tests easier and more maintainable.

Begin by loading context (Phase 0 in your prompt).
"""

    # Run the shared generator session boilerplate
    session_result = await run_generator_session(
        project_dir=project_dir,
        spec_dir=spec_dir,
        analysis_results=analysis_results,
        session_title="FIXTURE GENERATOR SESSION",
        session_description="Generating pytest fixtures and test data factories...",
        prompt_name="fixture_generator",
        agent_type="fixture_generator",
        session_name="fixture-generator-session",
        starting_message=starting_message,
        log_phase=LogPhase.VALIDATION,
        log_summary=(
            f"Analyzing {classes_count} classes, "
            f"{functions_count} functions, "
            f"{models_count} models for fixture generation"
        ),
        model=model,
        max_thinking_tokens=max_thinking_tokens,
        verbose=verbose,
    )

    framework = "pytest-fixtures"

    if not session_result["success"]:
        return {
            "generated_files": [],
            "success": False,
            "error": session_result["error"],
            "framework": framework,
        }

    # Scan for newly created fixture files
    print()
    print_status("Scanning for generated fixture files...", "progress")

    fixture_files: list[Path] = []

    # Check tests/conftest.py
    conftest_path = project_dir / "tests" / "conftest.py"
    if conftest_path.exists():
        fixture_files.append(conftest_path.relative_to(project_dir))
        print_key_value("Found conftest", str(conftest_path.relative_to(project_dir)))

    # Check tests/fixtures/ directory
    fixtures_dir = project_dir / "tests" / "fixtures"
    if fixtures_dir.exists():
        for fixture_file in fixtures_dir.glob("*.py"):
            if fixture_file.name != "__init__.py":
                fixture_files.append(fixture_file.relative_to(project_dir))
                print_key_value(
                    "Found fixture file",
                    str(fixture_file.relative_to(project_dir)),
                )

    if not fixture_files:
        print()
        print_status(
            "No fixture files found. Check that agent created files in tests/conftest.py or tests/fixtures/",
            "warning",
        )
        return {
            "generated_files": [],
            "success": True,
            "error": None,
            "framework": framework,
        }

    print()
    print_key_value("Total fixture files", str(len(fixture_files)))

    # Validate fixtures
    print()
    print_status("Validating generated fixtures...", "progress")
    validation_success = await validate_fixture_files(fixture_files, project_dir)

    # Log results
    log_generator_result(
        spec_dir=spec_dir,
        test_files=fixture_files,
        validation_success=validation_success,
        framework=framework,
    )

    if not validation_success:
        print()
        print_status("Fixture validation failed - check syntax and imports", "warning")

    return {
        "generated_files": [str(f) for f in fixture_files],
        "success": True,
        "error": None,
        "framework": framework,
    }
