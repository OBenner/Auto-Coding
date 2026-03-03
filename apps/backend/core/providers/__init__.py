"""
Core Providers Module
=====================

Multi-provider abstraction layer for LLM and embedding providers.

This module provides:
- Provider factory: create_engine_provider() for creating AI backends
- Configuration: ProviderConfig for provider settings
- Base classes: AIEngineProvider ABC, SessionConfig, AgentSession
- Exceptions: ProviderError hierarchy for error handling

Example:
    from core.providers import create_engine_provider
    from core.providers.config import ProviderConfig

    config = ProviderConfig.from_env()
    provider = create_engine_provider(config)
"""

from core.providers.exceptions import (
    ProviderConfigError,
    ProviderError,
    ProviderNotInstalled,
)
from core.providers.factory import (
    create_agent_session,
    create_engine_provider,
    get_available_provider_names,
)

__all__ = [
    # Factory functions
    "create_agent_session",
    "create_engine_provider",
    "get_available_provider_names",
    # Exceptions
    "ProviderError",
    "ProviderNotInstalled",
    "ProviderConfigError",
]
