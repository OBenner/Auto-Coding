"""
LiteLLM Provider Adapter
========================

Wraps the LiteLLM library to implement the AIEngineProvider interface.
This enables access to 100+ LLMs through a unified API.

LiteLLM supports models from:
- OpenAI (gpt-4, gpt-3.5-turbo)
- Anthropic (claude-3-opus, claude-3-sonnet)
- Google (gemini-pro)
- Azure OpenAI
- AWS Bedrock
- Cohere, Replicate, and many more

Environment Variables:
    LITELLM_MODEL: Model identifier (e.g., gpt-4, anthropic/claude-3-opus)
    LITELLM_API_BASE: Optional custom API base URL
    LITELLM_API_KEY: Optional API key (depends on model provider)

Provider-specific keys are also supported:
    OPENAI_API_KEY: For OpenAI models
    ANTHROPIC_API_KEY: For Anthropic models
    GOOGLE_API_KEY: For Google models
    etc.
"""

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from core.providers.adapters.openai_compat import (
    assistant_message_from_tool_calls,
    format_openai_tool_schema,
    parse_openai_tool_calls,
)
from core.providers.base import (
    AgentSession,
    AIEngineProvider,
    ProviderToolCallResponse,
    SessionConfig,
)
from core.providers.exceptions import (
    ProviderConfigError,
    ProviderError,
    ProviderNotInstalled,
)

if TYPE_CHECKING:
    from core.providers.config import ProviderConfig

logger = logging.getLogger(__name__)


# Common models available through LiteLLM
LITELLM_MODELS = [
    # OpenAI
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    # Anthropic
    "anthropic/claude-3-opus-20240229",
    "anthropic/claude-3-sonnet-20240229",
    "anthropic/claude-3-haiku-20240307",
    # Google
    "gemini/gemini-pro",
    "gemini/gemini-1.5-pro",
    # Azure
    "azure/gpt-4",
    "azure/gpt-35-turbo",
    # Bedrock
    "bedrock/anthropic.claude-3-sonnet",
    # Ollama (local)
    "ollama/llama3",
    "ollama/mistral",
    "ollama/codellama",
]


