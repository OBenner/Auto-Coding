"""
Test Generator Agent Module
============================

AI agent that generates tests based on code analysis results.
Supports multiple test frameworks:
- pytest for Python code
- Vitest for TypeScript/React code

Uses the Test Generator Agent prompt to create comprehensive test coverage.
"""

import json
import logging
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

# Import framework-specific generators
from .vitest_generator import generate_vitest_tests, validate_vitest_tests

logger = logging.getLogger(__name__)


def detect_test_framework(analysis_results: dict[str, Any]) -> str:
    """
    Detect which test framework to use based on analysis results.

    Args:
        analysis_results: Code analysis results from CodeAnalyzer or TypeScriptAnalyzer

    Returns:
        "pytest" for Python code, "vitest" for TypeScript/React code
    """
    # Check for TypeScript/React indicators
    has_components = "components" in analysis_results and analysis_results.get(
        "components"
    )
    has_hooks = "hooks" in analysis_results and analysis_results.get("hooks")
    has_tsx_files = any(
        str(f).endswith((".tsx", ".ts"))
        for f in analysis_results.get("analyzed_files", [])
    )

    # Check for Python indicators
    has_classes = "classes" in analysis_results and analysis_results.get("classes")
    has_py_files = any(
        str(f).endswith(".py") for f in analysis_results.get("analyzed_files", [])
    )

    # Decision logic
    if has_components or has_hooks or has_tsx_files:
        return "vitest"
    elif has_classes or has_py_files:
        return "pytest"
    else:
        # Default to pytest if unclear
        logger.warning(
            "Could not determine test framework from analysis results, defaulting to pytest"
        )
        return "pytest"


def validate_generated_tests(
    test_files: list[Path], project_dir: Path, framework: str = "pytest"
) -> bool:
    """
    Validate that generated tests are syntactically correct.

    Routes to framework-specific validation:
    - pytest: Uses pytest --collect-only to verify tests can be collected
    - vitest: Uses TypeScript compiler and Vitest to verify tests

    Args:
        test_files: List of generated test file paths
        project_dir: Project root directory
        framework: Test framework ("pytest" or "vitest")

    Returns:
        True if all tests are valid, False otherwise
    """
    if not test_files:
        logger.warning("No test files to validate")
        return False

    # Route to framework-specific validation
    if framework == "vitest":
        logger.info("Using Vitest validation for TypeScript/React tests")
        return validate_vitest_tests(test_files, project_dir)

    # Default to pytest validation
    logger.info("Using pytest validation for Python tests")

    import subprocess

    print()
    print_status("Validating generated pytest tests...", "progress")

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

    print_status("All generated tests are valid", "success")
    return True


async def run_test_generator_session(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run Test Generator Agent session to generate tests for analyzed code.

    Automatically detects the appropriate test framework (pytest or vitest)
    based on the code analysis results and routes to the corresponding generator.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results from CodeAnalyzer or TypeScriptAnalyzer
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - generated_files: List of generated test file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
        - framework: Test framework used ("pytest" or "vitest")
    """
    # Detect which test framework to use
    framework = detect_test_framework(analysis_results)
    logger.info(f"Detected test framework: {framework}")

    # Route to the appropriate generator
    if framework == "vitest":
        logger.info("Routing to Vitest generator for TypeScript/React tests")
        result = await generate_vitest_tests(
            project_dir=project_dir,
            spec_dir=spec_dir,
            analysis_results=analysis_results,
            model=model,
            max_thinking_tokens=max_thinking_tokens,
            verbose=verbose,
        )
        result["framework"] = "vitest"
        return result

    # Default to pytest for Python tests
    logger.info("Routing to pytest generator for Python tests")

    # Initialize task logger
    task_logger = get_task_logger(spec_dir)

    # Print session header
    content = [
        bold(f"{icon(Icons.SPARKLES)} TEST GENERATOR SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Generating pytest tests for analyzed code..."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Determine model and thinking budget
    # Test generation is part of the QA phase
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
        task_logger.start_phase(LogPhase.CODING, "Starting test generation...")
        task_logger.log_entry(
            LogEntryType.INFO,
            f"Analyzing {len(analysis_results.get('functions', []))} functions, "
            f"{len(analysis_results.get('classes', []))} classes",
        )

    # Load the test generator prompt
    try:
        prompt = get_agent_prompt("test_generator")
    except Exception as e:
        error_msg = f"Failed to load test_generator prompt: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Create the starting message with analysis results
    starting_message = f"""You are the Test Generator Agent. Your task is to generate comprehensive pytest tests based on the code analysis results below.

## Code Analysis Results

{json.dumps(analysis_results, indent=2)}

## Your Task

1. Read the spec.md to understand what was implemented
2. Review the implementation_plan.json to see what features were built
3. Study existing test patterns in tests/conftest.py and tests/test_*.py
4. Generate pytest test files for the functions and classes above
5. Ensure tests cover edge cases detected in the analysis
6. Follow the project's testing conventions
7. Aim for 80%+ code coverage

Generate test files in the tests/ directory following the naming convention test_*.py.

Begin by loading context (Phase 0 in your prompt).
"""

    # Create SDK client with test_generator agent type
    try:
        client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            agent_type="test_generator",
            max_thinking_tokens=max_thinking_tokens,
        )
    except Exception as e:
        error_msg = f"Failed to create Claude SDK client: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Run the agent session
    print_status("Running Test Generator Agent...", "progress")
    try:
        response = await client.create_agent_session(
            name="test-generator-session",
            starting_message=starting_message,
            system_prompt=prompt,
        )

        if verbose:
            logger.info(f"Test Generator Agent response: {response}")

        # Log session completion
        if task_logger:
            task_logger.log_entry(
                LogEntryType.SUCCESS, "Test Generator Agent session completed"
            )

    except Exception as e:
        error_msg = f"Test Generator Agent session failed: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Scan tests/ directory for newly created test files
    print()
    print_status("Scanning for generated test files...", "progress")

    tests_dir = project_dir / "tests"
    if not tests_dir.exists():
        logger.warning("tests/ directory not found")
        return {
            "generated_files": [],
            "success": False,
            "error": "tests/ directory not found",
        }

    # Find all test_*.py files (exclude conftest.py)
    test_files = []
    for test_file in tests_dir.glob("test_*.py"):
        relative_path = test_file.relative_to(project_dir)
        test_files.append(relative_path)

    if not test_files:
        logger.warning("No test files were generated")
        print_status("No test files found in tests/", "warning")
        return {
            "generated_files": [],
            "success": False,
            "error": "No test files generated",
        }

    print_key_value("Generated files", str(len(test_files)))
    for test_file in test_files:
        print(f"  {muted('•')} {test_file}")
    print()

    # Validate generated tests
    validation_success = validate_generated_tests(test_files, project_dir, "pytest")

    # Log results
    if task_logger:
        if validation_success:
            task_logger.log_entry(
                LogEntryType.SUCCESS,
                f"Generated and validated {len(test_files)} test files",
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
        "framework": "pytest",
    }
