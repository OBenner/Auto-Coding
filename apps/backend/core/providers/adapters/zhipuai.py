"""
ZhipuAI (GLM) Provider Adapter
==============================

Wraps the ZhipuAI SDK (GLM models) to implement the AIEngineProvider interface.
Enables access to ZhipuAI's Chinese language models through a unified API.

ZhipuAI supports models:
- glm-4-flash: Free model (use glm-4-flash-250414 for testing)
- glm-4.7: Default production model
- glm-4-air: Lightweight model
- glm-4-plus: Enhanced model

Environment Variables:
    ZHIPUAI_API_KEY: ZhipuAI API key
    ZHIPUAI_MODEL: Model identifier (default: glm-4.7)

Provider Capabilities:
- Streaming responses (async iterator)
- Function calling (tool use)
- Multi-modal: text, vision, images, video, embeddings
"""

import logging
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from core.providers.base import AgentSession, AIEngineProvider, SessionConfig
from core.providers.exceptions import (
    ProviderConfigError,
    ProviderError,
    ProviderNotInstalled,
)

if TYPE_CHECKING:
    from core.providers.config import ProviderConfig

logger = logging.getLogger(__name__)


# Common models available through ZhipuAI
ZHIPUAI_MODELS = [
    "glm-4-flash-250414",  # Free model
    "glm-4.7",  # Default production model
    "glm-4-air",  # Lightweight model
    "glm-4-plus",  # Enhanced model
]


class ZhipuAISession(AgentSession):
    """Agent session for ZhipuAI provider.

    Manages conversation history and provides message sending interface.
    ZhipuAI SDK is stateless so we maintain state here.

    Attributes:
        model: The ZhipuAI model identifier
        messages: Conversation history
    """

    def __init__(
        self,
        session_id: str,
        model: str,
        api_key: str,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """Initialize ZhipuAI session.

        Args:
            session_id: Unique identifier for this session
            model: ZhipuAI model identifier
            api_key: ZhipuAI API key
            system_prompt: Optional system prompt
            temperature: Optional temperature for generation
            max_tokens: Optional max tokens for response
        """
        super().__init__(session_id, provider_name="zhipuai")
        self._model = model
        self._api_key = api_key
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
            ProviderNotInstalled: If zai-sdk is not installed
        """
        if not self._is_active:
            raise ProviderError("Session is closed")

        try:
            from zai import ZhipuAiClient
        except ImportError as e:
            raise ProviderNotInstalled(
                "ZhipuAI provider requires the zai-sdk package. "
                "Install with: pip install zai-sdk>=0.2.2\n"
                f"Error: {e}"
            )

        # Initialize client if needed
        if self._client is None:
            self._client = ZhipuAiClient(api_key=self._api_key)

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
                response = await self._client.chat.completions.create(
                    **completion_kwargs
                )
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
                response = await self._client.chat.completions.create(
                    **completion_kwargs
                )
                if hasattr(response, "choices") and response.choices:
                    content = response.choices[0].message.content
                    if content:
                        self.add_assistant_message(content)
                        yield content

        except Exception as e:
            logger.error(f"ZhipuAI completion error: {e}")
            raise ProviderError(f"ZhipuAI completion failed: {e}") from e

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
        logger.debug(f"ZhipuAI session {self.session_id} closed")


class ZhipuAIProvider(AIEngineProvider):
    """ZhipuAI provider implementation.

    Provides access to ZhipuAI's GLM models (Chinese language models).
    Supports streaming responses, function calling, and multi-modal capabilities.

    Usage:
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig.from_env()
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(
            name="coder-session",
            system_prompt="You are an expert developer.",
            model="glm-4-flash-250414"
        )
        session = provider.create_session(session_config)

        # Send message and stream response
        async for chunk in provider.send_message("Write hello world in Python"):
            print(chunk, end="")

    Attributes:
        config: Provider configuration
    """

    def __init__(self, config: "ProviderConfig"):
        """Initialize ZhipuAI provider.

        Args:
            config: Provider configuration with credentials
        """
        self._config = config
        self._active_session: ZhipuAISession | None = None
        self._validation_errors: list[str] = []

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "zhipuai"

    @property
    def config(self) -> "ProviderConfig":
        """Get the provider configuration."""
        return self._config

    def create_session(self, config: SessionConfig) -> ZhipuAISession:
        """Create a new ZhipuAI session.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)

        Returns:
            ZhipuAISession for interacting with the GLM model

        Raises:
            ProviderConfigError: If API key or model is not configured
            ProviderNotInstalled: If zai-sdk package is not installed
        """
        # Get API key from config
        api_key = self._config.zhipuai_api_key
        if not api_key:
            raise ProviderConfigError(
                "ZhipuAI provider requires an API key. "
                "Set ZHIPUAI_API_KEY environment variable."
            )

        # Get model from session config or provider config
        model = config.model or self._config.zhipuai_model
        if not model:
            raise ProviderConfigError(
                "ZhipuAI provider requires a model. "
                "Set ZHIPUAI_MODEL environment variable or pass model in SessionConfig."
            )

        # Verify zai-sdk is installed
        try:
            from zai import ZhipuAiClient  # noqa: F401
        except ImportError as e:
            raise ProviderNotInstalled(
                "ZhipuAI provider requires the zai-sdk package. "
                "Install with: pip install zai-sdk>=0.2.2\n"
                f"Error: {e}"
            )

        # Generate session ID
        session_id = f"zhipuai-{uuid.uuid4().hex[:12]}"

        # Create session
        session = ZhipuAISession(
            session_id=session_id,
            model=model,
            api_key=api_key,
            system_prompt=config.system_prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        self._active_session = session

        logger.info(f"Created ZhipuAI session {session_id} (model={model})")

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
        """Return list of commonly supported ZhipuAI models.

        Returns:
            List of model identifiers
        """
        return ZHIPUAI_MODELS.copy()

    def validate_config(self) -> bool:
        """Validate provider configuration.

        ZhipuAI requires an API key and a model to be specified.

        Returns:
            True if minimum configuration is present
        """
        self._validation_errors = []

        # Check for API key
        api_key = self._config.zhipuai_api_key
        if not api_key:
            self._validation_errors.append(
                "ZhipuAI provider requires ZHIPUAI_API_KEY environment variable"
            )

        # Check for model
        if not self._config.zhipuai_model:
            self._validation_errors.append(
                "ZhipuAI provider requires ZHIPUAI_MODEL environment variable"
            )

        return len(self._validation_errors) == 0

    def get_validation_errors(self) -> list[str]:
        """Get detailed validation error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        return self._validation_errors.copy()

    def health_check(self) -> bool:
        """Check if provider is healthy.

        Validates config and checks if zai-sdk is installed.

        Returns:
            True if provider can create sessions
        """
        if not self.validate_config():
            return False

        # Check if zai-sdk is installed
        try:
            from zai import ZhipuAiClient  # noqa: F401

            return True
        except ImportError:
            self._validation_errors.append("zai-sdk package is not installed")
            return False

    def get_active_session(self) -> ZhipuAISession | None:
        """Get the currently active session, if any.

        Returns:
            Active ZhipuAISession or None
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
        logger.debug("ZhipuAI provider closed")

    def __repr__(self) -> str:
        """Return string representation of provider."""
        return (
            f"ZhipuAIProvider(name={self.name!r}, model={self._config.zhipuai_model!r})"
        )
