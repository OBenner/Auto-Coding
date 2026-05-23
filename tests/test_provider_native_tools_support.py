"""Provider-declared native tool support contract.

Phase 1.4 of ``docs/roadmap/non-claude-provider-autonomy.md`` introduces
``AIEngineProvider.supports_native_tools(model)`` and a session-level
``provider_supports_native_tools(model)`` hook so the runtime can skip
the native tool loop for providers/models known to not support it,
rather than discovering the limitation via an exception round trip.

Each provider with a mixed model lineup (Ollama, ZhipuAI) is pinned
here. The default contract — provider supports native tools for every
model — is asserted via the base class to keep
OpenAI/OpenRouter/LiteLLM/Google paths unchanged today.
"""

from __future__ import annotations

import pytest

from core.providers.adapters.ollama import OllamaProvider
from core.providers.adapters.zhipuai import ZhipuAIProvider
from core.providers.base import AIEngineProvider


class _ProbeProvider(AIEngineProvider):
    """Concrete subclass that only exposes the default supports_native_tools."""

    @property
    def name(self) -> str:  # pragma: no cover - smoke shim
        return "probe"

    def create_session(self, config):  # pragma: no cover - smoke shim
        raise NotImplementedError

    async def send_message(self, message):  # pragma: no cover - smoke shim
        if False:
            yield ""

    def get_supported_models(self):  # pragma: no cover - smoke shim
        return []

    def validate_config(self) -> bool:  # pragma: no cover - smoke shim
        return True


def test_base_provider_assumes_native_tool_support():
    """Providers that do not override the hook keep today's behavior."""
    assert _ProbeProvider.supports_native_tools("any-model") is True
    assert _ProbeProvider.supports_native_tools(None) is True


@pytest.mark.parametrize(
    "model",
    [
        "llama3.1:70b-instruct",
        "llama3.2",
        "qwen2.5:32b-instruct",
        "mistral-nemo:latest",
        "command-r-plus",
        "firefunction-v2",
        "hermes-3-llama-3.1-70b",
        "phi-4",
    ],
)
def test_ollama_known_tool_capable_models_pass(model: str):
    assert OllamaProvider.supports_native_tools(model) is True


@pytest.mark.parametrize(
    "model",
    [
        "llama2:7b",
        "codellama:13b",
        "phi-2",
        "gemma:2b",
        "tinyllama",
        "mistral:7b",
        "neural-chat",
        "",
        None,
    ],
)
def test_ollama_unknown_or_old_models_skip_native_loop(model):
    assert OllamaProvider.supports_native_tools(model) is False


def test_ollama_match_is_case_insensitive():
    assert OllamaProvider.supports_native_tools("LLAMA3.1:70B") is True
    assert OllamaProvider.supports_native_tools("Qwen2.5") is True


@pytest.mark.parametrize(
    "model",
    [
        "glm-4-flash-250414",
        "glm-4.7",
        "glm-4-air",
        "glm-4-plus",
        "glm-4v-plus",
        "GLM-4.6",
    ],
)
def test_zhipuai_glm4_family_supports_native_tools(model: str):
    assert ZhipuAIProvider.supports_native_tools(model) is True


@pytest.mark.parametrize(
    "model",
    [
        "glm-3-turbo",
        "chatglm2-6b",
        "embedding-3",
        "cogview-3",
        "",
        None,
    ],
)
def test_zhipuai_pre_glm4_models_skip_native_loop(model):
    assert ZhipuAIProvider.supports_native_tools(model) is False


def test_ollama_session_delegates_to_provider_classmethod():
    """The session-level hook must mirror the provider classmethod."""
    from core.providers.adapters.ollama import OllamaSession

    session = OllamaSession(
        session_id="t",
        model="llama3.1:8b",
    )
    assert session.provider_supports_native_tools(None) is True
    session_old = OllamaSession(
        session_id="t",
        model="llama2:7b",
    )
    assert session_old.provider_supports_native_tools(None) is False


def test_zhipuai_session_delegates_to_provider_classmethod():
    """The ZhipuAI session hook also delegates to the provider classmethod."""
    from core.providers.adapters.zhipuai import ZhipuAISession

    session = ZhipuAISession(
        session_id="t",
        model="glm-4.7",
        api_key="test",
    )
    assert session.provider_supports_native_tools(None) is True
    session_old = ZhipuAISession(
        session_id="t",
        model="glm-3-turbo",
        api_key="test",
    )
    assert session_old.provider_supports_native_tools(None) is False
