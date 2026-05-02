"""Static CLI runner profile registry for Phase 8 runtime planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

RunnerTier = Literal["first_class", "strategic", "generic_pool"]
RunnerRole = Literal["implementation", "analysis", "review", "fallback"]


@dataclass(frozen=True)
class CliRunnerProfile:
    """Capability profile for one local or account-backed AI CLI runner."""

    runner_id: str
    display_name: str
    tier: RunnerTier
    role: RunnerRole
    runner_status: str
    capability_tags: tuple[str, ...]
    supported_runtime_modes: tuple[str, ...]
    command_hint: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize runner metadata for CLI, UI, and future policy checks."""
        payload = asdict(self)
        payload["capability_tags"] = list(self.capability_tags)
        payload["supported_runtime_modes"] = list(self.supported_runtime_modes)
        return payload


CLI_RUNNER_PROFILES: tuple[CliRunnerProfile, ...] = (
    CliRunnerProfile(
        runner_id="codex_cli",
        display_name="Codex CLI",
        tier="first_class",
        role="implementation",
        runner_status="wired",
        capability_tags=(
            "headless",
            "filesystem_edit",
            "shell",
            "structured_events",
            "cost_report",
        ),
        supported_runtime_modes=("full_autonomous",),
        command_hint="codex exec",
        notes="Current account-backed CLI runtime adapter.",
    ),
    CliRunnerProfile(
        runner_id="claude_code",
        display_name="Claude Code",
        tier="first_class",
        role="implementation",
        runner_status="planned",
        capability_tags=(
            "headless",
            "filesystem_edit",
            "shell",
            "mcp",
            "subagents",
        ),
        supported_runtime_modes=("full_autonomous",),
        command_hint="claude",
        notes="Compatibility path for existing Claude Code workflows.",
    ),
    CliRunnerProfile(
        runner_id="gemini_cli",
        display_name="Gemini CLI",
        tier="first_class",
        role="analysis",
        runner_status="planned",
        capability_tags=("headless", "large_context", "analysis", "fallback"),
        supported_runtime_modes=("analysis_only", "patch_proposal"),
        command_hint="gemini",
        notes="Best suited for discovery, repository analysis, and fallback.",
    ),
    CliRunnerProfile(
        runner_id="aider",
        display_name="Aider",
        tier="first_class",
        role="implementation",
        runner_status="planned",
        capability_tags=("git_aware", "filesystem_edit", "byok", "local_model"),
        supported_runtime_modes=("generic_edit", "patch_proposal"),
        command_hint="aider",
        notes="Focused git-native editing runner.",
    ),
    CliRunnerProfile(
        runner_id="coderabbit_cli",
        display_name="CodeRabbit CLI",
        tier="first_class",
        role="review",
        runner_status="planned",
        capability_tags=("review_only", "git_aware", "quality_gate"),
        supported_runtime_modes=("analysis_only",),
        command_hint="coderabbit",
        notes="Independent review gate rather than an implementation runner.",
    ),
    CliRunnerProfile(
        runner_id="github_copilot_cli",
        display_name="GitHub Copilot CLI",
        tier="strategic",
        role="fallback",
        runner_status="planned",
        capability_tags=("github_native", "enterprise", "issue_pr_workflows"),
        supported_runtime_modes=("analysis_only", "patch_proposal"),
        command_hint="gh copilot",
        notes="Strategic GitHub-native workflow integration.",
    ),
    CliRunnerProfile(
        runner_id="cursor_cli",
        display_name="Cursor CLI",
        tier="strategic",
        role="implementation",
        runner_status="planned",
        capability_tags=("project_rules", "workspace_context", "fallback"),
        supported_runtime_modes=("generic_edit", "patch_proposal"),
        command_hint="cursor-agent or configured Cursor CLI",
        notes="Use when teams already rely on Cursor rules and account state.",
    ),
    CliRunnerProfile(
        runner_id="generic_cli_pool",
        display_name="Generic CLI Pool",
        tier="generic_pool",
        role="fallback",
        runner_status="planned",
        capability_tags=("policy_wrapped", "headless_probe", "capability_declared"),
        supported_runtime_modes=("analysis_only", "patch_proposal"),
        command_hint="configured per runner",
        notes="For OpenCode, Goose, Amp, Qwen Code, DeepV Code, and similar CLIs.",
    ),
)


def cli_runner_profiles_as_dicts() -> list[dict[str, Any]]:
    """Return all configured CLI runner profiles as dictionaries."""
    return [profile.to_dict() for profile in CLI_RUNNER_PROFILES]
