"""Per-provider autonomy policy.

Single source of truth for thresholds that gate direct-API providers on
their way to ``full_autonomous``. Defaults match the constants that used
to live in ``cli/provider_smoke_commands.py``; per-provider overrides come
from an optional JSON file and from environment variables.

Precedence (highest first):

1. ``AUTO_CODE_AUTONOMY_<PROVIDER>_<KNOB>`` environment variable
2. ``AUTO_CODE_AUTONOMY_DEFAULT_<KNOB>`` environment variable
3. ``providers[<provider>]`` entry in the policy file
4. ``defaults`` entry in the policy file
5. Module-level defaults below
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

AUTONOMY_POLICY_FILE_ENV = "AUTO_CODE_AUTONOMY_POLICY_FILE"
AUTONOMY_POLICY_ENV_PREFIX = "AUTO_CODE_AUTONOMY_"

DEFAULT_MIN_STABLE_RUNS = 3
DEFAULT_MAX_HISTORY_AGE_DAYS = 7
DEFAULT_REQUIRED_E2E_RUNS: tuple[str, ...] = (
    "generic_edit",
    "mini_pipeline",
    "transaction_batch_probe",
    "unsupported_tools_probe",
    "gateway_model_probe",
)
DEFAULT_REQUIRED_LIVE_FAULT_CASES: tuple[str, ...] = (
    "unsupported_tools",
    "gateway_model_limitations",
)
DEFAULT_REQUIRED_LIVE_TASK_FAMILIES: tuple[str, ...] = (
    "single_file_edit",
    "multi_step_edit",
    "recovery_resume",
    "transaction_batching",
)
DEFAULT_ALLOWED_PHASES: tuple[str, ...] = ("coding",)

DIRECT_API_PROVIDERS: tuple[str, ...] = (
    "openai",
    "google",
    "openrouter",
    "litellm",
    "zhipuai",
    "ollama",
)


@dataclass(frozen=True)
class AutonomyPolicy:
    """Resolved autonomy gate policy for a single provider."""

    provider: str
    min_stable_runs: int = DEFAULT_MIN_STABLE_RUNS
    max_history_age_days: int = DEFAULT_MAX_HISTORY_AGE_DAYS
    required_e2e_runs: tuple[str, ...] = DEFAULT_REQUIRED_E2E_RUNS
    required_live_fault_cases: tuple[str, ...] = DEFAULT_REQUIRED_LIVE_FAULT_CASES
    required_live_task_families: tuple[str, ...] = DEFAULT_REQUIRED_LIVE_TASK_FAMILIES
    allowed_phases: tuple[str, ...] = DEFAULT_ALLOWED_PHASES
    direct_api_eligible: bool = True
    sources: tuple[str, ...] = field(default_factory=tuple)

    @property
    def max_history_age(self) -> timedelta:
        """Return ``max_history_age_days`` as a ``timedelta``."""
        return timedelta(days=self.max_history_age_days)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe policy snapshot."""
        return {
            "provider": self.provider,
            "min_stable_runs": self.min_stable_runs,
            "max_history_age_days": self.max_history_age_days,
            "required_e2e_runs": list(self.required_e2e_runs),
            "required_live_fault_cases": list(self.required_live_fault_cases),
            "required_live_task_families": list(self.required_live_task_families),
            "allowed_phases": list(self.allowed_phases),
            "direct_api_eligible": self.direct_api_eligible,
            "sources": list(self.sources),
        }


_KNOB_PARSERS = {
    "min_stable_runs": "_int",
    "max_history_age_days": "_int",
    "required_e2e_runs": "_str_tuple",
    "required_live_fault_cases": "_str_tuple",
    "required_live_task_families": "_str_tuple",
    "allowed_phases": "_str_tuple",
    "direct_api_eligible": "_bool",
}


# Preset names (mirrored in :class:`core.autonomy_level.AutonomyPreset`) and
# the knob seeds they apply on top of module defaults. ``standard`` is a
# no-op so today's defaults stay verbatim. ``strict`` raises the bar
# (more stable runs, fresher evidence). ``lax`` relaxes the bar
# (fewer runs, longer freshness window, lighter required cases) for
# experimentation or single-developer environments.
AUTONOMY_PRESET_NAMES: tuple[str, ...] = ("strict", "standard", "lax")
_PRESET_SEEDS: dict[str, dict[str, Any]] = {
    "strict": {
        "min_stable_runs": 10,
        "max_history_age_days": 3,
    },
    "standard": {},
    "lax": {
        "min_stable_runs": 1,
        "max_history_age_days": 30,
        "required_live_fault_cases": ("unsupported_tools",),
        "required_live_task_families": (
            "single_file_edit",
            "multi_step_edit",
        ),
    },
}


