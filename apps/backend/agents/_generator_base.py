"""
Shared Generator Session Base
==============================

Common boilerplate for test generator agent sessions (pytest, vitest, e2e).
Provides session setup, client creation, agent execution, and result collection.
"""

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

logger = logging.getLogger(__name__)


async def run_generator_session(
    *,
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    session_title: str,
    session_description: str,
    prompt_name: str,
    agent_type: str,
    session_name: str,
    starting_message: str,
    log_phase: LogPhase,
    log_summary: str,
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run a generator agent session with common boilerplate.

    Handles: task logger init, session header, model/thinking setup,
    prompt loading, client creation, agent execution, and error handling.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results
        session_title: Title for the session header box (e.g. "VITEST GENERATOR SESSION")
        session_description: Description shown in the header box
        prompt_name: Name of the agent prompt to load
        agent_type: Agent type for create_client
        session_name: Name for the agent session
        starting_message: Starting message for the agent
        log_phase: LogPhase to use for task logger
        log_summary: Summary line for task logger start
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with success status and error (if any).
        Does NOT include generated_files - caller handles file scanning.
    """
    task_logger = get_task_logger(spec_dir)

    # Print session header
    content = [
        bold(f"{icon(Icons.SPARKLES)} {session_title}"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted(session_description),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Determine model and thinking budget
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
        task_logger.start_phase(log_phase, log_summary)
        task_logger.log_info(log_summary)

    # Load the agent prompt
    try:
        prompt = get_agent_prompt(prompt_name)
    except Exception as e:
        error_msg = f"Failed to load {prompt_name} prompt: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_error(error_msg)
        return {"success": False, "error": error_msg}

    # Create SDK client
    try:
        client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            agent_type=agent_type,
            max_thinking_tokens=max_thinking_tokens,
        )
    except Exception as e:
        error_msg = f"Failed to create Claude SDK client: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_error(error_msg)
        return {"success": False, "error": error_msg}

    # Run the agent session.
    #
    # ClaudeSDKClient has no `create_agent_session` method. Agent turns are
    # driven by run_agent_session() (agents/session.py) — the same helper the
    # planner/coder/qa phases use. It sends the message, streams the response,
    # and returns (status, response_text, usage_metadata, decision_tracker).
    # The client must be connected first, so we drive it inside `async with`.
    #
    # The agent-specific role prompt is delivered as the leading message (the
    # SDK client only carries the generic base system prompt), matching how the
    # planner / performance_profiler sessions pass their prompts.
    from .session import run_agent_session

    print_status(
        f"Running {session_title.title().replace('Session', 'Agent')}...", "progress"
    )
    session_message = f"{prompt}\n\n{starting_message}"
    try:
        async with client:
            status, response_text, _usage, _decisions = await run_agent_session(
                client=client,
                message=session_message,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=log_phase,
            )

        if status == "error":
            error_msg = f"{session_name} failed: {response_text}"
            logger.error(error_msg)
            if task_logger:
                task_logger.log_error(error_msg)
            return {"success": False, "error": error_msg}

        if verbose:
            logger.info(f"{session_name} response: {response_text}")

        if task_logger:
            task_logger.log_success(f"{session_name} completed")

    except Exception as e:
        error_msg = f"{session_name} failed: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_error(error_msg)
        return {"success": False, "error": error_msg}

    return {"success": True, "error": None}


def log_generator_result(
    *,
    spec_dir: Path,
    test_files: list,
    validation_success: bool,
    framework: str,
) -> None:
    """Log generator results to task logger."""
    task_logger = get_task_logger(spec_dir)
    if not task_logger:
        return

    if validation_success:
        task_logger.log_success(
            f"Generated and validated {len(test_files)} {framework} test files"
        )
    else:
        task_logger.log_entry(
            LogEntryType.WARNING,
            f"Generated {len(test_files)} test files but validation failed",
        )
