"""
OpenAI Provider Adapter
========================

Wraps the OpenAI API to implement the AIEngineProvider interface.
This enables direct access to OpenAI models (GPT-4o, o1, o3, etc.).

Environment Variables:
    OPENAI_API_KEY: API key from platform.openai.com (required)
    OPENAI_MODEL: Model identifier (default: gpt-4o)
    OPENAI_BASE_URL: Optional custom API base URL
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

DEFAULT_OPENAI_MODEL = "gpt-4o"

# Popular OpenAI models
OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "o1",
    "o1-mini",
    "o3",
    "o3-mini",
    "gpt-3.5-turbo",
]


class OpenAISession(AgentSession):
    """Agent session for OpenAI provider.

    Manages conversation history and provides message sending interface.
    """

    def __init__(
        self,
        session_id: str,
        model: str,
        api_key: str,
        system_prompt: str = "",
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        super().__init__(session_id, provider_name="openai")
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._messages: list[dict[str, str]] = []
        self._client: Any = None

        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    @property
    def model(self) -> str:
        return self._model

    @property
    def messages(self) -> list[dict[str, str]]:
        return self._messages.copy()

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise ProviderNotInstalled(
                    "OpenAI provider requires the openai package. "
                    "Install with: pip install openai\n"
                    f"Error: {e}"
                )

            client_kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                client_kwargs["base_url"] = self._base_url

            self._client = AsyncOpenAI(**client_kwargs)

        return self._client

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})

    async def complete(self, message: str, stream: bool = True) -> AsyncIterator[str]:
        if not self._is_active:
            raise ProviderError("Session is closed")

        client = self._get_client()
        self.add_user_message(message)

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
                response = await client.chat.completions.create(**completion_kwargs)
                full_response = ""

                async for chunk in response:
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            full_response += delta.content
                            yield delta.content

                if full_response:
                    self.add_assistant_message(full_response)
            else:
                response = await client.chat.completions.create(**completion_kwargs)
                if hasattr(response, "choices") and response.choices:
                    content = response.choices[0].message.content
                    if content:
                        self.add_assistant_message(content)
                        yield content

        except Exception as e:
            logger.error(f"OpenAI completion error: {e}")
            raise ProviderError(f"OpenAI completion failed: {e}") from e

    def clear_history(self, keep_system: bool = True) -> None:
        if keep_system:
            system_msgs = [m for m in self._messages if m["role"] == "system"]
            self._messages = system_msgs
        else:
            self._messages = []

    def close(self) -> None:
        super().close()
        self._messages = []
        self._client = None
        logger.debug(f"OpenAI session {self.session_id} closed")


class OpenAIProvider(AIEngineProvider):
    """OpenAI provider implementation.

    Provides direct access to OpenAI models (GPT-4o, o1, o3, etc.).
    """

    def __init__(self, config: "ProviderConfig"):
        self._config = config
        self._active_session: OpenAISession | None = None
        self._validation_errors: list[str] = []

    @property
    def name(self) -> str:
        return "openai"

    @property
    def config(self) -> "ProviderConfig":
        return self._config

    def create_session(self, config: SessionConfig) -> OpenAISession:
        api_key = self._config.openai_api_key
        if not api_key:
            raise ProviderConfigError(
                "OpenAI provider requires an API key. "
                "Set OPENAI_API_KEY environment variable."
            )

        try:
            from openai import AsyncOpenAI  # noqa: F401
        except ImportError as e:
            raise ProviderNotInstalled(
                "OpenAI provider requires the openai package. "
                "Install with: pip install openai\n"
                f"Error: {e}"
            )

        model = config.model or self._config.openai_model or DEFAULT_OPENAI_MODEL
        base_url = self._config.openai_base_url or None

        if config.extra:
            model = config.extra.get("model", model)
            base_url = config.extra.get("base_url", base_url)

        session_id = f"openai-{uuid.uuid4().hex[:12]}"

        session = OpenAISession(
            session_id=session_id,
            model=model,
            api_key=api_key,
            system_prompt=config.system_prompt,
            base_url=base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        self._active_session = session
        logger.info(f"Created OpenAI session {session_id} (model={model})")
        return session

    async def send_message(self, message: str) -> AsyncIterator[str]:
        if not self._active_session:
            raise ProviderError("No active session. Call create_session() first.")

        if not self._active_session.is_active:
            raise ProviderError("Session is closed. Create a new session.")

        async for chunk in self._active_session.complete(message, stream=True):
            yield chunk

    def get_supported_models(self) -> list[str]:
        return OPENAI_MODELS.copy()

    def validate_config(self) -> bool:
        self._validation_errors = []

        if not self._config.openai_api_key:
            self._validation_errors.append(
                "OpenAI provider requires OPENAI_API_KEY environment variable"
            )
            return False

        return True

    def get_validation_errors(self) -> list[str]:
        return self._validation_errors.copy()

    def health_check(self) -> bool:
        if not self.validate_config():
            return False

        try:
            from openai import AsyncOpenAI  # noqa: F401

            return True
        except ImportError:
            self._validation_errors.append("openai package is not installed")
            return False

    def get_active_session(self) -> OpenAISession | None:
        if self._active_session and self._active_session.is_active:
            return self._active_session
        return None

    def close(self) -> None:
        if self._active_session:
            self._active_session.close()
            self._active_session = None
        logger.debug("OpenAI provider closed")

    def __repr__(self) -> str:
        return (
            f"OpenAIProvider(name={self.name!r}, model={self._config.openai_model!r})"
        )
