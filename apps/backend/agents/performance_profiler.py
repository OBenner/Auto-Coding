"""
Performance Profiler Agent Module
==================================

Specialized agent for analyzing and optimizing application performance.
Identifies bottlenecks, profiles runtime and memory usage, suggests optimizations,
and can implement performance improvements autonomously.
"""

import logging
from pathlib import Path

from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget
from phase_event import ExecutionPhase, emit_phase
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

from .session import run_agent_session, save_token_stats

logger = logging.getLogger(__name__)


async def run_performance_profiler(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    verbose: bool = False,
) -> bool:
    """
    Run the performance profiler agent to analyze and optimize code performance.

    The profiler agent will:
    - Profile runtime performance and memory usage
    - Identify bottlenecks and optimization opportunities
    - Suggest specific optimizations
    - Implement optimizations with user approval
    - Provide before/after performance comparisons
    - Track performance trends over time

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        model: Claude model to use
        verbose: Whether to show detailed output

    Returns:
        bool: True if profiling completed successfully
    """
    from prompts_pkg import get_performance_profiler_prompt

    # Initialize status manager for ccstatusline
    status_manager = StatusManager(project_dir)
    status_manager.set_active(spec_dir.name, BuildState.BUILDING)
    emit_phase(ExecutionPhase.PERFORMANCE_PROFILING, "Profiling performance")

    # Initialize task logger for persistent logging
    task_logger = get_task_logger(spec_dir)

    # Show header
    content = [
        bold(f"{icon(Icons.GEAR)} PERFORMANCE PROFILER SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Analyzing and optimizing application performance."),
        "",
        muted("The agent will profile your code and suggest optimizations."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Start performance profiling phase in task logger
    if task_logger:
        task_logger.start_phase(
            LogPhase.CODING, "Starting performance profiling session..."
        )
        task_logger.set_session(1)

    # Create client with phase-specific model and thinking budget
    # Respects task_metadata.json configuration when no CLI override
    profiler_model = get_phase_model(spec_dir, "performance_profiling", model)
    profiler_thinking_budget = get_phase_thinking_budget(
        spec_dir, "performance_profiling"
    )
    client = create_client(
        project_dir,
        spec_dir,
        profiler_model,
        agent_type="performance_profiler",
        max_thinking_tokens=profiler_thinking_budget,
    )

    # Generate performance profiler prompt
    prompt = get_performance_profiler_prompt(spec_dir)

    print_status("Running performance profiler...", "progress")
    print()

    try:
        # Run single profiling session
        async with client:
            status, _, usage_metadata = await run_agent_session(
                client, prompt, spec_dir, verbose, phase=LogPhase.CODING
            )

        # Save token statistics for performance profiling phase
        if usage_metadata:
            try:
                input_tokens = usage_metadata.get("input_tokens", 0)
                output_tokens = usage_metadata.get("output_tokens", 0)

                if (
                    "input_tokens" not in usage_metadata
                    or "output_tokens" not in usage_metadata
                ):
                    logger.debug(
                        "Usage metadata missing expected token keys; defaulting to 0s: %s",
                        usage_metadata,
                    )

                saved = save_token_stats(
                    spec_dir,
                    "performance_profiling",
                    input_tokens,
                    output_tokens,
                )
                if saved:
                    logger.debug(
                        "Performance profiling token stats saved: %d in, %d out",
                        input_tokens,
                        output_tokens,
                    )
            except Exception as e:
                logger.warning(
                    "Failed to save performance profiling token stats: %s", e
                )

        # End profiling phase in task logger
        if task_logger:
            task_logger.end_phase(
                LogPhase.CODING,
                success=(status != "error"),
                message="Performance profiling session completed",
            )

        if status == "error":
            print()
            print_status("Performance profiling failed", "error")
            status_manager.update(state=BuildState.ERROR)
            return False

        # Success
        print()
        content = [
            bold(f"{icon(Icons.SUCCESS)} PERFORMANCE PROFILING COMPLETE"),
            "",
            muted("Performance analysis and optimizations completed."),
            muted("Review the profiling results and optimization suggestions."),
        ]
        print(box(content, width=70, style="heavy"))
        print()
        status_manager.update(state=BuildState.COMPLETE)
        return True

    except Exception as e:
        print()
        print_status(f"Performance profiling error: {e}", "error")
        if task_logger:
            task_logger.log_error(f"Performance profiling error: {e}", LogPhase.CODING)
        status_manager.update(state=BuildState.ERROR)
        return False
