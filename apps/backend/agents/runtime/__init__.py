"""
Runtime abstraction for agent sessions.

This package separates model providers from agent runtimes. Providers create
sessions for model access; runtimes declare what an agent session can safely do
inside an Auto Code workspace.
"""

from .adapters import create_runtime_session
from .artifacts import save_runtime_fallback_artifact
from .capabilities import (
    RuntimeCapabilities,
    RuntimeCapabilityError,
    RuntimeRequirements,
)
from .cli_profiles import (
    CLI_RUNNER_PROFILES,
    CliRunnerProfile,
    cli_runner_profiles_as_dicts,
)
from .fallback import (
    RUNTIME_FALLBACK_ENV,
    RuntimeFallbackDecision,
    capabilities_for_runtime_mode,
    requirements_for_runtime_mode,
    resolve_runtime_mode_with_fallback,
    runtime_fallback_enabled,
)
from .local_actions import (
    LocalActionExecutor,
    LocalActionToolSpec,
    ToolActionResult,
    local_action_response_schema,
    local_action_tool_schemas,
    local_action_tool_specs,
    render_local_action_prompt,
)
from .mcp_bridge import (
    RuntimeMcpBridge,
    RuntimeMcpSupport,
    RuntimeMcpToolSpec,
    resolve_runtime_mcp_support,
)
from .modes import RuntimeMode, get_runtime_mode, normalize_runtime_mode
from .result import AgentRunResult
from .session_engine import run_runtime_session
from .subagents import (
    RuntimeSubagentOrchestrator,
    RuntimeSubagentResult,
    RuntimeSubagentRun,
    RuntimeSubagentSupport,
    RuntimeSubagentTask,
    resolve_runtime_subagent_support,
)

__all__ = [
    "AgentRunResult",
    "RuntimeCapabilities",
    "RuntimeCapabilityError",
    "RuntimeFallbackDecision",
    "RuntimeRequirements",
    "RUNTIME_FALLBACK_ENV",
    "CLI_RUNNER_PROFILES",
    "CliRunnerProfile",
    "RuntimeMode",
    "RuntimeMcpBridge",
    "RuntimeMcpSupport",
    "RuntimeMcpToolSpec",
    "RuntimeSubagentOrchestrator",
    "RuntimeSubagentResult",
    "RuntimeSubagentRun",
    "RuntimeSubagentSupport",
    "RuntimeSubagentTask",
    "LocalActionExecutor",
    "LocalActionToolSpec",
    "ToolActionResult",
    "capabilities_for_runtime_mode",
    "cli_runner_profiles_as_dicts",
    "create_runtime_session",
    "get_runtime_mode",
    "local_action_response_schema",
    "local_action_tool_schemas",
    "local_action_tool_specs",
    "normalize_runtime_mode",
    "render_local_action_prompt",
    "requirements_for_runtime_mode",
    "resolve_runtime_mcp_support",
    "resolve_runtime_subagent_support",
    "resolve_runtime_mode_with_fallback",
    "run_runtime_session",
    "runtime_fallback_enabled",
    "save_runtime_fallback_artifact",
]
