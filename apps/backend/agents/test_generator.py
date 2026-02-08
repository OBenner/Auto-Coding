"""
Test Generator Agent Module
============================

AI agent that generates pytest tests based on code analysis results.
Uses the Test Generator Agent prompt to create comprehensive test coverage.
"""

import json
import logging
from pathlib import Path
from typing import Any

from analysis.coverage_analyzer import (
    CoverageAnalyzer,
    parse_coverage_json,
    CoverageResult,
    FileCoverage,
)
from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget
from prompts_pkg.prompt_loader import get_agent_prompt
from spec.coverage_config import load_coverage_config, CoverageConfig
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


def analyze_coverage_gaps(
    project_dir: Path,
    source_dir: str | None = None,
    config: CoverageConfig | None = None,
) -> tuple[CoverageResult | None, dict[str, Any]]:
    """
    Run coverage analysis and identify gaps in test coverage.

    Args:
        project_dir: Root directory of the project
        source_dir: Directory to measure coverage for (e.g., "apps/backend")
        config: Coverage configuration with thresholds (optional)

    Returns:
        Tuple of (coverage_result, gaps_summary)
        - coverage_result: CoverageResult with analysis data or None if failed
        - gaps_summary: Dictionary with gap statistics and files needing attention
    """
    analyzer = CoverageAnalyzer(project_dir)

    print_status("Running coverage analysis to identify gaps...", "progress")

    # Check if pytest-cov is available
    installed, message = analyzer.check_pytest_cov_installed()
    if not installed:
        logger.warning(f"pytest-cov not available: {message}")
        return None, {"error": message, "coverage_gaps": []}

    # Determine source directory if not specified
    if source_dir is None:
        # Default to apps/backend for backend projects
        if (project_dir / "apps" / "backend").exists():
            source_dir = "apps/backend"
        else:
            # Use current directory
            source_dir = "."

    # Run coverage with JSON output
    coverage_output = project_dir / ".coverage.test_generator.json"
    result = analyzer.run_coverage(
        source_dir=source_dir,
        output_format="json",
        output_file=coverage_output,
    )

    if not result.success:
        logger.warning(f"Coverage analysis failed: {result.error_message}")
        return None, {"error": result.error_message, "coverage_gaps": []}

    # Parse the JSON coverage report
    try:
        coverage_result = parse_coverage_json(coverage_output)
    except Exception as e:
        logger.error(f"Failed to parse coverage JSON: {e}")
        return None, {"error": str(e), "coverage_gaps": []}

    # Identify coverage gaps
    gaps_summary = {
        "total_coverage": coverage_result.total_coverage,
        "files_with_gaps": [],
        "critical_gaps": [],
        "missing_lines_by_file": {},
    }

    # Get minimum coverage threshold
    min_coverage = config.minimum_coverage if config else 80.0

    # Analyze each file for gaps
    for file_path, file_coverage in coverage_result.files.items():
        # Check if file is below threshold
        if file_coverage.coverage_percent < min_coverage:
            gap_info = {
                "file_path": file_path,
                "coverage_percent": file_coverage.coverage_percent,
                "required_coverage": min_coverage,
                "gap_percent": min_coverage - file_coverage.coverage_percent,
                "missing_lines": file_coverage.lines_missing,
                "lines_total": file_coverage.lines_total,
                "lines_covered": file_coverage.lines_covered,
            }
            gaps_summary["files_with_gaps"].append(file_path)
            gaps_summary["missing_lines_by_file"][file_path] = file_coverage.lines_missing

            # Mark as critical gap if significantly below threshold
            if file_coverage.coverage_percent < min_coverage * 0.5:
                gaps_summary["critical_gaps"].append(file_path)

    # Log results
    files_with_gaps_count = len(gaps_summary["files_with_gaps"])
    if files_with_gaps_count > 0:
        print_status(
            f"Found {files_with_gaps_count} file(s) with coverage gaps",
            "warning",
        )
        print_key_value("Total coverage", f"{coverage_result.total_coverage:.1f}%")
        print_key_value("Files with gaps", str(files_with_gaps_count))
        if gaps_summary["critical_gaps"]:
            print_key_value("Critical gaps", str(len(gaps_summary["critical_gaps"])))
    else:
        print_status(
            f"Coverage meets threshold: {coverage_result.total_coverage:.1f}%",
            "success",
        )

    return coverage_result, gaps_summary


