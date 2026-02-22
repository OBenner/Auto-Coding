"""
QA Validation Loop Orchestration
=================================

Main QA loop that coordinates reviewer and fixer sessions until
approval or max iterations.
"""

import asyncio
import os
import time as time_module
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agents.e2e_generator import generate_e2e_tests
from agents.memory_manager import save_user_correction
from agents.test_generator import run_test_generator_session
from analysis.code_analyzer import CodeAnalyzer
from analysis.coverage_reporter import collect_coverage, format_coverage_summary
from analysis.failure_analyzer import analyze_failure, is_analysis_enabled
from analysis.ts_analyzer import TypeScriptAnalyzer
from core.client import create_client
from debug import debug, debug_error, debug_section, debug_success, debug_warning
from integrations.graphiti.memory import get_graphiti_memory, is_graphiti_enabled
from linear_updater import (
    LinearTaskState,
    is_linear_enabled,
    linear_qa_approved,
    linear_qa_max_iterations,
    linear_qa_rejected,
    linear_qa_started,
)
from phase_config import get_phase_model, get_phase_thinking_budget
from phase_event import ExecutionPhase, emit_phase
from progress import count_subtasks, is_build_complete
from security.constants import PROJECT_DIR_ENV_VAR
from services.recovery import RecoveryManager
from task_logger import (
    LogPhase,
    get_task_logger,
)

from .criteria import (
    get_qa_iteration_count,
    get_qa_signoff_status,
    is_qa_approved,
)
from .fixer import run_qa_fixer_session
from .report import (
    create_manual_test_plan,
    escalate_to_human,
    get_iteration_history,
    get_recurring_issue_summary,
    has_recurring_issues,
    is_no_test_project,
    record_iteration,
)
from .reviewer import run_qa_agent_session

# Configuration
MAX_QA_ITERATIONS = 50
MAX_CONSECUTIVE_ERRORS = 3  # Stop after 3 consecutive errors without progress

# Auto-generated marker for QA_FIX_REQUEST.md
QA_FIX_REQUEST_MARKER = "<!-- AUTO_GENERATED_BY_QA_AGENT -->"


# =============================================================================
# USER CORRECTION DETECTION
# =============================================================================


def check_user_correction(spec_dir: Path) -> tuple[bool, dict[str, Any] | None]:
    """
    Check if QA_FIX_REQUEST.md was manually edited by the user.

    The QA agent should include a marker comment in auto-generated files.
    If the marker is missing, we assume the user manually edited the file.

    Args:
        spec_dir: Spec directory

    Returns:
        (is_user_correction, correction_details) tuple where:
        - is_user_correction: True if file was manually edited
        - correction_details: Dict with timestamp, file content, etc. (or None)
    """
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"

    if not fix_request_file.exists():
        return False, None

    try:
        content = fix_request_file.read_text(encoding="utf-8")

        # Check for auto-generated marker
        has_marker = QA_FIX_REQUEST_MARKER in content

        # If marker is missing, file was manually created/edited by user
        is_user_correction = not has_marker

        if is_user_correction:
            # Get file metadata
            stat = fix_request_file.stat()
            modification_time = datetime.fromtimestamp(stat.st_mtime, tz=UTC)

            correction_details = {
                "file_path": str(fix_request_file),
                "modified_at": modification_time.isoformat(),
                "content_preview": content[:500],  # First 500 chars for context
                "detected_at": datetime.now(UTC).isoformat(),
            }

            debug(
                "qa_loop",
                "User correction detected in QA_FIX_REQUEST.md",
                modified_at=correction_details["modified_at"],
            )

            return True, correction_details

        debug(
            "qa_loop",
            "QA_FIX_REQUEST.md has auto-generated marker - agent-created",
        )
        return False, None

    except (OSError, UnicodeDecodeError) as e:
        debug_warning("qa_loop", f"Failed to check user correction: {e}")
        return False, None


# =============================================================================
# TEST REVIEW HELPERS
# =============================================================================


