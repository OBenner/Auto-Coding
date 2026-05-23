"""Direct API autonomous runtime adapter."""

from ..capabilities import RuntimeCapabilities
from .generic_edit import GenericEditRuntimeSession


class DirectApiAutonomousRuntimeSession(GenericEditRuntimeSession):
    """Promoted direct-provider runtime backed by the Generic Edit engine."""

    name = "direct_api_autonomous"
    capabilities = RuntimeCapabilities.direct_api_autonomous()
