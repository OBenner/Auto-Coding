"""
Runtime abstraction for agent sessions.

This package separates model providers from agent runtimes. Providers create
sessions for model access; runtimes declare what an agent session can safely do
inside an Auto Code workspace.
"""

from .adapters import create_runtime_session
from .capabilities import (
    RuntimeCapabilities,
    RuntimeCapabilityError,
    RuntimeRequirements,
)
from .local_actions import LocalActionExecutor, ToolActionResult
from .modes import RuntimeMode, get_runtime_mode, normalize_runtime_mode
from .result import AgentRunResult
from .session_engine import run_runtime_session

__all__ = [
    "AgentRunResult",
    "RuntimeCapabilities",
    "RuntimeCapabilityError",
    "RuntimeRequirements",
    "RuntimeMode",
    "LocalActionExecutor",
    "ToolActionResult",
    "create_runtime_session",
    "get_runtime_mode",
    "normalize_runtime_mode",
    "run_runtime_session",
]
