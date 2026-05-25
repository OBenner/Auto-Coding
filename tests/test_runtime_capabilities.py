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


# ---------------------------------------------------------------------
# Phase 1.1 — MCP execution grant
# ---------------------------------------------------------------------


def test_mcp_execution_enabled_grants_mcp_capability():
    """``mcp_execution_enabled`` lets a promoted-edit runtime satisfy ``mcp``."""
    policy = RuntimePolicy(
        promoted_to_full_autonomous=True,
        mcp_execution_enabled=True,
    )

    granted = policy.granted_capabilities()
    assert "mcp" in granted
    assert "native_tool_loop" in granted


def test_mcp_execution_grant_independent_of_full_autonomous():
    """Operators can grant the MCP capability without full-autonomous promotion."""
    policy = RuntimePolicy(
        promoted_to_full_autonomous=False,
        mcp_execution_enabled=True,
    )

    granted = policy.granted_capabilities()
    assert granted == frozenset({"mcp"})


def test_mcp_grant_does_not_include_subagents_or_sandbox():
    """Phase 1.1 grants only ``mcp``, not Phase 1.2/1.3 capabilities."""
    policy = RuntimePolicy(
        promoted_to_full_autonomous=True,
        mcp_execution_enabled=True,
    )

    granted = policy.granted_capabilities()
    assert "subagents" not in granted
    assert "sandbox" not in granted


def test_default_policy_does_not_grant_mcp():
    policy = RuntimePolicy()

    assert "mcp" not in policy.granted_capabilities()


def test_policy_to_dict_includes_mcp_flag_and_grant():
    policy = RuntimePolicy(
        promoted_to_full_autonomous=True,
        mcp_execution_enabled=True,
    )

    payload = policy.to_dict()

    assert payload["mcp_execution_enabled"] is True
    assert "mcp" in payload["granted_capabilities"]
    assert "native_tool_loop" in payload["granted_capabilities"]


def test_supports_requires_mcp_when_policy_grants_it():
    """An MCP-requiring requirement is satisfied through the policy grant."""
    promoted = RuntimeCapabilities.promoted_edit()
    mcp_requirements = RuntimeRequirements(
        mode="mcp_demo",
        required=("text_completion", "mcp"),
    )

    no_grant = RuntimePolicy(mcp_execution_enabled=False)
    assert promoted.supports(mcp_requirements, policy=no_grant) is False
    assert "mcp" in promoted.missing(mcp_requirements, policy=no_grant)

    grant = RuntimePolicy(mcp_execution_enabled=True)
    assert promoted.supports(mcp_requirements, policy=grant) is True
    assert promoted.missing(mcp_requirements, policy=grant) == []


# ---------------------------------------------------------------------
# Phase 1.2 — mutating subagents grant
# ---------------------------------------------------------------------


def test_mutating_subagents_enabled_grants_subagents_capability():
    """``mutating_subagents_enabled`` lets the promoted runtime satisfy ``subagents``."""
    policy = RuntimePolicy(
        promoted_to_full_autonomous=True,
        mutating_subagents_enabled=True,
    )

    granted = policy.granted_capabilities()
    assert "subagents" in granted


def test_subagents_grant_independent_of_other_flags():
    """The subagents grant composes independently of mcp/full-autonomous grants."""
    policy = RuntimePolicy(mutating_subagents_enabled=True)

    granted = policy.granted_capabilities()
    assert granted == frozenset({"subagents"})


def test_subagents_grant_does_not_imply_sandbox_or_mcp():
    policy = RuntimePolicy(
        promoted_to_full_autonomous=True,
        mutating_subagents_enabled=True,
    )

    granted = policy.granted_capabilities()
    assert "sandbox" not in granted
    assert "mcp" not in granted


def test_policy_to_dict_exposes_mutating_subagents_flag():
    policy = RuntimePolicy(mutating_subagents_enabled=True)

    payload = policy.to_dict()
    assert payload["mutating_subagents_enabled"] is True
    assert "subagents" in payload["granted_capabilities"]


def test_supports_requires_subagents_when_policy_grants_it():
    promoted = RuntimeCapabilities.promoted_edit()
    requirement = RuntimeRequirements(
        mode="parallel_coder",
        required=("text_completion", "subagents"),
    )

    blocked = RuntimePolicy(mutating_subagents_enabled=False)
    assert promoted.supports(requirement, policy=blocked) is False
    assert "subagents" in promoted.missing(requirement, policy=blocked)

    allowed = RuntimePolicy(mutating_subagents_enabled=True)
    assert promoted.supports(requirement, policy=allowed) is True


# ---------------------------------------------------------------------
# Phase 1.3 — sandbox grant
# ---------------------------------------------------------------------


def test_sandbox_enabled_grants_sandbox_capability():
    policy = RuntimePolicy(sandbox_enabled=True)

    assert "sandbox" in policy.granted_capabilities()


def test_sandbox_grant_composes_with_other_grants():
    policy = RuntimePolicy(
        promoted_to_full_autonomous=True,
        mcp_execution_enabled=True,
        mutating_subagents_enabled=True,
        sandbox_enabled=True,
    )

    granted = policy.granted_capabilities()
    assert granted == frozenset(
        {"native_tool_loop", "mcp", "subagents", "sandbox"}
    )


def test_supports_requires_sandbox_when_policy_grants_it():
    promoted = RuntimeCapabilities.promoted_edit()
    requirement = RuntimeRequirements(
        mode="hardened_coder",
        required=("text_completion", "sandbox"),
    )

    no_sandbox = RuntimePolicy(sandbox_enabled=False)
    assert promoted.supports(requirement, policy=no_sandbox) is False
    assert "sandbox" in promoted.missing(requirement, policy=no_sandbox)

    with_sandbox = RuntimePolicy(sandbox_enabled=True)
    assert promoted.supports(requirement, policy=with_sandbox) is True


def test_policy_to_dict_exposes_sandbox_flag():
    payload = RuntimePolicy(sandbox_enabled=True).to_dict()

    assert payload["sandbox_enabled"] is True
    assert "sandbox" in payload["granted_capabilities"]


def test_default_policy_does_not_grant_sandbox():
    policy = RuntimePolicy()

    assert "sandbox" not in policy.granted_capabilities()