class LiteLLMSession(AgentSession):
    """Agent session for LiteLLM provider.

    Manages conversation history and provides message sending interface.
    Unlike Claude SDK, LiteLLM is stateless so we maintain state here.

    Attributes:
        model: The LiteLLM model identifier
        messages: Conversation history
    """

    def __init__(
        self,
        session_id: str,
        model: str,
        system_prompt: str = "",
        api_base: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """Initialize LiteLLM session.

        Args:
            session_id: Unique identifier for this session
            model: LiteLLM model identifier
            system_prompt: Optional system prompt
            api_base: Optional custom API base URL
            api_key: Optional API key
            temperature: Optional temperature for generation
            max_tokens: Optional max tokens for response
        """
        super().__init__(session_id, provider_name="litellm")
        self._model = model
        self._api_base = api_base
        self._api_key = api_key
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._messages: list[dict[str, Any]] = []

        # Add system prompt if provided
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    @property
    def model(self) -> str:
        """Get the model identifier."""
        return self._model

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Get the conversation history."""
        return self._messages.copy()

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

    def add_tool_result(self, tool_call_id: str, name: str, result: Any) -> None:
        """Append a provider-native tool result to the session history."""
        content = result if isinstance(result, str) else json.dumps(result)
        self._messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": content,
            }
        )

    def _completion_kwargs(self, *, stream: bool) -> dict[str, Any]:
        completion_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._messages,
            "stream": stream,
        }

        if self._api_base:
            completion_kwargs["api_base"] = self._api_base
        if self._api_key:
            completion_kwargs["api_key"] = self._api_key
        if self._temperature is not None:
            completion_kwargs["temperature"] = self._temperature
        if self._max_tokens is not None:
            completion_kwargs["max_tokens"] = self._max_tokens

        return completion_kwargs

    async def complete(self, message: str, stream: bool = True) -> AsyncIterator[str]:
        """Send a message and get streaming response.

        Args:
            message: The message to send
            stream: Whether to stream the response

        Yields:
            Response text chunks

        Raises:
            ProviderError: If completion fails
            ProviderNotInstalled: If litellm is not installed
        """
        if not self._is_active:
            raise ProviderError("Session is closed")

        try:
            import litellm
        except ImportError as e:
            raise ProviderNotInstalled(
                "LiteLLM provider requires the litellm package. "
                "Install with: pip install litellm\n"
                f"Error: {e}"
            )

        # Add user message to history
        self.add_user_message(message)

        completion_kwargs = self._completion_kwargs(stream=stream)

        try:
            if stream:
                # Streaming completion
                response = await litellm.acompletion(**completion_kwargs)
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
                response = await litellm.acompletion(**completion_kwargs)
                if hasattr(response, "choices") and response.choices:
                    content = response.choices[0].message.content
                    if content:
                        self.add_assistant_message(content)
                        yield content

        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}")
            raise ProviderError(f"LiteLLM completion failed: {e}") from e

    async def complete_with_tool_calls(
        self,
        message: str | None,
        tools: list[dict[str, Any]],
    ) -> ProviderToolCallResponse:
        """Send a non-streaming LiteLLM request with function tools."""
        if not self._is_active:
            raise ProviderError("Session is closed")

        try:
            import litellm
        except ImportError as e:
            raise ProviderNotInstalled(
                "LiteLLM provider requires the litellm package. "
                "Install with: pip install litellm\n"
                f"Error: {e}"
            )

        if message:
            self.add_user_message(message)

        completion_kwargs = self._completion_kwargs(stream=False)
        completion_kwargs["tools"] = [format_openai_tool_schema(tool) for tool in tools]
        completion_kwargs["tool_choice"] = "auto"

        try:
            response = await litellm.acompletion(**completion_kwargs)
            if not hasattr(response, "choices") or not response.choices:
                return ProviderToolCallResponse(content="")

            message_obj = response.choices[0].message
            content = str(getattr(message_obj, "content", "") or "")
            tool_calls = parse_openai_tool_calls(message_obj)
            if content or tool_calls:
                self._messages.append(
                    assistant_message_from_tool_calls(
                        content=content,
                        tool_calls=tool_calls,
                    )
                )
            return ProviderToolCallResponse(
                content=content,
                tool_calls=tuple(tool_calls),
            )
        except Exception as e:
            logger.error(f"LiteLLM tool-call completion error: {e}")
            raise ProviderError(f"LiteLLM tool-call completion failed: {e}") from e

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
        logger.debug(f"LiteLLM session {self.session_id} closed")


class LiteLLMProvider(AIEngineProvider):
    """LiteLLM provider implementation.

    Provides access to 100+ LLMs through the LiteLLM unified API.
    This enables using OpenAI, Anthropic, Google, Azure, and many other
    providers through a single interface.

    Usage:
        from core.providers.adapters.litellm import LiteLLMProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig.from_env()
        provider = LiteLLMProvider(config)

        session_config = SessionConfig(
            name="coder-session",
            system_prompt="You are an expert developer.",
            model="gpt-4"
        )
        session = provider.create_session(session_config)

        # Send message and stream response
        async for chunk in provider.send_message("Write hello world in Python"):
            print(chunk, end="")

    Attributes:
        config: Provider configuration
    """

    def __init__(self, config: "ProviderConfig"):
        """Initialize LiteLLM provider.

        Args:
            config: Provider configuration with credentials
        """
        self._config = config
        self._active_session: LiteLLMSession | None = None
        self._validation_errors: list[str] = []

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "litellm"

    @property
    def config(self) -> "ProviderConfig":
        """Get the provider configuration."""
        return self._config

    def create_session(self, config: SessionConfig) -> LiteLLMSession:
        """Create a new LiteLLM session.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)

        Returns:
            LiteLLMSession for interacting with the LLM

        Raises:
            ProviderConfigError: If model is not configured
            ProviderNotInstalled: If litellm package is not installed
        """
        # Get model from session config or provider config
        model = config.model or self._config.litellm_model
        if not model:
            raise ProviderConfigError(
                "LiteLLM provider requires a model. "
                "Set LITELLM_MODEL environment variable or pass model in SessionConfig."
            )

        # Verify litellm is installed
        try:
            # Optional: litellm is an optional runtime dependency
            import litellm  # noqa: F401
        except ImportError as e:
            raise ProviderNotInstalled(
                "LiteLLM provider requires the litellm package. "
                "Install with: pip install litellm\n"
                f"Error: {e}"
            )

        # Get optional settings
        api_base = self._config.litellm_api_base or None
        api_key = self._config.litellm_api_key or None

        # Get from extra config if provided
        if config.extra:
            api_base = config.extra.get("api_base", api_base)
            api_key = config.extra.get("api_key", api_key)

        # Generate session ID
        session_id = f"litellm-{uuid.uuid4().hex[:12]}"

        # Create session
        session = LiteLLMSession(
            session_id=session_id,
            model=model,
            system_prompt=config.system_prompt,
            api_base=api_base,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        self._active_session = session

        logger.info(f"Created LiteLLM session {session_id} (model={model})")

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
        """Return list of commonly supported LiteLLM models.

        Note: LiteLLM supports 100+ models, this is a curated list.
        See https://docs.litellm.ai/docs/providers for full list.

        Returns:
            List of common model identifiers
        """
        return LITELLM_MODELS.copy()

    def validate_config(self) -> bool:
        """Validate provider configuration.

        LiteLLM requires at minimum a model to be specified.
        API keys depend on the model provider being used.

        Returns:
            True if minimum configuration is present
        """
        self._validation_errors = []

        if not self._config.litellm_model:
            self._validation_errors.append(
                "LiteLLM provider requires LITELLM_MODEL environment variable"
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

        Validates config and checks if litellm is installed.

        Returns:
            True if provider can create sessions
        """
        if not self.validate_config():
            return False

        # Check if litellm is installed
        try:
            # Optional: litellm is an optional runtime dependency
            import litellm  # noqa: F401

            return True
        except ImportError:
            self._validation_errors.append("litellm package is not installed")
            return False

    def get_active_session(self) -> LiteLLMSession | None:
        """Get the currently active session, if any.

        Returns:
            Active LiteLLMSession or None
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
        logger.debug("LiteLLM provider closed")

    def __repr__(self) -> str:
        """Return string representation of provider."""
        return (
            f"LiteLLMProvider(name={self.name!r}, model={self._config.litellm_model!r})"
        )
