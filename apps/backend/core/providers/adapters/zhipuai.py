"""
ZhipuAI (GLM) Provider Adapter
==============================

Wraps the ZhipuAI SDK (GLM models) to implement the AIEngineProvider interface.
This enables access to ZhipuAI's Chinese language models through a unified API.

ZhipuAI supports models:
- glm-4-flash: Free model (use glm-4-flash-250414 for testing)
- glm-4.7: Default production model
- glm-4-air: Lightweight model
- glm-4-plus: Enhanced model

Environment Variables:
    ZHIPUAI_API_KEY: ZhipuAI API key (primary)
    ZAI_API_KEY: ZhipuAI API key (alternative)
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
    "glm-4.7",              # Default production model
    "glm-4-air",            # Lightweight model
    "glm-4-plus",           # Enhanced model
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
