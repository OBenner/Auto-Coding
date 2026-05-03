"""
AI Engine Provider Abstract Base Class
======================================

Defines the interface for all AI engine providers.
Each provider (Claude, LiteLLM, OpenRouter) must implement this interface.

This abstraction enables:
- Pluggable AI backends without changing agent code
- Consistent interface for session management and messaging
- Provider-specific implementations hidden behind common API
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ProviderToolCall:
    """Provider-native tool/function call normalized for runtime adapters."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderToolCallResponse:
    """Provider response containing optional text and tool/function calls."""

    content: str
    tool_calls: tuple[ProviderToolCall, ...] = ()


@dataclass
class SessionConfig:
    """Configuration for creating an agent session.

    Attributes:
        name: Session name/identifier
        system_prompt: System prompt for the agent
        provider: Provider name (e.g., 'claude', 'litellm', 'openrouter', 'zhipuai')
        model: Model identifier (provider-specific)
        max_tokens: Maximum tokens for responses
        temperature: Temperature for response generation
        tools: List of tools available to the agent
        working_directory: Working directory for file operations
        allowed_commands: List of allowed bash commands
        extra: Provider-specific extra configuration
    """

    name: str
    system_prompt: str = ""
    provider: str | None = None
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    tools: list[str] | None = None
    working_directory: str | None = None
    allowed_commands: list[str] | None = None
    extra: dict[str, Any] | None = None


class AgentSession:
    """Base class for agent sessions.

    Represents an active session with an AI provider.
    Subclasses implement provider-specific session handling.
    """

    def __init__(self, session_id: str, provider_name: str):
        """Initialize session.

        Args:
            session_id: Unique identifier for this session
            provider_name: Name of the provider (e.g., 'claude', 'litellm')
        """
        self.session_id = session_id
        self.provider_name = provider_name
        self._is_active = True

    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        return self._is_active

    def close(self) -> None:
        """Close the session."""
        self._is_active = False
        logger.debug(f"Session {self.session_id} closed")


class AIEngineProvider(ABC):
    """Abstract base class for AI engine providers.

    All AI engine providers must implement this interface to work
    with the Auto-Code agent system. This abstraction enables:

    - Swapping between Claude, LiteLLM, OpenRouter, etc.
    - Consistent session management across providers
    - Unified error handling via provider exceptions

    Example implementation:
        class ClaudeAgentProvider(AIEngineProvider):
            def __init__(self, config: ProviderConfig):
                self._config = config
                self._client = None

            def create_session(self, config: SessionConfig) -> AgentSession:
                # Create Claude-specific session
                ...

            async def send_message(self, message: str) -> AsyncIterator[str]:
                # Send message to Claude and stream response
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'claude', 'litellm', 'openrouter')."""
        pass

    @abstractmethod
    def create_session(self, config: SessionConfig) -> AgentSession:
        """Create a new agent session.

        Args:
            config: Session configuration including system prompt, model, etc.

        Returns:
            AgentSession instance for interacting with the agent

        Raises:
            ProviderError: If session creation fails
            ProviderConfigError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Args:
            message: The message to send to the AI

        Yields:
            Response chunks as they are received

        Raises:
            ProviderError: If message sending fails
        """
        pass

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """Return list of supported model identifiers.

        Returns:
            List of model names/identifiers this provider supports
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration.

        Checks that all required credentials and settings are present.

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    def get_validation_errors(self) -> list[str]:
        """Get detailed validation error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        return []

    def health_check(self) -> bool:
        """Check if provider is healthy and can accept requests.

        Default implementation just validates config.
        Subclasses can override to add connectivity checks.

        Returns:
            True if provider is healthy
        """
        return self.validate_config()

    # Abstract base class: optional cleanup hook with default no-op.
    # Not marked @abstractmethod since cleanup is optional.
    def close(self) -> None:  # noqa: B027
        """Clean up provider resources.

        Called when provider is no longer needed.
        Default implementation does nothing.
        Subclasses should override if they need cleanup.
        """

    def __repr__(self) -> str:
        """Return string representation of provider."""
        return f"{self.__class__.__name__}(name={self.name!r})"
