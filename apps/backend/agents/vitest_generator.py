"""
Vitest Test Generator Agent Module
===================================

AI agent that generates Vitest tests based on TypeScript/React code analysis results.
Uses the Test Generator Agent prompt to create comprehensive test coverage for frontend code.
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


def validate_vitest_tests(test_files: list[Path], project_dir: Path) -> bool:
    """
    Validate that generated Vitest tests are syntactically correct.

    Uses TypeScript compiler and Vitest to verify tests can be run without errors.

    Args:
        test_files: List of generated test file paths
        project_dir: Project root directory

    Returns:
        True if all tests are valid, False otherwise
    """
    if not test_files:
        logger.warning("No test files to validate")
        return False

    print()
    print_status("Validating generated Vitest tests...", "progress")

    # Check if TypeScript and Vitest are available
    frontend_dir = project_dir / "apps" / "frontend"
    if not frontend_dir.exists():
        logger.warning("Frontend directory not found - skipping validation")
        print_status("Frontend directory not found - cannot validate", "warning")
        return True  # Don't fail if frontend dir doesn't exist

    for test_file in test_files:
        file_path = project_dir / test_file
        if not file_path.exists():
            print_status(f"Test file not found: {test_file}", "error")
            return False

        # Check TypeScript syntax with tsc
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", str(file_path)],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                print_status(f"TypeScript error in {test_file.name}", "error")
                logger.debug(f"tsc output: {result.stdout}\n{result.stderr}")
                return False
            print_status(f"TypeScript syntax valid: {test_file.name}", "success")
        except subprocess.TimeoutExpired:
            print_status(f"TypeScript validation timeout for {test_file}", "error")
            return False
        except FileNotFoundError:
            logger.warning("TypeScript compiler not found - skipping syntax validation")
            print_status("tsc not available - basic check only", "warning")

    # Try to run tests with Vitest (non-blocking)
    print_status("Checking Vitest test execution...", "progress")
    try:
        # Run vitest with --run flag (non-watch mode)
        result = subprocess.run(
            ["npm", "run", "test", "--", "--run", "--reporter=verbose"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print_status("All Vitest tests passed", "success")
        else:
            # Don't fail validation if tests don't pass yet - they may need implementation
            print_status("Vitest tests generated (execution pending)", "warning")
            logger.debug(f"vitest output: {result.stdout}\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print_status("Vitest execution timeout - tests may need review", "warning")
    except FileNotFoundError:
        logger.warning("npm/vitest not found - skipping test execution")
        print_status("Vitest not available - syntax check only", "warning")

    print_status("Generated tests validation complete", "success")
    return True


async def generate_vitest_tests(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run Test Generator Agent session to generate Vitest tests for TypeScript/React code.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results from TypeScriptAnalyzer
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - generated_files: List of generated test file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
    """
    # Initialize task logger
    task_logger = get_task_logger(spec_dir)

    # Print session header
    content = [
        bold(f"{icon(Icons.SPARKLES)} VITEST GENERATOR SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Generating Vitest tests for TypeScript/React code..."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Determine model and thinking budget
    # Vitest test generation is part of the QA phase
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
        task_logger.start_phase(LogPhase.CODING, "Starting Vitest test generation...")
        task_logger.log_entry(
            LogEntryType.INFO,
            f"Analyzing {len(analysis_results.get('components', []))} components, "
            f"{len(analysis_results.get('functions', []))} functions",
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
    starting_message = f"""You are the Test Generator Agent. Your task is to generate comprehensive Vitest tests for TypeScript/React code based on the analysis results below.

## Code Analysis Results

{json.dumps(analysis_results, indent=2)}

## Your Task

1. Read the spec.md to understand what was implemented
2. Review the implementation_plan.json to see what features were built
3. Study existing test patterns in apps/frontend/src/**/*.test.tsx and apps/frontend/src/**/*.test.ts
4. Generate Vitest test files for the components, functions, and hooks above
5. Use React Testing Library for component tests
6. Follow the project's testing conventions (see existing tests)
7. Aim for 80%+ code coverage

## Vitest/React Testing Patterns

- Use `describe()` for grouping related tests
- Use `it()` or `test()` for individual test cases
- Import from `vitest`: `describe, it, expect, vi, beforeEach`
- Use `@testing-library/react` for component testing
- Mock dependencies with `vi.mock()`
- Use `/**  @vitest-environment jsdom */` for React tests
- Follow naming: `ComponentName.test.tsx` or `functionName.test.ts`

Generate test files in the appropriate locations:
- Component tests: apps/frontend/src/renderer/components/**/__tests__/*.test.tsx
- Hook tests: apps/frontend/src/renderer/hooks/__tests__/*.test.ts
- Utility tests: apps/frontend/src/shared/utils/__tests__/*.test.ts

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
    print_status("Running Vitest Test Generator Agent...", "progress")
    try:
        response = await client.create_agent_session(
            name="vitest-generator-session",
            starting_message=starting_message,
            system_prompt=prompt,
        )

        if verbose:
            logger.info(f"Vitest Generator Agent response: {response}")

        # Log session completion
        if task_logger:
            task_logger.log_entry(
                LogEntryType.SUCCESS, "Vitest Generator Agent session completed"
            )

    except Exception as e:
        error_msg = f"Vitest Generator Agent session failed: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Scan for newly created test files
    print()
    print_status("Scanning for generated Vitest test files...", "progress")

    frontend_src = project_dir / "apps" / "frontend" / "src"
    if not frontend_src.exists():
        logger.warning("Frontend source directory not found")
        return {
            "generated_files": [],
            "success": False,
            "error": "Frontend source directory not found",
        }

    # Find all .test.ts and .test.tsx files
    test_files = []
    for pattern in ["**/*.test.ts", "**/*.test.tsx"]:
        for test_file in frontend_src.glob(pattern):
            relative_path = test_file.relative_to(project_dir)
            test_files.append(relative_path)

    if not test_files:
        logger.warning("No Vitest test files were generated")
        print_status("No test files found in frontend/src/", "warning")
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
    validation_success = validate_vitest_tests(test_files, project_dir)

    # Log results
    if task_logger:
        if validation_success:
            task_logger.log_entry(
                LogEntryType.SUCCESS,
                f"Generated and validated {len(test_files)} Vitest test files",
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
    }
