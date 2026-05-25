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

    def provider_supports_native_tools(self, model: str | None) -> bool:
        """Delegate to :meth:`OllamaProvider.supports_native_tools` for the model.

        The runtime calls this before opening the native tool loop so an
        Ollama session running a non-tool-capable local model skips the
        loop without paying for an unsupported-tools error round trip.
        """
        return OllamaProvider.supports_native_tools(model or self.model)

    def _build_client_kwargs(self) -> dict[str, Any]:
        return {
            "base_url": f"{self._base_url}/v1",
            "api_key": self._api_key or "ollama",  # Ollama ignores API key
        }


# Substrings that identify Ollama-served models known to support the
# OpenAI-compatible ``tools`` parameter. Matched case-insensitively
# against the configured model identifier. Older or smaller models
# (llama2, codellama, phi-2, gemma:2b, mistral:7b without instruct
# tuning, etc.) generally return JSON in content rather than producing
# real tool_calls; for those we skip the native loop instead of paying
# for an exception round-trip.
_OLLAMA_NATIVE_TOOL_MODEL_TOKENS: tuple[str, ...] = (
    "llama3.1",
    "llama3.2",
    "llama3.3",
    "qwen2.5",
    "qwen3",
    "mistral-nemo",
    "mistral-large",
    "command-r",
    "command-r-plus",
    "firefunction",
    "functionary",
    "hermes-3",
    "phi-4",
    "phi4",
    "granite3",
)


class OllamaProvider(OpenAICompatibleProvider):
    """Ollama provider implementation.

    Provides access to local LLMs running via Ollama.
    Uses Ollama's OpenAI-compatible API endpoint.
    """

    _provider_name = "ollama"
    _supported_models = OLLAMA_MODELS

    @classmethod
    def supports_native_tools(cls, model: str | None) -> bool:
        """Ollama-served models vary widely in tool-call support.

        Returns ``True`` only when the configured model identifier
        matches a known-good token from
        :data:`_OLLAMA_NATIVE_TOOL_MODEL_TOKENS`. Anything else (older
        llama2 lines, tiny phi/gemma variants, custom local builds)
        skips the native loop in favor of the JSON action loop. The
        check is intentionally string-based because Ollama lets users
        run arbitrary local model tags that no central registry covers.
        """
        if not model or not model.strip():
            return False
        haystack = model.strip().lower()
        return any(token in haystack for token in _OLLAMA_NATIVE_TOOL_MODEL_TOKENS)

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
