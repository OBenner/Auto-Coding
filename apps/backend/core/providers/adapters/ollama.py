"""
Ollama Local Model Provider Adapter
====================================

Integration with Ollama's local model API to implement the AIEngineProvider interface.

Ollama provides a local inference server with an OpenAI-compatible API, allowing
you to run models like Llama, Mistral, CodeLlama, and others on your own hardware.

This adapter uses the OpenAI Python SDK with Ollama's OpenAI-compatible endpoint
to provide:
- Local model execution (no external API calls)
- Privacy-first operation (data stays on your machine)
- OpenAI-compatible interface
- Support for all Ollama models

Default Configuration:
- Base URL: http://localhost:11434/v1
- API Key: "ollama" (dummy key required by OpenAI SDK)
- Model: Must be specified via OLLAMA_MODEL environment variable

Setup:
1. Install Ollama: https://ollama.ai
2. Pull a model: ollama pull llama2
3. Set OLLAMA_MODEL=llama2 in .env
4. Optional: Set OLLAMA_BASE_URL if using non-default port
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


# Default Ollama configuration
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"  # Dummy key required by OpenAI SDK

# Popular Ollama models (non-exhaustive)
OLLAMA_MODELS = [
    "llama2",
    "llama3",
    "mistral",
    "codellama",
    "phi",
    "gemma",
    "qwen",
    "deepseek-coder",
]


class OllamaAgentSession(AgentSession):
    """Agent session wrapping Ollama client.

    Provides session management for Ollama API interactions using
    the OpenAI-compatible interface. Handles streaming responses and
    maintains conversation state.

    Attributes:
        client: The underlying AsyncOpenAI client instance (configured for Ollama)
        model: The Ollama model being used
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
        """Initialize Ollama session.

        Args:
            session_id: Unique identifier for this session
            client: AsyncOpenAI client instance (configured for Ollama)
            model: Ollama model identifier
            system_prompt: System prompt for the agent
            max_tokens: Maximum tokens for responses
            temperature: Temperature for response generation
        """
        super().__init__(session_id, provider_name="ollama")
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
        """Send a query to the Ollama agent.

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
        """Receive response messages from the Ollama agent.

        Streams the response and updates conversation history.

        Yields:
            Response chunks from the Ollama API

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

            # Call Ollama API with streaming (via OpenAI-compatible endpoint)
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
            raise ProviderError(f"Ollama API call failed: {e}") from e

    def close(self) -> None:
        """Close the session."""
        super().close()
        logger.debug(f"Ollama session {self.session_id} closed")


class OllamaProvider(AIEngineProvider):
    """Ollama local model provider implementation.

    Uses the OpenAI Python SDK with Ollama's OpenAI-compatible endpoint
    to implement the AIEngineProvider interface. Supports all Ollama models
    for local, privacy-first execution.

    Usage:
        from core.providers.adapters.ollama import OllamaProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig.from_env()
        provider = OllamaProvider(config)

        session_config = SessionConfig(
            name="coder-session",
            system_prompt="You are an expert developer.",
            model="llama2"
        )
        session = provider.create_session(session_config)

    Attributes:
        config: Provider configuration
    """

    def __init__(self, config: "ProviderConfig"):
        """Initialize Ollama provider.

        Args:
            config: Provider configuration with credentials and settings
        """
        self._config = config
        self._active_session: OllamaAgentSession | None = None
        self._validation_errors: list[str] = []
        self._client: "AsyncOpenAI | None" = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "ollama"

    @property
    def config(self) -> "ProviderConfig":
        """Get the provider configuration."""
        return self._config

    def _get_client(self) -> "AsyncOpenAI":
        """Get or create AsyncOpenAI client configured for Ollama.

        Returns:
            AsyncOpenAI client instance configured for Ollama

        Raises:
            ProviderNotInstalled: If openai package is not installed
            ProviderConfigError: If model is not specified
        """
        if self._client is not None:
            return self._client

        if not self._config.ollama_model:
            raise ProviderConfigError("Ollama provider requires OLLAMA_MODEL")

        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            from core.providers.exceptions import ProviderNotInstalled

            raise ProviderNotInstalled(
                "Ollama provider requires openai package. "
                "Install with: pip install openai"
            ) from e

        # Ensure base URL ends with /v1 for OpenAI compatibility
        base_url = self._config.ollama_base_url or DEFAULT_OLLAMA_BASE_URL
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        # Create client with Ollama-specific configuration
        self._client = AsyncOpenAI(
            api_key=OLLAMA_API_KEY,  # Dummy key required by OpenAI SDK
            base_url=base_url,
        )

        logger.debug(f"Created Ollama client with base_url: {base_url}")
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
    ) -> OllamaAgentSession:
        """Create a new Ollama agent session.

        Creates an AsyncOpenAI client configured for Ollama and wraps it
        in an OllamaAgentSession for the provider abstraction.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)
            project_dir: Working directory for the agent (not used for Ollama)
            spec_dir: Spec directory for this session (not used for Ollama)
            agent_type: Agent type identifier (not used for Ollama)
            max_thinking_tokens: Token budget for extended thinking (not used)
            output_format: Optional structured output format
            agents: Optional dict of subagent definitions (not used)

        Returns:
            OllamaAgentSession wrapping the OpenAI client

        Raises:
            ProviderConfigError: If configuration is invalid
            ProviderError: If session creation fails
        """
        # Get client (will validate config)
        client = self._get_client()

        # Determine model to use
        model = config.model or self._config.ollama_model
        if not model:
            raise ProviderConfigError(
                "No model specified in session config or provider config"
            )

        # Create session
        session_id = str(uuid.uuid4())
        session = OllamaAgentSession(
            session_id=session_id,
            client=client,
            model=model,
            system_prompt=config.system_prompt,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

        self._active_session = session
        logger.info(f"Created Ollama session {session_id} with model {model}")

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

        Note: This returns a list of popular Ollama models, but Ollama
        supports many more. Use 'ollama list' to see available models.

        Returns:
            List of popular Ollama model names
        """
        return OLLAMA_MODELS.copy()

    def validate_config(self) -> bool:
        """Validate provider configuration.

        Checks that model is specified.

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

        if not self._config.ollama_model:
            errors.append("Ollama provider requires OLLAMA_MODEL environment variable")

        return errors

    def close(self) -> None:
        """Clean up provider resources."""
        if self._active_session:
            self._active_session.close()
            self._active_session = None

        if self._client:
            # AsyncOpenAI client doesn't need explicit cleanup
            self._client = None

        logger.debug("Ollama provider closed")
