"""
AI Engine Provider Adapters Package
====================================

Concrete implementations of AIEngineProvider for different backends.

This package provides:
- ClaudeAgentProvider: Wraps Claude Agent SDK (default)
- LiteLLMProvider: LiteLLM unified API (100+ models)
- OpenRouterProvider: OpenRouter cloud routing (400+ models)

Usage:
    from core.providers.adapters import ClaudeAgentProvider
    from core.providers.config import ProviderConfig

    config = ProviderConfig.from_env()
    provider = ClaudeAgentProvider(config)
    session = provider.create_session(session_config)
"""

from typing import TYPE_CHECKING, Any, AsyncIterator

from core.providers.base import AgentSession, AIEngineProvider, SessionConfig
from core.providers.exceptions import ProviderNotInstalled

if TYPE_CHECKING:
    from core.providers.config import ProviderConfig


class ClaudeAgentProvider(AIEngineProvider):
    """Claude Agent SDK provider implementation.

    Wraps the Claude Agent SDK to provide AI engine functionality.
    This is the default and recommended provider for Auto-Claude.

    Note: Full implementation in adapters/claude.py (subtask-2-2).
    This stub class ensures the package structure is valid.

    Attributes:
        config: Provider configuration
    """

    def __init__(self, config: "ProviderConfig"):
        """Initialize Claude provider.

        Args:
            config: Provider configuration with credentials
        """
        self._config = config
        self._session: AgentSession | None = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "claude"

    def create_session(self, config: SessionConfig) -> AgentSession:
        """Create a new agent session.

        Args:
            config: Session configuration

        Returns:
            AgentSession instance

        Raises:
            NotImplementedError: Full implementation in subtask-2-2
        """
        raise NotImplementedError(
            "ClaudeAgentProvider.create_session() not yet implemented. "
            "See subtask-2-2 for full implementation."
        )

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream response.

        Args:
            message: Message to send

        Yields:
            Response chunks

        Raises:
            NotImplementedError: Full implementation in subtask-2-2
        """
        raise NotImplementedError(
            "ClaudeAgentProvider.send_message() not yet implemented. "
            "See subtask-2-2 for full implementation."
        )
        # Yield nothing - this is just for type checker
        yield ""

    def get_supported_models(self) -> list[str]:
        """Return supported Claude models.

        Returns:
            List of supported model identifiers
        """
        return [
            "claude-sonnet-4-20250514",
            "claude-sonnet-4-5-20250929",
            "claude-opus-4-20250514",
        ]

    def validate_config(self) -> bool:
        """Validate provider configuration.

        Returns:
            True if configuration is valid
        """
        # Claude SDK uses OAuth, API key is optional
        return True


__all__ = [
    "ClaudeAgentProvider",
]
