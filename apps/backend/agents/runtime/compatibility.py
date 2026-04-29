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
        mode="patch_proposal",
        purpose="Validated local application of model-proposed diffs",
        capabilities="Text completion, structured output, local patch validation",
    ),
)


PROVIDER_RUNTIME_COMPATIBILITY: tuple[ProviderRuntimeCompatibility, ...] = (
    ProviderRuntimeCompatibility(
        provider="claude",
        full_autonomous="yes",
        analysis_only="yes",
        patch_proposal="not needed",
        notes="Uses Claude Agent SDK path for the full Auto Code runtime.",
    ),
    ProviderRuntimeCompatibility(
        provider="openai",
        full_autonomous="no",
        analysis_only="yes",
        patch_proposal="limited",
        notes="Direct SDK sessions are text-only from Auto Code's perspective.",
    ),
    ProviderRuntimeCompatibility(
        provider="google",
        full_autonomous="no",
        analysis_only="yes",
        patch_proposal="limited",
        notes="Gemini sessions can stream text; tool/MCP parity is not implemented.",
    ),
    ProviderRuntimeCompatibility(
        provider="litellm",
        full_autonomous="no",
        analysis_only="yes",
        patch_proposal="limited",
        notes="Gateway provider; Auto Code treats routed models as text-only.",
    ),
    ProviderRuntimeCompatibility(
        provider="openrouter",
        full_autonomous="no",
        analysis_only="yes",
        patch_proposal="limited",
        notes="OpenAI-compatible gateway without native Auto Code tools.",
    ),
    ProviderRuntimeCompatibility(
        provider="zhipuai",
        full_autonomous="no",
        analysis_only="yes",
        patch_proposal="limited",
        notes="Text completion support only.",
    ),
    ProviderRuntimeCompatibility(
        provider="ollama",
        full_autonomous="no",
        analysis_only="yes",
        patch_proposal="limited",
        notes="Local OpenAI-compatible models for private text-only work.",
    ),
)


def runtime_mode_info_as_dicts() -> list[dict[str, str]]:
    """Return runtime mode descriptions for JSON output."""
    return [asdict(mode) for mode in RUNTIME_MODE_INFO]


def provider_runtime_compatibility_as_dicts() -> list[dict[str, str]]:
    """Return provider compatibility rows for JSON output."""
    return [row.to_dict() for row in PROVIDER_RUNTIME_COMPATIBILITY]