def _move_tests_to_review_directory(
    project_dir: Path,
    spec_dir: Path,
    generated_files: list[str],
) -> Path:
    """
    Move generated tests to a review directory for user approval.

    Creates a review directory in the spec folder, moves generated test files
    there, and creates an instruction file for the user.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        generated_files: List of generated test file paths (relative to project_dir)

    Returns:
        Path to the review directory
    """
    import shutil

    # Create review directory
    review_dir = spec_dir / "generated_tests_review"
    review_dir.mkdir(exist_ok=True)
    debug("qa_loop", "Created test review directory", review_dir=str(review_dir))

    # Move each generated test file to review directory, preserving relative paths
    moved_files = []
    for file_path_str in generated_files:
        file_path = Path(file_path_str)

        # Reject absolute or upward-traversing paths
        if file_path.is_absolute() or ".." in file_path.parts:
            debug_error(
                "qa_loop",
                f"Skipping unsafe path: {file_path_str}",
            )
            continue

        source = project_dir / file_path
        dest = review_dir / file_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        if source.exists():
            try:
                shutil.move(str(source), str(dest))
                moved_files.append(str(file_path))
                debug("qa_loop", "Moved test to review", file=str(file_path))
            except Exception as e:
                debug_error("qa_loop", f"Failed to move {file_path.name}: {e}")
        else:
            debug_warning("qa_loop", f"Test file not found for review: {file_path}")

    # Create instruction file
    instruction_file = review_dir / "README.md"
    instructions = f"""# Generated Tests - Awaiting Review

## Overview
The QA loop has generated {len(moved_files)} test file(s) based on the implemented code.
These tests are waiting for your review and approval before being committed to the project.

## Generated Test Files
{chr(10).join(f"- {name}" for name in moved_files)}

## Review Process

1. **Review the tests** in this directory
   - Check that tests are meaningful and correct
   - Verify they follow project conventions
   - Ensure edge cases are covered appropriately

2. **Approve tests** (if they look good):
   ```bash
   # Copy approved tests to your project (preserving directory structure)
   cp -r {review_dir}/ {project_dir}/

   # Commit them with your changes
   git add tests/ apps/frontend/src/
   git commit -m "Add generated tests for [feature name]"
   ```

3. **Reject tests** (if they need work):
   - Delete or modify the test files in this review directory
   - Optionally provide feedback for regeneration
   - The tests will NOT be automatically committed

## Notes
- These tests are isolated in the review directory
- They will NOT be automatically committed to your project
- You have full control over which tests to include
- You can modify tests before copying them to your project

---
Generated: {time_module.strftime("%Y-%m-%d %H:%M:%S")}
"""

    try:
        with open(instruction_file, "w", encoding="utf-8") as f:
            f.write(instructions)
        debug("qa_loop", "Created review instructions", file=str(instruction_file))
    except Exception as e:
        debug_error("qa_loop", f"Failed to create instruction file: {e}")

    # Print user-facing message
    print("\n" + "=" * 70)
    print("  📋 GENERATED TESTS - REVIEW REQUIRED")
    print("=" * 70)
    print(
        f"\n✅ {len(moved_files)} test file(s) have been generated and saved for review."
    )
    print(f"\n📁 Review directory: {review_dir}")
    print("\nGenerated tests:")
    for name in moved_files:
        print(f"   • {name}")
    print(f"\n📖 See {instruction_file.name} for review instructions")
    print("\n⚠️  Tests are NOT automatically committed - review and approve manually.")
    print("=" * 70)

    return review_dir


# =============================================================================
# QA VALIDATION LOOP
# =============================================================================


