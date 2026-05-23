"""Capability vs policy semantics for the runtime layer.

These tests pin the honest contract introduced by Phase 0.1 of
``docs/roadmap/non-claude-provider-autonomy.md``:

- :class:`RuntimeCapabilities` describes only what the runtime can
  physically do.
- :class:`RuntimePolicy` describes evidence-based promotions on top of
  capability.
- The :meth:`supports`/:meth:`missing` helpers optionally accept a
  policy so the promotion path is visible at the call site.
- The legacy :meth:`RuntimeCapabilities.direct_api_autonomous` constructor
  is deprecated but still returns the honest promoted-edit shape.
"""

from __future__ import annotations

import warnings

import pytest

from agents.runtime.capabilities import (
    RuntimeCapabilities,
    RuntimeCapabilityError,
    RuntimePolicy,
    RuntimeRequirements,
)


def test_promoted_edit_capability_matches_generic_edit_shape():
    """``promoted_edit`` and ``generic_edit`` must declare the same flags.

    The point of Phase 0.1 is that a Generic Edit session does not grow
    extra physical capabilities just because the AutonomyPolicy gate
    promoted it; only its policy changes.
    """
    assert RuntimeCapabilities.promoted_edit() == RuntimeCapabilities.generic_edit()


def test_promoted_edit_does_not_claim_native_tool_loop():
    """Capability honesty: no ``native_tool_loop`` flag without provider proof."""
    promoted = RuntimeCapabilities.promoted_edit()
    assert promoted.native_tool_loop is False


def test_full_coder_requirement_is_unmet_by_capability_alone():
    """``promoted_edit`` alone cannot satisfy ``full_coder``; policy is needed."""
    promoted = RuntimeCapabilities.promoted_edit()
    requirements = RuntimeRequirements.full_coder()

    assert promoted.supports(requirements) is False
    assert "native_tool_loop" in promoted.missing(requirements)


def test_promotion_policy_grants_native_tool_loop():
    """A promoted-to-full-autonomous policy lets ``promoted_edit`` cover full_coder."""
    promoted = RuntimeCapabilities.promoted_edit()
    requirements = RuntimeRequirements.full_coder()
    policy = RuntimePolicy(promoted_to_full_autonomous=True)

    assert promoted.supports(requirements, policy=policy) is True
    assert promoted.missing(requirements, policy=policy) == []


def test_default_policy_grants_nothing():
    """A default :class:`RuntimePolicy` must not change capability outcomes."""
    promoted = RuntimeCapabilities.promoted_edit()
    requirements = RuntimeRequirements.full_coder()
    policy = RuntimePolicy()

    assert promoted.supports(requirements, policy=policy) is False
    assert "native_tool_loop" in promoted.missing(requirements, policy=policy)


def test_policy_does_not_grant_mcp_subagents_or_sandbox():
    """Promotion is narrow: only the tool-loop flag, not MCP/subagents/sandbox."""
    policy = RuntimePolicy(promoted_to_full_autonomous=True)
    granted = policy.granted_capabilities()

    assert "native_tool_loop" in granted
    assert "mcp" not in granted
    assert "subagents" not in granted
    assert "sandbox" not in granted


def test_policy_to_dict_is_json_safe_and_sorted():
    """``RuntimePolicy.to_dict`` exposes a stable, JSON-safe snapshot."""
    payload = RuntimePolicy(promoted_to_full_autonomous=True).to_dict()

    assert payload["promoted_to_full_autonomous"] is True
    assert payload["granted_capabilities"] == ["native_tool_loop"]


def test_default_policy_to_dict_is_empty():
    """An unset policy reports no granted capabilities."""
    payload = RuntimePolicy().to_dict()

    assert payload["promoted_to_full_autonomous"] is False
    assert payload["granted_capabilities"] == []


def test_direct_api_autonomous_constructor_is_deprecated_alias():
    """Legacy ``direct_api_autonomous()`` warns and returns ``promoted_edit()``."""
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        legacy = RuntimeCapabilities.direct_api_autonomous()

    assert legacy == RuntimeCapabilities.promoted_edit()
    assert any(
        issubclass(item.category, DeprecationWarning)
        and "promoted_edit" in str(item.message)
        for item in captured
    )


def test_capability_error_message_includes_policy_block():
    """When raised with a policy, the error explains policy-granted capabilities."""
    promoted = RuntimeCapabilities.promoted_edit()
    requirements = RuntimeRequirements.full_coder()
    policy = RuntimePolicy(promoted_to_full_autonomous=False)

    error = RuntimeCapabilityError(
        provider_name="openai",
        runtime_name="promoted_edit",
        requirements=requirements,
        capabilities=promoted,
        policy=policy,
    )

    message = str(error)
    assert "Policy-granted capabilities" in message
    assert "Promoted to full autonomous: False" in message


def test_capability_error_without_policy_omits_policy_block():
    """When no policy is provided the error stays at the capability layer."""
    promoted = RuntimeCapabilities.promoted_edit()
    requirements = RuntimeRequirements.full_coder()

    error = RuntimeCapabilityError(
        provider_name="openai",
        runtime_name="promoted_edit",
        requirements=requirements,
        capabilities=promoted,
    )

    assert "Policy-granted capabilities" not in str(error)


@pytest.mark.parametrize(
    "factory",
    [
        RuntimeCapabilities.claude_agent_sdk,
        RuntimeCapabilities.codex_cli,
    ],
)
def test_full_runtime_capabilities_still_satisfy_full_coder_without_policy(factory):
    """Claude SDK and Codex CLI keep their honest ``full_coder`` support."""
    assert factory().supports(RuntimeRequirements.full_coder())


def test_runtime_policy_is_frozen():
    """The dataclass is frozen so it cannot be mutated after construction."""
    policy = RuntimePolicy(promoted_to_full_autonomous=True)

    with pytest.raises(Exception):
        policy.promoted_to_full_autonomous = False  # type: ignore[misc]
