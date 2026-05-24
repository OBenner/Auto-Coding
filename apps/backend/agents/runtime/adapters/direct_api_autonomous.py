"""Direct API autonomous runtime adapter.

This adapter wraps the Generic Edit engine and advertises its honest
capability set (:meth:`RuntimeCapabilities.promoted_edit`) plus a
:class:`RuntimePolicy` that flips ``promoted_to_full_autonomous`` to
``True``. The factory selects this adapter only when the
:func:`resolve_direct_api_autonomous_gate` evidence gate passes for the
caller's provider, so the promotion is always backed by recorded e2e and
reliability evidence rather than by a hardcoded capability claim.

Phase 1.1: when ``AUTO_CODE_AUTONOMY=safe`` (or ``bold``), or when the
operator opts in via ``AUTO_CODE_EXTERNAL_MCP_CLIENT=true``, the runtime
also flips ``mcp_execution_enabled`` so direct providers honestly
declare an ``mcp`` capability. The flag is computed from
:func:`resolve_autonomy_settings` rather than hardcoded so explicit
low-level env overrides keep winning.
"""

from collections.abc import Mapping

from core.autonomy_level import resolve_autonomy_settings

from ..capabilities import RuntimeCapabilities, RuntimePolicy
from .generic_edit import GenericEditRuntimeSession


def _build_runtime_policy(
    env: Mapping[str, str] | None = None,
) -> RuntimePolicy:
    """Build the runtime policy for a promoted direct-API session."""
    settings = resolve_autonomy_settings(env=env)
    return RuntimePolicy(
        promoted_to_full_autonomous=True,
        mcp_execution_enabled=settings.external_mcp_client_enabled,
        mutating_subagents_enabled=settings.mutating_subagents_enabled,
        sandbox_enabled=settings.sandbox_enabled,
    )


class DirectApiAutonomousRuntimeSession(GenericEditRuntimeSession):
    """Promoted direct-provider runtime backed by the Generic Edit engine."""

    name = "direct_api_autonomous"
    capabilities = RuntimeCapabilities.promoted_edit()

    @property
    def runtime_policy(self) -> RuntimePolicy:  # type: ignore[override]
        """Resolve the runtime policy lazily so env changes take effect.

        Built per-call rather than at class instantiation time so tests
        and operators that flip ``AUTO_CODE_AUTONOMY`` between sessions
        see the updated grant without needing to reinstantiate.
        """
        return _build_runtime_policy()
