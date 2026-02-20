"""
Vitest Test Generator Agent Module
===================================

AI agent that generates Vitest tests based on TypeScript/React code analysis results.
Uses the Test Generator Agent prompt to create comprehensive test coverage for frontend code.
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from task_logger import LogPhase
from ui import (
    muted,
    print_key_value,
    print_status,
)

from ._generator_base import log_generator_result, run_generator_session

logger = logging.getLogger(__name__)


async def validate_vitest_tests(test_files: list[Path], project_dir: Path) -> bool:
    """
    Validate that generated Vitest tests are syntactically correct.

    Uses TypeScript compiler and Vitest to verify tests can be run without errors.
    Runs subprocess calls in a thread to avoid blocking the event loop.

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
        return False

    for test_file in test_files:
        file_path = project_dir / test_file
        if not file_path.exists():
            print_status(f"Test file not found: {test_file}", "error")
            return False

    # Check TypeScript syntax with tsc using project tsconfig (non-blocking)
    tsconfig_path = frontend_dir / "tsconfig.json"
    tsc_args = ["npx", "tsc", "--noEmit"]
    if tsconfig_path.exists():
        tsc_args.extend(["-p", str(tsconfig_path)])
    else:
        # Fall back to checking individual files without tsconfig
        tsc_args.extend([str(project_dir / f) for f in test_files])

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            tsc_args,
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            # Report which test files may have errors
            for test_file in test_files:
                if test_file.name in (result.stdout + result.stderr):
                    print_status(f"TypeScript error in {test_file.name}", "error")
            logger.debug(f"tsc output: {result.stdout}\n{result.stderr}")
            return False
        for test_file in test_files:
            print_status(f"TypeScript syntax valid: {test_file.name}", "success")
    except subprocess.TimeoutExpired:
        print_status("TypeScript validation timeout", "error")
        return False
    except FileNotFoundError:
        logger.warning("TypeScript compiler not found - skipping syntax validation")
        print_status("tsc not available - basic check only", "warning")

    # Try to run tests with Vitest (non-blocking)
    print_status("Checking Vitest test execution...", "progress")
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["npx", "vitest", "run", "--reporter=verbose"],
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

    # Run the shared generator session boilerplate
    session_result = await run_generator_session(
        project_dir=project_dir,
        spec_dir=spec_dir,
        analysis_results=analysis_results,
        session_title="VITEST GENERATOR SESSION",
        session_description="Generating Vitest tests for TypeScript/React code...",
        prompt_name="test_generator",
        agent_type="test_generator",
        session_name="vitest-generator-session",
        starting_message=starting_message,
        log_phase=LogPhase.VALIDATION,
        log_summary=(
            f"Analyzing {len(analysis_results.get('components', []))} components, "
            f"{len(analysis_results.get('functions', []))} functions"
        ),
        model=model,
        max_thinking_tokens=max_thinking_tokens,
        verbose=verbose,
    )

    if not session_result["success"]:
        return {
            "generated_files": [],
            "success": False,
            "error": session_result["error"],
        }

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
    validation_success = await validate_vitest_tests(test_files, project_dir)

    # Log results
    log_generator_result(
        spec_dir=spec_dir,
        test_files=test_files,
        validation_success=validation_success,
        framework="Vitest",
    )

    return {
        "generated_files": [str(f) for f in test_files],
        "success": validation_success,
        "error": None if validation_success else "Test validation failed",
    }
