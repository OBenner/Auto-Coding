"""User-facing autonomy levels.

Implements [ADR-006](../../docs/architecture/adr/ADR-006-autonomy-levels.md):
one ``AUTO_CODE_AUTONOMY`` env var with four discrete levels collapses
the ``AUTO_CODE_RUNTIME_*`` / ``AUTO_CODE_DIRECT_API_*`` matrix into a
single operator question. Existing low-level env vars keep working;
they win over level-derived defaults so advanced configurations never
break silently.

Precedence (highest first):

1. Explicit low-level env var
   (``AUTO_CODE_RUNTIME_MODE``, ``AUTO_CODE_RUNTIME_FALLBACK``,
   ``AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS``).
2. ``AUTO_CODE_AUTONOMY`` level mapping.
3. Module defaults (today's behavior, equivalent to the ``claude`` level).

``AUTO_CODE_AUTONOMY_PRESET`` selects an :class:`AutonomyPreset` that
seeds AutonomyPolicy thresholds. Per-knob env vars
(``AUTO_CODE_AUTONOMY_<PROVIDER>_<KNOB>``) still apply on top.
"""

from __future__ import annotations

import logging
import os
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)

AUTONOMY_LEVEL_ENV = "AUTO_CODE_AUTONOMY"
AUTONOMY_PRESET_ENV = "AUTO_CODE_AUTONOMY_PRESET"

# Low-level env vars whose explicit values override level-derived defaults.
RUNTIME_MODE_ENV = "AUTO_CODE_RUNTIME_MODE"
LEGACY_RUNTIME_MODE_ENV = "AUTO_CLAUDE_RUNTIME_MODE"
RUNTIME_FALLBACK_ENV = "AUTO_CODE_RUNTIME_FALLBACK"
DIRECT_API_AUTONOMOUS_ENV = "AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS"
EXTERNAL_MCP_CLIENT_ENV = "AUTO_CODE_EXTERNAL_MCP_CLIENT"
MUTATING_SUBAGENTS_ENV = "AUTO_CODE_MUTATING_SUBAGENTS"
SANDBOX_ENV = "AUTO_CODE_SANDBOX"

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}


class AutonomyLevel(StrEnum):
    """User-facing autonomy levels from least to most independent."""

    OFF = "off"
    CLAUDE = "claude"
    SAFE = "safe"
    BOLD = "bold"

    @classmethod
    def default(cls) -> AutonomyLevel:
        """The level used when ``AUTO_CODE_AUTONOMY`` is unset."""
        return cls.CLAUDE


class AutonomyPreset(StrEnum):
    """AutonomyPolicy threshold presets."""

    STRICT = "strict"
    STANDARD = "standard"
    LAX = "lax"

    @classmethod
    def default(cls) -> AutonomyPreset:
        """The preset used when ``AUTO_CODE_AUTONOMY_PRESET`` is unset."""
        return cls.STANDARD


