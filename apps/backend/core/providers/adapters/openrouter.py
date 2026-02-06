"""
OpenRouter Provider Adapter
===========================

Wraps OpenRouter's OpenAI-compatible API to implement the AIEngineProvider interface.
This enables access to 400+ LLMs through OpenRouter's unified routing.

OpenRouter supports models from:
- Anthropic (Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku)
- OpenAI (GPT-4, GPT-4 Turbo, GPT-3.5 Turbo)
- Google (Gemini Pro, PaLM)
- Meta (Llama 3)
- Mistral (Mistral 7B, Mixtral 8x7B)
- And many more...

Environment Variables:
    OPENROUTER_API_KEY: API key from openrouter.ai (required)
    OPENROUTER_MODEL: Model identifier (default: anthropic/claude-sonnet-4)
    OPENROUTER_BASE_URL: API base URL (default: https://openrouter.ai/api/v1)

Note:
    OpenRouter uses the OpenAI-compatible API format, so we use the openai
    Python package with a custom base_url pointing to OpenRouter's endpoint.
"""

import logging
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Optional

from core.providers.base import AgentSession, AIEngineProvider, SessionConfig
from core.providers.exceptions import (
    ProviderConfigError,
    ProviderError,
    ProviderNotInstalled,
)

if TYPE_CHECKING:
    from core.providers.config import ProviderConfig

logger = logging.getLogger(__name__)


# Default OpenRouter configuration
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4"

# Popular models available through OpenRouter
OPENROUTER_MODELS = [
    # Anthropic
    "anthropic/claude-3-opus",
    "anthropic/claude-3-sonnet",
    "anthropic/claude-3-haiku",
    "anthropic/claude-sonnet-4",
    # OpenAI
    "openai/gpt-4",
    "openai/gpt-4-turbo",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-3.5-turbo",
    # Google
    "google/gemini-pro",
    "google/gemini-1.5-pro",
    # Meta
    "meta-llama/llama-3-70b-instruct",
    "meta-llama/llama-3-8b-instruct",
    # Mistral
    "mistralai/mistral-7b-instruct",
    "mistralai/mixtral-8x7b-instruct",
    # Open source / community
    "cohere/command-r",
    "cohere/command-r-plus",
]


