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
        "phi4",
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


# ----------------------------------------------------------------------
# OpenAI provider
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "model",
    [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-5",
        "gpt-5.2",
        "gpt-5-mini",
        "o1",
        "o3",
        "o3-mini",
        "o3-pro",
        "o4-mini",
        "chatgpt-4o-latest",
    ],
)
def test_openai_chat_and_reasoning_models_support_native_tools(model: str):
    from core.providers.adapters.openai import OpenAIProvider

    assert OpenAIProvider.supports_native_tools(model) is True


@pytest.mark.parametrize(
    "model",
    [
        "text-embedding-3-large",
        "text-embedding-ada-002",
        "whisper-1",
        "tts-1",
        "dall-e-3",
        "davinci-002",
        "babbage-002",
        "omni-moderation-latest",
        "",
        None,
    ],
)
def test_openai_non_chat_models_skip_native_loop(model):
    from core.providers.adapters.openai import OpenAIProvider

    assert OpenAIProvider.supports_native_tools(model) is False


# ----------------------------------------------------------------------
# OpenRouter provider
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "model",
    [
        "anthropic/claude-sonnet-4",
        "openai/gpt-4o",
        "google/gemini-2.0-flash",
        "meta-llama/llama-3.1-70b-instruct",
        "mistralai/mistral-large",
        "qwen/qwen-2.5-72b-instruct",
        "cohere/command-r-plus",
        "x-ai/grok-2",
        "deepseek/deepseek-chat",
    ],
)
def test_openrouter_known_vendor_routes_support_native_tools(model: str):
    from core.providers.adapters.openrouter import OpenRouterProvider

    assert OpenRouterProvider.supports_native_tools(model) is True


@pytest.mark.parametrize(
    "model",
    [
        "openai/text-embedding-3-large",
        "voyage/embed-3",
        "cohere/rerank-3",
        "openai/whisper",
        "openai/tts-1",
        "unknown-vendor/some-model",
        "",
        None,
    ],
)
def test_openrouter_non_tool_or_unknown_routes_skip_native_loop(model):
    from core.providers.adapters.openrouter import OpenRouterProvider

    assert OpenRouterProvider.supports_native_tools(model) is False


# ----------------------------------------------------------------------
# LiteLLM provider
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "model",
    [
        "openai/gpt-4o",
        "azure/gpt-4",
        "anthropic/claude-sonnet-4",
        "google/gemini-2.0-flash",
        "vertex_ai/gemini-2.0-flash",
        "bedrock/anthropic.claude-sonnet-4",
        "groq/llama-3.1-70b",
        "mistral/mistral-large",
        "deepseek/deepseek-chat",
        "ollama/llama3.1",
        "gpt-4o",
        "claude-sonnet-4-5",
        "gemini-2.0-flash",
        "mistral-large",
    ],
)
def test_litellm_known_routes_and_bare_names_support_native_tools(model: str):
    from core.providers.adapters.litellm import LiteLLMProvider

    assert LiteLLMProvider.supports_native_tools(model) is True


@pytest.mark.parametrize(
    "model",
    [
        "openai/text-embedding-3-large",
        "vertex_ai/text-bison",
        "google/embedding-001",
        "whisper-large-v3",
        "tinyllama",
        "phi-2",
        "",
        None,
    ],
)
def test_litellm_non_tool_or_unknown_models_skip_native_loop(model):
    from core.providers.adapters.litellm import LiteLLMProvider

    assert LiteLLMProvider.supports_native_tools(model) is False


# ----------------------------------------------------------------------
# Google provider
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "model",
    [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-thinking",
        "gemini-3-pro",
        "gemini-pro-1.5",
    ],
)
def test_google_modern_gemini_supports_native_tools(model: str):
    from core.providers.adapters.google import GoogleProvider

    assert GoogleProvider.supports_native_tools(model) is True


@pytest.mark.parametrize(
    "model",
    [
        "gemini-1.0-pro",
        "gemini-1.0-pro-vision",
        "text-bison-001",
        "text-unicorn",
        "chat-bison-001",
        "code-bison-001",
        "imagen-3",
        "text-embedding-004",
        "",
        None,
    ],
)
def test_google_legacy_and_non_chat_models_skip_native_loop(model):
    from core.providers.adapters.google import GoogleProvider

    assert GoogleProvider.supports_native_tools(model) is False


def test_google_supports_native_tools_accepts_generative_model_object():
    """``self.model`` may be a GenerativeModel; we read ``model_name`` from it."""
    from core.providers.adapters.google import GoogleProvider

    class _FakeGenerativeModel:
        model_name = "models/gemini-2.0-flash"

    assert GoogleProvider.supports_native_tools(_FakeGenerativeModel()) is True


def test_google_supports_native_tools_rejects_unknown_object_silently():
    """An opaque object without ``model_name`` falls back to False, not a crash."""
    from core.providers.adapters.google import GoogleProvider

    class _Opaque:
        pass

    assert GoogleProvider.supports_native_tools(_Opaque()) is False


# ----------------------------------------------------------------------
# Public factory helper
# ----------------------------------------------------------------------


def test_provider_native_tool_capability_helper_for_openai():
    from core.providers.factory import provider_native_tool_capability

    payload = provider_native_tool_capability("openai", "gpt-4o")

    assert payload["provider"] == "openai"
    assert payload["model"] == "gpt-4o"
    assert payload["declared"] == "supported"
    assert payload["decision_source"] == "provider_classmethod"


def test_provider_native_tool_capability_helper_reports_unsupported():
    from core.providers.factory import provider_native_tool_capability

    payload = provider_native_tool_capability("ollama", "llama2:7b")

    assert payload["declared"] == "unsupported"
    assert payload["decision_source"] == "provider_classmethod"


def test_provider_native_tool_capability_helper_unknown_provider():
    from core.providers.factory import provider_native_tool_capability

    payload = provider_native_tool_capability("not-a-real-provider", "x")

    assert payload["declared"] == "unknown"
    assert payload["decision_source"] == "unknown_provider"


def test_provider_native_tool_capability_helper_normalizes_provider_name():
    from core.providers.factory import provider_native_tool_capability

    payload = provider_native_tool_capability(" OpenAI ", "gpt-4o")

    assert payload["provider"] == "openai"
    assert payload["declared"] == "supported"