def format_coverage_gaps_prompt(gaps_summary: dict[str, Any]) -> str:
    """
    Format coverage gaps as a prompt for the AI agent.

    Args:
        gaps_summary: Summary from analyze_coverage_gaps

    Returns:
        Formatted string describing coverage gaps
    """
    if "error" in gaps_summary:
        return f"Coverage analysis failed: {gaps_summary['error']}"

    if not gaps_summary.get("files_with_gaps"):
        return "Coverage meets all thresholds. No gaps detected."

    lines = []
    lines.append("## Coverage Gaps Detected")
    lines.append("")
    lines.append(f"**Total Coverage:** {gaps_summary['total_coverage']:.1f}%")
    lines.append(f"**Files with Gaps:** {len(gaps_summary['files_with_gaps'])}")
    lines.append("")

    if gaps_summary.get("critical_gaps"):
        lines.append("### Critical Gaps (Significantly Below Threshold)")
        for file_path in gaps_summary["critical_gaps"][:5]:
            lines.append(f"- {file_path}")
        lines.append("")

    lines.append("### Files Requiring Additional Tests")
    for file_path in gaps_summary["files_with_gaps"][:10]:
        missing_lines = gaps_summary["missing_lines_by_file"].get(file_path, [])
        if missing_lines:
            line_ranges = _format_line_ranges(missing_lines[:20])
            lines.append(f"- **{file_path}**")
            lines.append(f"  - Missing lines: {line_ranges}")
        else:
            lines.append(f"- **{file_path}**")

    if len(gaps_summary["files_with_gaps"]) > 10:
        lines.append(f"- ... and {len(gaps_summary['files_with_gaps']) - 10} more files")

    lines.append("")
    lines.append("**Action Required:** Generate additional tests to cover the missing lines above.")
    lines.append("Focus on the specific line numbers that are not covered.")

    return "\n".join(lines)


def _format_line_ranges(line_numbers: list[int]) -> str:
    """
    Format a list of line numbers into compact ranges.

    Args:
        line_numbers: List of line numbers

    Returns:
        Formatted string like "1-5, 10, 15-20"
    """
    if not line_numbers:
        return ""

    sorted_lines = sorted(set(line_numbers))
    ranges = []
    start = sorted_lines[0]
    end = sorted_lines[0]

    for line in sorted_lines[1:]:
        if line == end + 1:
            end = line
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = line
            end = line

    # Add final range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)


