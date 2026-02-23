"""
Ollama Provider Adapter
========================

Wraps the Ollama API to implement the AIEngineProvider interface.
This enables running local LLMs via Ollama (Llama, DeepSeek, CodeLlama, etc.).

Ollama uses an OpenAI-compatible API, so this adapter leverages the openai
package pointed at the local Ollama server.

Environment Variables:
    OLLAMA_MODEL: Model identifier (e.g., llama3, deepseek-r1:7b) (required)
    OLLAMA_BASE_URL: API base URL (default: http://localhost:11434)
    OLLAMA_API_KEY: Optional API key for authenticated instances
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

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

# Popular Ollama models
OLLAMA_MODELS = [
    "llama3.3",
    "llama3.1",
    "deepseek-r1",
    "deepseek-r1:7b",
    "qwen2.5",
    "qwen2.5-coder",
    "codellama",
    "mistral",
    "gemma2",
    "phi4",
]


class OllamaSession(AgentSession):
    """Agent session for Ollama provider.

    Uses the OpenAI-compatible API that Ollama exposes at /v1/*.
    """

    def __init__(
        self,
        session_id: str,
        model: str,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        system_prompt: str = "",
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        super().__init__(session_id, provider_name="ollama")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
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
                    "Ollama provider requires the openai package. "
                    "Install with: pip install openai\n"
                    f"Error: {e}"
                )

            # Ollama exposes an OpenAI-compatible endpoint at /v1
            client_kwargs: dict[str, Any] = {
                "base_url": f"{self._base_url}/v1",
                "api_key": self._api_key or "ollama",  # Ollama ignores API key
            }

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
            logger.error(f"Ollama completion error: {e}")
            raise ProviderError(f"Ollama completion failed: {e}") from e

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
        logger.debug(f"Ollama session {self.session_id} closed")


class OllamaProvider(AIEngineProvider):
    """Ollama provider implementation.

    Provides access to local LLMs running via Ollama.
    Uses Ollama's OpenAI-compatible API endpoint.
    """

    def __init__(self, config: "ProviderConfig"):
        self._config = config
        self._active_session: OllamaSession | None = None
        self._validation_errors: list[str] = []

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def config(self) -> "ProviderConfig":
        return self._config

    def create_session(self, config: SessionConfig) -> OllamaSession:
        model = config.model or self._config.ollama_model
        if not model:
            raise ProviderConfigError(
                "Ollama provider requires a model. "
                "Set OLLAMA_MODEL environment variable."
            )

        try:
            from openai import AsyncOpenAI  # noqa: F401
        except ImportError as e:
            raise ProviderNotInstalled(
                "Ollama provider requires the openai package. "
                "Install with: pip install openai\n"
                f"Error: {e}"
            )

        base_url = self._config.ollama_base_url or DEFAULT_OLLAMA_BASE_URL
        api_key = self._config.ollama_api_key or None

        if config.extra:
            model = config.extra.get("model", model)
            base_url = config.extra.get("base_url", base_url)

        session_id = f"ollama-{uuid.uuid4().hex[:12]}"

        session = OllamaSession(
            session_id=session_id,
            model=model,
            base_url=base_url,
            system_prompt=config.system_prompt,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        self._active_session = session
        logger.info(f"Created Ollama session {session_id} (model={model})")
        return session

    async def send_message(self, message: str) -> AsyncIterator[str]:
        if not self._active_session:
            raise ProviderError("No active session. Call create_session() first.")

        if not self._active_session.is_active:
            raise ProviderError("Session is closed. Create a new session.")

        async for chunk in self._active_session.complete(message, stream=True):
            yield chunk

    def get_supported_models(self) -> list[str]:
        return OLLAMA_MODELS.copy()

    def validate_config(self) -> bool:
        self._validation_errors = []

        if not self._config.ollama_model:
            self._validation_errors.append(
                "Ollama provider requires OLLAMA_MODEL environment variable"
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

    def get_active_session(self) -> OllamaSession | None:
        if self._active_session and self._active_session.is_active:
            return self._active_session
        return None

    def close(self) -> None:
        if self._active_session:
            self._active_session.close()
            self._active_session = None
        logger.debug("Ollama provider closed")

    def __repr__(self) -> str:
        return (
            f"OllamaProvider(name={self.name!r}, model={self._config.ollama_model!r})"
        )
