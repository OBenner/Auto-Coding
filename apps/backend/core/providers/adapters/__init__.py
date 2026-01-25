"""
AI Engine Provider Adapters Package
====================================

Concrete implementations of AIEngineProvider for different backends.

This package provides:
- ClaudeAgentProvider: Wraps Claude Agent SDK (default)
- LiteLLMProvider: LiteLLM unified API (100+ models)
- OpenRouterProvider: OpenRouter cloud routing (400+ models) [future]

Usage:
    from core.providers.adapters import ClaudeAgentProvider
    from core.providers.config import ProviderConfig

    config = ProviderConfig.from_env()
    provider = ClaudeAgentProvider(config)
    session = provider.create_session(session_config)

    # Or use LiteLLM for 100+ models (requires litellm package)
    # Lazy import to avoid ImportError if litellm not installed
    from core.providers.adapters.litellm import LiteLLMProvider
    litellm_provider = LiteLLMProvider(config)

Note:
    LiteLLM adapter uses lazy imports - it won't fail at import time
    if litellm package isn't installed. Error only occurs when creating
    a LiteLLM provider without the package installed.
"""

from typing import TYPE_CHECKING

# Import the full Claude adapter implementation (always available)
from core.providers.adapters.claude import (
    ClaudeAgentProvider,
    ClaudeAgentSession,
    CLAUDE_MODELS,
)


# Lazy imports for optional providers
# These are defined here for convenience but import lazily
def _get_litellm_provider():
    """Lazy import for LiteLLMProvider."""
    from core.providers.adapters.litellm import LiteLLMProvider
    return LiteLLMProvider


def _get_litellm_session():
    """Lazy import for LiteLLMSession."""
    from core.providers.adapters.litellm import LiteLLMSession
    return LiteLLMSession


def _get_litellm_models():
    """Lazy import for LITELLM_MODELS."""
    from core.providers.adapters.litellm import LITELLM_MODELS
    return LITELLM_MODELS


# For TYPE_CHECKING, we can import directly since it won't execute
if TYPE_CHECKING:
    from core.providers.adapters.litellm import (
        LiteLLMProvider,
        LiteLLMSession,
        LITELLM_MODELS,
    )


__all__ = [
    # Claude (always available)
    "ClaudeAgentProvider",
    "ClaudeAgentSession",
    "CLAUDE_MODELS",
    # LiteLLM (lazy imports via factory or direct import from submodule)
    # Users should import directly: from core.providers.adapters.litellm import LiteLLMProvider
]
