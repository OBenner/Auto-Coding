"""
Refactoring Generator Agent Module
====================================

AI agent that generates code refactoring suggestions and applies automated refactoring
based on code analysis results. Uses the Refactoring Generator Agent prompt to detect
code smells, anti-patterns, and opportunities for improvement.
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

logger = logging.getLogger(__name__)


def validate_generated_refactorings(
    refactoring_files: list[Path], project_dir: Path
) -> bool:
    """
    Validate that generated refactoring files exist and are well-formed.

    Checks that:
    - Files exist and are readable
    - Python files are syntactically valid
    - No empty refactoring files were produced

    Args:
        refactoring_files: List of generated/modified file paths
        project_dir: Project root directory

    Returns:
        True if all refactoring files are valid, False otherwise
    """
    if not refactoring_files:
        logger.warning("No refactoring files to validate")
        return False

    print()
    print_status("Validating generated refactorings...", "progress")

    for refactoring_file in refactoring_files:
        file_path = project_dir / refactoring_file
        if not file_path.exists():
            print_status(f"Refactoring file not found: {refactoring_file}", "error")
            return False

        # Check file is not empty
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                print_status(
                    f"Empty refactoring file: {refactoring_file}", "error"
                )
                return False

            # Basic Python syntax validation
            if file_path.suffix == ".py":
                import ast

                try:
                    ast.parse(content)
                except SyntaxError as e:
                    print_status(
                        f"Syntax error in {refactoring_file.name}: {e}", "error"
                    )
                    return False

            print_status(f"Valid refactoring: {file_path.name}", "success")
        except Exception as e:
            print_status(f"Error reading {refactoring_file}: {e}", "error")
            return False

    print_status("All generated refactorings are valid", "success")
    return True


async def run_refactoring_generator_session(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run Refactoring Generator Agent session to suggest and apply code refactoring.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results from detectors (error_pattern_detector,
                          naming_detector, organization_detector, etc.)
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - generated_files: List of refactored/generated file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
    """
    starting_message = f"""You are the Refactoring Generator Agent. Your task is to analyze code quality issues and apply targeted refactoring based on the analysis results below.

## Code Analysis Results

{json.dumps(analysis_results, indent=2)}

## Your Task

1. Read the spec.md to understand what was implemented
2. Review the implementation_plan.json to see what features were built
3. Study existing code patterns in apps/backend/ to understand conventions
4. Apply refactoring to address the detected code smells and anti-patterns:
   - Fix naming issues (variables, functions, classes)
   - Eliminate error pattern anti-patterns
   - Improve code organization and module structure
   - Extract duplicated logic into reusable helpers
   - Simplify complex conditional logic
5. Follow the project's coding conventions
6. Ensure all refactored files are syntactically valid
7. Do not change external interfaces or break existing functionality

## Refactoring Priorities

- High: Syntax errors, undefined variables, incorrect exception handling
- Medium: Naming violations, duplicated code blocks, overly long functions
- Low: Style improvements, minor reorganization

Apply refactoring directly to the source files. Focus on correctness and maintainability.

Begin by loading context (Phase 0 in your prompt).
"""

    # Run the shared generator session boilerplate
    session_result = await run_generator_session(
        project_dir=project_dir,
        spec_dir=spec_dir,
        analysis_results=analysis_results,
        session_title="REFACTORING GENERATOR SESSION",
        session_description="Analyzing code and applying automated refactoring...",
        prompt_name="refactoring_generator",
        agent_type="refactoring_generator",
        session_name="refactoring-generator-session",
        starting_message=starting_message,
        log_phase=LogPhase.CODING,
        log_summary=(
            f"Analyzing {len(analysis_results.get('issues', []))} issues across "
            f"{len(analysis_results.get('files', []))} files"
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

    # Scan for refactored Python files
    print()
    print_status("Scanning for refactored files...", "progress")

    backend_src = project_dir / "apps" / "backend"
    if not backend_src.exists():
        logger.warning("Backend source directory not found")
        return {
            "generated_files": [],
            "success": False,
            "error": "Backend source directory not found",
        }

    # Collect files listed in analysis_results as having been processed
    refactoring_files: list[Path] = []
    for file_entry in analysis_results.get("files", []):
        file_path = project_dir / file_entry
        if file_path.exists() and file_path.suffix == ".py":
            refactoring_files.append(Path(file_entry))

    if not refactoring_files:
        logger.warning("No refactored files identified from analysis results")
        print_status("No refactored files found from analysis results", "warning")
        return {
            "generated_files": [],
            "success": False,
            "error": "No refactored files identified",
        }

    print_key_value("Refactored files", str(len(refactoring_files)))
    for refactoring_file in refactoring_files:
        print(f"  {muted('•')} {refactoring_file}")
    print()

    # Validate refactored files
    validation_success = validate_generated_refactorings(
        refactoring_files, project_dir
    )

    # Log results
    log_generator_result(
        spec_dir=spec_dir,
        test_files=refactoring_files,
        validation_success=validation_success,
        framework="Refactoring",
    )

    return {
        "generated_files": [str(f) for f in refactoring_files],
        "success": validation_success,
        "error": None if validation_success else "Refactoring validation failed",
    }
