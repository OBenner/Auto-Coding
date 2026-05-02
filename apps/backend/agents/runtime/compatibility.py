"""Provider/runtime compatibility metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .capabilities import RuntimeCapabilities
from .mcp_bridge import resolve_runtime_mcp_support
from .subagents import resolve_runtime_subagent_support


@dataclass(frozen=True)
class RuntimeModeInfo:
    """User-facing runtime mode description."""

    mode: str
    purpose: str
    capabilities: str


@dataclass(frozen=True)
class ProviderRuntimeCompatibility:
    """User-facing provider compatibility row."""

    provider: str
    full_autonomous: str
    generic_edit: str
    analysis_only: str
    patch_proposal: str
    mcp_tools: str
    subagents: str
    notes: str

    def to_dict(self) -> dict[str, str]:
        """Serialize row for JSON output."""
        return asdict(self)


RUNTIME_MODE_INFO: tuple[RuntimeModeInfo, ...] = (
    RuntimeModeInfo(
        mode="full_autonomous",
        purpose="Full planner/coder/QA workflow",
        capabilities="Claude Agent SDK tools, MCP, shell, filesystem edits, subagents",
    ),
    RuntimeModeInfo(
        mode="analysis_only",
        purpose="Non-mutating text analysis",
        capabilities="Text completion or streaming",
    ),
    RuntimeModeInfo(
        mode="generic_edit",
        purpose="Provider-neutral local file, patch, and shell action loop",
        capabilities="Text completion, structured actions, local tools, MCP bridge",
    ),
    RuntimeModeInfo(
        mode="patch_proposal",
        purpose="Validated local application of model-proposed diffs",
        capabilities="Text completion, structured output, local patch validation",
    ),
)


def _subagent_strategy_label(
    *,
    provider_name: str,
    runtime_name: str,
    capabilities: RuntimeCapabilities,
    orchestrator_available: bool,
) -> str:
    support = resolve_runtime_subagent_support(
        provider_name=provider_name,
        runtime_name=runtime_name,
        capabilities=capabilities,
        orchestrator_available=orchestrator_available,
    )
    return support.strategy if support.available else "no"


def _mcp_strategy_label(
    *,
    provider_name: str,
    runtime_name: str,
    capabilities: RuntimeCapabilities,
    bridge_available: bool,
) -> str:
    support = resolve_runtime_mcp_support(
        provider_name=provider_name,
        runtime_name=runtime_name,
        capabilities=capabilities,
        bridge_available=bridge_available,
        tool_count=1 if bridge_available else 0,
    )
    return support.strategy if support.available else "no"


_CLAUDE_SUBAGENTS = _subagent_strategy_label(
    provider_name="claude",
    runtime_name="claude_agent_sdk",
    capabilities=RuntimeCapabilities.claude_agent_sdk(),
    orchestrator_available=False,
)
_CODEX_SUBAGENTS = _subagent_strategy_label(
    provider_name="codex",
    runtime_name="codex_cli",
    capabilities=RuntimeCapabilities.codex_cli(),
    orchestrator_available=True,
)
_GENERIC_SUBAGENTS = _subagent_strategy_label(
    provider_name="generic",
    runtime_name="generic_edit",
    capabilities=RuntimeCapabilities.generic_edit(),
    orchestrator_available=True,
)
_CLAUDE_MCP = _mcp_strategy_label(
    provider_name="claude",
    runtime_name="claude_agent_sdk",
    capabilities=RuntimeCapabilities.claude_agent_sdk(),
    bridge_available=False,
)
_CODEX_MCP = _mcp_strategy_label(
    provider_name="codex",
    runtime_name="codex_cli",
    capabilities=RuntimeCapabilities.codex_cli(),
    bridge_available=False,
)
_GENERIC_MCP = _mcp_strategy_label(
    provider_name="generic",
    runtime_name="generic_edit",
    capabilities=RuntimeCapabilities.generic_edit(),
    bridge_available=True,
)


PROVIDER_RUNTIME_COMPATIBILITY: tuple[ProviderRuntimeCompatibility, ...] = (
    ProviderRuntimeCompatibility(
        provider="claude",
        full_autonomous="yes",
        generic_edit="not needed",
        analysis_only="yes",
        patch_proposal="not needed",
        mcp_tools=_CLAUDE_MCP,
        subagents=_CLAUDE_SUBAGENTS,
        notes="Uses Claude Agent SDK path for the full Auto Code runtime.",
    ),
    ProviderRuntimeCompatibility(
        provider="codex",
        full_autonomous="yes",
        generic_edit="not needed",
        analysis_only="yes",
        patch_proposal="not needed",
        mcp_tools=_CODEX_MCP,
        subagents=_CODEX_SUBAGENTS,
        notes="Uses Codex CLI account login through CODEX_HOME and codex exec.",
    ),
    ProviderRuntimeCompatibility(
        provider="openai",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        mcp_tools=_GENERIC_MCP,
        subagents=_GENERIC_SUBAGENTS,
        notes="Direct SDK sessions use native tools when available, with JSON fallback.",
    ),
    ProviderRuntimeCompatibility(
        provider="google",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        mcp_tools=_GENERIC_MCP,
        subagents=_GENERIC_SUBAGENTS,
        notes="Gemini can use local JSON actions with orchestrated child sessions.",
    ),
    ProviderRuntimeCompatibility(
        provider="litellm",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        mcp_tools=_GENERIC_MCP,
        subagents=_GENERIC_SUBAGENTS,
        notes="Gateway provider; native tools depend on routed model/gateway support.",
    ),
    ProviderRuntimeCompatibility(
        provider="openrouter",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        mcp_tools=_GENERIC_MCP,
        subagents=_GENERIC_SUBAGENTS,
        notes="OpenAI-compatible gateway with native tools plus JSON fallback.",
    ),
    ProviderRuntimeCompatibility(
        provider="zhipuai",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        mcp_tools=_GENERIC_MCP,
        subagents=_GENERIC_SUBAGENTS,
        notes=(
            "Direct ZhipuAI/Z.AI chat path is OpenAI-like and limited; the "
            "Claude-compatible Z.AI path is tracked as a Claude Code CLI runner."
        ),
    ),
    ProviderRuntimeCompatibility(
        provider="ollama",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        mcp_tools=_GENERIC_MCP,
        subagents=_GENERIC_SUBAGENTS,
        notes="Local models can attempt generic_edit without remote code sharing.",
    ),
)


def runtime_mode_info_as_dicts() -> list[dict[str, str]]:
    """Return runtime mode descriptions for JSON output."""
    return [asdict(mode) for mode in RUNTIME_MODE_INFO]


def provider_choices() -> list[str]:
    """Return provider names supported by runtime compatibility metadata."""
    return [row.provider for row in PROVIDER_RUNTIME_COMPATIBILITY]


def runtime_mode_choices() -> list[str]:
    """Return CLI-friendly runtime mode choices from runtime metadata."""
    choices: list[str] = []
    for mode in RUNTIME_MODE_INFO:
        choices.append(mode.mode)
        choices.append(mode.mode.replace("_", "-"))
    return choices


def provider_runtime_compatibility_as_dicts() -> list[dict[str, str]]:
    """Return provider compatibility rows for JSON output."""
    return [row.to_dict() for row in PROVIDER_RUNTIME_COMPATIBILITY]
