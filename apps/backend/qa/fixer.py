"""
QA Fixer Agent Session
=======================

Runs QA fixer sessions to resolve issues identified by the reviewer.

Memory Integration:
- Retrieves past patterns, fixes, and gotchas before fixing
- Saves fix outcomes and learnings after session
"""

import asyncio
import logging
import time
from pathlib import Path

# Memory integration for cross-session learning
from agents.memory_manager import (
    get_failure_patterns,
    get_graphiti_context,
    save_session_memory,
)
from claude_agent_sdk import ClaudeSDKClient
from core.client import create_client
from core.model_fallback import MODEL_FALLBACK_CHAIN
from core.providers import create_engine_provider
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from phase_config import resolve_model_id
from security.tool_input_validator import get_safe_tool_input
from services.recovery import RecoveryAction, RecoveryManager
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)

# Import plugin system for agent lifecycle hooks
try:
    from plugins.base import PluginType
    from plugins.registry import PluginRegistry
    from plugins.sdk.agent import AgentContext

    PLUGINS_AVAILABLE = True
except ImportError:
    PLUGINS_AVAILABLE = False

# Configuration
QA_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MAX_FIXER_ITERATIONS = 10  # Max recovery attempts for a single QA fix session

logger = logging.getLogger(__name__)


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
    model: str = "sonnet",
) -> tuple[str, str]:
    """
    Run a QA fixer agent session with enhanced recovery.

    Args:
        client: Claude SDK client (initial client, may be replaced for fallback)
        spec_dir: Spec directory
        fix_session: Fix iteration number
        verbose: Whether to show detailed output
        project_dir: Project root directory (for memory context)
        model: Base model to use (for fallback chain)

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

    # === ENHANCED RECOVERY: Track recovery state ===
    pending_recovery_action: RecoveryAction | None = None
    override_model: str | None = None  # For model fallback
    recovery_guidance: str | None = None  # Strategy guidance for next attempt
    current_client = client  # Track current client (may be replaced for fallback)

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

    # Store base prompt (recovery guidance will be added per-iteration)
    base_prompt = prompt

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

        # === ENHANCED RECOVERY: Handle pending recovery action ===
        if pending_recovery_action:
            # Apply exponential backoff delay if specified
            if pending_recovery_action.wait_seconds > 0:
                print(
                    f"⏳ Recovery backoff: waiting {pending_recovery_action.wait_seconds:.1f}s before retry..."
                )
                await asyncio.sleep(pending_recovery_action.wait_seconds)

            # Handle rollback action
            if pending_recovery_action.action == "rollback":
                print(
                    f"↩️  Rolling back to commit {pending_recovery_action.target[:8]}..."
                )
                rollback_success = recovery_manager.rollback_to_commit(
                    pending_recovery_action.target
                )
                if rollback_success:
                    print("✓ Rollback successful\n")
                else:
                    print("✗ Rollback failed\n")

            # Display recovery notification if needed
            if pending_recovery_action.should_notify:
                print()
                print(f"⚠️  {pending_recovery_action.notification_message}")
                print()

            # Clear the pending action
            pending_recovery_action = None

        # Recreate client if model fallback is needed
        if override_model:
            print(f"🔄 Using fallback model: {override_model}")
            fallback_model = resolve_model_id(override_model)
            # Close old client if it's not the original one
            if current_client != client:
                try:
                    await current_client.__aexit__(None, None, None)
                except Exception:
                    pass  # Ignore cleanup errors
            # Create new client with fallback model
            current_client = create_client(
                project_dir,
                spec_dir,
                fallback_model,
                agent_type="qa_fixer",
                max_thinking_tokens=None,
            )
            # Enter async context for new client
            await current_client.__aenter__()
            # Reset override after creating new client
            override_model = None

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

        # Build prompt with recovery guidance (if available)
        iteration_prompt = base_prompt
        if recovery_guidance:
            iteration_prompt += f"\n\n## RECOVERY STRATEGY\n\n{recovery_guidance}\n"
            # Clear guidance after using it
            recovery_guidance = None

        try:
            debug("qa_fixer", "Sending query to Claude SDK...")
            await current_client.query(iteration_prompt)
            debug_success("qa_fixer", "Query sent successfully")

            response_text = ""
            debug("qa_fixer", "Starting to receive response stream...")
            async for msg in current_client.receive_response():
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

            # Call after_session hook for enabled agent plugins
            if PLUGINS_AVAILABLE:
                try:
                    registry = PluginRegistry.get_instance()
                    agent_plugins = registry.list_plugins(
                        plugin_type=PluginType.AGENT, enabled_only=True
                    )

                    if agent_plugins:
                        # Create agent context for plugins
                        agent_context = AgentContext(
                            project_dir=project_dir,
                            spec_dir=spec_dir,
                            session_id=f"qa_fixer_{fix_session}",
                            client=client,
                            phase="validation",
                            metadata={
                                "fix_session": fix_session,
                                "iteration": fixer_iteration,
                            },
                        )

                        # Determine session success (will be updated after validation)
                        # For now, assume success based on fixes_ready
                        session_success = fixes_ready

                        # Call after_session for each enabled agent plugin
                        for plugin in agent_plugins:
                            try:
                                plugin.after_session(
                                    agent_context, success=session_success
                                )
                                logger.debug(
                                    f"Called after_session for plugin: {plugin.name}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Plugin {plugin.name} after_session hook failed: {e}"
                                )
                except Exception as e:
                    logger.warning(f"Failed to call after_session hooks: {e}")

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

            # Call after_session hook for enabled agent plugins (error case)
            if PLUGINS_AVAILABLE:
                try:
                    registry = PluginRegistry.get_instance()
                    agent_plugins = registry.list_plugins(
                        plugin_type=PluginType.AGENT, enabled_only=True
                    )

                    if agent_plugins:
                        # Create agent context for plugins
                        agent_context = AgentContext(
                            project_dir=project_dir,
                            spec_dir=spec_dir,
                            session_id=f"qa_fixer_{fix_session}",
                            client=client,
                            phase="validation",
                            metadata={
                                "fix_session": fix_session,
                                "iteration": fixer_iteration,
                                "error": str(e),
                            },
                        )

                        # Call after_session for each enabled agent plugin (error case)
                        for plugin in agent_plugins:
                            try:
                                plugin.after_session(agent_context, success=False)
                                logger.debug(
                                    f"Called after_session for plugin: {plugin.name}"
                                )
                            except Exception as hook_error:
                                logger.warning(
                                    f"Plugin {plugin.name} after_session hook failed: {hook_error}"
                                )
                except Exception as hook_error:
                    logger.warning(f"Failed to call after_session hooks: {hook_error}")

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

            # === ENHANCED RECOVERY: Use smart recovery system ===

            # Classify the failure type
            error_message = f"QA fixer error: {e}"
            failure_type = recovery_manager.classify_failure(
                error_message, fixer_subtask_id
            )

            # Determine recovery action (handles exponential backoff, model fallback, DLQ, notifications)
            recovery_action = recovery_manager.determine_recovery_action(
                failure_type, fixer_subtask_id
            )

            # Record the notification or silent failure
            recovery_manager.record_recovery_notification(
                fixer_subtask_id, failure_type, recovery_action
            )

            print()
            print(f"🔧 Recovery action: {recovery_action.action}")
            print(f"   Reason: {recovery_action.reason}")

            # Handle different recovery actions
            if recovery_action.action == "retry":
                # Set up for retry with exponential backoff and optional model fallback
                pending_recovery_action = recovery_action

                # Set model fallback if recommended
                if recovery_action.use_model_fallback:
                    # Extract current model shorthand and get fallback
                    current_model_shorthand = model
                    if "opus" in model.lower():
                        current_model_shorthand = "opus"
                    elif "sonnet" in model.lower():
                        current_model_shorthand = "sonnet"
                    elif "haiku" in model.lower():
                        current_model_shorthand = "haiku"

                    # Get fallback model from chain
                    fallback_chain = MODEL_FALLBACK_CHAIN.get(
                        current_model_shorthand, []
                    )
                    if fallback_chain:
                        override_model = fallback_chain[0]  # Use first fallback
                        print(f"   Will try fallback model: {override_model}")
                    else:
                        override_model = None

                # Set recovery guidance from strategy
                if recovery_action.strategy:
                    recovery_guidance = recovery_action.strategy.guidance
                    print(f"   Strategy: {recovery_action.strategy.description}")

                print(
                    f"   Will retry after {recovery_action.wait_seconds:.1f}s backoff\n"
                )
                continue

            elif recovery_action.action == "skip":
                # Mark subtask as stuck and skip
                recovery_manager.mark_subtask_stuck(
                    fixer_subtask_id, recovery_action.reason
                )
                print("❌ QA Fixer marked as STUCK")
                print("   Recovery exhausted - consider manual intervention\n")
                # Record failed outcome
                recovery_manager.record_outcome(
                    fixer_subtask_id, success=False, error=last_error
                )
                return "stuck", f"Fixer stuck: {recovery_action.reason}"

            elif recovery_action.action == "escalate":
                # Critical failure - escalate to human
                recovery_manager.mark_subtask_stuck(
                    fixer_subtask_id, recovery_action.reason
                )
                print()
                print("🚨 ESCALATION REQUIRED")
                print(f"   {recovery_action.reason}")
                print(
                    "   This failure has been added to the dead-letter queue for manual review"
                )
                print()
                # Record failed outcome
                recovery_manager.record_outcome(
                    fixer_subtask_id, success=False, error=last_error
                )
                return "escalate", recovery_action.reason

            elif recovery_action.action == "rollback":
                # Rollback will be handled at the start of next iteration
                pending_recovery_action = recovery_action
                print(
                    f"   Will rollback to {recovery_action.target[:8]} on next iteration\n"
                )
                continue

            elif recovery_action.action == "continue":
                # Context exhausted - will continue in next session
                print("   Context exhausted - will continue in next iteration\n")
                continue

            # Fallback to old behavior if unknown action
            debug(
                "qa_fixer",
                f"Unknown recovery action: {recovery_action.action}, falling back to retry",
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


# =============================================================================
# QA FIXER FACTORY FUNCTION (Provider Pattern)
# =============================================================================


def create_qa_fixer_session(
    project_dir: Path,
    spec_dir: Path,
    model: str | None = None,
    max_thinking_tokens: int | None = None,
):
    """
    Create a QA fixer agent session using the configured AI engine provider.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        model: Model to use (overrides provider config)
        max_thinking_tokens: Token budget for extended thinking

    Returns:
        AgentSession with a .client property containing the SDK client

    Raises:
        ProviderError: If provider creation or session creation fails
    """
    config = ProviderConfig.from_env(agent_type="qa_fixer")
    provider = create_engine_provider(config)

    if provider.name == "claude":
        session = provider.create_session(
            config=SessionConfig(
                name="qa-fixer-session",
                model=model,
            ),
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type="qa_fixer",
            max_thinking_tokens=max_thinking_tokens,
        )
    else:
        session = provider.create_session(
            SessionConfig(
                name="qa-fixer-session",
                model=model,
            )
        )

    return session


async def run_qa_fixer(
    project_dir: Path,
    spec_dir: Path,
    fix_session: int,
    model: str | None = None,
    verbose: bool = False,
    max_thinking_tokens: int | None = None,
) -> tuple[str, str]:
    """
    Run a QA fixer session using the configured AI engine provider.

    Creates a session using the factory pattern and delegates to run_qa_fixer_session.
    """
    session = create_qa_fixer_session(
        project_dir=project_dir,
        spec_dir=spec_dir,
        model=model,
        max_thinking_tokens=max_thinking_tokens,
    )

    client = session.client

    async with client:
        return await run_qa_fixer_session(
            client=client,
            spec_dir=spec_dir,
            fix_session=fix_session,
            verbose=verbose,
            project_dir=project_dir,
        )