@dataclass(frozen=True)
class ResolvedAutonomySettings:
    """Settings derived from an autonomy level plus low-level env overrides."""

    level: AutonomyLevel
    preset: AutonomyPreset
    runtime_mode: str
    runtime_fallback_enabled: bool
    direct_api_gate_enabled: bool
    direct_api_skip_gate: bool
    external_mcp_client_enabled: bool
    mutating_subagents_enabled: bool
    sandbox_requested: bool
    sandbox_available: bool
    sandbox_backend: str | None
    explicit_overrides: tuple[str, ...] = field(default_factory=tuple)

    @property
    def sandbox_enabled(self) -> bool:
        """Return whether the sandbox grant should actually fire.

        Sandbox is only granted when the operator asked for it AND the
        host exposes a working backend (Seatbelt/bubblewrap/
        AppContainer). Otherwise the runtime keeps ``sandbox`` missing
        so the capability error is honest.
        """
        return self.sandbox_requested and self.sandbox_available

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe snapshot for diagnostics payloads."""
        return {
            "level": self.level.value,
            "preset": self.preset.value,
            "runtime_mode": self.runtime_mode,
            "runtime_fallback_enabled": self.runtime_fallback_enabled,
            "direct_api_gate_enabled": self.direct_api_gate_enabled,
            "direct_api_skip_gate": self.direct_api_skip_gate,
            "external_mcp_client_enabled": self.external_mcp_client_enabled,
            "mutating_subagents_enabled": self.mutating_subagents_enabled,
            "sandbox_requested": self.sandbox_requested,
            "sandbox_available": self.sandbox_available,
            "sandbox_backend": self.sandbox_backend,
            "sandbox_enabled": self.sandbox_enabled,
            "explicit_overrides": list(self.explicit_overrides),
        }


# Mapping table from autonomy level to default values for the low-level knobs.
# Each entry is the *default* the level provides; explicit env vars still win.
_LEVEL_DEFAULTS: dict[AutonomyLevel, dict[str, object]] = {
    AutonomyLevel.OFF: {
        "runtime_mode": "analysis_only",
        "runtime_fallback_enabled": False,
        "direct_api_gate_enabled": False,
        "direct_api_skip_gate": False,
        "external_mcp_client_enabled": False,
        "mutating_subagents_enabled": False,
        # Off does no shell work, so sandboxing is irrelevant.
        "sandbox_requested": False,
    },
    AutonomyLevel.CLAUDE: {
        "runtime_mode": "full_autonomous",
        "runtime_fallback_enabled": False,
        "direct_api_gate_enabled": False,
        "direct_api_skip_gate": False,
        # Claude path uses the SDK's built-in MCP support; no external
        # MCP client bridge is needed by default.
        "external_mcp_client_enabled": False,
        # Claude's Task tool supplies mutating subagents through the SDK;
        # the policy grant is not needed for that path.
        "mutating_subagents_enabled": False,
        # Claude SDK ships its own sandbox; the cross-platform shim is
        # not part of the Claude code path.
        "sandbox_requested": False,
    },
    AutonomyLevel.SAFE: {
        "runtime_mode": "full_autonomous",
        "runtime_fallback_enabled": True,
        "direct_api_gate_enabled": True,
        "direct_api_skip_gate": False,
        # Direct providers need the external MCP client bridge to reach
        # Graphiti, Linear, Electron, Puppeteer, and custom servers; this
        # is the only way they can match the Claude SDK MCP surface.
        "external_mcp_client_enabled": True,
        # Mutating subagents stay off for safe: the conflict-aware merge
        # protocol is only scaffolded. Power users opt in via bold.
        "mutating_subagents_enabled": False,
        # Direct providers run shell actions through Generic Edit;
        # request the sandbox by default so safe gets a real
        # confinement layer whenever the host platform has one.
        "sandbox_requested": True,
    },
    AutonomyLevel.BOLD: {
        "runtime_mode": "full_autonomous",
        "runtime_fallback_enabled": True,
        "direct_api_gate_enabled": True,
        "direct_api_skip_gate": True,
        "external_mcp_client_enabled": True,
        # Bold accepts the experimental merge protocol; runtime still
        # enforces transaction boundaries and per-child artifacts.
        "mutating_subagents_enabled": True,
        "sandbox_requested": True,
    },
}


def _parse_level(value: str | None) -> AutonomyLevel:
    if value is None or not value.strip():
        return AutonomyLevel.default()
    normalized = value.strip().lower()
    try:
        return AutonomyLevel(normalized)
    except ValueError:
        valid = ", ".join(level.value for level in AutonomyLevel)
        raise ValueError(
            f"Invalid {AUTONOMY_LEVEL_ENV}={value!r}; expected one of {valid}."
        ) from None


def _parse_preset(value: str | None) -> AutonomyPreset:
    if value is None or not value.strip():
        return AutonomyPreset.default()
    normalized = value.strip().lower()
    try:
        return AutonomyPreset(normalized)
    except ValueError:
        valid = ", ".join(preset.value for preset in AutonomyPreset)
        raise ValueError(
            f"Invalid {AUTONOMY_PRESET_ENV}={value!r}; expected one of {valid}."
        ) from None


def _parse_bool_env(value: str | None) -> bool | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    if not stripped:
        return None
    if stripped in _TRUTHY:
        return True
    if stripped in _FALSY:
        return False
    return None


def _normalize_runtime_mode(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped.lower().replace("-", "_")


def resolve_autonomy_settings(
    env: Mapping[str, str] | None = None,
) -> ResolvedAutonomySettings:
    """Resolve the autonomy level + preset and overlay explicit env overrides.

    Reads ``AUTO_CODE_AUTONOMY`` and ``AUTO_CODE_AUTONOMY_PRESET`` first
    to pick defaults, then layers in any explicit low-level env var the
    operator set. The returned object records which low-level vars were
    explicit so diagnostics can surface them.
    """
    env_map = os.environ if env is None else env

    level = _parse_level(env_map.get(AUTONOMY_LEVEL_ENV))
    preset = _parse_preset(env_map.get(AUTONOMY_PRESET_ENV))

    defaults = _LEVEL_DEFAULTS[level]
    runtime_mode = str(defaults["runtime_mode"])
    runtime_fallback_enabled = bool(defaults["runtime_fallback_enabled"])
    direct_api_gate_enabled = bool(defaults["direct_api_gate_enabled"])
    direct_api_skip_gate = bool(defaults["direct_api_skip_gate"])
    external_mcp_client_enabled = bool(defaults["external_mcp_client_enabled"])
    mutating_subagents_enabled = bool(defaults["mutating_subagents_enabled"])
    sandbox_requested = bool(defaults["sandbox_requested"])

    explicit_overrides: list[str] = []

    runtime_mode_override = _normalize_runtime_mode(
        env_map.get(RUNTIME_MODE_ENV) or env_map.get(LEGACY_RUNTIME_MODE_ENV)
    )
    if runtime_mode_override:
        runtime_mode = runtime_mode_override
        explicit_overrides.append(RUNTIME_MODE_ENV)

    fallback_override = _parse_bool_env(env_map.get(RUNTIME_FALLBACK_ENV))
    if fallback_override is not None:
        runtime_fallback_enabled = fallback_override
        explicit_overrides.append(RUNTIME_FALLBACK_ENV)

    direct_api_override = _parse_bool_env(env_map.get(DIRECT_API_AUTONOMOUS_ENV))
    if direct_api_override is not None:
        if direct_api_override:
            warnings.warn(
                f"{DIRECT_API_AUTONOMOUS_ENV} is deprecated; set "
                f"{AUTONOMY_LEVEL_ENV}=safe (or bold for power-user mode) "
                "to enable direct-API autonomous promotion. The env var "
                "will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
        direct_api_gate_enabled = direct_api_override
        explicit_overrides.append(DIRECT_API_AUTONOMOUS_ENV)

    external_mcp_override = _parse_bool_env(env_map.get(EXTERNAL_MCP_CLIENT_ENV))
    if external_mcp_override is not None:
        external_mcp_client_enabled = external_mcp_override
        explicit_overrides.append(EXTERNAL_MCP_CLIENT_ENV)

    mutating_subagents_override = _parse_bool_env(
        env_map.get(MUTATING_SUBAGENTS_ENV)
    )
    if mutating_subagents_override is not None:
        mutating_subagents_enabled = mutating_subagents_override
        explicit_overrides.append(MUTATING_SUBAGENTS_ENV)

    sandbox_override = _parse_bool_env(env_map.get(SANDBOX_ENV))
    if sandbox_override is not None:
        sandbox_requested = sandbox_override
        explicit_overrides.append(SANDBOX_ENV)

    # Detect whether the host actually has a real backend. Imported
    # lazily so the autonomy module does not pay for sandbox helpers in
    # paths that never request sandboxing.
    from core.sandbox import describe_sandbox_backend

    backend_info = describe_sandbox_backend(env=env_map)
    sandbox_available = backend_info.available

    return ResolvedAutonomySettings(
        level=level,
        preset=preset,
        runtime_mode=runtime_mode,
        runtime_fallback_enabled=runtime_fallback_enabled,
        direct_api_gate_enabled=direct_api_gate_enabled,
        direct_api_skip_gate=direct_api_skip_gate,
        external_mcp_client_enabled=external_mcp_client_enabled,
        mutating_subagents_enabled=mutating_subagents_enabled,
        sandbox_requested=sandbox_requested,
        sandbox_available=sandbox_available,
        sandbox_backend=backend_info.backend.value,
        explicit_overrides=tuple(explicit_overrides),
    )
