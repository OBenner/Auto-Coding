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

from typing import Any

from core.providers.adapters.openai_compat import (
    OpenAICompatibleProvider,
    OpenAICompatibleSession,
)
from core.providers.base import SessionConfig

DEFAULT_OPENAI_MODEL = "gpt-4o"

# Popular OpenAI models (updated February 2026)
OPENAI_MODELS = [
    "gpt-5.2",
    "gpt-5.2-pro",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4o",
    "gpt-4o-mini",
    "o4-mini",
    "o3",
    "o3-mini",
    "o3-pro",
]


class OpenAISession(OpenAICompatibleSession):
    """Agent session for OpenAI provider."""

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
        super().__init__(
            session_id=session_id,
            provider_name="openai",
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._api_key = api_key
        self._base_url = base_url

    def _build_client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return kwargs


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider implementation.

    Provides direct access to OpenAI models (GPT-4o, o1, o3, etc.).
    """

    _provider_name = "openai"
    _supported_models = OPENAI_MODELS

    def _get_api_key(self) -> str | None:
        return self._config.openai_api_key

    def _is_config_set(self) -> bool:
        return bool(self._config.openai_api_key)

    def _config_env_var(self) -> str:
        return "OPENAI_API_KEY"

    def _get_model(self, session_config: SessionConfig) -> str:
        model = (
            session_config.model or self._config.openai_model or DEFAULT_OPENAI_MODEL
        )
        if session_config.extra:
            model = session_config.extra.get("model", model)
        return model

    def _create_session_instance(
        self, session_id: str, model: str, config: SessionConfig
    ) -> OpenAISession:
        from core.providers.exceptions import ProviderConfigError

        api_key = self._config.openai_api_key
        if not api_key:
            raise ProviderConfigError(
                "OpenAI provider requires an API key. "
                "Set OPENAI_API_KEY environment variable."
            )

        base_url = self._config.openai_base_url or None
        if config.extra:
            base_url = config.extra.get("base_url", base_url)

        return OpenAISession(
            session_id=session_id,
            model=model,
            api_key=api_key,
            system_prompt=config.system_prompt,
            base_url=base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def __repr__(self) -> str:
        return (
            f"OpenAIProvider(name={self.name!r}, model={self._config.openai_model!r})"
        )
