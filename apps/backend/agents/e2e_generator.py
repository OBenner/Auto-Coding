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
import subprocess
from pathlib import Path
from typing import Any

from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget
from prompts_pkg.prompt_loader import get_agent_prompt
from task_logger import LogEntryType, LogPhase, get_task_logger
from ui import (
    Icons,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_key_value,
    print_status,
)

logger = logging.getLogger(__name__)


def validate_e2e_tests(test_files: list[Path], project_dir: Path) -> bool:
    """
    Validate that generated E2E tests are syntactically correct.

    Uses pytest --collect-only to verify tests can be collected without errors.

    Args:
        test_files: List of generated test file paths
        project_dir: Project root directory

    Returns:
        True if all tests are valid, False otherwise
    """
    if not test_files:
        logger.warning("No E2E test files to validate")
        return False

    print()
    print_status("Validating generated E2E tests...", "progress")

    for test_file in test_files:
        file_path = project_dir / test_file
        if not file_path.exists():
            print_status(f"Test file not found: {test_file}", "error")
            return False

        # Check Python syntax
        try:
            with open(file_path, encoding="utf-8") as f:
                compile(f.read(), str(file_path), "exec")
            print_status(f"Syntax valid: {test_file.name}", "success")
        except SyntaxError as e:
            print_status(f"Syntax error in {test_file}: {e}", "error")
            return False

        # Check if pytest can collect tests
        try:
            result = subprocess.run(
                ["pytest", str(file_path), "--collect-only", "-q"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
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

    print_status("All generated E2E tests are valid", "success")
    return True


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
    # Initialize task logger
    task_logger = get_task_logger(spec_dir)

    # Print session header
    content = [
        bold(f"{icon(Icons.SPARKLES)} E2E TEST GENERATOR SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Generating E2E tests with Electron MCP integration..."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Determine model and thinking budget
    # E2E test generation is part of the QA phase
    if model is None:
        model = get_phase_model(spec_dir, "qa")
    if max_thinking_tokens is None:
        max_thinking_tokens = get_phase_thinking_budget(spec_dir, "qa")

    print_key_value("Model", model)
    print_key_value(
        "Thinking budget",
        str(max_thinking_tokens) if max_thinking_tokens else "Default",
    )
    print()

    # Log session start
    if task_logger:
        task_logger.start_phase(LogPhase.CODING, "Starting E2E test generation...")
        components_count = len(analysis_results.get("components", []))
        features_count = len(analysis_results.get("features", []))
        task_logger.log_entry(
            LogEntryType.INFO,
            f"Analyzing {components_count} components, "
            f"{features_count} features for E2E tests",
        )

    # Load the e2e_generator prompt
    try:
        prompt = get_agent_prompt("e2e_generator")
    except Exception as e:
        error_msg = f"Failed to load e2e_generator prompt: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {
            "generated_files": [],
            "success": False,
            "error": error_msg,
            "framework": "e2e-electron-mcp",
        }

    # Create the starting message with analysis results
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
- Follow the pattern: Connect → Navigate → Interact → Verify
- Test complete user workflows (not individual functions)
- Validate UI state, navigation, and data flow
- Handle both success and error scenarios

Generate test files in the tests/e2e/ directory following the naming convention test_e2e_*.py.

Begin by loading context (Phase 0 in your prompt).
"""

    # Create SDK client with e2e_generator agent type
    try:
        client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            agent_type="e2e_generator",
            max_thinking_tokens=max_thinking_tokens,
        )
    except Exception as e:
        error_msg = f"Failed to create Claude SDK client: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {
            "generated_files": [],
            "success": False,
            "error": error_msg,
            "framework": "e2e-electron-mcp",
        }

    # Run the agent session
    print_status("Running E2E Test Generator Agent...", "progress")
    try:
        response = await client.create_agent_session(
            name="e2e-generator-session",
            starting_message=starting_message,
            system_prompt=prompt,
        )

        if verbose:
            logger.info(f"E2E Generator Agent response: {response}")

        # Log session completion
        if task_logger:
            task_logger.log_entry(
                LogEntryType.SUCCESS, "E2E Generator Agent session completed"
            )

    except Exception as e:
        error_msg = f"E2E Generator Agent session failed: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {
            "generated_files": [],
            "success": False,
            "error": error_msg,
            "framework": "e2e-electron-mcp",
        }

    # Scan tests/e2e/ directory for newly created test files
    print()
    print_status("Scanning for generated E2E test files...", "progress")

    tests_e2e_dir = project_dir / "tests" / "e2e"
    if not tests_e2e_dir.exists():
        logger.warning("tests/e2e/ directory not found")
        # Try to find E2E tests in the main tests/ directory
        tests_dir = project_dir / "tests"
        if tests_dir.exists():
            test_files = []
            for test_file in tests_dir.glob("test_e2e_*.py"):
                relative_path = test_file.relative_to(project_dir)
                test_files.append(relative_path)
            if test_files:
                print_status(
                    f"Found {len(test_files)} E2E tests in tests/", "success"
                )
        else:
            return {
                "generated_files": [],
                "success": False,
                "error": "tests/ directory not found",
                "framework": "e2e-electron-mcp",
            }
    else:
        # Find all test_e2e_*.py files in tests/e2e/
        test_files = []
        for test_file in tests_e2e_dir.glob("test_e2e_*.py"):
            relative_path = test_file.relative_to(project_dir)
            test_files.append(relative_path)

    if not test_files:
        logger.warning("No E2E test files were generated")
        print_status("No E2E test files found", "warning")
        return {
            "generated_files": [],
            "success": False,
            "error": "No test files generated",
            "framework": "e2e-electron-mcp",
        }

    print_key_value("Generated files", str(len(test_files)))
    for test_file in test_files:
        print(f"  {muted('•')} {test_file}")
    print()

    # Validate generated tests
    validation_success = validate_e2e_tests(test_files, project_dir)

    # Log results
    if task_logger:
        if validation_success:
            task_logger.log_entry(
                LogEntryType.SUCCESS,
                f"Generated and validated {len(test_files)} E2E test files",
            )
        else:
            task_logger.log_entry(
                LogEntryType.WARNING,
                f"Generated {len(test_files)} test files but validation failed",
            )

    return {
        "generated_files": [str(f) for f in test_files],
        "success": validation_success,
        "error": None if validation_success else "Test validation failed",
        "framework": "e2e-electron-mcp",
    }
