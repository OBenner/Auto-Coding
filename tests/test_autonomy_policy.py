"""Tests for the per-provider autonomy policy module."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest

from core.autonomy_policy import (
    AUTONOMY_POLICY_FILE_ENV,
    DEFAULT_MAX_HISTORY_AGE_DAYS,
    DEFAULT_MIN_STABLE_RUNS,
    DEFAULT_REQUIRED_E2E_RUNS,
    DEFAULT_REQUIRED_LIVE_FAULT_CASES,
    DEFAULT_REQUIRED_LIVE_TASK_FAMILIES,
    DIRECT_API_PROVIDERS,
    AutonomyPolicy,
    all_direct_api_policies,
    autonomy_policy_for,
)


def test_defaults_match_legacy_constants():
    """A policy without overrides exposes the same numbers as the old constants."""
    policy = autonomy_policy_for("openai", env={})

    assert policy.provider == "openai"
    assert policy.min_stable_runs == DEFAULT_MIN_STABLE_RUNS == 3
    assert policy.max_history_age_days == DEFAULT_MAX_HISTORY_AGE_DAYS == 7
    assert policy.required_e2e_runs == DEFAULT_REQUIRED_E2E_RUNS
    assert policy.required_live_fault_cases == DEFAULT_REQUIRED_LIVE_FAULT_CASES
    assert policy.required_live_task_families == DEFAULT_REQUIRED_LIVE_TASK_FAMILIES
    assert policy.allowed_phases == ("coding",)
    assert policy.direct_api_eligible is True
    assert policy.sources == ()


def test_non_direct_provider_is_not_eligible():
    """Providers outside the direct-API allowlist are flagged as ineligible."""
    policy = autonomy_policy_for("claude", env={})

    assert policy.direct_api_eligible is False
    assert policy.provider == "claude"


def test_env_default_overrides_module_defaults():
    """``AUTO_CODE_AUTONOMY_DEFAULT_*`` env vars seed every provider."""
    env = {"AUTO_CODE_AUTONOMY_DEFAULT_MIN_STABLE_RUNS": "10"}

    policy = autonomy_policy_for("openai", env=env)

    assert policy.min_stable_runs == 10
    assert "env:DEFAULT" in policy.sources


def test_env_provider_overrides_default():
    """Per-provider env vars beat the default env tier and the module defaults."""
    env = {
        "AUTO_CODE_AUTONOMY_DEFAULT_MIN_STABLE_RUNS": "5",
        "AUTO_CODE_AUTONOMY_OPENAI_MIN_STABLE_RUNS": "12",
        "AUTO_CODE_AUTONOMY_OPENAI_MAX_HISTORY_AGE_DAYS": "3",
    }

    policy = autonomy_policy_for("openai", env=env)

    assert policy.min_stable_runs == 12
    assert policy.max_history_age_days == 3
    assert policy.max_history_age == timedelta(days=3)
    assert "env:OPENAI" in policy.sources


def test_env_provider_does_not_leak_to_other_providers():
    """Overrides for openai must not affect ollama."""
    env = {"AUTO_CODE_AUTONOMY_OPENAI_MIN_STABLE_RUNS": "20"}

    openai_policy = autonomy_policy_for("openai", env=env)
    ollama_policy = autonomy_policy_for("ollama", env=env)

    assert openai_policy.min_stable_runs == 20
    assert ollama_policy.min_stable_runs == DEFAULT_MIN_STABLE_RUNS


def test_env_str_tuple_is_csv_decoded():
    """List-typed knobs accept comma-separated env values."""
    env = {
        "AUTO_CODE_AUTONOMY_OPENAI_REQUIRED_E2E_RUNS": (
            "generic_edit, mini_pipeline ,transaction_batch_probe"
        ),
    }

    policy = autonomy_policy_for("openai", env=env)

    assert policy.required_e2e_runs == (
        "generic_edit",
        "mini_pipeline",
        "transaction_batch_probe",
    )


def test_invalid_env_int_is_ignored():
    """Garbage int values fall back to the default rather than raising."""
    env = {"AUTO_CODE_AUTONOMY_OPENAI_MIN_STABLE_RUNS": "not-a-number"}

    policy = autonomy_policy_for("openai", env=env)

    assert policy.min_stable_runs == DEFAULT_MIN_STABLE_RUNS


def test_unknown_env_knob_is_ignored():
    """Unknown knob names should not raise or land in the policy."""
    env = {"AUTO_CODE_AUTONOMY_OPENAI_FRUITS": "apple,banana"}

    policy = autonomy_policy_for("openai", env=env)

    assert policy.min_stable_runs == DEFAULT_MIN_STABLE_RUNS


def test_policy_file_defaults_and_provider_overrides(tmp_path: Path):
    """File defaults seed all providers; per-provider entries override them."""
    policy_path = tmp_path / "autonomy.json"
    policy_path.write_text(
        json.dumps(
            {
                "defaults": {
                    "min_stable_runs": 6,
                    "max_history_age_days": 5,
                },
                "providers": {
                    "openai": {
                        "min_stable_runs": 10,
                        "required_live_fault_cases": [
                            "gateway_model_limitations",
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    openai_policy = autonomy_policy_for(
        "openai", env={}, policy_file=policy_path
    )
    google_policy = autonomy_policy_for(
        "google", env={}, policy_file=policy_path
    )

    assert openai_policy.min_stable_runs == 10
    assert openai_policy.max_history_age_days == 5
    assert openai_policy.required_live_fault_cases == ("gateway_model_limitations",)
    assert any("openai" in src for src in openai_policy.sources)

    assert google_policy.min_stable_runs == 6
    assert google_policy.max_history_age_days == 5
    assert google_policy.required_live_fault_cases == DEFAULT_REQUIRED_LIVE_FAULT_CASES


def test_policy_file_path_can_be_pointed_to_via_env(tmp_path: Path):
    """When the explicit path is omitted, the env-var path is honoured."""
    policy_path = tmp_path / "autonomy.json"
    policy_path.write_text(
        json.dumps({"providers": {"openai": {"min_stable_runs": 17}}}),
        encoding="utf-8",
    )
    env = {AUTONOMY_POLICY_FILE_ENV: str(policy_path)}

    policy = autonomy_policy_for("openai", env=env)

    assert policy.min_stable_runs == 17


def test_env_provider_overrides_policy_file(tmp_path: Path):
    """Env vars sit above file entries in the precedence chain."""
    policy_path = tmp_path / "autonomy.json"
    policy_path.write_text(
        json.dumps({"providers": {"openai": {"min_stable_runs": 4}}}),
        encoding="utf-8",
    )
    env = {
        AUTONOMY_POLICY_FILE_ENV: str(policy_path),
        "AUTO_CODE_AUTONOMY_OPENAI_MIN_STABLE_RUNS": "9",
    }

    policy = autonomy_policy_for("openai", env=env)

    assert policy.min_stable_runs == 9


def test_malformed_policy_file_falls_back_to_defaults(tmp_path: Path):
    """Bad JSON should not poison the resolver."""
    policy_path = tmp_path / "autonomy.json"
    policy_path.write_text("{not json", encoding="utf-8")

    policy = autonomy_policy_for(
        "openai", env={}, policy_file=policy_path
    )

    assert policy.min_stable_runs == DEFAULT_MIN_STABLE_RUNS
    assert policy.sources == ()


def test_missing_policy_file_falls_back_to_defaults(tmp_path: Path):
    """A missing file path is treated the same as no file at all."""
    policy = autonomy_policy_for(
        "openai", env={}, policy_file=tmp_path / "nope.json"
    )

    assert policy.min_stable_runs == DEFAULT_MIN_STABLE_RUNS


def test_to_dict_round_trips_knobs():
    """``to_dict`` produces stable JSON-safe output keyed by knob name."""
    policy = autonomy_policy_for(
        "openai",
        env={"AUTO_CODE_AUTONOMY_OPENAI_MIN_STABLE_RUNS": "11"},
    )

    payload = policy.to_dict()

    assert payload["provider"] == "openai"
    assert payload["min_stable_runs"] == 11
    assert payload["required_e2e_runs"] == list(DEFAULT_REQUIRED_E2E_RUNS)
    assert payload["direct_api_eligible"] is True
    assert payload["sources"] == ["env:OPENAI"]


def test_all_direct_api_policies_covers_every_provider():
    """Sanity: the convenience helper returns one policy per direct provider."""
    policies = all_direct_api_policies(env={})

    assert set(policies) == set(DIRECT_API_PROVIDERS)
    for name, policy in policies.items():
        assert isinstance(policy, AutonomyPolicy)
        assert policy.provider == name
        assert policy.direct_api_eligible is True


def test_provider_name_is_normalised():
    """Provider lookup tolerates mixed-case input."""
    policy = autonomy_policy_for("OpenAI", env={})

    assert policy.provider == "openai"


def test_max_history_age_property():
    """The timedelta helper reflects ``max_history_age_days``."""
    policy = autonomy_policy_for(
        "openai", env={"AUTO_CODE_AUTONOMY_OPENAI_MAX_HISTORY_AGE_DAYS": "2"}
    )

    assert policy.max_history_age == timedelta(days=2)


def test_negative_int_env_value_is_ignored():
    """Negative thresholds fall back to defaults rather than corrupting state."""
    env = {"AUTO_CODE_AUTONOMY_OPENAI_MIN_STABLE_RUNS": "-3"}

    policy = autonomy_policy_for("openai", env=env)

    assert policy.min_stable_runs == DEFAULT_MIN_STABLE_RUNS


def test_empty_str_tuple_env_value_is_ignored():
    """Whitespace-only or empty CSV does not wipe the required-runs list."""
    env = {"AUTO_CODE_AUTONOMY_OPENAI_REQUIRED_E2E_RUNS": " , , "}

    policy = autonomy_policy_for("openai", env=env)

    assert policy.required_e2e_runs == DEFAULT_REQUIRED_E2E_RUNS


def test_preset_standard_is_a_noop():
    """``standard`` preset must produce the same policy as no preset at all."""
    no_preset = autonomy_policy_for("openai", env={})
    standard = autonomy_policy_for("openai", env={}, preset="standard")

    assert no_preset.min_stable_runs == standard.min_stable_runs
    assert no_preset.max_history_age_days == standard.max_history_age_days
    assert no_preset.required_e2e_runs == standard.required_e2e_runs
    assert no_preset.required_live_fault_cases == standard.required_live_fault_cases
    assert (
        no_preset.required_live_task_families
        == standard.required_live_task_families
    )


def test_preset_strict_raises_thresholds():
    """``strict`` requires more stable runs and fresher evidence."""
    policy = autonomy_policy_for("openai", env={}, preset="strict")

    assert policy.min_stable_runs == 10
    assert policy.max_history_age_days == 3
    assert "preset:strict" in policy.sources


def test_preset_lax_relaxes_thresholds_and_required_coverage():
    """``lax`` reduces required runs/coverage for experimentation."""
    policy = autonomy_policy_for("openai", env={}, preset="lax")

    assert policy.min_stable_runs == 1
    assert policy.max_history_age_days == 30
    assert policy.required_live_fault_cases == ("unsupported_tools",)
    assert policy.required_live_task_families == (
        "single_file_edit",
        "multi_step_edit",
    )
    assert "preset:lax" in policy.sources


def test_per_provider_env_overrides_preset_seeds():
    """Explicit per-provider env vars sit above preset seeds in precedence."""
    policy = autonomy_policy_for(
        "openai",
        env={"AUTO_CODE_AUTONOMY_OPENAI_MIN_STABLE_RUNS": "7"},
        preset="strict",
    )

    assert policy.min_stable_runs == 7
    # ``strict``'s max_history_age_days seed still applies because nothing
    # overrode it.
    assert policy.max_history_age_days == 3


def test_policy_file_overrides_preset_seeds_for_specified_knobs(tmp_path: Path):
    """File ``defaults`` block wins over preset seeds for the knobs it sets."""
    policy_path = tmp_path / "autonomy.json"
    policy_path.write_text(
        json.dumps({"defaults": {"min_stable_runs": 5}}),
        encoding="utf-8",
    )

    policy = autonomy_policy_for(
        "openai", env={}, policy_file=policy_path, preset="lax"
    )

    assert policy.min_stable_runs == 5
    # ``lax``'s max_history_age_days seed still applies; only the
    # specifically overridden knob came from the file.
    assert policy.max_history_age_days == 30


def test_unknown_preset_raises_value_error():
    with pytest.raises(ValueError) as excinfo:
        autonomy_policy_for("openai", env={}, preset="yolo")

    message = str(excinfo.value)
    assert "yolo" in message
    assert "standard" in message


def test_all_direct_api_policies_accepts_preset():
    """The convenience helper threads the preset to every provider."""
    policies = all_direct_api_policies(env={}, preset="strict")

    for provider, policy in policies.items():
        assert policy.min_stable_runs == 10, provider
        assert policy.max_history_age_days == 3, provider
