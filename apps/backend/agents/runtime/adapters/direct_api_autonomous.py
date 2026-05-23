"""Direct API autonomous runtime adapter.

This adapter wraps the Generic Edit engine and advertises its honest
capability set (:meth:`RuntimeCapabilities.promoted_edit`) plus a
:class:`RuntimePolicy` that flips ``promoted_to_full_autonomous`` to
``True``. The factory selects this adapter only when the
:func:`resolve_direct_api_autonomous_gate` evidence gate passes for the
caller's provider, so the promotion is always backed by recorded e2e and
reliability evidence rather than by a hardcoded capability claim.
"""

from ..capabilities import RuntimeCapabilities, RuntimePolicy
from .generic_edit import GenericEditRuntimeSession


class DirectApiAutonomousRuntimeSession(GenericEditRuntimeSession):
    """Promoted direct-provider runtime backed by the Generic Edit engine."""

    name = "direct_api_autonomous"
    capabilities = RuntimeCapabilities.promoted_edit()
    runtime_policy = RuntimePolicy(promoted_to_full_autonomous=True)