def autonomy_policy_for(
    provider: str,
    *,
    env: Mapping[str, str] | None = None,
    policy_file: Path | None = None,
    preset: str | None = None,
) -> AutonomyPolicy:
    """Resolve the autonomy policy for ``provider``.

    Resolution order (later wins):

    1. Module defaults (the ``AutonomyPolicy`` dataclass field defaults).
    2. Preset seeds when ``preset`` is one of
       :data:`AUTONOMY_PRESET_NAMES`. Defaults to ``standard`` (no-op).
    3. ``defaults`` block in the JSON policy file pointed to by
       ``AUTO_CODE_AUTONOMY_POLICY_FILE`` or ``policy_file``.
    4. ``providers[<provider>]`` block in the same JSON file.
    5. ``AUTO_CODE_AUTONOMY_DEFAULT_<KNOB>`` environment variables.
    6. ``AUTO_CODE_AUTONOMY_<PROVIDER>_<KNOB>`` environment variables.
    """
    env_map = os.environ if env is None else env
    provider_key = provider.strip().lower()
    file_payload, file_source = _load_policy_file(env_map, policy_file)

    sources: list[str] = []
    knobs: dict[str, Any] = {}

    preset_name = (preset or "standard").strip().lower()
    if preset_name not in AUTONOMY_PRESET_NAMES:
        valid = ", ".join(AUTONOMY_PRESET_NAMES)
        raise ValueError(
            f"Invalid autonomy preset {preset!r}; expected one of {valid}."
        )
    preset_seeds = _PRESET_SEEDS[preset_name]
    if preset_seeds:
        _merge_knobs(knobs, preset_seeds)
        sources.append(f"preset:{preset_name}")

    defaults_payload = _dict(file_payload.get("defaults"))
    if defaults_payload:
        _merge_knobs(knobs, defaults_payload)
        if file_source:
            sources.append(f"file:{file_source}#defaults")

    providers_section = _dict(file_payload.get("providers"))
    provider_payload = _dict(providers_section.get(provider_key))
    if provider_payload:
        _merge_knobs(knobs, provider_payload)
        if file_source:
            sources.append(f"file:{file_source}#providers.{provider_key}")

    env_defaults = _knobs_from_env(env_map, scope="DEFAULT")
    if env_defaults:
        _merge_knobs(knobs, env_defaults)
        sources.append("env:DEFAULT")

    env_provider = _knobs_from_env(env_map, scope=provider_key.upper())
    if env_provider:
        _merge_knobs(knobs, env_provider)
        sources.append(f"env:{provider_key.upper()}")

    if provider_key not in DIRECT_API_PROVIDERS:
        # Hard override: claude / codex / unknown providers can never be
        # tagged direct_api_eligible, no matter what env or file says.
        knobs["direct_api_eligible"] = False

    base = AutonomyPolicy(provider=provider_key)
    return replace(base, **knobs, sources=tuple(sources))


def all_direct_api_policies(
    *,
    env: Mapping[str, str] | None = None,
    policy_file: Path | None = None,
    preset: str | None = None,
) -> dict[str, AutonomyPolicy]:
    """Return resolved policies for every known direct-API provider."""
    return {
        provider: autonomy_policy_for(
            provider, env=env, policy_file=policy_file, preset=preset
        )
        for provider in DIRECT_API_PROVIDERS
    }


def _load_policy_file(
    env: Mapping[str, str],
    explicit_path: Path | None,
) -> tuple[dict[str, Any], str | None]:
    """Return the parsed policy file payload and a source label."""
    path = explicit_path
    if path is None:
        env_path = env.get(AUTONOMY_POLICY_FILE_ENV, "").strip()
        if env_path:
            path = Path(env_path)
    if path is None:
        return {}, None
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.debug("Autonomy policy file %s not found, using defaults", path)
        return {}, None
    except OSError as exc:
        logger.warning(
            "Autonomy policy file %s is unreadable (%s); using defaults", path, exc
        )
        return {}, None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Autonomy policy file %s contains invalid JSON (%s); using defaults",
            path,
            exc,
        )
        return {}, None
    if not isinstance(payload, dict):
        logger.warning(
            "Autonomy policy file %s must contain a JSON object; using defaults",
            path,
        )
        return {}, None
    return payload, str(path)


def _knobs_from_env(env: Mapping[str, str], *, scope: str) -> dict[str, Any]:
    """Pull recognised knobs from environment variables for ``scope``."""
    prefix = f"{AUTONOMY_POLICY_ENV_PREFIX}{scope}_"
    knobs: dict[str, Any] = {}
    for raw_name, raw_value in env.items():
        if not raw_name.startswith(prefix):
            continue
        suffix = raw_name[len(prefix) :].lower()
        if suffix not in _KNOB_PARSERS:
            continue
        parsed = _parse_knob(suffix, raw_value)
        if parsed is not None:
            knobs[suffix] = parsed
    return knobs


def _merge_knobs(target: dict[str, Any], payload: Mapping[str, Any]) -> None:
    """Apply only recognised knobs from ``payload`` onto ``target``."""
    for knob, raw_value in payload.items():
        if knob not in _KNOB_PARSERS:
            continue
        parsed = _parse_knob(knob, raw_value)
        if parsed is not None:
            target[knob] = parsed


def _parse_knob(knob: str, value: Any) -> Any:
    """Parse a single knob value according to its declared type."""
    parser = _KNOB_PARSERS[knob]
    if parser == "_int":
        return _coerce_int(value)
    if parser == "_bool":
        return _coerce_bool(value)
    if parser == "_str_tuple":
        return _coerce_str_tuple(value)
    return None


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return None


def _coerce_str_tuple(value: Any) -> tuple[str, ...] | None:
    if isinstance(value, str):
        items: Iterable[str] = (part.strip() for part in value.split(","))
    elif isinstance(value, (list, tuple)):
        items = (str(part).strip() for part in value)
    else:
        return None
    cleaned = tuple(part for part in items if part)
    return cleaned if cleaned else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
