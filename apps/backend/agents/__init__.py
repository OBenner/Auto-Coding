"""
Agents Module
=============

Modular agent system for autonomous coding.

This module provides:
- run_autonomous_agent: Main coder agent loop
- run_followup_planner: Follow-up planner for completed specs
- Memory management (Graphiti + file-based fallback)
- Session management and post-processing
- Utility functions for git and plan management

Uses lazy imports to avoid circular dependencies.
"""

# Explicit imports required by CodeQL static analysis
# (CodeQL doesn't recognize __getattr__ dynamic exports)
from .documentation_generator import run_documentation_generator_session
from .utils import sync_spec_to_source

__all__ = [
    "run_documentation_generator_session",
    "sync_spec_to_source",
]


def __getattr__(name):
    """Lazy imports to avoid circular dependencies."""
    if name in ("AUTO_CONTINUE_DELAY_SECONDS", "HUMAN_INTERVENTION_FILE"):
        from .base import AUTO_CONTINUE_DELAY_SECONDS, HUMAN_INTERVENTION_FILE

        return locals()[name]
    elif name == "run_autonomous_agent":
        from .coder import run_autonomous_agent

        return run_autonomous_agent
    elif name in (
        "debug_memory_system_status",
        "get_graphiti_context",
        "save_session_memory",
        "save_session_to_graphiti",
    ):
        from .memory_manager import (
            debug_memory_system_status,
            get_graphiti_context,
            save_session_memory,
            save_session_to_graphiti,
        )

        return locals()[name]
    elif name == "run_followup_planner":
        from .planner import run_followup_planner

        return run_followup_planner
    elif name == "run_documentation_generator_session":
        from .documentation_generator import run_documentation_generator_session

        return run_documentation_generator_session
    elif name in ("post_session_processing", "run_agent_session"):
        from .session import post_session_processing, run_agent_session

        return locals()[name]
    elif name in (
        "find_phase_for_subtask",
        "find_subtask_in_plan",
        "get_commit_count",
        "get_latest_commit",
        "load_implementation_plan",
        "sync_spec_to_source",
    ):
        from .utils import (
            find_phase_for_subtask,
            find_subtask_in_plan,
            get_commit_count,
            get_latest_commit,
            load_implementation_plan,
            sync_spec_to_source,
        )

        return locals()[name]
    raise AttributeError(f"module 'agents' has no attribute '{name}'")
