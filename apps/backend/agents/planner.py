"""
Planner Agent Module
====================

Handles follow-up planner sessions for adding new subtasks to completed specs.
"""

import logging
from pathlib import Path

from analysis.prevention_scanner import PreventionScanner
from core.providers import create_engine_provider
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig, get_provider_config
from implementation_plan import ImplementationPlan
from phase_config import get_phase_model, get_phase_thinking_budget
from phase_event import ExecutionPhase, emit_phase
from prompts_pkg.prompts import get_followup_planner_prompt
from task_logger import (
    LogPhase,
    get_task_logger,
)
from ui import (
    BuildState,
    Icons,
    StatusManager,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_status,
)

from .runtime import (
    RuntimeCapabilityError,
    RuntimeRequirements,
    create_runtime_session,
    get_runtime_mode,
    run_runtime_session,
)
from .session import run_agent_session, save_token_stats

# Import plugin system for agent lifecycle hooks
try:
    from plugins.base import PluginType
    from plugins.registry import PluginRegistry
    from plugins.sdk.agent import AgentContext

    PLUGINS_AVAILABLE = True
except ImportError:
    PLUGINS_AVAILABLE = False

logger = logging.getLogger(__name__)


def create_planner_session(
    project_dir: Path,
    spec_dir: Path,
    model: str | None = None,
    max_thinking_tokens: int | None = None,
):
    """
    Create a planner agent session using the configured AI engine provider.

    This function is used by both the follow-up planner and verification tests.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        model: Model to use (overrides provider config)
        max_thinking_tokens: Token budget for extended thinking

    Returns:
        AgentSession for the configured provider

    Raises:
        ProviderError: If provider creation or session creation fails
    """
    # Create provider from environment configuration (with per-agent overrides)
    config = ProviderConfig.from_env(agent_type="planner")
    provider = create_engine_provider(config)

    # For Claude provider, pass provider-specific kwargs
    if provider.name == "claude":
        session = provider.create_session(
            config=SessionConfig(
                name="planner-session",
                model=model,
            ),
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type="planner",
            max_thinking_tokens=max_thinking_tokens,
        )
    else:
        session = provider.create_session(
            SessionConfig(
                name="planner-session",
                model=model,
            )
        )

    return session


