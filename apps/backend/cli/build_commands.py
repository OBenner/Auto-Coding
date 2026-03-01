"""
Build Commands
==============

CLI commands for building specs and handling the main build flow.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

# Import only what we need at module level
# Heavy imports are lazy-loaded in functions to avoid import errors
from progress import print_paused_banner
from review import ReviewState

from cli.artifacts import create_artifact_manager
from cli.exit_codes import ExitCode
from cli.json_output import format_build_result
from ui import (
    BuildState,
    Icons,
    MenuOption,
    StatusManager,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_status,
    select_menu,
    success,
    warning,
)
from workspace import (
    WorkspaceMode,
    check_existing_build,
    choose_workspace,
    finalize_workspace,
    get_existing_build_worktree,
    handle_workspace_choice,
    setup_workspace,
)

from .input_handlers import (
    read_from_file,
    read_multiline_input,
)
from .utils import is_ci_mode


def _generate_test_report_data(
    spec_dir: Path,
    qa_approved: bool,
) -> dict[str, Any]:
    """
    Generate test report data from QA results.

    Collects QA iteration history, test generation info, and approval status
    for CI/CD artifact generation.

    Args:
        spec_dir: Spec directory
        qa_approved: Whether QA approved the build

    Returns:
        Dictionary with test report data for artifact manager
    """
    import json

    # Load implementation plan to get QA stats
    impl_plan_path = spec_dir / "implementation_plan.json"
    qa_stats = {}
    iteration_history = []

    if impl_plan_path.exists():
        try:
            with open(impl_plan_path, encoding="utf-8") as f:
                impl_plan = json.load(f)
            qa_stats = impl_plan.get("qa_stats", {})
            iteration_history = impl_plan.get("qa_iteration_history", [])
        except (OSError, json.JSONDecodeError):
            pass

    # Count iterations by status
    iterations_approved = sum(1 for it in iteration_history if it.get("status") == "approved")
    iterations_rejected = sum(1 for it in iteration_history if it.get("status") == "rejected")
    iterations_error = sum(1 for it in iteration_history if it.get("status") == "error")
    total_iterations = len(iteration_history)

    # Count total issues found
    total_issues = sum(len(it.get("issues", [])) for it in iteration_history)

    # Check for generated tests
    generated_tests_dir = spec_dir / "generated_tests_review"
    generated_test_count = 0
    if generated_tests_dir.exists():
        generated_test_count = sum(
            1 for f in generated_tests_dir.iterdir() if f.is_file() and f.suffix == ".py"
        )

    # Build test report data
    test_report_data = {
        "qaApproved": qa_approved,
        "totalIterations": total_iterations,
        "iterationsApproved": iterations_approved,
        "iterationsRejected": iterations_rejected,
        "iterationsError": iterations_error,
        "totalIssues": total_issues,
        "generatedTests": generated_test_count,
    }

    # Add issue breakdown if available
    issues_by_type = qa_stats.get("issues_by_type", {})
    if issues_by_type:
        test_report_data["issuesByType"] = issues_by_type

    # Add duration summary if available
    durations = [
        it.get("duration_seconds", 0)
        for it in iteration_history
        if it.get("duration_seconds") is not None
    ]
    if durations:
        test_report_data["totalDuration"] = round(sum(durations), 2)
        test_report_data["averageDuration"] = round(sum(durations) / len(durations), 2)

    return test_report_data

# Pattern management commands are available in pattern_commands.py
# Run: python apps/backend/cli/pattern_commands.py --help


def handle_build_command(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    provider: str | None,
    max_iterations: int | None,
    verbose: bool,
    force_isolated: bool,
    force_direct: bool,
    auto_continue: bool,
    skip_qa: bool,
    force_bypass_approval: bool,
    base_branch: str | None = None,
    json_mode: bool = False,
    restart_from: str | None = None,
) -> None:
    """
    Handle the main build command.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory path
        model: Model to use (used as default; may be overridden by task_metadata.json)
        provider: AI provider to use (claude, litellm, openrouter, zhipuai)
        max_iterations: Maximum number of iterations (None for unlimited)
        verbose: Enable verbose output
        force_isolated: Force isolated workspace mode
        force_direct: Force direct workspace mode
        auto_continue: Auto-continue mode (non-interactive)
        skip_qa: Skip automatic QA validation
        force_bypass_approval: Force bypass approval check
        base_branch: Base branch for worktree creation (default: current branch)
        json_mode: Enable JSON output mode for CI/CD pipelines
        restart_from: Subtask ID to restart from (None for normal execution)
    """
    # Lazy imports to avoid loading heavy modules
    from agents import run_autonomous_agent, sync_spec_to_source
    from debug import (
        debug,
        debug_info,
        debug_section,
        debug_success,
    )
    from phase_config import get_phase_model
    from prompts_pkg.prompts import get_base_branch_from_metadata
    from qa_loop import run_qa_validation_loop, should_run_qa

    from .utils import print_banner, validate_environment

    # Set provider from CLI argument if provided
    if provider:
        from core.providers.config import AIEngineProvider

        valid_providers = [p.value for p in AIEngineProvider]
        if provider not in valid_providers:
            print(
                f"\nError: Invalid provider '{provider}'. Must be one of: {', '.join(valid_providers)}"
            )
            sys.exit(1)
        os.environ["AI_ENGINE_PROVIDER"] = provider
        debug("run.py", f"Provider set from CLI: {provider}")
        # Map CLI --model to provider-specific env var for consistent display
        if model:
            model_env_map = {
                "claude": "CLAUDE_MODEL",
                "litellm": "LITELLM_MODEL",
                "openrouter": "OPENROUTER_MODEL",
                "zhipuai": "ZHIPUAI_MODEL",
            }
            env_key = model_env_map.get(provider)
            if env_key:
                os.environ[env_key] = model

    # Determine if we should skip interactive prompts (CI mode, JSON mode, or auto-continue)
    non_interactive = auto_continue or json_mode or is_ci_mode()

    # Track build start time for JSON output
    build_start_time = time.time()
    build_status = ExitCode.SUCCESS
    error_message = None
    changed_files = []

    # Initialize artifact manager for CI mode
    artifact_manager = None
    if json_mode:
        artifact_manager = create_artifact_manager(spec_dir=spec_dir, enabled=True)

    # Get the resolved model for the planning phase (first phase of build)
    # This respects task_metadata.json phase configuration from the UI
    planning_model = get_phase_model(spec_dir, "planning", model)
    coding_model = get_phase_model(spec_dir, "coding", model)
    qa_model = get_phase_model(spec_dir, "qa", model)

    print_banner()
    print(f"\nProject directory: {project_dir}")
    print(f"Spec: {spec_dir.name}")

    # Get current provider for display
    from core.providers.config import get_provider_config

    provider_config = get_provider_config()
    provider_display = (
        provider_config.get_provider_summary() if provider_config else "unknown"
    )

    # Show provider and model information
    print(f"Provider: {provider_display}")
    # Show phase-specific models if they differ
    if planning_model != coding_model or coding_model != qa_model:
        print(
            f"Models: Planning={planning_model.split('-')[1] if '-' in planning_model else planning_model}, "
            f"Coding={coding_model.split('-')[1] if '-' in coding_model else coding_model}, "
            f"QA={qa_model.split('-')[1] if '-' in qa_model else qa_model}"
        )
    else:
        print(f"Model: {planning_model}")

    if max_iterations:
        print(f"Max iterations: {max_iterations}")
    else:
        print("Max iterations: Unlimited (runs until all subtasks complete)")

    print()

    # Validate environment
    if not validate_environment(spec_dir):
        sys.exit(ExitCode.SYSTEM_ERROR)

    # Check human review approval
    review_state = ReviewState.load(spec_dir)
    if not review_state.is_approval_valid(spec_dir):
        if force_bypass_approval:
            # User explicitly bypassed approval check
            print()
            print(
                warning(
                    f"{icon(Icons.WARNING)} WARNING: Bypassing approval check with --force"
                )
            )
            print(muted("This spec has not been approved for building."))
            print()
        else:
            print()
            content = [
                bold(f"{icon(Icons.WARNING)} BUILD BLOCKED - REVIEW REQUIRED"),
                "",
                "This spec requires human approval before building.",
            ]

            if review_state.approved and not review_state.is_approval_valid(spec_dir):
                # Spec changed after approval
                content.append("")
                content.append(warning("The spec has been modified since approval."))
                content.append("Please re-review and re-approve.")

            content.extend(
                [
                    "",
                    highlight("To review and approve:"),
                    f"  python auto-claude/review.py --spec-dir {spec_dir}",
                    "",
                    muted("Or use --force to bypass this check (not recommended)."),
                ]
            )
            print(box(content, width=70, style="heavy"))
            print()
            sys.exit(ExitCode.BUILD_FAILED)
    else:
        debug_success(
            "run.py", "Review approval validated", approved_by=review_state.approved_by
        )

    # Check for existing build
    if get_existing_build_worktree(project_dir, spec_dir.name):
        if non_interactive:
            # Non-interactive mode: auto-continue with existing build
            debug("run.py", "Non-interactive mode: continuing with existing build")
            print("Non-interactive: Resuming existing build...")
        else:
            continue_existing = check_existing_build(project_dir, spec_dir.name)
            if continue_existing:
                # Continue with existing worktree
                pass
            else:
                # User chose to start fresh or merged existing
                pass

    # Choose workspace (skip for parallel mode - it always uses worktrees)
    working_dir = project_dir
    worktree_manager = None
    source_spec_dir = None  # Track original spec dir for syncing back from worktree

    # Let user choose workspace mode (or auto-select if --auto-continue or CI mode)
    workspace_mode = choose_workspace(
        project_dir,
        spec_dir.name,
        force_isolated=force_isolated,
        force_direct=force_direct,
        auto_continue=non_interactive,
    )

    # If base_branch not provided via CLI, try to read from task_metadata.json
    # This ensures the backend uses the branch configured in the frontend
    if base_branch is None:
        metadata_branch = get_base_branch_from_metadata(spec_dir)
        if metadata_branch:
            base_branch = metadata_branch
            debug("run.py", f"Using base branch from task metadata: {base_branch}")

    if workspace_mode == WorkspaceMode.ISOLATED:
        # Keep reference to original spec directory for syncing progress back
        source_spec_dir = spec_dir

        working_dir, worktree_manager, localized_spec_dir = setup_workspace(
            project_dir,
            spec_dir.name,
            workspace_mode,
            source_spec_dir=spec_dir,
            base_branch=base_branch,
        )
        # Use the localized spec directory (inside worktree) for AI access
        if localized_spec_dir:
            spec_dir = localized_spec_dir

    # Run the autonomous agent
    debug_section("run.py", "Starting Build Execution")
    debug(
        "run.py",
        "Build configuration",
        model=model,
        workspace_mode=str(workspace_mode),
        working_dir=str(working_dir),
        spec_dir=str(spec_dir),
    )

    try:
        debug("run.py", "Starting agent execution")

        asyncio.run(
            run_autonomous_agent(
                project_dir=working_dir,  # Use worktree if isolated
                spec_dir=spec_dir,
                model=model,
                max_iterations=max_iterations,
                verbose=verbose,
                source_spec_dir=source_spec_dir,  # For syncing progress back to main project
                restart_from=restart_from,  # Restart from specific subtask if specified
            )
        )
        debug_success("run.py", "Agent execution completed")

        # Run QA validation BEFORE finalization (while worktree still exists)
        # QA must sign off before the build is considered complete
        qa_approved = True  # Default to approved if QA is skipped
        if not skip_qa and should_run_qa(spec_dir):
            print("\n" + "=" * 70)
            print("  SUBTASKS COMPLETE - STARTING QA VALIDATION")
            print("=" * 70)
            print("\nAll subtasks completed. Now running QA validation loop...")
            print("This ensures production-quality output before sign-off.\n")

            try:
                qa_approved = asyncio.run(
                    run_qa_validation_loop(
                        project_dir=working_dir,
                        spec_dir=spec_dir,
                        model=model,
                        verbose=verbose,
                    )
                )

                if qa_approved:
                    print("\n" + "=" * 70)
                    print("  ✅ QA VALIDATION PASSED")
                    print("=" * 70)
                    print("\nAll acceptance criteria verified.")
                    print("The implementation is production-ready.\n")
                else:
                    print("\n" + "=" * 70)
                    print("  ⚠️  QA VALIDATION INCOMPLETE")
                    print("=" * 70)
                    print("\nSome issues require manual attention.")
                    print(f"See: {spec_dir / 'qa_report.md'}")
                    print(f"Or:  {spec_dir / 'QA_FIX_REQUEST.md'}")
                    print(
                        f"\nResume QA: python auto-claude/run.py --spec {spec_dir.name} --qa\n"
                    )

                # Generate test report artifact for CI mode
                if artifact_manager:
                    test_report_data = _generate_test_report_data(spec_dir, qa_approved)
                    artifact_manager.save_test_report(test_report_data)

                # Sync implementation plan to main project after QA
                # This ensures the main project has the latest status (human_review)
                if sync_spec_to_source(spec_dir, source_spec_dir):
                    debug_info(
                        "run.py", "Implementation plan synced to main project after QA"
                    )
            except KeyboardInterrupt:
                print("\n\nQA validation paused.")
                print(f"Resume: python auto-claude/run.py --spec {spec_dir.name} --qa")

                # Generate test report artifact even on interrupt
                if artifact_manager:
                    test_report_data = _generate_test_report_data(spec_dir, qa_approved)
                    artifact_manager.save_test_report(test_report_data)

        # Post-build finalization (only for isolated sequential mode)
        # This happens AFTER QA validation so the worktree still exists
        if worktree_manager:
            choice = finalize_workspace(
                project_dir,
                spec_dir.name,
                worktree_manager,
                auto_continue=non_interactive,
            )
            handle_workspace_choice(
                choice, project_dir, spec_dir.name, worktree_manager
            )

    except KeyboardInterrupt:
        _handle_build_interrupt(
            spec_dir=spec_dir,
            project_dir=project_dir,
            worktree_manager=worktree_manager,
            working_dir=working_dir,
            model=model,
            max_iterations=max_iterations,
            verbose=verbose,
            json_mode=json_mode,
            non_interactive=non_interactive,
        )
    except Exception as e:
        error_message = str(e)
        build_status = ExitCode.SYSTEM_ERROR
        print(f"\nFatal error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        if json_mode:
            duration = time.time() - build_start_time

            # Save build log artifact even on error
            if artifact_manager:
                build_log_data = {
                    "status": build_status.name,
                    "timestamp": None,  # Will be added by artifact manager
                    "duration": round(duration, 2),
                    "exitCode": ExitCode.SYSTEM_ERROR,
                    "error": error_message,
                }
                artifact_manager.save_build_log(build_log_data)

            json_output = format_build_result(
                status=build_status,
                spec_name=spec_dir.name,
                exit_code=ExitCode.SYSTEM_ERROR,
                duration_seconds=duration,
                error_message=error_message,
            )
            print(json_output)
        sys.exit(ExitCode.SYSTEM_ERROR)

    # Calculate build duration and prepare JSON output if requested
    if json_mode:
        duration = time.time() - build_start_time

        # Try to get changed files list if build succeeded
        if build_status == ExitCode.SUCCESS and worktree_manager:
            try:
                import subprocess

                worktree_path = get_existing_build_worktree(project_dir, spec_dir.name)
                if worktree_path:
                    result = subprocess.run(
                        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                        cwd=worktree_path,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        changed_files = [
                            f.strip() for f in result.stdout.strip().split("\n") if f.strip()
                        ]
            except Exception:
                # If we can't get changed files, continue without them
                pass

        # Prepare metadata
        metadata = {
            "model": model,
            "planningModel": planning_model,
            "codingModel": coding_model,
            "qaModel": qa_model,
            "maxIterations": max_iterations,
            "workspaceMode": "isolated" if worktree_manager else "direct",
        }

        # Collect artifact information if artifact manager is enabled
        artifacts_dict = {}
        if artifact_manager:
            # Save build log artifact
            build_log_data = {
                "status": build_status.name,
                "timestamp": None,  # Will be added by artifact manager
                "duration": round(duration, 2),
                "exitCode": int(build_status),
            }

            if error_message:
                build_log_data["error"] = error_message

            if changed_files:
                build_log_data["changedFiles"] = changed_files
                build_log_data["filesChanged"] = len(changed_files)

            if metadata:
                build_log_data["metadata"] = metadata

            # Save the build log
            build_log_path = artifact_manager.save_build_log(build_log_data)
            if build_log_path:
                artifacts_dict["build-log"] = str(build_log_path)

            # Add test report if it was generated during QA
            test_report_path = artifact_manager.get_artifact_path("test-report.json")
            if test_report_path:
                artifacts_dict["test-report"] = str(test_report_path)

        # Format and print JSON output
        json_output = format_build_result(
            status=build_status,
            spec_name=spec_dir.name,
            exit_code=build_status,
            duration_seconds=duration,
            error_message=error_message,
            changed_files=changed_files if changed_files else None,
            artifacts=artifacts_dict if artifacts_dict else None,
            metadata=metadata,
        )
        print(json_output)


def _handle_build_interrupt(
    spec_dir: Path,
    project_dir: Path,
    worktree_manager,
    working_dir: Path,
    model: str,
    max_iterations: int | None,
    verbose: bool,
    json_mode: bool = False,
    non_interactive: bool = False,
) -> None:
    """
    Handle keyboard interrupt during build.

    Args:
        spec_dir: Spec directory path
        project_dir: Project root directory
        worktree_manager: Worktree manager instance (if using isolated mode)
        working_dir: Current working directory
        model: Model being used
        max_iterations: Maximum iterations
        verbose: Verbose mode flag
        json_mode: Enable JSON output mode
        non_interactive: Skip interactive prompts (CI mode or auto-continue)
    """
    from agents import run_autonomous_agent

    # Create artifact manager for saving build logs on interrupt
    artifact_manager = None
    if json_mode:
        artifact_manager = create_artifact_manager(spec_dir=spec_dir, enabled=True)

    # Print paused banner
    print_paused_banner(spec_dir, spec_dir.name, has_worktree=bool(worktree_manager))

    # Update status file
    status_manager = StatusManager(project_dir)
    status_manager.update(state=BuildState.PAUSED)

    # In non-interactive mode (CI or auto-continue), exit immediately
    if non_interactive:
        print()
        print_status("Build interrupted in non-interactive mode. Exiting...", "warning")
        status_manager.set_inactive()
        if json_mode:
            # Save build log artifact on interrupt
            if artifact_manager:
                build_log_data = {
                    "status": "interrupted",
                    "timestamp": None,  # Will be added by artifact manager
                    "exitCode": ExitCode.SUCCESS,
                    "error": "Build interrupted in non-interactive mode",
                }
                artifact_manager.save_build_log(build_log_data)

            json_output = format_build_result(
                status=ExitCode.SUCCESS,
                spec_name=spec_dir.name,
                exit_code=ExitCode.SUCCESS,
                duration_seconds=None,
                error_message="Build interrupted in non-interactive mode",
            )
            print(json_output)
        sys.exit(ExitCode.SUCCESS)

    # Offer to add human input with enhanced menu
    try:
        options = [
            MenuOption(
                key="type",
                label="Type instructions",
                icon=Icons.EDIT,
                description="Enter guidance for the agent's next session",
            ),
            MenuOption(
                key="paste",
                label="Paste from clipboard",
                icon=Icons.CLIPBOARD,
                description="Paste text you've copied (Cmd+V / Ctrl+Shift+V)",
            ),
            MenuOption(
                key="file",
                label="Read from file",
                icon=Icons.DOCUMENT,
                description="Load instructions from a text file",
            ),
            MenuOption(
                key="skip",
                label="Continue without instructions",
                icon=Icons.SKIP,
                description="Resume the build as-is",
            ),
            MenuOption(
                key="quit",
                label="Quit",
                icon=Icons.DOOR,
                description="Exit without resuming",
            ),
        ]

        choice = select_menu(
            title="What would you like to do?",
            options=options,
            subtitle="Progress saved. You can add instructions for the agent.",
            allow_quit=False,  # We have explicit quit option
        )

        if choice == "quit" or choice is None:
            print()
            print_status("Exiting...", "info")
            status_manager.set_inactive()
            if json_mode:
                # Save build log artifact on quit
                if artifact_manager:
                    build_log_data = {
                        "status": "paused",
                        "timestamp": None,  # Will be added by artifact manager
                        "exitCode": ExitCode.SUCCESS,
                        "error": "Build paused by user",
                    }
                    artifact_manager.save_build_log(build_log_data)

                json_output = format_build_result(
                    status=ExitCode.SUCCESS,
                    spec_name=spec_dir.name,
                    exit_code=ExitCode.SUCCESS,
                    duration_seconds=None,
                    error_message="Build paused by user",
                )
                print(json_output)
            sys.exit(ExitCode.SUCCESS)

        human_input = ""

        if choice == "file":
            # Read from file
            human_input = read_from_file()
            if human_input is None:
                human_input = ""

        elif choice in ["type", "paste"]:
            human_input = read_multiline_input("Enter/paste your instructions below.")
            if human_input is None:
                print()
                print_status("Exiting without saving instructions...", "warning")
                status_manager.set_inactive()
                if json_mode:
                    # Save build log artifact on cancel
                    if artifact_manager:
                        build_log_data = {
                            "status": "paused",
                            "timestamp": None,  # Will be added by artifact manager
                            "exitCode": ExitCode.SUCCESS,
                            "error": "Build paused by user",
                        }
                        artifact_manager.save_build_log(build_log_data)

                    json_output = format_build_result(
                        status=ExitCode.SUCCESS,
                        spec_name=spec_dir.name,
                        exit_code=ExitCode.SUCCESS,
                        duration_seconds=None,
                        error_message="Build paused by user",
                    )
                    print(json_output)
                sys.exit(ExitCode.SUCCESS)

        if human_input:
            # Save to HUMAN_INPUT.md
            input_file = spec_dir / "HUMAN_INPUT.md"
            input_file.write_text(human_input, encoding="utf-8")

            content = [
                success(f"{icon(Icons.SUCCESS)} INSTRUCTIONS SAVED"),
                "",
                f"Saved to: {highlight(str(input_file.name))}",
                "",
                muted(
                    "The agent will read and follow these instructions when you resume."
                ),
            ]
            print()
            print(box(content, width=70, style="heavy"))
        elif choice != "skip":
            print()
            print_status("No instructions provided.", "info")

        # If 'skip' was selected, actually resume the build
        if choice == "skip":
            print()
            print_status("Resuming build...", "info")
            status_manager.update(state=BuildState.BUILDING)
            asyncio.run(
                run_autonomous_agent(
                    project_dir=working_dir,
                    spec_dir=spec_dir,
                    model=model,
                    max_iterations=max_iterations,
                    verbose=verbose,
                )
            )
            # Build completed or was interrupted again - exit
            if json_mode:
                # Save build log artifact on completion after resume
                if artifact_manager:
                    build_log_data = {
                        "status": "success",
                        "timestamp": None,  # Will be added by artifact manager
                        "exitCode": ExitCode.SUCCESS,
                        "error": "Build completed after resuming",
                    }
                    artifact_manager.save_build_log(build_log_data)

                json_output = format_build_result(
                    status=ExitCode.SUCCESS,
                    spec_name=spec_dir.name,
                    exit_code=ExitCode.SUCCESS,
                    duration_seconds=None,
                    error_message="Build completed after resuming",
                )
                print(json_output)
            sys.exit(ExitCode.SUCCESS)

    except KeyboardInterrupt:
        # User pressed Ctrl+C again during input prompt - exit immediately
        print()
        print_status("Exiting...", "warning")
        status_manager = StatusManager(project_dir)
        status_manager.set_inactive()
        if json_mode:
            # Save build log artifact on double Ctrl+C
            if artifact_manager:
                build_log_data = {
                    "status": "paused",
                    "timestamp": None,  # Will be added by artifact manager
                    "exitCode": ExitCode.SUCCESS,
                    "error": "Build paused by user (Ctrl+C)",
                }
                artifact_manager.save_build_log(build_log_data)

            json_output = format_build_result(
                status=ExitCode.SUCCESS,
                spec_name=spec_dir.name,
                exit_code=ExitCode.SUCCESS,
                duration_seconds=None,
                error_message="Build paused by user (Ctrl+C)",
            )
            print(json_output)
        sys.exit(ExitCode.SUCCESS)
    except EOFError:
        # stdin closed
        if json_mode:
            # Save build log artifact on EOF
            if artifact_manager:
                build_log_data = {
                    "status": "error",
                    "timestamp": None,  # Will be added by artifact manager
                    "exitCode": ExitCode.SYSTEM_ERROR,
                    "error": "Build interrupted (EOF)",
                }
                artifact_manager.save_build_log(build_log_data)

            json_output = format_build_result(
                status=ExitCode.SYSTEM_ERROR,
                spec_name=spec_dir.name,
                exit_code=ExitCode.SYSTEM_ERROR,
                duration_seconds=None,
                error_message="Build interrupted (EOF)",
            )
            print(json_output)
        pass

    # Resume instructions (shown when user provided instructions or chose file/type/paste)
    print()
    content = [
        bold(f"{icon(Icons.PLAY)} TO RESUME"),
        "",
        f"Run: {highlight(f'python auto-claude/run.py --spec {spec_dir.name}')}",
    ]
    if worktree_manager:
        content.append("")
        content.append(muted("Your build is in a separate workspace and is safe."))
    print(box(content, width=70, style="light"))
    print()
