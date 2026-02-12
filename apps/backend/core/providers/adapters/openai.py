"""
OpenAI Direct Provider Adapter
===============================

Direct integration with OpenAI's API to implement the AIEngineProvider interface.

This provider uses the OpenAI Python SDK directly (not through LiteLLM or other
wrappers) to communicate with OpenAI's models including GPT-4, GPT-4o, o1, and
future models.

The adapter provides:
- Direct API access for optimal performance
- Streaming responses
- Support for all OpenAI models
- Standard AIEngineProvider interface
"""

import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.providers.base import AgentSession, AIEngineProvider, SessionConfig
from core.providers.exceptions import ProviderConfigError, ProviderError

if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from core.providers.config import ProviderConfig

logger = logging.getLogger(__name__)


# Supported OpenAI models
OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    "o1",
    "o1-mini",
    "o3-mini",
]


class OpenAIAgentSession(AgentSession):
    """Agent session wrapping OpenAI client.

    Provides session management for OpenAI API interactions.
    Handles streaming responses and maintains conversation state.

    Attributes:
        client: The underlying AsyncOpenAI client instance
        model: The OpenAI model being used
        system_prompt: System prompt for the session
        messages: Conversation message history
    """

    def __init__(
        self,
        session_id: str,
        client: "AsyncOpenAI",
        model: str,
        system_prompt: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """Initialize OpenAI session.

        Args:
            session_id: Unique identifier for this session
            client: AsyncOpenAI client instance
            model: OpenAI model identifier
            system_prompt: System prompt for the agent
            max_tokens: Maximum tokens for responses
            temperature: Temperature for response generation
        """
        super().__init__(session_id, provider_name="openai")
        self._client = client
        self._model = model
        self._system_prompt = system_prompt
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._messages: list[dict[str, str]] = []

        # Add system prompt as first message
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    @property
    def client(self) -> "AsyncOpenAI":
        """Get the underlying OpenAI client."""
        return self._client

    @property
    def model(self) -> str:
        """Get the model identifier."""
        return self._model

    @property
    def messages(self) -> list[dict[str, str]]:
        """Get the conversation message history."""
        return self._messages

    async def query(self, message: str) -> None:
        """Send a query to the OpenAI agent.

        Args:
            message: The message/prompt to send

        Raises:
            ProviderError: If session is closed
        """
        if not self._is_active:
            raise ProviderError("Session is closed")

        # Add user message to history
        self._messages.append({"role": "user", "content": message})

    async def receive_response(self) -> AsyncIterator[Any]:
        """Receive response messages from the OpenAI agent.

        Streams the response and updates conversation history.

        Yields:
            Response chunks from the OpenAI API

        Raises:
            ProviderError: If session is closed or API call fails
        """
        if not self._is_active:
            raise ProviderError("Session is closed")

        try:
            # Prepare API call parameters
            params: dict[str, Any] = {
                "model": self._model,
                "messages": self._messages,
                "stream": True,
            }

            if self._max_tokens is not None:
                params["max_tokens"] = self._max_tokens

            if self._temperature is not None:
                params["temperature"] = self._temperature

            # Call OpenAI API with streaming
            full_response = ""
            async for chunk in await self._client.chat.completions.create(**params):
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response += delta.content
                    yield chunk

            # Add assistant response to history
            if full_response:
                self._messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            raise ProviderError(f"OpenAI API call failed: {e}") from e

    def close(self) -> None:
        """Close the session."""
        super().close()
        logger.debug(f"OpenAI session {self.session_id} closed")


class OpenAIProvider(AIEngineProvider):
    """OpenAI direct provider implementation.

    Uses the OpenAI Python SDK directly to implement the AIEngineProvider
    interface. Supports all OpenAI models including GPT-4, GPT-4o, o1, etc.

    Usage:
        from core.providers.adapters.openai import OpenAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig.from_env()
        provider = OpenAIProvider(config)

        session_config = SessionConfig(
            name="coder-session",
            system_prompt="You are an expert developer.",
            model="gpt-4o"
        )
        session = provider.create_session(session_config)

    Attributes:
        config: Provider configuration
    """

    def __init__(self, config: "ProviderConfig"):
        """Initialize OpenAI provider.

        Args:
            config: Provider configuration with credentials
        """
        self._config = config
        self._active_session: OpenAIAgentSession | None = None
        self._validation_errors: list[str] = []
        self._client: "AsyncOpenAI | None" = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "openai"

    @property
    def config(self) -> "ProviderConfig":
        """Get the provider configuration."""
        return self._config

    def _get_client(self) -> "AsyncOpenAI":
        """Get or create AsyncOpenAI client.

        Returns:
            AsyncOpenAI client instance

        Raises:
            ProviderNotInstalled: If openai package is not installed
            ProviderConfigError: If API key is missing
        """
        if self._client is not None:
            return self._client

        if not self._config.openai_api_key:
            raise ProviderConfigError("OpenAI provider requires OPENAI_API_KEY")

        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            from core.providers.exceptions import ProviderNotInstalled

            raise ProviderNotInstalled(
                "OpenAI provider requires openai package. "
                "Install with: pip install openai"
            ) from e

        # Create client
        client_kwargs: dict[str, Any] = {
            "api_key": self._config.openai_api_key,
        }

        # Add optional base URL if configured
        if self._config.openai_base_url:
            client_kwargs["base_url"] = self._config.openai_base_url

        self._client = AsyncOpenAI(**client_kwargs)
        return self._client

    def create_session(
        self,
        config: SessionConfig,
        project_dir: Path | None = None,
        spec_dir: Path | None = None,
        agent_type: str = "coder",
        max_thinking_tokens: int | None = None,
        output_format: dict | None = None,
        agents: dict | None = None,
    ) -> OpenAIAgentSession:
        """Create a new OpenAI agent session.

        Creates an AsyncOpenAI client and wraps it in an OpenAIAgentSession
        for the provider abstraction.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)
            project_dir: Working directory for the agent (not used for OpenAI)
            spec_dir: Spec directory for this session (not used for OpenAI)
            agent_type: Agent type identifier (not used for OpenAI)
            max_thinking_tokens: Token budget for extended thinking (not used)
            output_format: Optional structured output format
            agents: Optional dict of subagent definitions (not used)

        Returns:
            OpenAIAgentSession wrapping the OpenAI client

        Raises:
            ProviderConfigError: If configuration is invalid
            ProviderError: If session creation fails
        """
        # Get client (will validate config)
        client = self._get_client()

        # Determine model to use
        model = config.model or self._config.openai_model
        if not model:
            raise ProviderConfigError(
                "No model specified in session config or provider config"
            )

        # Create session
        session_id = str(uuid.uuid4())
        session = OpenAIAgentSession(
            session_id=session_id,
            client=client,
            model=model,
            system_prompt=config.system_prompt,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

        self._active_session = session
        logger.info(f"Created OpenAI session {session_id} with model {model}")

        return session

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Args:
            message: The message to send to the AI

        Yields:
            Response chunks as they are received

        Raises:
            ProviderError: If no active session or message sending fails
        """
        if self._active_session is None:
            raise ProviderError("No active session. Call create_session first.")

        await self._active_session.query(message)
        async for chunk in self._active_session.receive_response():
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_supported_models(self) -> list[str]:
        """Return list of supported model identifiers.

        Returns:
            List of OpenAI model names
        """
        return OPENAI_MODELS.copy()

    def validate_config(self) -> bool:
        """Validate provider configuration.

        Checks that API key is present.

        Returns:
            True if configuration is valid
        """
        errors = self.get_validation_errors()
        return len(errors) == 0

    def get_validation_errors(self) -> list[str]:
        """Get detailed validation error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self._config.openai_api_key:
            errors.append("OpenAI provider requires OPENAI_API_KEY environment variable")

        if not self._config.openai_model:
            errors.append("OpenAI provider requires OPENAI_MODEL environment variable")

        return errors

    def close(self) -> None:
        """Clean up provider resources."""
        if self._active_session:
            self._active_session.close()
            self._active_session = None

        if self._client:
            # AsyncOpenAI client doesn't need explicit cleanup
            self._client = None

        logger.debug("OpenAI provider closed")