class OpenRouterSession(AgentSession):
    """Agent session for OpenRouter provider.

    Manages conversation history and provides message sending interface.
    Uses the OpenAI Python client with custom base_url for OpenRouter.

    Attributes:
        model: The OpenRouter model identifier
        messages: Conversation history
    """

    def __init__(
        self,
        session_id: str,
        model: str,
        api_key: str,
        system_prompt: str = "",
        base_url: str = DEFAULT_OPENROUTER_BASE_URL,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Initialize OpenRouter session.

        Args:
            session_id: Unique identifier for this session
            model: OpenRouter model identifier (e.g., anthropic/claude-sonnet-4)
            api_key: OpenRouter API key
            system_prompt: Optional system prompt
            base_url: OpenRouter API base URL
            temperature: Optional temperature for generation
            max_tokens: Optional max tokens for response
        """
        super().__init__(session_id, provider_name="openrouter")
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._messages: list[dict[str, str]] = []
        self._client: Any = None

        # Add system prompt if provided
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    @property
    def model(self) -> str:
        """Get the model identifier."""
        return self._model

    @property
    def messages(self) -> list[dict[str, str]]:
        """Get the conversation history."""
        return self._messages.copy()

    def _get_client(self) -> Any:
        """Get or create the OpenAI client for OpenRouter.

        Returns:
            OpenAI client configured for OpenRouter

        Raises:
            ProviderNotInstalled: If openai package is not installed
        """
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise ProviderNotInstalled(
                    "OpenRouter provider requires the openai package. "
                    "Install with: pip install openai\n"
                    f"Error: {e}"
                )

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                default_headers={
                    "HTTP-Referer": "https://github.com/OBenner/Auto-Coding",
                    "X-Title": "Auto-Coding",
                },
            )

        return self._client

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation.

        Args:
            content: The user message content
        """
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation.

        Args:
            content: The assistant message content
        """
        self._messages.append({"role": "assistant", "content": content})

    async def complete(self, message: str, stream: bool = True) -> AsyncIterator[str]:
        """Send a message and get streaming response.

        Args:
            message: The message to send
            stream: Whether to stream the response

        Yields:
            Response text chunks

        Raises:
            ProviderError: If completion fails
            ProviderNotInstalled: If openai package is not installed
        """
        if not self._is_active:
            raise ProviderError("Session is closed")

        client = self._get_client()

        # Add user message to history
        self.add_user_message(message)

        # Build completion kwargs
        completion_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._messages,
            "stream": stream,
        }

        if self._temperature is not None:
            completion_kwargs["temperature"] = self._temperature
        if self._max_tokens is not None:
            completion_kwargs["max_tokens"] = self._max_tokens

        try:
            if stream:
                # Streaming completion
                response = await client.chat.completions.create(**completion_kwargs)
                full_response = ""

                async for chunk in response:
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            full_response += delta.content
                            yield delta.content

                # Add assistant response to history
                if full_response:
                    self.add_assistant_message(full_response)
            else:
                # Non-streaming completion
                response = await client.chat.completions.create(**completion_kwargs)
                if hasattr(response, "choices") and response.choices:
                    content = response.choices[0].message.content
                    if content:
                        self.add_assistant_message(content)
                        yield content

        except Exception as e:
            logger.error(f"OpenRouter completion error: {e}")
            raise ProviderError(f"OpenRouter completion failed: {e}") from e

    def clear_history(self, keep_system: bool = True) -> None:
        """Clear conversation history.

        Args:
            keep_system: If True, preserve system prompt
        """
        if keep_system:
            system_msgs = [m for m in self._messages if m["role"] == "system"]
            self._messages = system_msgs
        else:
            self._messages = []

    def close(self) -> None:
        """Close the session."""
        super().close()
        self._messages = []
        self._client = None
        logger.debug(f"OpenRouter session {self.session_id} closed")


class OpenRouterProvider(AIEngineProvider):
    """OpenRouter provider implementation.

    Provides access to 400+ LLMs through OpenRouter's unified API.
    OpenRouter uses an OpenAI-compatible API, enabling easy integration
    with existing code using the openai Python package.

    Usage:
        from core.providers.adapters.openrouter import OpenRouterProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig.from_env()
        provider = OpenRouterProvider(config)

        session_config = SessionConfig(
            name="coder-session",
            system_prompt="You are an expert developer.",
            model="anthropic/claude-sonnet-4"
        )
        session = provider.create_session(session_config)

        # Send message and stream response
        async for chunk in provider.send_message("Write hello world in Python"):
            print(chunk, end="")

    Attributes:
        config: Provider configuration
    """

    def __init__(self, config: "ProviderConfig"):
        """Initialize OpenRouter provider.

        Args:
            config: Provider configuration with credentials
        """
        self._config = config
        self._active_session: Optional[OpenRouterSession] = None
        self._validation_errors: list[str] = []

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "openrouter"

    @property
    def config(self) -> "ProviderConfig":
        """Get the provider configuration."""
        return self._config

    def create_session(self, config: SessionConfig) -> OpenRouterSession:
        """Create a new OpenRouter session.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)

        Returns:
            OpenRouterSession for interacting with the LLM

        Raises:
            ProviderConfigError: If API key is not configured
            ProviderNotInstalled: If openai package is not installed
        """
        # Verify API key is available
        api_key = self._config.openrouter_api_key
        if not api_key:
            raise ProviderConfigError(
                "OpenRouter provider requires an API key. "
                "Set OPENROUTER_API_KEY environment variable."
            )

        # Verify openai package is installed
        try:
            from openai import AsyncOpenAI  # noqa: F401
        except ImportError as e:
            raise ProviderNotInstalled(
                "OpenRouter provider requires the openai package. "
                "Install with: pip install openai\n"
                f"Error: {e}"
            )

        # Get model from session config or provider config
        model = config.model or self._config.openrouter_model or DEFAULT_OPENROUTER_MODEL

        # Get base URL from provider config
        base_url = self._config.openrouter_base_url or DEFAULT_OPENROUTER_BASE_URL

        # Get from extra config if provided
        if config.extra:
            model = config.extra.get("model", model)
            base_url = config.extra.get("base_url", base_url)

        # Generate session ID
        session_id = f"openrouter-{uuid.uuid4().hex[:12]}"

        # Create session
        session = OpenRouterSession(
            session_id=session_id,
            model=model,
            api_key=api_key,
            system_prompt=config.system_prompt,
            base_url=base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        self._active_session = session

        logger.info(f"Created OpenRouter session {session_id} (model={model})")

        return session

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Uses the active session to send a message and stream back responses.

        Args:
            message: The message to send

        Yields:
            Text response chunks as they are received

        Raises:
            ProviderError: If no active session or sending fails
        """
        if not self._active_session:
            raise ProviderError("No active session. Call create_session() first.")

        if not self._active_session.is_active:
            raise ProviderError("Session is closed. Create a new session.")

        async for chunk in self._active_session.complete(message, stream=True):
            yield chunk

    def get_supported_models(self) -> list[str]:
        """Return list of commonly supported OpenRouter models.

        Note: OpenRouter supports 400+ models, this is a curated list.
        See https://openrouter.ai/models for full list.

        Returns:
            List of common model identifiers
        """
        return OPENROUTER_MODELS.copy()

    def validate_config(self) -> bool:
        """Validate provider configuration.

        OpenRouter requires an API key to be configured.

        Returns:
            True if API key is present
        """
        self._validation_errors = []

        if not self._config.openrouter_api_key:
            self._validation_errors.append(
                "OpenRouter provider requires OPENROUTER_API_KEY environment variable"
            )
            return False

        return True

    def get_validation_errors(self) -> list[str]:
        """Get detailed validation error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        return self._validation_errors.copy()

    def health_check(self) -> bool:
        """Check if provider is healthy.

        Validates config and checks if openai package is installed.

        Returns:
            True if provider can create sessions
        """
        if not self.validate_config():
            return False

        # Check if openai is installed
        try:
            from openai import AsyncOpenAI  # noqa: F401

            return True
        except ImportError:
            self._validation_errors.append("openai package is not installed")
            return False

    def get_active_session(self) -> Optional[OpenRouterSession]:
        """Get the currently active session, if any.

        Returns:
            Active OpenRouterSession or None
        """
        if self._active_session and self._active_session.is_active:
            return self._active_session
        return None

    def close(self) -> None:
        """Clean up provider resources.

        Closes any active session.
        """
        if self._active_session:
            self._active_session.close()
            self._active_session = None
        logger.debug("OpenRouter provider closed")

    def __repr__(self) -> str:
        """Return string representation of provider."""
        return (
            f"OpenRouterProvider(name={self.name!r}, "
            f"model={self._config.openrouter_model!r})"
        )
