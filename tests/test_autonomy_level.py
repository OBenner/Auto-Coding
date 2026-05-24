"""Tests for ADR-006 user-facing autonomy levels.

Pin the precedence rules from ``docs/architecture/adr/ADR-006-autonomy-levels.md``:

1. Explicit low-level env vars win.
2. ``AUTO_CODE_AUTONOMY`` level mapping fills the gaps.
3. Module defaults apply when both are absent (today's behavior).
"""

from __future__ import annotations

import warnings

import pytest

from core.autonomy_level import (
    AUTONOMY_LEVEL_ENV,
    AUTONOMY_PRESET_ENV,
    DIRECT_API_AUTONOMOUS_ENV,
    LEGACY_RUNTIME_MODE_ENV,
    RUNTIME_FALLBACK_ENV,
    RUNTIME_MODE_ENV,
    AutonomyLevel,
    AutonomyPreset,
    resolve_autonomy_settings,
)


def test_default_level_is_claude_and_matches_pre_adr_behavior():
    """Without any env var the resolved settings match today's defaults."""
    settings = resolve_autonomy_settings(env={})

    assert settings.level is AutonomyLevel.CLAUDE
    assert settings.preset is AutonomyPreset.STANDARD
    assert settings.runtime_mode == "full_autonomous"
    assert settings.runtime_fallback_enabled is False
    assert settings.direct_api_gate_enabled is False
    assert settings.direct_api_skip_gate is False
    assert settings.explicit_overrides == ()


def test_level_off_disables_writes():
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "off"})

    assert settings.level is AutonomyLevel.OFF
    assert settings.runtime_mode == "analysis_only"
    assert settings.runtime_fallback_enabled is False
    assert settings.direct_api_gate_enabled is False


def test_level_claude_keeps_today_defaults():
    """The ``claude`` level explicitly chosen matches the implicit default."""
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "claude"})

    assert settings.runtime_mode == "full_autonomous"
    assert settings.runtime_fallback_enabled is False
    assert settings.direct_api_gate_enabled is False
    assert settings.direct_api_skip_gate is False


def test_level_safe_enables_fallback_and_direct_api_gate():
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "safe"})

    assert settings.runtime_mode == "full_autonomous"
    assert settings.runtime_fallback_enabled is True
    assert settings.direct_api_gate_enabled is True
    assert settings.direct_api_skip_gate is False


def test_level_bold_skips_gate():
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "bold"})

    assert settings.runtime_fallback_enabled is True
    assert settings.direct_api_gate_enabled is True
    assert settings.direct_api_skip_gate is True


def test_unknown_level_raises_value_error():
    with pytest.raises(ValueError) as excinfo:
        resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "yolo"})

    message = str(excinfo.value)
    assert "yolo" in message
    assert "off" in message
    assert "bold" in message


def test_preset_default_is_standard_when_unset():
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "safe"})

    assert settings.preset is AutonomyPreset.STANDARD


@pytest.mark.parametrize(
    "value, expected",
    [
        ("strict", AutonomyPreset.STRICT),
        ("standard", AutonomyPreset.STANDARD),
        ("lax", AutonomyPreset.LAX),
        ("STRICT", AutonomyPreset.STRICT),
    ],
)
def test_preset_parses_known_values(value: str, expected: AutonomyPreset):
    settings = resolve_autonomy_settings(env={AUTONOMY_PRESET_ENV: value})

    assert settings.preset is expected


def test_unknown_preset_raises_value_error():
    with pytest.raises(ValueError) as excinfo:
        resolve_autonomy_settings(env={AUTONOMY_PRESET_ENV: "yolo"})

    message = str(excinfo.value)
    assert "yolo" in message
    assert "strict" in message
    assert "lax" in message


def test_explicit_runtime_mode_overrides_level_default():
    """Operator who set runtime_mode explicitly keeps that value."""
    settings = resolve_autonomy_settings(
        env={
            AUTONOMY_LEVEL_ENV: "off",  # would imply analysis_only
            RUNTIME_MODE_ENV: "generic_edit",  # explicit override
        }
    )

    assert settings.runtime_mode == "generic_edit"
    assert RUNTIME_MODE_ENV in settings.explicit_overrides


def test_legacy_runtime_mode_env_is_recognised():
    settings = resolve_autonomy_settings(
        env={LEGACY_RUNTIME_MODE_ENV: "patch_proposal"}
    )

    assert settings.runtime_mode == "patch_proposal"
    assert RUNTIME_MODE_ENV in settings.explicit_overrides


def test_explicit_runtime_fallback_overrides_level_default():
    settings = resolve_autonomy_settings(
        env={
            AUTONOMY_LEVEL_ENV: "claude",  # would imply fallback off
            RUNTIME_FALLBACK_ENV: "true",  # explicit override
        }
    )

    assert settings.runtime_fallback_enabled is True
    assert RUNTIME_FALLBACK_ENV in settings.explicit_overrides


def test_explicit_runtime_fallback_can_disable_safe_level():
    settings = resolve_autonomy_settings(
        env={
            AUTONOMY_LEVEL_ENV: "safe",  # would imply fallback on
            RUNTIME_FALLBACK_ENV: "false",
        }
    )

    assert settings.runtime_fallback_enabled is False
    assert RUNTIME_FALLBACK_ENV in settings.explicit_overrides