def validate_generated_tests(test_files: list[Path], project_dir: Path) -> bool:
    """
    Validate that generated tests are syntactically correct.

    Uses pytest --collect-only to verify tests can be collected without errors.

    Args:
        test_files: List of generated test file paths
        project_dir: Project root directory

    Returns:
        True if all tests are valid, False otherwise
    """
    import subprocess

    if not test_files:
        logger.warning("No test files to validate")
        return False

    print()
    print_status("Validating generated tests...", "progress")

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
    Run Test Generator Agent session to generate pytest tests.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results from CodeAnalyzer
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
        bold(f"{icon(Icons.SPARKLES)} TEST GENERATOR SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Generating pytest tests for analyzed code..."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Determine model and thinking budget
    if model is None:
        model = get_phase_model("test_generation")
    if max_thinking_tokens is None:
        max_thinking_tokens = get_phase_thinking_budget("test_generation")

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

    # Load coverage configuration
    coverage_config: CoverageConfig | None = None
    try:
        coverage_config = load_coverage_config(project_dir, spec_dir)
        print_key_value("Min coverage", f"{coverage_config.minimum_coverage:.0f}%")
    except Exception as e:
        logger.warning(f"Failed to load coverage config: {e}")

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
7. Aim for {coverage_config.minimum_coverage if coverage_config else 80.0:.0f}%+ code coverage

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
    validation_success = validate_generated_tests(test_files, project_dir)

    if not validation_success:
        if task_logger:
            task_logger.log_entry(
                LogEntryType.WARNING,
                f"Generated {len(test_files)} test files but validation failed",
            )
        return {
            "generated_files": [str(f) for f in test_files],
            "success": False,
            "error": "Test validation failed",
            "coverage_analyzed": False,
        }

    print()

    # Run coverage analysis to identify gaps
    print()
    print_status("Analyzing coverage gaps...", "progress")
    coverage_result, gaps_summary = analyze_coverage_gaps(
        project_dir=project_dir,
        config=coverage_config,
    )

    # Check if there are significant coverage gaps
    needs_improvement = False
    if coverage_result and coverage_result.success:
        gap_count = len(gaps_summary.get("files_with_gaps", []))
        # If coverage is below threshold or there are critical gaps, improve tests
        min_threshold = coverage_config.minimum_coverage if coverage_config else 80.0
        if (
            coverage_result.total_coverage < min_threshold
            or len(gaps_summary.get("critical_gaps", [])) > 0
        ):
            needs_improvement = True

            print()
            print_status("Coverage gaps detected - running improvement iteration...", "warning")
            print()

            # Format coverage gaps for AI agent
            gaps_prompt = format_coverage_gaps_prompt(gaps_summary)

            # Create improvement message
            improvement_message = f"""{gaps_prompt}

## Your Task

Review the coverage gaps above and generate additional test cases to cover the missing lines.

**Important:**
- Focus on the specific line numbers that are NOT covered
- Add tests that exercise the missing code paths
- Pay special attention to critical gaps (files significantly below threshold)
- Do NOT modify existing tests - only add new test cases
- Use the same test files you created earlier (append new test functions)

Generate additional test cases to improve coverage to at least {min_threshold:.0f}%.
"""

            # Run improvement iteration
            try:
                print_status("Running Test Generator Agent improvement iteration...", "progress")
                response = await client.create_agent_session(
                    name="test-generator-improvement",
                    starting_message=improvement_message,
                    system_prompt=prompt,
                )

                if verbose:
                    logger.info(f"Test Generator improvement response: {response}")

                # Log improvement session
                if task_logger:
                    task_logger.log_entry(
                        LogEntryType.INFO,
                        f"Test improvement iteration completed",
                    )

                # Re-scan for new/updated test files
                print()
                print_status("Re-scanning for updated test files...", "progress")
                updated_test_files = []
                for test_file in tests_dir.glob("test_*.py"):
                    relative_path = test_file.relative_to(project_dir)
                    if relative_path not in [str(f) for f in test_files]:
                        updated_test_files.append(relative_path)

                if updated_test_files:
                    print_key_value("New/updated files", str(len(updated_test_files)))
                    for test_file in updated_test_files:
                        print(f"  {muted('•')} {test_file}")
                    print()

                # Re-validate after improvement
                if updated_test_files:
                    print_status("Re-validating tests after improvement...", "progress")
                    validation_success = validate_generated_tests(
                        updated_test_files, project_dir
                    )

                    # Re-run coverage analysis
                    print()
                    print_status("Re-analyzing coverage after improvement...", "progress")
                    coverage_result, gaps_summary = analyze_coverage_gaps(
                        project_dir=project_dir,
                        config=coverage_config,
                    )

                    if coverage_result and coverage_result.success:
                        print_key_value(
                            "Updated coverage", f"{coverage_result.total_coverage:.1f}%"
                        )

            except Exception as e:
                error_msg = f"Test improvement iteration failed: {e}"
                logger.error(error_msg)
                if task_logger:
                    task_logger.log_entry(LogEntryType.ERROR, error_msg)
                # Don't fail completely - return original tests
                print_status(f"Improvement iteration failed: {e}", "warning")

    # Log results
    if task_logger:
        if coverage_result and coverage_result.success:
            task_logger.log_entry(
                LogEntryType.SUCCESS,
                f"Generated {len(test_files)} test files, "
                f"coverage: {coverage_result.total_coverage:.1f}%, "
                f"gaps improved: {needs_improvement}",
            )
        else:
            task_logger.log_entry(
                LogEntryType.SUCCESS,
                f"Generated and validated {len(test_files)} test files",
            )

    return {
        "generated_files": [str(f) for f in test_files],
        "success": validation_success,
        "error": None if validation_success else "Test validation failed",
        "coverage_analyzed": coverage_result is not None and coverage_result.success,
        "coverage_percent": coverage_result.total_coverage if coverage_result else None,
        "coverage_gaps": len(gaps_summary.get("files_with_gaps", [])) if gaps_summary else 0,
    }