async def run_qa_validation_loop(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    verbose: bool = False,
) -> bool:
    """
    Run the full QA validation loop.

    This is the self-validating loop:
    1. QA Agent reviews
    2. If rejected → Fixer Agent fixes
    3. QA Agent re-reviews
    4. Loop until approved or max iterations

    Enhanced with:
    - Iteration tracking with detailed history
    - Recurring issue detection (3+ occurrences → human escalation)
    - No-test project handling

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        model: Claude model to use
        verbose: Whether to show detailed output

    Returns:
        True if QA approved, False otherwise
    """
    # Set environment variable for security hooks to find the correct project directory
    # This is needed because os.getcwd() may return the wrong directory in worktree mode
    os.environ[PROJECT_DIR_ENV_VAR] = str(project_dir.resolve())

    debug_section("qa_loop", "QA Validation Loop")
    debug(
        "qa_loop",
        "Starting QA validation loop",
        project_dir=str(project_dir),
        spec_dir=str(spec_dir),
        model=model,
        max_iterations=MAX_QA_ITERATIONS,
    )

    print("\n" + "=" * 70)
    print("  QA VALIDATION LOOP")
    print("  Self-validating quality assurance")
    print("=" * 70)

    # Initialize task logger for the validation phase
    task_logger = get_task_logger(spec_dir)

    # Verify build is complete
    if not is_build_complete(spec_dir):
        debug_warning("qa_loop", "Build is not complete, cannot run QA")
        print("\n❌ Build is not complete. Cannot run QA validation.")
        completed, total = count_subtasks(spec_dir)
        debug("qa_loop", "Build progress", completed=completed, total=total)
        print(f"   Progress: {completed}/{total} subtasks completed")
        return False

    # Emit phase event at start of QA validation (before any early returns)
    emit_phase(ExecutionPhase.QA_REVIEW, "Starting QA validation")

    # Check if there's pending human feedback that needs to be processed
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"
    has_human_feedback = fix_request_file.exists()

    # Detect if the file was manually edited by the user
    is_user_correction, correction_details = check_user_correction(spec_dir)

    # Check if already approved - but if there's human feedback, we need to process it first
    if is_qa_approved(spec_dir) and not has_human_feedback:
        debug_success("qa_loop", "Build already approved by QA")
        print("\n✅ Build already approved by QA.")
        return True

    # If there's human feedback, we need to run the fixer first before re-validating
    if has_human_feedback:
        if is_user_correction:
            debug(
                "qa_loop",
                "User correction detected - manually edited QA_FIX_REQUEST.md",
                correction_details=correction_details,
            )
            emit_phase(ExecutionPhase.QA_FIXING, "Processing user corrections")
            print("\n✏️  User correction detected in QA_FIX_REQUEST.md")
            print("   Running QA Fixer to apply your changes...")
        else:
            debug(
                "qa_loop",
                "Human feedback detected - will run fixer first",
                fix_request_file=str(fix_request_file),
            )
            emit_phase(ExecutionPhase.QA_FIXING, "Processing human feedback")
            print("\n📝 Human feedback detected. Running QA Fixer first...")

        # Get model and thinking budget for fixer (uses QA phase config)
        qa_model = get_phase_model(spec_dir, "qa", model)
        fixer_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")

        fix_client = create_client(
            project_dir,
            spec_dir,
            qa_model,
            agent_type="qa_fixer",
            max_thinking_tokens=fixer_thinking_budget,
        )

        async with fix_client:
            fix_status, fix_response = await run_qa_fixer_session(
                fix_client,
                spec_dir,
                0,
                False,  # iteration 0 for human feedback
            )

        if fix_status == "error":
            debug_error("qa_loop", f"Fixer error: {fix_response[:200]}")
            print(f"\n❌ Fixer encountered error: {fix_response}")
            return False

        if is_user_correction:
            debug_success(
                "qa_loop",
                "User correction fixes applied",
                correction_details=correction_details,
            )
            print(
                "\n✅ Fixes applied based on your corrections. Running QA validation..."
            )

            # Store user correction in Graphiti for cross-session learning
            try:
                # Read the full QA_FIX_REQUEST.md content to understand the correction
                fix_content = fix_request_file.read_text(encoding="utf-8")

                # Extract meaningful information
                what_was_wrong = "QA agent generated a fix request, but user manually edited it to provide better guidance"
                what_was_corrected = fix_content[
                    :1000
                ]  # First 1000 chars of the user's corrections

                # Build context dict with available information
                correction_context = {
                    "spec_id": spec_dir.name,
                    "modified_at": correction_details.get("modified_at"),
                    "detected_at": correction_details.get("detected_at"),
                    "file_path": str(fix_request_file.relative_to(project_dir)),
                    "correction_type": "qa_fix_request_manual_edit",
                }

                # Save to Graphiti memory (async call, non-blocking)
                await save_user_correction(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    what_was_wrong=what_was_wrong,
                    what_was_corrected=what_was_corrected,
                    correction_context=correction_context,
                )
                debug(
                    "qa_loop",
                    "User correction saved to Graphiti memory",
                    spec_id=spec_dir.name,
                )
            except Exception as e:
                # Don't fail the QA loop if memory save fails
                debug_warning(
                    "qa_loop",
                    f"Failed to save user correction to memory: {e}",
                )
        else:
            debug_success("qa_loop", "Human feedback fixes applied")
            print(
                "\n✅ Fixes applied based on human feedback. Running QA validation..."
            )

        # Remove the fix request file after processing
        try:
            fix_request_file.unlink()
            debug("qa_loop", "Removed processed QA_FIX_REQUEST.md")
        except OSError:
            pass  # Ignore if file removal fails

    # Check for no-test projects
    if is_no_test_project(spec_dir, project_dir):
        print("\n⚠️  No test framework detected in project.")
        print("Creating manual test plan...")
        manual_plan = create_manual_test_plan(spec_dir, spec_dir.name)
        print(f"📝 Manual test plan created: {manual_plan}")
        print("\nNote: Automated testing will be limited for this project.")

    # Generate tests for implemented code
    print("\n🧪 Analyzing code for test generation...")
    debug("qa_loop", "Starting test generation step")

    try:
        # Analyze implementation plan to find modified files
        impl_plan_file = spec_dir / "implementation_plan.json"
        modified_files = []

        if impl_plan_file.exists():
            import json

            with open(impl_plan_file, encoding="utf-8") as f:
                impl_plan = json.load(f)

            # Collect files from completed subtasks
            for phase in impl_plan.get("phases", []):
                for subtask in phase.get("subtasks", []):
                    if subtask.get("status") == "completed":
                        modified_files.extend(subtask.get("files_to_modify", []))
                        modified_files.extend(subtask.get("files_to_create", []))

            # Remove duplicates and filter Python and TypeScript files
            all_modified_files = list(set(modified_files))
            python_files = [f for f in all_modified_files if f.endswith(".py")]
            typescript_files = [
                f
                for f in all_modified_files
                if f.endswith((".ts", ".tsx"))
                and not f.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
            ]
            modified_files = python_files + typescript_files
            debug(
                "qa_loop",
                f"Found {len(python_files)} Python and {len(typescript_files)} TypeScript files to analyze",
                files=modified_files[:5],
            )

        if modified_files:
            # Analyze code in modified files
            py_analyzer = CodeAnalyzer()
            ts_analyzer = TypeScriptAnalyzer()
            combined_analysis = {
                "functions": [],
                "classes": [],
                "components": [],
                "imports": [],
                "edge_cases": [],
            }

            for file_path in modified_files:
                full_path = project_dir / file_path

                # Analyze Python files
                if full_path.exists() and full_path.suffix == ".py":
                    try:
                        analysis = py_analyzer.analyze_file(full_path)
                        combined_analysis["functions"].extend(
                            analysis.get("functions", [])
                        )
                        combined_analysis["classes"].extend(analysis.get("classes", []))
                        combined_analysis["imports"].extend(analysis.get("imports", []))
                        combined_analysis["edge_cases"].extend(
                            analysis.get("edge_cases", [])
                        )
                        debug(
                            "qa_loop",
                            f"Analyzed Python file {file_path}",
                            functions=len(analysis.get("functions", [])),
                            classes=len(analysis.get("classes", [])),
                        )
                    except Exception as e:
                        debug_warning("qa_loop", f"Failed to analyze {file_path}: {e}")

                # Analyze TypeScript files
                elif full_path.exists() and full_path.suffix in (".ts", ".tsx"):
                    try:
                        analysis = ts_analyzer.analyze_file(full_path)
                        combined_analysis["components"].extend(
                            analysis.get("components", [])
                        )
                        combined_analysis["functions"].extend(
                            analysis.get("functions", [])
                        )
                        combined_analysis["imports"].extend(analysis.get("imports", []))
                        combined_analysis["edge_cases"].extend(
                            analysis.get("edge_cases", [])
                        )
                        debug(
                            "qa_loop",
                            f"Analyzed TypeScript file {file_path}",
                            components=len(analysis.get("components", [])),
                            functions=len(analysis.get("functions", [])),
                        )
                    except Exception as e:
                        debug_warning("qa_loop", f"Failed to analyze {file_path}: {e}")

            if (
                combined_analysis["functions"]
                or combined_analysis["classes"]
                or combined_analysis["components"]
            ):
                print(
                    f"   Found {len(combined_analysis['functions'])} functions, "
                    f"{len(combined_analysis['classes'])} classes, and "
                    f"{len(combined_analysis['components'])} components"
                )
                print("   Generating tests...")

                # Run test generator
                test_result = await run_test_generator_session(
                    project_dir,
                    spec_dir,
                    combined_analysis,
                    model=model,
                    verbose=verbose,
                )

                if test_result.get("success"):
                    generated_files = test_result.get("generated_files", [])
                    framework = test_result.get("framework", "pytest")
                    print(
                        f"   ✅ Generated {len(generated_files)} {framework} test file(s)"
                    )
                    debug_success(
                        "qa_loop",
                        "Test generation completed",
                        file_count=len(generated_files),
                        framework=framework,
                    )

                    # Move generated tests to review directory for user approval
                    if generated_files:
                        _move_tests_to_review_directory(
                            project_dir, spec_dir, generated_files
                        )
                else:
                    error = test_result.get("error", "Unknown error")
                    print(f"   ⚠️  Test generation had issues: {error}")
                    debug_warning("qa_loop", f"Test generation incomplete: {error}")

                # Generate E2E tests for user-facing features
                if combined_analysis.get("components"):
                    print("\n🎭 Generating E2E tests for user-facing features...")
                    debug("qa_loop", "Starting E2E test generation")

                    try:
                        e2e_result = await generate_e2e_tests(
                            project_dir,
                            spec_dir,
                            combined_analysis,
                            model=model,
                            verbose=verbose,
                        )

                        if e2e_result.get("success"):
                            e2e_files = e2e_result.get("generated_files", [])
                            print(f"   ✅ Generated {len(e2e_files)} E2E test file(s)")
                            debug_success(
                                "qa_loop",
                                "E2E test generation completed",
                                file_count=len(e2e_files),
                            )

                            # Move E2E tests to review directory
                            if e2e_files:
                                _move_tests_to_review_directory(
                                    project_dir, spec_dir, e2e_files
                                )
                        else:
                            error = e2e_result.get("error", "Unknown error")
                            print(f"   ⚠️  E2E test generation had issues: {error}")
                            debug_warning(
                                "qa_loop", f"E2E test generation incomplete: {error}"
                            )
                    except Exception as e:
                        debug_error("qa_loop", f"E2E test generation failed: {e}")
                        print(f"   ⚠️  E2E test generation failed: {e}")
            else:
                print("   No testable functions or classes found")
                debug("qa_loop", "No testable code found in modified files")
        else:
            print("   No modified Python files to analyze")
            debug("qa_loop", "No modified files found in implementation plan")

        # Collect and report test coverage
        print("\n📊 Collecting test coverage reports...")
        debug("qa_loop", "Starting coverage collection")

        try:
            coverage_report = collect_coverage(project_dir, framework=None)

            if coverage_report:
                coverage_summary = format_coverage_summary(coverage_report)
                print("\n" + coverage_summary)
                debug_success(
                    "qa_loop",
                    "Coverage collection completed",
                    overall_coverage=coverage_report.overall_coverage,
                    framework=coverage_report.framework,
                )

                # Save coverage report to spec directory
                coverage_file = spec_dir / "coverage_report.json"
                import json

                coverage_data = {
                    "overall_coverage": coverage_report.overall_coverage,
                    "lines_total": coverage_report.lines_total,
                    "lines_covered": coverage_report.lines_covered,
                    "lines_missed": coverage_report.lines_missed,
                    "framework": coverage_report.framework,
                    "files": [
                        {
                            "file_path": f.file_path,
                            "coverage_percentage": f.coverage_percentage,
                            "lines_total": f.lines_total,
                            "lines_covered": f.lines_covered,
                            "lines_missed": f.lines_missed,
                        }
                        for f in coverage_report.files[:20]  # Top 20 files
                    ],
                    "uncovered_files": coverage_report.uncovered_files[
                        :10
                    ],  # Top 10 uncovered
                }
                coverage_json = json.dumps(coverage_data, indent=2)
                await asyncio.to_thread(
                    coverage_file.write_text, coverage_json, encoding="utf-8"
                )
                debug("qa_loop", f"Saved coverage report to {coverage_file}")
            else:
                print("   ⚠️  No coverage reports found")
                print("   Run tests with coverage enabled to generate reports")
                debug("qa_loop", "No coverage reports available")
        except Exception as e:
            debug_error("qa_loop", f"Coverage collection failed: {e}")
            print(f"   ⚠️  Coverage collection failed: {e}")

    except Exception as e:
        debug_error("qa_loop", f"Test generation failed: {e}")
        print(f"\n⚠️  Test generation failed: {e}")
        print("   Continuing with QA validation...")

    # Start validation phase in task logger
    if task_logger:
        task_logger.start_phase(LogPhase.VALIDATION, "Starting QA validation...")

    # Check Linear integration status
    linear_task = None
    if is_linear_enabled():
        linear_task = LinearTaskState.load(spec_dir)
        if linear_task and linear_task.task_id:
            print(f"Linear task: {linear_task.task_id}")
            # Update Linear to "In Review" when QA starts
            await linear_qa_started(spec_dir)
            print("Linear task moved to 'In Review'")

    qa_iteration = get_qa_iteration_count(spec_dir)
    consecutive_errors = 0
    last_error_context = None  # Track error for self-correction feedback

    while qa_iteration < MAX_QA_ITERATIONS:
        qa_iteration += 1
        iteration_start = time_module.time()

        debug_section("qa_loop", f"QA Iteration {qa_iteration}")
        debug(
            "qa_loop",
            f"Starting iteration {qa_iteration}/{MAX_QA_ITERATIONS}",
            iteration=qa_iteration,
            max_iterations=MAX_QA_ITERATIONS,
        )

        print(f"\n--- QA Iteration {qa_iteration}/{MAX_QA_ITERATIONS} ---")
        emit_phase(
            ExecutionPhase.QA_REVIEW, f"Running QA review iteration {qa_iteration}"
        )

        # Run QA reviewer with phase-specific model and thinking budget
        qa_model = get_phase_model(spec_dir, "qa", model)
        qa_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")
        debug(
            "qa_loop",
            "Creating client for QA reviewer session...",
            model=qa_model,
            thinking_budget=qa_thinking_budget,
        )
        client = create_client(
            project_dir,
            spec_dir,
            qa_model,
            agent_type="qa_reviewer",
            max_thinking_tokens=qa_thinking_budget,
        )

        async with client:
            debug("qa_loop", "Running QA reviewer agent session...")
            status, response = await run_qa_agent_session(
                client,
                project_dir,  # Pass project_dir for capability-based tool injection
                spec_dir,
                qa_iteration,
                MAX_QA_ITERATIONS,
                verbose,
                previous_error=last_error_context,  # Pass error context for self-correction
            )

        iteration_duration = time_module.time() - iteration_start
        debug(
            "qa_loop",
            "QA reviewer session completed",
            status=status,
            duration_seconds=f"{iteration_duration:.1f}",
            response_length=len(response),
        )

        if status == "approved":
            emit_phase(ExecutionPhase.COMPLETE, "QA validation passed")

            # Record successful iteration
            debug_success(
                "qa_loop",
                "QA APPROVED",
                iteration=qa_iteration,
                duration=f"{iteration_duration:.1f}s",
            )
            record_iteration(spec_dir, qa_iteration, "approved", [], iteration_duration)

            print("\n" + "=" * 70)
            print("  ✅ QA APPROVED")
            print("=" * 70)
            print("\nAll acceptance criteria verified.")
            print("The implementation is production-ready.")
            print("\nNext steps:")
            print("  1. Review the auto-claude/* branch")
            print("  2. Create a PR and merge to main")

            # End validation phase successfully
            if task_logger:
                task_logger.end_phase(
                    LogPhase.VALIDATION,
                    success=True,
                    message="QA validation passed - all criteria met",
                )

            # Update Linear: QA approved, awaiting human review
            if linear_task and linear_task.task_id:
                await linear_qa_approved(spec_dir)
                print("\nLinear: Task marked as QA approved, awaiting human review")

            return True

        elif status == "rejected":
            # Reset error tracking on valid response (rejected is a valid response)
            consecutive_errors = 0
            last_error_context = None

            debug_warning(
                "qa_loop",
                "QA REJECTED",
                iteration=qa_iteration,
                duration=f"{iteration_duration:.1f}s",
            )
            print(f"\n❌ QA found issues. Iteration {qa_iteration}/{MAX_QA_ITERATIONS}")

            # Get issues from QA report
            qa_status = get_qa_signoff_status(spec_dir)
            current_issues = qa_status.get("issues_found", []) if qa_status else []
            debug(
                "qa_loop",
                "Issues found by QA",
                issue_count=len(current_issues),
                issues=current_issues[:3] if current_issues else [],  # Show first 3
            )

            # Check for recurring issues BEFORE recording current iteration
            # This prevents the current issues from matching themselves in history
            history = get_iteration_history(spec_dir)
            has_recurring, recurring_issues = has_recurring_issues(
                current_issues, history
            )

            # Record rejected iteration AFTER checking for recurring issues
            record_iteration(
                spec_dir, qa_iteration, "rejected", current_issues, iteration_duration
            )

            # Analyze failure and store root causes in Graphiti (if enabled)
            if is_analysis_enabled() and is_graphiti_enabled():
                debug(
                    "qa_loop",
                    "Analyzing QA rejection to extract root causes",
                    issue_count=len(current_issues),
                    is_recurring=has_recurring,
                )

                try:
                    # Build failure context for analyzer
                    failure_context = {
                        "errors": [],  # QA rejections don't have errors, just issues
                        "issues": current_issues,
                        "is_recurring": has_recurring,
                        "qa_iteration": qa_iteration,
                        "occurrence_count": len(recurring_issues)
                        if has_recurring
                        else 1,
                    }

                    # Analyze the failure
                    analysis = analyze_failure(
                        spec_dir,
                        project_dir,
                        failure_type="qa_rejection",
                        failure_context=failure_context,
                    )

                    # Store root cause in Graphiti
                    memory = get_graphiti_memory(spec_dir, project_dir)
                    await memory.save_root_cause(
                        failure_type="qa_rejection",
                        root_cause=analysis.get("root_cause", {}),
                        failure_context={
                            "qa_iteration": qa_iteration,
                            "issue_count": len(current_issues),
                            "is_recurring": has_recurring,
                        },
                    )

                    debug_success(
                        "qa_loop",
                        "Root cause analysis stored in Graphiti",
                        category=analysis["root_cause"].get("category", "unknown"),
                        confidence=analysis["root_cause"].get("confidence", 0.0),
                    )

                except Exception as e:
                    # Don't fail the build if analysis fails
                    debug_warning("qa_loop", f"Failed to analyze QA rejection: {e}")

            if has_recurring:
                from .report import RECURRING_ISSUE_THRESHOLD

                debug_error(
                    "qa_loop",
                    "Recurring issues detected - escalating to human",
                    recurring_count=len(recurring_issues),
                    threshold=RECURRING_ISSUE_THRESHOLD,
                )
                print(
                    f"\n⚠️  Recurring issues detected ({len(recurring_issues)} issue(s) appeared {RECURRING_ISSUE_THRESHOLD}+ times)"
                )
                print("Escalating to human review due to recurring issues...")

                # Create escalation file
                await escalate_to_human(spec_dir, recurring_issues, qa_iteration)

                # End validation phase
                if task_logger:
                    task_logger.end_phase(
                        LogPhase.VALIDATION,
                        success=False,
                        message=f"QA escalated to human after {qa_iteration} iterations due to recurring issues",
                    )

                # Update Linear
                if linear_task and linear_task.task_id:
                    await linear_qa_max_iterations(spec_dir, qa_iteration)
                    print(
                        "\nLinear: Task marked as needing human intervention (recurring issues)"
                    )

                return False

            # Enhanced escalation: Check for early escalation signals
            # This uses the RecoveryManager to proactively identify high-risk situations
            should_escalate = False
            escalation_reason = ""

            try:
                recovery_manager = RecoveryManager(spec_dir, project_dir)

                # Build error description from QA issues for escalation analysis
                error_description = f"QA rejection with {len(current_issues)} issue(s)"
                if current_issues:
                    # Include first issue description for pattern matching
                    error_description += f": {current_issues[0].get('title', '')}"

                # Map QA iteration to a pseudo-subtask for recovery tracking
                qa_subtask_id = f"qa_iteration_{qa_iteration}"

                # Classify the failure type based on issues
                from services.recovery import FailureType

                failure_type = (
                    FailureType.VERIFICATION_FAILED
                )  # QA rejections are verification failures

                # Check if we should escalate early (before max iterations)
                should_escalate, escalation_reason = (
                    recovery_manager.should_escalate_early(
                        qa_subtask_id, failure_type, error_description
                    )
                )

                if should_escalate:
                    debug_error(
                        "qa_loop",
                        "Early escalation triggered by enhanced recovery logic",
                        reason=escalation_reason,
                        iteration=qa_iteration,
                        max_iterations=MAX_QA_ITERATIONS,
                    )
                    print("\n⚠️  Early Escalation Triggered")
                    print(f"   Reason: {escalation_reason}")
                    print(
                        f"   Escalating at iteration {qa_iteration}/{MAX_QA_ITERATIONS}..."
                    )

                    # Create escalation file
                    await escalate_to_human(spec_dir, current_issues, qa_iteration)

                    # End validation phase
                    if task_logger:
                        task_logger.end_phase(
                            LogPhase.VALIDATION,
                            success=False,
                            message=f"QA escalated to human after {qa_iteration} iterations: {escalation_reason}",
                        )

                    # Update Linear
                    if linear_task and linear_task.task_id:
                        await linear_qa_max_iterations(spec_dir, qa_iteration)
                        print(
                            "\nLinear: Task marked as needing human intervention (early escalation)"
                        )

                    return False

            except Exception as e:
                # Don't fail the QA loop if escalation check fails
                debug_warning("qa_loop", f"Early escalation check failed: {e}")
                # Continue with normal fixer loop

            # Record rejection in Linear
            if linear_task and linear_task.task_id:
                issues_count = len(current_issues)
                await linear_qa_rejected(spec_dir, issues_count, qa_iteration)

            if qa_iteration >= MAX_QA_ITERATIONS:
                print("\n⚠️  Maximum QA iterations reached.")
                print("Escalating to human review.")
                break

            # Run fixer with phase-specific thinking budget
            fixer_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")
            debug(
                "qa_loop",
                "Starting QA fixer session...",
                model=qa_model,
                thinking_budget=fixer_thinking_budget,
            )
            emit_phase(ExecutionPhase.QA_FIXING, "Fixing QA issues")
            print("\nRunning QA Fixer Agent...")

            fix_client = create_client(
                project_dir,
                spec_dir,
                qa_model,
                agent_type="qa_fixer",
                max_thinking_tokens=fixer_thinking_budget,
            )

            async with fix_client:
                fix_status, fix_response = await run_qa_fixer_session(
                    fix_client, spec_dir, qa_iteration, verbose
                )

            debug(
                "qa_loop",
                "QA fixer session completed",
                fix_status=fix_status,
                response_length=len(fix_response),
            )

            if fix_status == "error":
                debug_error("qa_loop", f"Fixer error: {fix_response[:200]}")
                print(f"\n❌ Fixer encountered error: {fix_response}")
                record_iteration(
                    spec_dir,
                    qa_iteration,
                    "error",
                    [{"title": "Fixer error", "description": fix_response}],
                )
                break
            elif fix_status == "circular":
                # Circular fix detected - record dead-end and continue QA loop
                debug_warning(
                    "qa_loop",
                    "Circular fix detected - recording dead-end and continuing",
                )
                print("\n⚠️  Circular Fix Detected")
                print("   The fixer attempted the same approach multiple times.")
                print("   Recording dead-end and continuing QA validation loop...")
                record_iteration(
                    spec_dir,
                    qa_iteration,
                    "circular",
                    [{"title": "Circular fix detected", "description": fix_response}],
                )
                # Continue to next QA iteration to see if a different approach is needed
                continue
            elif fix_status == "stuck":
                # Fixer is stuck - escalate to human
                debug_error(
                    "qa_loop",
                    "Fixer stuck after multiple recovery attempts - escalating to human",
                )
                print("\n⚠️  QA Fixer Stuck")
                print(
                    "   The fixer attempted multiple recovery approaches but could not resolve the issues."
                )
                print("   Escalating to human review...")
                record_iteration(
                    spec_dir,
                    qa_iteration,
                    "stuck",
                    [{"title": "Fixer stuck", "description": fix_response}],
                )

                # End validation phase as failed
                if task_logger:
                    task_logger.end_phase(
                        LogPhase.VALIDATION,
                        success=False,
                        message="QA fixer stuck after multiple recovery attempts - human intervention required",
                    )

                # Update Linear if enabled
                if linear_task and linear_task.task_id:
                    await linear_qa_max_iterations(spec_dir, qa_iteration)
                    print("\nLinear: Task marked as needing human intervention")

                return False

            debug_success("qa_loop", "Fixes applied, re-running QA validation")
            print("\n✅ Fixes applied. Re-running QA validation...")

        elif status == "error":
            consecutive_errors += 1
            debug_error(
                "qa_loop",
                f"QA session error: {response[:200]}",
                consecutive_errors=consecutive_errors,
                max_consecutive=MAX_CONSECUTIVE_ERRORS,
            )
            print(f"\n❌ QA error: {response}")
            print(
                f"   Consecutive errors: {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}"
            )
            record_iteration(
                spec_dir,
                qa_iteration,
                "error",
                [{"title": "QA error", "description": response}],
            )

            # Build error context for self-correction in next iteration
            last_error_context = {
                "error_type": "missing_implementation_plan_update",
                "error_message": response,
                "consecutive_errors": consecutive_errors,
                "expected_action": "You MUST update implementation_plan.json with a qa_signoff object containing 'status': 'approved' or 'status': 'rejected'",
                "file_path": str(spec_dir / "implementation_plan.json"),
            }

            # Check if we've hit max consecutive errors
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                debug_error(
                    "qa_loop",
                    f"Max consecutive errors ({MAX_CONSECUTIVE_ERRORS}) reached - escalating to human",
                )
                print(
                    f"\n⚠️  {MAX_CONSECUTIVE_ERRORS} consecutive errors without progress."
                )
                print(
                    "The QA agent is unable to properly update implementation_plan.json."
                )
                print("Escalating to human review.")

                # End validation phase as failed
                if task_logger:
                    task_logger.end_phase(
                        LogPhase.VALIDATION,
                        success=False,
                        message=f"QA agent failed {MAX_CONSECUTIVE_ERRORS} consecutive times - unable to update implementation_plan.json",
                    )
                return False

            print("Retrying with error feedback...")

    # Max iterations reached without approval
    emit_phase(ExecutionPhase.FAILED, "QA validation incomplete")
    debug_error(
        "qa_loop",
        "QA VALIDATION INCOMPLETE - max iterations reached",
        iterations=qa_iteration,
        max_iterations=MAX_QA_ITERATIONS,
    )
    print("\n" + "=" * 70)
    print("  ⚠️  QA VALIDATION INCOMPLETE")
    print("=" * 70)
    print(f"\nReached maximum iterations ({MAX_QA_ITERATIONS}) without approval.")
    print("\nRemaining issues require human review:")

    # Show iteration summary
    history = get_iteration_history(spec_dir)
    summary = get_recurring_issue_summary(history)
    debug(
        "qa_loop",
        "QA loop final summary",
        total_iterations=len(history),
        total_issues=summary.get("total_issues", 0),
        unique_issues=summary.get("unique_issues", 0),
    )
    if summary["total_issues"] > 0:
        print("\n📊 Iteration Summary:")
        print(f"   Total iterations: {len(history)}")
        print(f"   Total issues found: {summary['total_issues']}")
        print(f"   Unique issues: {summary['unique_issues']}")
        if summary.get("most_common"):
            print("   Most common issues:")
            for issue in summary["most_common"][:3]:
                print(f"     - {issue['title']} ({issue['occurrences']} occurrences)")

    # End validation phase as failed
    if task_logger:
        task_logger.end_phase(
            LogPhase.VALIDATION,
            success=False,
            message=f"QA validation incomplete after {qa_iteration} iterations",
        )

    # Show the fix request file if it exists
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"
    if fix_request_file.exists():
        print(f"\nSee: {fix_request_file}")

    qa_report_file = spec_dir / "qa_report.md"
    if qa_report_file.exists():
        print(f"See: {qa_report_file}")

    # Update Linear: max iterations reached, needs human intervention
    if linear_task and linear_task.task_id:
        await linear_qa_max_iterations(spec_dir, qa_iteration)
        print("\nLinear: Task marked as needing human intervention")

    print("\nManual intervention required.")
    return False
