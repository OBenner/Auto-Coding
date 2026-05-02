"""Static CLI runner profile registry for Phase 8 runtime planning."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from core.platform import find_executable

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
    executable_candidates: tuple[str, ...]
    notes: str

    def to_dict(self, *, include_detection: bool = False) -> dict[str, Any]:
        """Serialize runner metadata for CLI, UI, and future policy checks."""
        payload = asdict(self)
        payload["capability_tags"] = list(self.capability_tags)
        payload["supported_runtime_modes"] = list(self.supported_runtime_modes)
        payload["executable_candidates"] = list(self.executable_candidates)
        if include_detection:
            payload["availability"] = detect_cli_runner_availability(self).to_dict()
        return payload


@dataclass(frozen=True)
class CliRunnerAvailability:
    """Local executable detection result for one CLI runner profile."""

    runner_id: str
    executable_present: bool
    resolved_executable: str | None
    matched_candidate: str | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize availability metadata for diagnostics and settings UI."""
        return asdict(self)


@dataclass(frozen=True)
class CliRunnerRejection:
    """Machine-readable reason why a runner was excluded by selection policy."""

    runner_id: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize rejection reasons for API and UI diagnostics."""
        return {
            "runner_id": self.runner_id,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CliRunnerSelection:
    """Result of applying runtime/capability policy to CLI runner profiles."""

    runtime_mode: str | None
    required_capabilities: tuple[str, ...]
    role: RunnerRole | None
    tier: RunnerTier | None
    installed_only: bool
    selected_profiles: tuple[CliRunnerProfile, ...]
    rejected_profiles: tuple[CliRunnerRejection, ...]

    @property
    def selected_runner_ids(self) -> tuple[str, ...]:
        """Return selected runner IDs in policy preference order."""
        return tuple(profile.runner_id for profile in self.selected_profiles)

    def to_dict(self, *, include_detection: bool = False) -> dict[str, Any]:
        """Serialize selection output for runtime commands and settings UI."""
        return {
            "runtime_mode": self.runtime_mode,
            "required_capabilities": list(self.required_capabilities),
            "role": self.role,
            "tier": self.tier,
            "installed_only": self.installed_only,
            "selected_runner_ids": list(self.selected_runner_ids),
            "selected_profiles": [
                profile.to_dict(include_detection=include_detection)
                for profile in self.selected_profiles
            ],
            "rejected_profiles": [
                rejection.to_dict() for rejection in self.rejected_profiles
            ],
        }


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
        executable_candidates=("codex",),
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
        executable_candidates=("claude",),
        notes="Compatibility path for existing Claude Code workflows.",
    ),
    CliRunnerProfile(
        runner_id="zai_claude_code",
        display_name="Z.AI via Claude Code",
        tier="strategic",
        role="implementation",
        runner_status="planned",
        capability_tags=(
            "headless",
            "filesystem_edit",
            "shell",
            "mcp",
            "subagents",
            "anthropic_compatible",
            "claude_code_compatible",
            "zai_compatible",
            "glm",
            "byok",
        ),
        supported_runtime_modes=("full_autonomous",),
        command_hint=(
            "ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic "
            "ANTHROPIC_AUTH_TOKEN=<zai-key> claude"
        ),
        executable_candidates=("claude",),
        notes=(
            "Claude Code-compatible Z.AI GLM path; separate from the direct "
            "zhipuai OpenAI-like provider adapter."
        ),
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
        executable_candidates=("gemini",),
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
        executable_candidates=("aider",),
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
        executable_candidates=("coderabbit",),
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
        executable_candidates=("gh",),
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
        executable_candidates=("cursor-agent", "cursor"),
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
        executable_candidates=(),
        notes="For OpenCode, Goose, Amp, Qwen Code, DeepV Code, and similar CLIs.",
    ),
)


def _normalize_runtime_mode(runtime_mode: str | None) -> str | None:
    if not runtime_mode:
        return None
    return runtime_mode.replace("-", "_")


def _normalize_capabilities(
    required_capabilities: Iterable[str] | str | None,
) -> tuple[str, ...]:
    if required_capabilities is None:
        return ()
    if isinstance(required_capabilities, str):
        return (required_capabilities,)
    return tuple(dict.fromkeys(required_capabilities))


def detect_cli_runner_availability(
    profile: CliRunnerProfile,
) -> CliRunnerAvailability:
    """Detect whether a runner executable is present without invoking it."""
    for candidate in profile.executable_candidates:
        resolved = find_executable(candidate)
        if resolved:
            return CliRunnerAvailability(
                runner_id=profile.runner_id,
                executable_present=True,
                resolved_executable=resolved,
                matched_candidate=candidate,
                status="executable_present",
            )

    status = "not_configurable" if not profile.executable_candidates else "not_found"
    return CliRunnerAvailability(
        runner_id=profile.runner_id,
        executable_present=False,
        resolved_executable=None,
        matched_candidate=None,
        status=status,
    )


def select_cli_runner_profiles(
    *,
    runtime_mode: str | None = None,
    required_capabilities: Iterable[str] | str | None = None,
    role: RunnerRole | None = None,
    tier: RunnerTier | None = None,
    installed_only: bool = False,
    profiles: Iterable[CliRunnerProfile] = CLI_RUNNER_PROFILES,
) -> CliRunnerSelection:
    """Select CLI runners compatible with the requested runtime policy."""
    normalized_mode = _normalize_runtime_mode(runtime_mode)
    normalized_capabilities = _normalize_capabilities(required_capabilities)
    selected: list[CliRunnerProfile] = []
    rejected: list[CliRunnerRejection] = []

    for profile in profiles:
        reasons: list[str] = []
        if normalized_mode and normalized_mode not in profile.supported_runtime_modes:
            reasons.append("runtime_mode_unsupported")
        missing_capabilities = [
            capability
            for capability in normalized_capabilities
            if capability not in profile.capability_tags
        ]
        reasons.extend(
            f"missing_capability:{capability}" for capability in missing_capabilities
        )
        if role and profile.role != role:
            reasons.append("role_mismatch")
        if tier and profile.tier != tier:
            reasons.append("tier_mismatch")
        if installed_only:
            availability = detect_cli_runner_availability(profile)
            if not availability.executable_present:
                reasons.append(availability.status)

        if reasons:
            rejected.append(
                CliRunnerRejection(
                    runner_id=profile.runner_id,
                    reasons=tuple(reasons),
                )
            )
        else:
            selected.append(profile)

    return CliRunnerSelection(
        runtime_mode=normalized_mode,
        required_capabilities=normalized_capabilities,
        role=role,
        tier=tier,
        installed_only=installed_only,
        selected_profiles=tuple(selected),
        rejected_profiles=tuple(rejected),
    )


def cli_runner_profiles_as_dicts(
    *,
    include_detection: bool = False,
) -> list[dict[str, Any]]:
    """Return all configured CLI runner profiles as dictionaries."""
    return [
        profile.to_dict(include_detection=include_detection)
        for profile in CLI_RUNNER_PROFILES
    ]
