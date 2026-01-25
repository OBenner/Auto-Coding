"""
AI Engine Provider Adapters Package
====================================

Concrete implementations of AIEngineProvider for different backends.

This package provides:
- ClaudeAgentProvider: Wraps Claude Agent SDK (default)
- LiteLLMProvider: LiteLLM unified API (100+ models)
- OpenRouterProvider: OpenRouter cloud routing (400+ models) [future]

Usage:
    from core.providers.adapters import ClaudeAgentProvider, LiteLLMProvider
    from core.providers.config import ProviderConfig

    config = ProviderConfig.from_env()
    provider = ClaudeAgentProvider(config)
    session = provider.create_session(session_config)

    # Or use LiteLLM for 100+ models
    litellm_provider = LiteLLMProvider(config)
"""

# Import the full Claude adapter implementation
from core.providers.adapters.claude import (
    ClaudeAgentProvider,
    ClaudeAgentSession,
    CLAUDE_MODELS,
)

# Import LiteLLM adapter
from core.providers.adapters.litellm import (
    LiteLLMProvider,
    LiteLLMSession,
    LITELLM_MODELS,
)


__all__ = [
    # Claude
    "ClaudeAgentProvider",
    "ClaudeAgentSession",
    "CLAUDE_MODELS",
    # LiteLLM
    "LiteLLMProvider",
    "LiteLLMSession",
    "LITELLM_MODELS",
]
