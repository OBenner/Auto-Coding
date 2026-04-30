"""Provider/runtime compatibility metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass


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
    notes: str

    def to_dict(self) -> dict[str, str]:
        """Serialize row for JSON output."""
        return asdict(self)


RUNTIME_MODE_INFO: tuple[RuntimeModeInfo, ...] = (
    RuntimeModeInfo(
        mode="full_autonomous",
        purpose="Full planner/coder/QA workflow",
        capabilities="Claude Agent SDK tools, MCP, shell, filesystem edits",
    ),
    RuntimeModeInfo(
        mode="analysis_only",
        purpose="Non-mutating text analysis",
        capabilities="Text completion or streaming",
    ),
    RuntimeModeInfo(
        mode="generic_edit",
        purpose="Provider-neutral local file, patch, and shell action loop",
        capabilities="Text completion, structured JSON actions, local tools",
    ),
    RuntimeModeInfo(
        mode="patch_proposal",
        purpose="Validated local application of model-proposed diffs",
        capabilities="Text completion, structured output, local patch validation",
    ),
)


PROVIDER_RUNTIME_COMPATIBILITY: tuple[ProviderRuntimeCompatibility, ...] = (
    ProviderRuntimeCompatibility(
        provider="claude",
        full_autonomous="yes",
        generic_edit="not needed",
        analysis_only="yes",
        patch_proposal="not needed",
        notes="Uses Claude Agent SDK path for the full Auto Code runtime.",
    ),
    ProviderRuntimeCompatibility(
        provider="openai",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        notes="Direct SDK sessions use native tools when available, with JSON fallback.",
    ),
    ProviderRuntimeCompatibility(
        provider="google",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        notes="Gemini can use local JSON actions; MCP parity is not implemented.",
    ),
    ProviderRuntimeCompatibility(
        provider="litellm",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        notes="Gateway provider; native tools depend on routed model/gateway support.",
    ),
    ProviderRuntimeCompatibility(
        provider="openrouter",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        notes="OpenAI-compatible gateway with native tools plus JSON fallback.",
    ),
    ProviderRuntimeCompatibility(
        provider="zhipuai",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
        notes="OpenAI-like tool calls where available, with local JSON fallback.",
    ),
    ProviderRuntimeCompatibility(
        provider="ollama",
        full_autonomous="no",
        generic_edit="experimental",
        analysis_only="yes",
        patch_proposal="limited",
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
