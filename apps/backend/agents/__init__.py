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

# Explicit imports required by CodeQL static analysis
# (CodeQL doesn't recognize __getattr__ dynamic exports)
from .code_reviewer import run_code_review_session as run_code_review_session
from .coder import run_autonomous_agent as run_autonomous_agent
from .documentation_generator import (
    run_documentation_generator_session as run_documentation_generator_session,
)
from .memory_manager import debug_memory_system_status as debug_memory_system_status
from .memory_manager import get_graphiti_context as get_graphiti_context
from .memory_manager import save_session_memory as save_session_memory
from .memory_manager import save_session_to_graphiti as save_session_to_graphiti
from .migration_assistant import run_migration_assistant as run_migration_assistant
from .performance_profiler import run_performance_profiler as run_performance_profiler
from .planner import run_followup_planner as run_followup_planner
from .session import post_session_processing as post_session_processing
from .session import run_agent_session as run_agent_session
from .utils import find_phase_for_subtask as find_phase_for_subtask
from .utils import find_subtask_in_plan as find_subtask_in_plan
from .utils import get_commit_count as get_commit_count
from .utils import get_latest_commit as get_latest_commit
from .utils import get_workspace_project_dirs as get_workspace_project_dirs
from .utils import load_implementation_plan as load_implementation_plan
from .utils import load_workspace_context as load_workspace_context
from .utils import sync_spec_to_source as sync_spec_to_source

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


def __getattr__(name):
    """Lazy imports for names that may cause circular dependencies."""
    if name in ("AUTO_CONTINUE_DELAY_SECONDS", "HUMAN_INTERVENTION_FILE"):
        from .base import AUTO_CONTINUE_DELAY_SECONDS, HUMAN_INTERVENTION_FILE

        return locals()[name]
    elif name in ("load_workspace_context", "get_workspace_project_dirs"):
        from .utils import get_workspace_project_dirs, load_workspace_context

        return locals()[name]
    raise AttributeError(f"module 'agents' has no attribute '{name}'")
