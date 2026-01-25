"""
AI Engine Provider Adapters Package
====================================

Concrete implementations of AIEngineProvider for different backends.

This package provides:
- ClaudeAgentProvider: Wraps Claude Agent SDK (default)
- LiteLLMProvider: LiteLLM unified API (100+ models) [future]
- OpenRouterProvider: OpenRouter cloud routing (400+ models) [future]

Usage:
    from core.providers.adapters import ClaudeAgentProvider
    from core.providers.config import ProviderConfig

    config = ProviderConfig.from_env()
    provider = ClaudeAgentProvider(config)
    session = provider.create_session(session_config)
"""

# Import the full Claude adapter implementation
from core.providers.adapters.claude import (
    ClaudeAgentProvider,
    ClaudeAgentSession,
    CLAUDE_MODELS,
)


__all__ = [
    "ClaudeAgentProvider",
    "ClaudeAgentSession",
    "CLAUDE_MODELS",
]
