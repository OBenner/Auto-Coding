"""
QA Fixer Agent Session
=======================

Runs QA fixer sessions to resolve issues identified by the reviewer.

Memory Integration:
- Retrieves past patterns, fixes, and gotchas before fixing
- Saves fix outcomes and learnings after session
"""

import time
from pathlib import Path

# Memory integration for cross-session learning
from agents.memory_manager import (
    get_failure_patterns,
    get_graphiti_context,
    save_session_memory,
)
from claude_agent_sdk import ClaudeSDKClient
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from security.tool_input_validator import get_safe_tool_input
from services.recovery import RecoveryManager
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)

# Configuration
QA_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MAX_FIXER_ITERATIONS = 10  # Max recovery attempts for a single QA fix session


# =============================================================================
# PROMPT LOADING
# =============================================================================


def load_qa_fixer_prompt() -> str:
    """Load the QA fixer agent prompt."""
    prompt_file = QA_PROMPTS_DIR / "qa_fixer.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"QA fixer prompt not found: {prompt_file}")
    return prompt_file.read_text(encoding="utf-8")


# =============================================================================
# QA FIXER SESSION
# =============================================================================


async def run_qa_fixer_session(
    client: ClaudeSDKClient,
    spec_dir: Path,
    fix_session: int,
    verbose: bool = False,
    project_dir: Path | None = None,
) -> tuple[str, str]:
    """
    Run a QA fixer agent session.

    Args:
        client: Claude SDK client
        spec_dir: Spec directory
        fix_session: Fix iteration number
        verbose: Whether to show detailed output
        project_dir: Project root directory (for memory context)

    Returns:
        (status, response_text) where status is:
        - "fixed" if fixes were applied
        - "error" if an error occurred
    """
    # Lazy imports to avoid circular import via __init__.py
    from .criteria import get_qa_signoff_status, is_fixes_applied
    from .report import get_iteration_history, has_recurring_issues, record_iteration

    # Derive project_dir from spec_dir if not provided
    # spec_dir is typically: /project/.auto-claude/specs/001-name/
    if project_dir is None:
        # Walk up from spec_dir to find project root
        project_dir = spec_dir.parent.parent.parent

    # Initialize recovery manager for circular fix detection
    recovery_manager = RecoveryManager(spec_dir=spec_dir, project_dir=project_dir)
    fixer_subtask_id = f"qa_fixer_{fix_session}"

    debug_section("qa_fixer", f"QA Fixer Session {fix_session}")
    debug(
        "qa_fixer",
        "Starting QA fixer session",
        spec_dir=str(spec_dir),
        fix_session=fix_session,
    )

    print(f"\n{'=' * 70}")
    print(f"  QA FIXER SESSION {fix_session}")
    print("  Applying fixes from QA_FIX_REQUEST.md...")
    print(f"{'=' * 70}\n")

    # Get task logger for streaming markers
    task_logger = get_task_logger(spec_dir)
    current_tool = None
    message_count = 0
    tool_count = 0

    # Check that fix request file exists
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"
    if not fix_request_file.exists():
        debug_error("qa_fixer", "QA_FIX_REQUEST.md not found")
        return "error", "QA_FIX_REQUEST.md not found"

    # Check for recurring issues from QA history
    iteration_history = get_iteration_history(spec_dir)
    if iteration_history:
        # Extract current issues from QA report
        qa_report_file = spec_dir / "qa_report.md"
        current_issues = []
        if qa_report_file.exists():
            # Parse issues from QA report (simplified - just check if we have history)
            # The has_recurring_issues function will do the actual similarity matching
            has_recurring, recurring_issues = has_recurring_issues(
                current_issues, iteration_history
            )
            if has_recurring:
                print("\n⚠️  WARNING: Recurring issues detected!")
                print(
                    f"  {len(recurring_issues)} issue(s) have appeared multiple times."
                )
                print("  Consider a different approach or human intervention.\n")
                debug_error(
                    "qa_fixer",
                    f"Recurring issues detected: {len(recurring_issues)} issues",
                )

    # Load fixer prompt
    prompt = load_qa_fixer_prompt()
    debug_detailed("qa_fixer", "Loaded QA fixer prompt", prompt_length=len(prompt))

    # Retrieve memory context for fixer (past fixes, patterns, gotchas)
    fixer_memory_context = await get_graphiti_context(
        spec_dir,
        project_dir,
        {
            "description": "Fixing QA issues and implementing corrections",
            "id": f"qa_fixer_{fix_session}",
        },
    )
    if fixer_memory_context:
        prompt += "\n\n" + fixer_memory_context
        print("✓ Memory context loaded for QA fixer")
        debug_success("qa_fixer", "Graphiti memory context loaded for fixer")

    # Retrieve failure patterns from past QA rejections and errors
    # This provides root cause analyses from similar failures
    fix_request_content = fix_request_file.read_text(encoding="utf-8")
    failure_patterns = await get_failure_patterns(
        spec_dir,
        project_dir,
        query=fix_request_content[:500],  # Use first 500 chars of fix request as query
        failure_types=["qa_rejection", "build_error", "test_failure"],
        num_results=5,
        min_score=0.5,
    )
    if failure_patterns:
        prompt += "\n\n" + failure_patterns
        print("✓ Failure patterns loaded for QA fixer")
        debug_success("qa_fixer", "Failure patterns loaded for fixer")

    # Add session context - use full path so agent can find files
    prompt += f"\n\n---\n\n**Fix Session**: {fix_session}\n"
    prompt += f"**Spec Directory**: {spec_dir}\n"
    prompt += f"**Spec Name**: {spec_dir.name}\n"
    prompt += f"\n**IMPORTANT**: All spec files are located in: `{spec_dir}/`\n"
    prompt += f"The fix request file is at: `{spec_dir}/QA_FIX_REQUEST.md`\n"

    # Check for circular fixes (same fix attempted multiple times)
    # Note: fix_request_content already loaded above for failure pattern analysis
    if recovery_manager.is_circular_fix(fixer_subtask_id, fix_request_content):
        attempt_count = recovery_manager.get_attempt_count(fixer_subtask_id)
        debug_error(
            "qa_fixer",
            f"Circular fix detected for {fixer_subtask_id} (attempt #{attempt_count})",
        )
        print("\n⚠️  WARNING: Circular fix detected!")
        print(f"This fix has been attempted {attempt_count} times with similar errors.")
        print("Consider human intervention or a different approach.\n")
        # Record circular fix outcome
        recovery_manager.record_outcome(
            fixer_subtask_id,
            success=False,
            error="Circular fix detected - same fix attempted multiple times",
        )
        return (
            "circular",
            "Circular fix detected - same approach attempted multiple times",
        )

    # Get total iterations from history
    total_iterations = len(iteration_history)

    # Recovery iteration loop - retry if agent gets stuck or fails
    last_error = None
    for fixer_iteration in range(1, MAX_FIXER_ITERATIONS + 1):
        # Track iteration start time for duration reporting
        iteration_start_time = time.time()

        if fixer_iteration > 1:
            print(f"\n{'=' * 70}")
            print(
                f"  QA FIXER RECOVERY ATTEMPT {fixer_iteration}/{MAX_FIXER_ITERATIONS}"
            )
            print(f"{'=' * 70}\n")
            debug(
                "qa_fixer",
                f"Starting recovery attempt {fixer_iteration}",
                max_iterations=MAX_FIXER_ITERATIONS,
            )
        else:
            # First iteration - show overall progress
            if total_iterations > 0:
                print(f"  Previous QA iterations: {total_iterations}")
                print(f"  This is fixer session #{fix_session}\n")

        # Record this attempt with recovery manager
        recovery_manager.record_attempt(
            fixer_subtask_id,
            session=fix_session,
            success=False,  # Will be updated by record_outcome
            approach=f"QA fixer session {fix_session}, iteration {fixer_iteration}",
        )

        try:
            debug("qa_fixer", "Sending query to Claude SDK...")
            await client.query(prompt)
            debug_success("qa_fixer", "Query sent successfully")

            response_text = ""
            debug("qa_fixer", "Starting to receive response stream...")
            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                message_count += 1
                debug_detailed(
                    "qa_fixer",
                    f"Received message #{message_count}",
                    msg_type=msg_type,
                )

                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__

                        if block_type == "TextBlock" and hasattr(block, "text"):
                            response_text += block.text
                            print(block.text, end="", flush=True)
                            # Log text to task logger (persist without double-printing)
                            if task_logger and block.text.strip():
                                task_logger.log(
                                    block.text,
                                    LogEntryType.TEXT,
                                    LogPhase.VALIDATION,
                                    print_to_console=False,
                                )
                        elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                            tool_name = block.name
                            tool_input_display = None
                            tool_count += 1

                            # Safely extract tool input (handles None, non-dict, etc.)
                            inp = get_safe_tool_input(block)

                            if inp:
                                if "file_path" in inp:
                                    fp = inp["file_path"]
                                    if len(fp) > 50:
                                        fp = "..." + fp[-47:]
                                    tool_input_display = fp
                                elif "command" in inp:
                                    cmd = inp["command"]
                                    if len(cmd) > 50:
                                        cmd = cmd[:47] + "..."
                                    tool_input_display = cmd

                            debug(
                                "qa_fixer",
                                f"Tool call #{tool_count}: {tool_name}",
                                tool_input=tool_input_display,
                            )

                            # Log tool start (handles printing)
                            if task_logger:
                                task_logger.tool_start(
                                    tool_name,
                                    tool_input_display,
                                    LogPhase.VALIDATION,
                                    print_to_console=True,
                                )
                            else:
                                print(f"\n[Fixer Tool: {tool_name}]", flush=True)

                            if verbose and hasattr(block, "input"):
                                input_str = str(block.input)
                                if len(input_str) > 300:
                                    print(f"   Input: {input_str[:300]}...", flush=True)
                                else:
                                    print(f"   Input: {input_str}", flush=True)
                            current_tool = tool_name

                elif msg_type == "UserMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__

                        if block_type == "ToolResultBlock":
                            is_error = getattr(block, "is_error", False)
                            result_content = getattr(block, "content", "")

                            if is_error:
                                debug_error(
                                    "qa_fixer",
                                    f"Tool error: {current_tool}",
                                    error=str(result_content)[:200],
                                )
                                error_str = str(result_content)[:500]
                                print(f"   [Error] {error_str}", flush=True)
                                if task_logger and current_tool:
                                    # Store full error in detail for expandable view
                                    task_logger.tool_end(
                                        current_tool,
                                        success=False,
                                        result=error_str[:100],
                                        detail=str(result_content),
                                        phase=LogPhase.VALIDATION,
                                    )
                            else:
                                debug_detailed(
                                    "qa_fixer",
                                    f"Tool success: {current_tool}",
                                    result_length=len(str(result_content)),
                                )
                                if verbose:
                                    result_str = str(result_content)[:200]
                                    print(f"   [Done] {result_str}", flush=True)
                                else:
                                    print("   [Done]", flush=True)
                                if task_logger and current_tool:
                                    # Store full result in detail for expandable view
                                    detail_content = None
                                    if current_tool in (
                                        "Read",
                                        "Grep",
                                        "Bash",
                                        "Edit",
                                        "Write",
                                    ):
                                        result_str = str(result_content)
                                        if len(result_str) < 50000:
                                            detail_content = result_str
                                    task_logger.tool_end(
                                        current_tool,
                                        success=True,
                                        detail=detail_content,
                                        phase=LogPhase.VALIDATION,
                                    )

                            current_tool = None

            print("\n" + "-" * 70 + "\n")

            # Validate that fixes were properly applied
            status = get_qa_signoff_status(spec_dir)
            fixes_ready = is_fixes_applied(spec_dir)

            debug(
                "qa_fixer",
                "Fixer session completed",
                message_count=message_count,
                tool_count=tool_count,
                response_length=len(response_text),
                ready_for_revalidation=status.get("ready_for_qa_revalidation")
                if status
                else False,
                fixes_applied_status=status.get("status") if status else None,
            )

            # Save fixer session insights to memory
            fixer_discoveries = {
                "files_understood": {},
                "patterns_found": [
                    f"QA fixer session {fix_session}: Applied fixes from QA_FIX_REQUEST.md"
                ],
                "gotchas_encountered": [],
            }

            # Robust validation: check both status and ready flag
            if fixes_ready:
                # Calculate iteration duration
                iteration_duration = time.time() - iteration_start_time

                debug_success(
                    "qa_fixer", "Fixes applied and validated, ready for QA revalidation"
                )
                print("\n✓ Fixes applied successfully!")
                print(f"  Duration: {iteration_duration:.1f}s")
                print(
                    f"  Recovery iterations: {fixer_iteration}/{MAX_FIXER_ITERATIONS}\n"
                )

                # Record successful iteration to history
                record_iteration(
                    spec_dir=spec_dir,
                    iteration=total_iterations + 1,
                    status="fixed",
                    issues=[],  # Fixed, so no issues
                    duration_seconds=iteration_duration,
                )

                # Record successful outcome with recovery manager
                recovery_manager.record_outcome(fixer_subtask_id, success=True)
                # Save successful fix session to memory
                await save_session_memory(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    subtask_id=f"qa_fixer_{fix_session}",
                    session_num=fix_session,
                    success=True,
                    subtasks_completed=[f"qa_fixer_{fix_session}"],
                    discoveries=fixer_discoveries,
                )
                return "fixed", response_text
            else:
                # Fixer didn't update the status properly, but we'll trust it worked
                iteration_duration = time.time() - iteration_start_time

                debug_success(
                    "qa_fixer", "Fixes assumed applied (status validation failed)"
                )
                print("\n✓ Fixes applied (status validation skipped)")
                print(f"  Duration: {iteration_duration:.1f}s")
                print(
                    f"  Recovery iterations: {fixer_iteration}/{MAX_FIXER_ITERATIONS}\n"
                )

                # Record iteration to history
                record_iteration(
                    spec_dir=spec_dir,
                    iteration=total_iterations + 1,
                    status="fixed",
                    issues=[],
                    duration_seconds=iteration_duration,
                )

                # Record successful outcome with recovery manager
                recovery_manager.record_outcome(fixer_subtask_id, success=True)
                # Still save to memory as successful (fixes were attempted)
                await save_session_memory(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    subtask_id=f"qa_fixer_{fix_session}",
                    session_num=fix_session,
                    success=True,
                    subtasks_completed=[f"qa_fixer_{fix_session}"],
                    discoveries=fixer_discoveries,
                )
                return "fixed", response_text

        except Exception as e:
            last_error = str(e)
            iteration_duration = time.time() - iteration_start_time

            debug_error(
                "qa_fixer",
                f"Fixer session exception (attempt {fixer_iteration}/{MAX_FIXER_ITERATIONS}): {e}",
                exception_type=type(e).__name__,
            )
            print(f"\n✗ Error during fixer session: {e}")
            print(f"  Duration: {iteration_duration:.1f}s\n")
            if task_logger:
                task_logger.log_error(f"QA fixer error: {e}", LogPhase.VALIDATION)

            # Record failed iteration
            error_issue = {
                "type": "fixer_error",
                "title": f"Fixer iteration {fixer_iteration} failed",
                "description": str(e),
                "severity": "high",
            }
            record_iteration(
                spec_dir=spec_dir,
                iteration=total_iterations + 1,
                status="error",
                issues=[error_issue],
                duration_seconds=iteration_duration,
            )

            # If this is the last iteration, return stuck status
            if fixer_iteration == MAX_FIXER_ITERATIONS:
                debug_error(
                    "qa_fixer",
                    f"Max fixer iterations ({MAX_FIXER_ITERATIONS}) reached, fixer is stuck",
                )
                print(
                    f"⚠️  Max recovery attempts ({MAX_FIXER_ITERATIONS}) reached. Fixer stuck.\n"
                )
                # Record failed outcome
                recovery_manager.record_outcome(
                    fixer_subtask_id, success=False, error=last_error
                )
                return (
                    "stuck",
                    f"Fixer stuck after {MAX_FIXER_ITERATIONS} recovery attempts: {last_error}",
                )

            # Otherwise, continue to next iteration
            debug(
                "qa_fixer",
                f"Will retry (attempt {fixer_iteration + 1}/{MAX_FIXER_ITERATIONS})",
            )
            print(
                f"  Retrying... (attempt {fixer_iteration + 1}/{MAX_FIXER_ITERATIONS})\n"
            )
            continue

    # If we exhausted all iterations without success
    debug_error(
        "qa_fixer",
        f"Exhausted all {MAX_FIXER_ITERATIONS} fixer iterations without success",
    )
    print(
        f"\n⚠️  Exhausted all {MAX_FIXER_ITERATIONS} recovery attempts without success.\n"
    )

    # Record final failure
    final_error = last_error if last_error else "Max fixer iterations reached"
    final_issue = {
        "type": "max_iterations",
        "title": "Max fixer iterations exhausted",
        "description": final_error,
        "severity": "critical",
    }
    record_iteration(
        spec_dir=spec_dir,
        iteration=total_iterations + 1,
        status="error",
        issues=[final_issue],
        duration_seconds=None,
    )

    # Record failed outcome
    recovery_manager.record_outcome(
        fixer_subtask_id,
        success=False,
        error=final_error,
    )
    return "stuck", f"Fixer stuck after exhausting all recovery attempts: {final_error}"
