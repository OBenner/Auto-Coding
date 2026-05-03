"""Runtime mode selection."""

import os
from typing import Literal

RuntimeMode = Literal[
    "full_autonomous",
    "generic_edit",
    "patch_proposal",
    "analysis_only",
]

VALID_RUNTIME_MODES: tuple[RuntimeMode, ...] = (
    "full_autonomous",
    "generic_edit",
    "patch_proposal",
    "analysis_only",
)

GLOBAL_RUNTIME_MODE_ENV = "AUTO_CODE_RUNTIME_MODE"
LEGACY_GLOBAL_RUNTIME_MODE_ENV = "AUTO_CLAUDE_RUNTIME_MODE"


def normalize_runtime_mode(value: str | None) -> RuntimeMode:
    """Normalize a runtime mode string."""
    mode = (value or "full_autonomous").strip().lower().replace("-", "_")
    if mode not in VALID_RUNTIME_MODES:
        allowed = ", ".join(VALID_RUNTIME_MODES)
        raise ValueError(f"Invalid runtime mode '{value}'. Must be one of: {allowed}")
    return mode  # type: ignore[return-value]


def get_runtime_mode(agent_type: str) -> RuntimeMode:
    """Resolve runtime mode from per-agent or global environment."""
    per_agent = os.environ.get(f"AGENT_RUNTIME_MODE_{agent_type.upper()}")
    if per_agent:
        return normalize_runtime_mode(per_agent)

    global_mode = os.environ.get(GLOBAL_RUNTIME_MODE_ENV)
    if global_mode:
        return normalize_runtime_mode(global_mode)

    legacy_global_mode = os.environ.get(LEGACY_GLOBAL_RUNTIME_MODE_ENV)
    if legacy_global_mode:
        return normalize_runtime_mode(legacy_global_mode)

    return "full_autonomous"