async def run_followup_planner(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    verbose: bool = False,
) -> bool:
    """
    Run the follow-up planner to add new subtasks to a completed spec.

    This is a simplified version of run_autonomous_agent that:
    1. Creates a client
    2. Loads the followup planner prompt
    3. Runs a single planning session
    4. Returns after the plan is updated (doesn't enter coding loop)

    The planner agent will:
    - Read FOLLOWUP_REQUEST.md for the new task
    - Read the existing implementation_plan.json
    - Add new phase(s) with pending subtasks
    - Update the plan status back to in_progress

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the completed spec
        model: Claude model to use
        verbose: Whether to show detailed output

    Returns:
        bool: True if planning completed successfully
    """
    # Initialize status manager for ccstatusline
    status_manager = StatusManager(project_dir)
    status_manager.set_active(spec_dir.name, BuildState.PLANNING)
    emit_phase(ExecutionPhase.PLANNING, "Follow-up planning")

    # Initialize task logger for persistent logging
    task_logger = get_task_logger(spec_dir)

    # Show header
    content = [
        bold(f"{icon(Icons.GEAR)} FOLLOW-UP PLANNER SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Adding follow-up work to completed spec."),
        "",
        muted("The agent will read your FOLLOWUP_REQUEST.md and add new subtasks."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Start planning phase in task logger
    if task_logger:
        task_logger.start_phase(LogPhase.PLANNING, "Starting follow-up planning...")
        task_logger.set_session(1)

    # Create client with phase-specific model and thinking budget
    # Respects task_metadata.json configuration when no CLI override
    planning_model = get_phase_model(spec_dir, "planning", model)
    planning_thinking_budget = get_phase_thinking_budget(spec_dir, "planning")

    # Create session using provider factory
    session = create_planner_session(
        project_dir,
        spec_dir,
        model=planning_model,
        max_thinking_tokens=planning_thinking_budget,
    )

    provider_name = getattr(session, "provider_name", None)
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise ValueError(
            "Planner session missing provider_name; provider-backed sessions must "
            "declare their runtime provider"
        )
    runtime_session = create_runtime_session(
        provider_name=provider_name,
        agent_session=session,
        claude_session_runner=run_agent_session,
        runtime_mode=get_runtime_mode("planner"),
        project_dir=project_dir,
    )
    client = runtime_session.context_client

    # Generate follow-up planner prompt
    prompt = get_followup_planner_prompt(spec_dir)

    # Run prevention scanner before planning
    print_status("Running prevention scanner...", "progress")
    try:
        scanner = PreventionScanner()
        scan_result = scanner.scan(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        # Log scan summary
        if task_logger:
            summary = scanner.format_summary(scan_result)
            task_logger.log_message(summary, LogPhase.PLANNING)

        if scan_result.should_block:
            logger.warning("Prevention scanner found blocking issues")
            print_status(
                f"⚠️  Critical issues found: {scan_result.summary.get('critical', 0)} critical, "
                f"{scan_result.summary.get('high', 0)} high",
                "warning",
            )
        elif scan_result.should_warn:
            logger.info("Prevention scanner found warnings")
            print_status(
                f"Note: {scan_result.summary.get('total_issues', 0)} issues detected "
                f"(see prevention_scan.json)",
                "info",
            )
        else:
            logger.info("Prevention scanner found no critical issues")
            print_status("✅ No critical issues detected", "success")
    except Exception as e:
        logger.warning(f"Prevention scanner failed: {e}")
        print_status(f"Prevention scanner warning: {e}", "warning")
        # Continue with planning even if scanner fails

    print()
    print_status("Running follow-up planner...", "progress")
    print()

    try:
        # Run single planning session
        result = await run_runtime_session(
            runtime_session,
            prompt,
            spec_dir,
            verbose,
            phase=LogPhase.PLANNING,
            requirements=RuntimeRequirements.planner(),
        )
        status = result.status
        response = result.response_text
        usage_metadata = result.usage_metadata

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
                        session_id=f"followup-planner-{spec_dir.name}",
                        client=client,
                        phase="planning",
                        metadata={"status": status},
                    )

                    # Call after_session for each enabled agent plugin
                    session_success = status != "error"
                    for plugin in agent_plugins:
                        try:
                            plugin.after_session(agent_context, success=session_success)
                            logger.debug(
                                f"Called after_session for plugin: {plugin.name}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Plugin {plugin.name} after_session hook failed: {e}"
                            )
            except Exception as e:
                logger.warning(f"Failed to call after_session hooks: {e}")

        # Save token statistics for planning phase
        if usage_metadata:
            try:
                saved = save_token_stats(
                    spec_dir,
                    "planning",
                    usage_metadata["input_tokens"],
                    usage_metadata["output_tokens"],
                )
                if saved:
                    logger.debug(
                        f"Planning phase token stats saved: {usage_metadata['input_tokens']} in, "
                        f"{usage_metadata['output_tokens']} out"
                    )
            except Exception as e:
                logger.warning(f"Failed to save planning phase token stats: {e}")

        # End planning phase in task logger
        if task_logger:
            task_logger.end_phase(
                LogPhase.PLANNING,
                success=(status != "error"),
                message="Follow-up planning session completed",
            )

        if status == "error":
            print()
            print_status("Follow-up planning failed", "error")
            status_manager.update(state=BuildState.ERROR)
            return False

        # Verify the plan was updated (should have pending subtasks now)
        plan_file = spec_dir / "implementation_plan.json"
        if plan_file.exists():
            plan = ImplementationPlan.load(plan_file)

            # Capture and persist provider configuration
            provider_config = get_provider_config()
            if provider_config:
                plan.provider_config = {
                    "provider": provider_config.provider,
                    "model": provider_config.get_model_for_provider(),
                }

            # Check if there are any pending subtasks
            all_subtasks = [c for p in plan.phases for c in p.subtasks]
            pending_subtasks = [c for c in all_subtasks if c.status.value == "pending"]

            if pending_subtasks:
                # Reset the plan status to in_progress (in case planner didn't)
                plan.reset_for_followup()
                await plan.async_save(plan_file)

                print()
                content = [
                    bold(f"{icon(Icons.SUCCESS)} FOLLOW-UP PLANNING COMPLETE"),
                    "",
                    f"New pending subtasks: {highlight(str(len(pending_subtasks)))}",
                    f"Total subtasks: {len(all_subtasks)}",
                    "",
                    muted("Next steps:"),
                    f"  Run: {highlight(f'python auto-claude/run.py --spec {spec_dir.name}')}",
                ]
                print(box(content, width=70, style="heavy"))
                print()
                status_manager.update(state=BuildState.PAUSED)
                return True
            else:
                print()
                print_status(
                    "Warning: No pending subtasks found after planning", "warning"
                )
                print(muted("The planner may not have added new subtasks."))
                print(muted("Check implementation_plan.json manually."))
                status_manager.update(state=BuildState.PAUSED)
                return False
        else:
            print()
            print_status(
                "Error: implementation_plan.json not found after planning", "error"
            )
            status_manager.update(state=BuildState.ERROR)
            return False

    except RuntimeCapabilityError as e:
        print()
        print_status(str(e), "error")
        if task_logger:
            task_logger.log_error(str(e), LogPhase.PLANNING)
        status_manager.update(state=BuildState.ERROR)
        return False

    except Exception as e:
        print()
        print_status(f"Follow-up planning error: {e}", "error")
        if task_logger:
            task_logger.log_error(f"Follow-up planning error: {e}", LogPhase.PLANNING)
        status_manager.update(state=BuildState.ERROR)
        return False
