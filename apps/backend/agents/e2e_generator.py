"""
E2E Test Generator Agent Module
=================================

AI agent that generates E2E tests based on user-facing feature analysis.
Uses Electron MCP tools to create interactive UI tests that validate user workflows.

Generated tests use the Electron MCP server to interact with the running application
via Chrome DevTools Protocol, enabling automated testing of user interactions.
"""

import json
import logging
from pathlib import Path
from typing import Any

from task_logger import LogPhase
from ui import (
    muted,
    print_key_value,
    print_status,
)

from ._generator_base import log_generator_result, run_generator_session
from ._validation import validate_python_tests

logger = logging.getLogger(__name__)


async def validate_e2e_tests(test_files: list[Path], project_dir: Path) -> bool:
    """
    Validate that generated E2E tests are syntactically correct.

    Uses Python syntax check and pytest --collect-only to verify tests.
    Runs subprocess calls in a thread to avoid blocking the event loop.

    Args:
        test_files: List of generated test file paths
        project_dir: Project root directory

    Returns:
        True if all tests are valid, False otherwise
    """
    return await validate_python_tests(test_files, project_dir, label="E2E")


async def generate_e2e_tests(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run E2E Test Generator Agent session to generate E2E tests for user-facing features.

    Uses Electron MCP tools to generate interactive UI tests that validate user workflows
    through the running Electron application.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results (can include components, features, etc.)
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - generated_files: List of generated test file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
        - framework: Test framework used ("e2e-electron-mcp")
    """
    starting_message = f"""You are the E2E Test Generator Agent. Your task is to generate comprehensive E2E tests for user-facing features using Electron MCP integration.

## Code Analysis Results

{json.dumps(analysis_results, indent=2)}

## Your Task

1. Read the spec.md to understand what user-facing features were implemented
2. Review the implementation_plan.json to see what UI flows were built
3. Study existing E2E test patterns in tests/e2e/test_*.py (if they exist)
4. Identify user workflows that need E2E validation
5. Generate E2E test files using Electron MCP tools for UI interaction
6. Follow the project's testing conventions
7. Focus on critical user journeys and acceptance criteria

## E2E Test Pattern (Electron MCP)

Your tests should:
- Use pytest as the test framework
- Import Electron MCP tools from the agent SDK
- Follow the pattern: Connect -> Navigate -> Interact -> Verify
- Test complete user workflows (not individual functions)
- Validate UI state, navigation, and data flow
- Handle both success and error scenarios

Generate test files in the tests/e2e/ directory following the naming convention test_e2e_*.py.

Begin by loading context (Phase 0 in your prompt).
"""

    # Run the shared generator session boilerplate
    components_count = len(analysis_results.get("components", []))
    features_count = len(analysis_results.get("features", []))
    session_result = await run_generator_session(
        project_dir=project_dir,
        spec_dir=spec_dir,
        analysis_results=analysis_results,
        session_title="E2E TEST GENERATOR SESSION",
        session_description="Generating E2E tests with Electron MCP integration...",
        prompt_name="e2e_generator",
        agent_type="e2e_generator",
        session_name="e2e-generator-session",
        starting_message=starting_message,
        log_phase=LogPhase.VALIDATION,
        log_summary=(
            f"Analyzing {components_count} components, "
            f"{features_count} features for E2E tests"
        ),
        model=model,
        max_thinking_tokens=max_thinking_tokens,
        verbose=verbose,
    )

    framework = "e2e-electron-mcp"

    if not session_result["success"]:
        return {
            "generated_files": [],
            "success": False,
            "error": session_result["error"],
            "framework": framework,
        }

    # Scan tests/e2e/ directory for newly created test files
    print()
    print_status("Scanning for generated E2E test files...", "progress")

    test_files: list[Path] = []
    tests_e2e_dir = project_dir / "tests" / "e2e"
    if tests_e2e_dir.exists():
        for test_file in tests_e2e_dir.glob("test_e2e_*.py"):
            test_files.append(test_file.relative_to(project_dir))
    else:
        # Try to find E2E tests in the main tests/ directory
        tests_dir = project_dir / "tests"
        if tests_dir.exists():
            for test_file in tests_dir.glob("test_e2e_*.py"):
                test_files.append(test_file.relative_to(project_dir))
            if test_files:
                print_status(f"Found {len(test_files)} E2E tests in tests/", "success")
        else:
            return {
                "generated_files": [],
                "success": False,
                "error": "tests/ directory not found",
                "framework": framework,
            }

    if not test_files:
        logger.warning("No E2E test files were generated")
        print_status("No E2E test files found", "warning")
        return {
            "generated_files": [],
            "success": False,
            "error": "No test files generated",
            "framework": framework,
        }

    print_key_value("Generated files", str(len(test_files)))
    for test_file in test_files:
        print(f"  {muted('•')} {test_file}")
    print()

    # Validate generated tests
    validation_success = await validate_e2e_tests(test_files, project_dir)

    # Log results
    log_generator_result(
        spec_dir=spec_dir,
        test_files=test_files,
        validation_success=validation_success,
        framework="E2E",
    )

    return {
        "generated_files": [str(f) for f in test_files],
        "success": validation_success,
        "error": None if validation_success else "Test validation failed",
        "framework": framework,
    }
