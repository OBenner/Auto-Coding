"""
Agents Module
=============

Modular agent system for autonomous coding.

This module provides:
- run_autonomous_agent: Main coder agent loop
- run_followup_planner: Follow-up planner for completed specs
- run_code_review_session: Code review agent for security/performance analysis
- Memory management (Graphiti + file-based fallback)
- Session management and post-processing
- Utility functions for git and plan management

Uses lazy imports via __getattr__ to avoid circular dependencies.
Explicit re-exports below satisfy CodeQL static analysis.
"""

from importlib import import_module

__all__ = [
    # Main API
    "run_autonomous_agent",
    "run_followup_planner",
    "run_migration_assistant",
    "run_performance_profiler",
    "run_code_review_session",
    "run_documentation_generator_session",
    # Memory
    "debug_memory_system_status",
    "get_graphiti_context",
    "save_session_memory",
    "save_session_to_graphiti",
    # Session
    "run_agent_session",
    "post_session_processing",
    # Utils
    "get_latest_commit",
    "get_commit_count",
    "load_implementation_plan",
    "find_subtask_in_plan",
    "find_phase_for_subtask",
    "sync_spec_to_source",
    # Workspace
    "load_workspace_context",
    "get_workspace_project_dirs",
]

_LAZY_EXPORTS = {
    "run_code_review_session": (".code_reviewer", "run_code_review_session"),
    "run_autonomous_agent": (".coder", "run_autonomous_agent"),
    "run_documentation_generator_session": (
        ".documentation_generator",
        "run_documentation_generator_session",
    ),
    "debug_memory_system_status": (
        ".memory_manager",
        "debug_memory_system_status",
    ),
    "get_graphiti_context": (".memory_manager", "get_graphiti_context"),
    "save_session_memory": (".memory_manager", "save_session_memory"),
    "save_session_to_graphiti": (".memory_manager", "save_session_to_graphiti"),
    "run_migration_assistant": (".migration_assistant", "run_migration_assistant"),
    "run_performance_profiler": (
        ".performance_profiler",
        "run_performance_profiler",
    ),
    "run_followup_planner": (".planner", "run_followup_planner"),
    "post_session_processing": (".session", "post_session_processing"),
    "run_agent_session": (".session", "run_agent_session"),
    "find_phase_for_subtask": (".utils", "find_phase_for_subtask"),
    "find_subtask_in_plan": (".utils", "find_subtask_in_plan"),
    "get_commit_count": (".utils", "get_commit_count"),
    "get_latest_commit": (".utils", "get_latest_commit"),
    "get_workspace_project_dirs": (".utils", "get_workspace_project_dirs"),
    "load_implementation_plan": (".utils", "load_implementation_plan"),
    "load_workspace_context": (".utils", "load_workspace_context"),
    "sync_spec_to_source": (".utils", "sync_spec_to_source"),
}


def __getattr__(name):
    """Lazy imports for names that may need optional runtime dependencies."""
    if name in ("AUTO_CONTINUE_DELAY_SECONDS", "HUMAN_INTERVENTION_FILE"):
        from .base import AUTO_CONTINUE_DELAY_SECONDS, HUMAN_INTERVENTION_FILE

        return locals()[name]

    if name in _LAZY_EXPORTS:
        module_name, export_name = _LAZY_EXPORTS[name]
        value = getattr(import_module(module_name, __name__), export_name)
        globals()[name] = value
        return value

    raise AttributeError(f"module 'agents' has no attribute '{name}'")