def test_direct_api_env_override_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        settings = resolve_autonomy_settings(
            env={DIRECT_API_AUTONOMOUS_ENV: "true"}
        )

    assert settings.direct_api_gate_enabled is True
    assert DIRECT_API_AUTONOMOUS_ENV in settings.explicit_overrides
    assert any(
        issubclass(item.category, DeprecationWarning)
        and AUTONOMY_LEVEL_ENV in str(item.message)
        for item in captured
    )


def test_direct_api_env_override_disables_gate_when_explicit_false():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        settings = resolve_autonomy_settings(
            env={
                AUTONOMY_LEVEL_ENV: "safe",
                DIRECT_API_AUTONOMOUS_ENV: "false",
            }
        )

    assert settings.direct_api_gate_enabled is False
    assert DIRECT_API_AUTONOMOUS_ENV in settings.explicit_overrides


def test_garbage_runtime_fallback_env_falls_back_to_level_default():
    settings = resolve_autonomy_settings(
        env={
            AUTONOMY_LEVEL_ENV: "safe",
            RUNTIME_FALLBACK_ENV: "maybe",  # not a recognised truthy/falsy
        }
    )

    # Garbage value is ignored, level default applies.
    assert settings.runtime_fallback_enabled is True
    assert RUNTIME_FALLBACK_ENV not in settings.explicit_overrides


def test_empty_runtime_mode_env_does_not_override_level():
    settings = resolve_autonomy_settings(
        env={
            AUTONOMY_LEVEL_ENV: "claude",
            RUNTIME_MODE_ENV: "",
        }
    )

    assert settings.runtime_mode == "full_autonomous"
    assert RUNTIME_MODE_ENV not in settings.explicit_overrides


def test_to_dict_is_json_safe():
    settings = resolve_autonomy_settings(
        env={AUTONOMY_LEVEL_ENV: "safe", AUTONOMY_PRESET_ENV: "strict"}
    )
    payload = settings.to_dict()

    assert payload["level"] == "safe"
    assert payload["preset"] == "strict"
    assert payload["runtime_mode"] == "full_autonomous"
    assert payload["runtime_fallback_enabled"] is True
    assert payload["direct_api_gate_enabled"] is True
    assert payload["direct_api_skip_gate"] is False
    assert payload["explicit_overrides"] == []


def test_explicit_overrides_listed_in_to_dict():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        settings = resolve_autonomy_settings(
            env={
                RUNTIME_MODE_ENV: "generic_edit",
                RUNTIME_FALLBACK_ENV: "true",
                DIRECT_API_AUTONOMOUS_ENV: "true",
            }
        )
    payload = settings.to_dict()

    assert set(payload["explicit_overrides"]) == {
        RUNTIME_MODE_ENV,
        RUNTIME_FALLBACK_ENV,
        DIRECT_API_AUTONOMOUS_ENV,
    }


def test_level_case_insensitive():
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "BOLD"})

    assert settings.level is AutonomyLevel.BOLD


# ---------------------------------------------------------------------
# External MCP client wiring (Phase 1.1)
# ---------------------------------------------------------------------


def test_external_mcp_client_off_for_default_claude_level():
    """Default level keeps the external MCP client off (Claude SDK has its own)."""
    settings = resolve_autonomy_settings(env={})

    assert settings.external_mcp_client_enabled is False


def test_external_mcp_client_off_for_off_level():
    settings = resolve_autonomy_settings(
        env={AUTONOMY_LEVEL_ENV: "off"},
    )

    assert settings.external_mcp_client_enabled is False


def test_safe_level_auto_enables_external_mcp_client():
    """``safe`` flips the external MCP client bridge on so direct providers can MCP."""
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "safe"})

    assert settings.external_mcp_client_enabled is True


def test_bold_level_auto_enables_external_mcp_client():
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "bold"})

    assert settings.external_mcp_client_enabled is True


def test_explicit_external_mcp_client_env_wins_over_level_default():
    """``AUTO_CODE_EXTERNAL_MCP_CLIENT=false`` overrides the safe-level default."""
    from core.autonomy_level import EXTERNAL_MCP_CLIENT_ENV

    settings = resolve_autonomy_settings(
        env={
            AUTONOMY_LEVEL_ENV: "safe",
            EXTERNAL_MCP_CLIENT_ENV: "false",
        },
    )

    assert settings.external_mcp_client_enabled is False
    assert EXTERNAL_MCP_CLIENT_ENV in settings.explicit_overrides


def test_explicit_external_mcp_client_env_can_force_enable_on_claude_level():
    """Power users can flip the bridge on without changing the level."""
    from core.autonomy_level import EXTERNAL_MCP_CLIENT_ENV

    settings = resolve_autonomy_settings(
        env={
            AUTONOMY_LEVEL_ENV: "claude",
            EXTERNAL_MCP_CLIENT_ENV: "true",
        },
    )

    assert settings.external_mcp_client_enabled is True
    assert EXTERNAL_MCP_CLIENT_ENV in settings.explicit_overrides


def test_to_dict_includes_external_mcp_client_flag():
    settings = resolve_autonomy_settings(env={AUTONOMY_LEVEL_ENV: "safe"})

    payload = settings.to_dict()

    assert payload["external_mcp_client_enabled"] is True
