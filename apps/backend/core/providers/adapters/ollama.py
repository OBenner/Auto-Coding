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

from typing import Any

from core.providers.adapters.openai_compat import (
    OpenAICompatibleProvider,
    OpenAICompatibleSession,
)
from core.providers.base import SessionConfig

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


class OllamaSession(OpenAICompatibleSession):
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
        super().__init__(
            session_id=session_id,
            provider_name="ollama",
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _build_client_kwargs(self) -> dict[str, Any]:
        return {
            "base_url": f"{self._base_url}/v1",
            "api_key": self._api_key or "ollama",  # Ollama ignores API key
        }


class OllamaProvider(OpenAICompatibleProvider):
    """Ollama provider implementation.

    Provides access to local LLMs running via Ollama.
    Uses Ollama's OpenAI-compatible API endpoint.
    """

    _provider_name = "ollama"
    _supported_models = OLLAMA_MODELS

    def _get_api_key(self) -> str | None:
        return self._config.ollama_api_key

    def _is_config_set(self) -> bool:
        return bool(self._config.ollama_model)

    def _config_env_var(self) -> str:
        return "OLLAMA_MODEL"

    def _get_model(self, session_config: SessionConfig) -> str:
        model = session_config.model or self._config.ollama_model or ""
        if session_config.extra:
            model = session_config.extra.get("model", model)
        return model

    def _create_session_instance(
        self, session_id: str, model: str, config: SessionConfig
    ) -> OllamaSession:
        base_url = self._config.ollama_base_url or DEFAULT_OLLAMA_BASE_URL
        api_key = self._config.ollama_api_key or None

        if config.extra:
            base_url = config.extra.get("base_url", base_url)

        return OllamaSession(
            session_id=session_id,
            model=model,
            base_url=base_url,
            system_prompt=config.system_prompt,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def __repr__(self) -> str:
        return (
            f"OllamaProvider(name={self.name!r}, model={self._config.ollama_model!r})"
        )
