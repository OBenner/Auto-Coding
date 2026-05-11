import asyncio
import copy
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from agents.runtime import (
    RuntimeRequirements,
    create_runtime_session,
    local_action_tool_schemas,
    run_runtime_session,
)
from core.platform import run_process
from core.providers.adapters.google import GoogleProvider, sanitize_google_schema
from core.providers.adapters.litellm import LiteLLMProvider
from core.providers.adapters.ollama import OllamaProvider
from core.providers.adapters.openai import OpenAIProvider
from core.providers.adapters.openai_compat import parse_openai_tool_calls
from core.providers.adapters.openrouter import OpenRouterProvider
from core.providers.adapters.zhipuai import ZhipuAIProvider
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig


def _chunk(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=text))]
    )


class _AsyncChunkStream:
    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for chunk in self._chunks:
            yield _chunk(chunk)


def _install_fake_openai(
    monkeypatch: pytest.MonkeyPatch,
    chunks: list[str],
) -> SimpleNamespace:
    calls: list[dict] = []
    instances: list[object] = []

    class FakeCompletions:
        async def create(self, **kwargs):
            await asyncio.sleep(0)
            calls.append(copy.deepcopy(kwargs))
            return _AsyncChunkStream(chunks)

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = SimpleNamespace(
                completions=FakeCompletions(),
            )
            instances.append(self)

    module = ModuleType("openai")
    module.AsyncOpenAI = FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", module)
    return SimpleNamespace(calls=calls, instances=instances)


def _install_fake_openai_responses(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[SimpleNamespace],
) -> SimpleNamespace:
    calls: list[dict] = []
    instances: list[object] = []

    class FakeCompletions:
        async def create(self, **kwargs):
            await asyncio.sleep(0)
            calls.append(copy.deepcopy(kwargs))
            return responses.pop(0)

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = SimpleNamespace(
                completions=FakeCompletions(),
            )
            instances.append(self)

    module = ModuleType("openai")
    module.AsyncOpenAI = FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", module)
    return SimpleNamespace(calls=calls, instances=instances)


def _openai_tool_call_response(
    *,
    tool_call_id: str,
    name: str,
    arguments: dict,
    content: str | None = None,
) -> SimpleNamespace:
    tool_call = SimpleNamespace(
        id=tool_call_id,
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )
    message = SimpleNamespace(content=content, tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _submitted_tool_names(call: dict) -> list[str]:
    return [tool["function"]["name"] for tool in call["tools"]]


def test_provider_tool_call_parser_accepts_gateway_argument_shapes():
    message = {
        "tool_calls": [
            {
                "id": "call_dict_args",
                "function": {
                    "name": "read_file",
                    "arguments": {"path": "README.md"},
                },
            },
            {
                "call_id": "call_top_level",
                "name": "finish",
                "args": {"summary": "done"},
            },
        ]
    }

    tool_calls = parse_openai_tool_calls(message)

    assert [tool_call.id for tool_call in tool_calls] == [
        "call_dict_args",
        "call_top_level",
    ]
    assert [tool_call.name for tool_call in tool_calls] == ["read_file", "finish"]
    assert tool_calls[0].arguments == {"path": "README.md"}
    assert tool_calls[1].arguments == {"summary": "done"}


def test_provider_tool_call_parser_accepts_gemini_part_shapes():
    message = SimpleNamespace(
        parts=[
            SimpleNamespace(
                function_call=SimpleNamespace(
                    name="write_file",
                    args={"path": "notes.txt", "content": "hello"},
                )
            )
        ]
    )

    tool_calls = parse_openai_tool_calls(message)

    assert tool_calls[0].id == "call_1"
    assert tool_calls[0].name == "write_file"
    assert tool_calls[0].arguments == {"path": "notes.txt", "content": "hello"}


def _install_fake_litellm(
    monkeypatch: pytest.MonkeyPatch,
    chunks: list[str],
) -> SimpleNamespace:
    calls: list[dict] = []

    async def acompletion(**kwargs):
        await asyncio.sleep(0)
        calls.append(copy.deepcopy(kwargs))
        return _AsyncChunkStream(chunks)

    module = ModuleType("litellm")
    module.acompletion = acompletion
    monkeypatch.setitem(sys.modules, "litellm", module)
    return SimpleNamespace(calls=calls)


def _install_fake_litellm_responses(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[SimpleNamespace],
) -> SimpleNamespace:
    calls: list[dict] = []

    async def acompletion(**kwargs):
        await asyncio.sleep(0)
        calls.append(copy.deepcopy(kwargs))
        return responses.pop(0)

    module = ModuleType("litellm")
    module.acompletion = acompletion
    monkeypatch.setitem(sys.modules, "litellm", module)
    return SimpleNamespace(calls=calls)


def _install_fake_google(
    monkeypatch: pytest.MonkeyPatch,
    chunks: list[str],
) -> SimpleNamespace:
    configured: list[str] = []
    model_calls: list[dict] = []
    sent_messages: list[str] = []

    class FakeGoogleResponse:
        text = "".join(chunks)

        def __iter__(self):
            for chunk in chunks:
                yield SimpleNamespace(text=chunk)

    class FakeChat:
        def send_message(self, message: str, stream: bool = True):
            sent_messages.append(message)
            assert stream is True
            return FakeGoogleResponse()

    class FakeGenerativeModel:
        def __init__(self, model_name: str, system_instruction: str = ""):
            model_calls.append(
                {
                    "model_name": model_name,
                    "system_instruction": system_instruction,
                }
            )

        def start_chat(self, history=None):
            assert history == []
            return FakeChat()

    def configure(api_key: str):
        configured.append(api_key)

    google_pkg = ModuleType("google")
    google_pkg.__path__ = []
    genai = ModuleType("google.generativeai")
    genai.configure = configure
    genai.GenerativeModel = FakeGenerativeModel
    google_pkg.generativeai = genai

    monkeypatch.setitem(sys.modules, "google", google_pkg)
    monkeypatch.setitem(sys.modules, "google.generativeai", genai)
    return SimpleNamespace(
        configured=configured,
        model_calls=model_calls,
        sent_messages=sent_messages,
    )


def _google_tool_response(name: str, arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(
        parts=[
            SimpleNamespace(
                function_call=SimpleNamespace(
                    name=name,
                    args=arguments,
                )
            )
        ]
    )


def _google_tool_batch_response(
    calls: list[tuple[str, dict]],
) -> SimpleNamespace:
    return SimpleNamespace(
        parts=[
            SimpleNamespace(
                function_call=SimpleNamespace(
                    name=name,
                    args=arguments,
                )
            )
            for name, arguments in calls
        ]
    )


def _install_fake_google_tool_responses(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[SimpleNamespace],
) -> SimpleNamespace:
    configured: list[str] = []
    model_calls: list[dict] = []
    generate_calls: list[dict] = []

    class FakeGenerativeModel:
        def __init__(self, model_name: str, system_instruction: str = ""):
            model_calls.append(
                {
                    "model_name": model_name,
                    "system_instruction": system_instruction,
                }
            )

        def generate_content(self, contents, tools=None):
            generate_calls.append(
                {
                    "contents": copy.deepcopy(contents),
                    "tools": copy.deepcopy(tools),
                }
            )
            return responses.pop(0)

    def configure(api_key: str):
        configured.append(api_key)

    google_pkg = ModuleType("google")
    google_pkg.__path__ = []
    genai = ModuleType("google.generativeai")
    genai.configure = configure
    genai.GenerativeModel = FakeGenerativeModel
    google_pkg.generativeai = genai

    monkeypatch.setitem(sys.modules, "google", google_pkg)
    monkeypatch.setitem(sys.modules, "google.generativeai", genai)
    return SimpleNamespace(
        configured=configured,
        model_calls=model_calls,
        generate_calls=generate_calls,
    )


def _install_fake_zai(
    monkeypatch: pytest.MonkeyPatch,
    chunks: list[str],
) -> SimpleNamespace:
    calls: list[dict] = []
    api_keys: list[str] = []

    class FakeCompletions:
        async def create(self, **kwargs):
            await asyncio.sleep(0)
            calls.append(copy.deepcopy(kwargs))
            return _AsyncChunkStream(chunks)

    class FakeZhipuAiClient:
        def __init__(self, api_key: str):
            api_keys.append(api_key)
            self.chat = SimpleNamespace(completions=FakeCompletions())

    module = ModuleType("zai")
    module.ZhipuAiClient = FakeZhipuAiClient
    monkeypatch.setitem(sys.modules, "zai", module)
    return SimpleNamespace(calls=calls, api_keys=api_keys)


def _install_fake_zai_responses(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[SimpleNamespace],
) -> SimpleNamespace:
    calls: list[dict] = []
    api_keys: list[str] = []

    class FakeCompletions:
        async def create(self, **kwargs):
            await asyncio.sleep(0)
            calls.append(copy.deepcopy(kwargs))
            return responses.pop(0)

    class FakeZhipuAiClient:
        def __init__(self, api_key: str):
            api_keys.append(api_key)
            self.chat = SimpleNamespace(completions=FakeCompletions())

    module = ModuleType("zai")
    module.ZhipuAiClient = FakeZhipuAiClient
    monkeypatch.setitem(sys.modules, "zai", module)
    return SimpleNamespace(calls=calls, api_keys=api_keys)


async def _run_analysis_smoke(session, provider_name: str, tmp_path: Path):
    runtime_session = create_runtime_session(
        provider_name=provider_name,
        agent_session=session,
    )

    return await run_runtime_session(
        runtime_session,
        "say smoke",
        tmp_path,
        requirements=RuntimeRequirements.text_only(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "provider_cls",
        "provider_name",
        "config_kwargs",
        "session_model",
        "expected_response",
    ),
    [
        (
            OpenAIProvider,
            "openai",
            {"provider": "openai", "openai_api_key": "test-key"},
            "gpt-4o",
            "openai ok",
        ),
        (
            OpenRouterProvider,
            "openrouter",
            {"provider": "openrouter", "openrouter_api_key": "test-key"},
            "openai/gpt-4o",
            "openrouter ok",
        ),
        (
            OllamaProvider,
            "ollama",
            {"provider": "ollama", "ollama_model": "llama3.1"},
            None,
            "ollama ok",
        ),
    ],
)
async def test_openai_compatible_providers_support_analysis_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    provider_cls,
    provider_name: str,
    config_kwargs: dict,
    session_model: str | None,
    expected_response: str,
):
    prefix, suffix = expected_response.split(" ", 1)
    fake_openai = _install_fake_openai(monkeypatch, [f"{prefix} ", suffix])
    provider = provider_cls(ProviderConfig(**config_kwargs))
    session = provider.create_session(
        SessionConfig(
            name=f"{provider_name}-analysis",
            system_prompt="system",
            model=session_model,
        )
    )

    result = await _run_analysis_smoke(session, provider_name, tmp_path)

    assert result.status == "complete"
    assert result.response_text == expected_response
    assert fake_openai.calls[0]["stream"] is True
    assert fake_openai.calls[0]["messages"][-1] == {
        "role": "user",
        "content": "say smoke",
    }


@pytest.mark.asyncio
async def test_openai_compatible_session_exposes_native_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_openai = _install_fake_openai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_1",
                name="read_file",
                arguments={"path": "README.md", "max_chars": 1000},
            )
        ],
    )
    provider = OpenAIProvider(
        ProviderConfig(provider="openai", openai_api_key="test-key")
    )
    session = provider.create_session(SessionConfig(name="openai-tools"))

    response = await session.complete_with_tool_calls(
        "Inspect the project",
        local_action_tool_schemas(),
    )
    session.add_tool_result(
        response.tool_calls[0].id,
        response.tool_calls[0].name,
        {"ok": True, "message": "Read README.md"},
    )

    assert response.content == ""
    assert response.tool_calls[0].id == "call_1"
    assert response.tool_calls[0].name == "read_file"
    assert response.tool_calls[0].arguments == {
        "path": "README.md",
        "max_chars": 1000,
    }
    assert fake_openai.calls[0]["stream"] is False
    assert fake_openai.calls[0]["tool_choice"] == "auto"
    assert fake_openai.calls[0]["tools"][0]["type"] == "function"
    assert _submitted_tool_names(fake_openai.calls[0])[:4] == [
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
    ]
    assert session.messages[-2]["role"] == "assistant"
    assert session.messages[-2]["tool_calls"][0]["function"]["name"] == "read_file"
    assert session.messages[-1]["role"] == "tool"
    assert session.messages[-1]["tool_call_id"] == "call_1"
    assert "name" not in session.messages[-1]
    assert "README.md" in session.messages[-1]["content"]


@pytest.mark.asyncio
async def test_ollama_session_exposes_native_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_openai = _install_fake_openai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_ollama_1",
                name="read_file",
                arguments={"path": "README.md"},
            )
        ],
    )
    provider = OllamaProvider(
        ProviderConfig(provider="ollama", ollama_model="llama3.1")
    )
    session = provider.create_session(SessionConfig(name="ollama-tools"))

    response = await session.complete_with_tool_calls(
        "Inspect the project",
        local_action_tool_schemas(),
    )
    session.add_tool_result(
        response.tool_calls[0].id,
        response.tool_calls[0].name,
        {"ok": True, "message": "Read README.md"},
    )

    assert response.tool_calls[0].id == "call_ollama_1"
    assert response.tool_calls[0].name == "read_file"
    assert response.tool_calls[0].arguments == {"path": "README.md"}
    assert fake_openai.instances[0].kwargs["base_url"] == "http://localhost:11434/v1"
    assert fake_openai.instances[0].kwargs["api_key"] == "ollama"
    assert fake_openai.calls[0]["stream"] is False
    assert fake_openai.calls[0]["tool_choice"] == "auto"
    assert _submitted_tool_names(fake_openai.calls[0])[:4] == [
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
    ]
    assert session.messages[-1]["role"] == "tool"
    assert session.messages[-1]["tool_call_id"] == "call_ollama_1"
    assert "name" not in session.messages[-1]


@pytest.mark.asyncio
async def test_openrouter_session_exposes_native_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_openai = _install_fake_openai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_or_1",
                name="read_file",
                arguments={"path": "README.md"},
            )
        ],
    )
    provider = OpenRouterProvider(
        ProviderConfig(provider="openrouter", openrouter_api_key="test-key")
    )
    session = provider.create_session(SessionConfig(name="openrouter-tools"))

    response = await session.complete_with_tool_calls(
        "Inspect the project",
        local_action_tool_schemas(),
    )
    session.add_tool_result(
        response.tool_calls[0].id,
        response.tool_calls[0].name,
        {"ok": True, "message": "Read README.md"},
    )

    assert response.tool_calls[0].id == "call_or_1"
    assert response.tool_calls[0].name == "read_file"
    assert fake_openai.calls[0]["stream"] is False
    assert fake_openai.calls[0]["tool_choice"] == "auto"
    assert fake_openai.instances[0].kwargs["base_url"] == (
        "https://openrouter.ai/api/v1"
    )
    assert "HTTP-Referer" in fake_openai.instances[0].kwargs["default_headers"]
    assert session.messages[-1]["role"] == "tool"
    assert "name" not in session.messages[-1]


@pytest.mark.asyncio
async def test_litellm_session_exposes_native_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_litellm = _install_fake_litellm_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_lite_1",
                name="read_file",
                arguments={"path": "README.md"},
            )
        ],
    )
    provider = LiteLLMProvider(
        ProviderConfig(provider="litellm", litellm_model="openai/gpt-4o")
    )
    session = provider.create_session(SessionConfig(name="litellm-tools"))

    response = await session.complete_with_tool_calls(
        "Inspect the project",
        local_action_tool_schemas(),
    )
    session.add_tool_result(
        response.tool_calls[0].id,
        response.tool_calls[0].name,
        {"ok": True, "message": "Read README.md"},
    )

    assert response.tool_calls[0].id == "call_lite_1"
    assert response.tool_calls[0].name == "read_file"
    assert fake_litellm.calls[0]["stream"] is False
    assert fake_litellm.calls[0]["tool_choice"] == "auto"
    assert _submitted_tool_names(fake_litellm.calls[0])[:4] == [
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
    ]
    assert session.messages[-1]["role"] == "tool"
    assert "name" not in session.messages[-1]


@pytest.mark.asyncio
async def test_zhipuai_session_exposes_native_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_zai = _install_fake_zai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_zhipu_1",
                name="read_file",
                arguments={"path": "README.md"},
            )
        ],
    )
    provider = ZhipuAIProvider(
        ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4-flash",
        )
    )
    session = provider.create_session(SessionConfig(name="zhipuai-tools"))

    response = await session.complete_with_tool_calls(
        "Inspect the project",
        local_action_tool_schemas(),
    )
    session.add_tool_result(
        response.tool_calls[0].id,
        response.tool_calls[0].name,
        {"ok": True, "message": "Read README.md"},
    )

    assert response.tool_calls[0].id == "call_zhipu_1"
    assert response.tool_calls[0].name == "read_file"
    assert response.tool_calls[0].arguments == {"path": "README.md"}
    assert fake_zai.api_keys == ["test-key"]
    assert fake_zai.calls[0]["stream"] is False
    assert fake_zai.calls[0]["tool_choice"] == "auto"
    assert _submitted_tool_names(fake_zai.calls[0])[:4] == [
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
    ]
    assert session.messages[-2]["role"] == "assistant"
    assert session.messages[-2]["tool_calls"][0]["function"]["name"] == "read_file"
    assert session.messages[-1]["role"] == "tool"
    assert session.messages[-1]["tool_call_id"] == "call_zhipu_1"
    assert "name" not in session.messages[-1]


@pytest.mark.asyncio
async def test_google_session_exposes_native_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_google = _install_fake_google_tool_responses(
        monkeypatch,
        [
            _google_tool_response(
                "read_file",
                {"path": "README.md", "max_chars": 1000},
            )
        ],
    )
    provider = GoogleProvider(
        ProviderConfig(
            provider="google",
            google_api_key="test-key",
            google_model="gemini-2.0-flash",
        )
    )
    session = provider.create_session(SessionConfig(name="google-tools"))

    response = await session.complete_with_tool_calls(
        "Inspect the project",
        local_action_tool_schemas(),
    )
    session.add_tool_result(
        response.tool_calls[0].id,
        response.tool_calls[0].name,
        {"ok": True, "message": "Read README.md"},
    )

    assert response.content == ""
    assert response.tool_calls[0].id == "call_1"
    assert response.tool_calls[0].name == "read_file"
    assert response.tool_calls[0].arguments == {
        "path": "README.md",
        "max_chars": 1000,
    }
    assert fake_google.configured == ["test-key"]
    declarations = fake_google.generate_calls[0]["tools"][0]["function_declarations"]
    assert [declaration["name"] for declaration in declarations[:4]] == [
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
    ]
    assert "additionalProperties" not in declarations[0]["parameters"]
    assert "maximum" not in declarations[3]["parameters"]["properties"]["max_chars"]
    assert session.messages[-2]["role"] == "model"
    assert session.messages[-2]["parts"][0]["function_call"]["name"] == "read_file"
    assert session.messages[-1]["role"] == "function"
    assert session.messages[-1]["tool_call_id"] == "call_1"
    assert session.messages[-1]["parts"][0]["function_response"]["name"] == (
        "read_file"
    )


def test_google_schema_sanitizer_strips_json_schema_validation_keywords():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "path": {"type": "string", "minLength": 1, "maxLength": 80},
            "count": {"type": "integer", "minimum": 1, "maximum": 10},
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {"oneOf": [{"type": "string"}]},
            },
        },
        "required": ["path"],
    }

    sanitized = sanitize_google_schema(schema)

    assert sanitized == {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "count": {"type": "integer"},
            "items": {
                "type": "array",
                "items": {},
            },
        },
        "required": ["path"],
    }


@pytest.mark.asyncio
async def test_litellm_provider_supports_analysis_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    fake_litellm = _install_fake_litellm(monkeypatch, ["litellm ", "ok"])
    provider = LiteLLMProvider(
        ProviderConfig(provider="litellm", litellm_model="openai/gpt-4o")
    )
    session = provider.create_session(
        SessionConfig(name="litellm-analysis", system_prompt="system")
    )

    result = await _run_analysis_smoke(session, "litellm", tmp_path)

    assert result.status == "complete"
    assert result.response_text == "litellm ok"
    assert fake_litellm.calls[0]["model"] == "openai/gpt-4o"
    assert fake_litellm.calls[0]["stream"] is True


@pytest.mark.asyncio
async def test_google_provider_supports_analysis_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    fake_google = _install_fake_google(monkeypatch, ["google ", "ok"])
    provider = GoogleProvider(
        ProviderConfig(
            provider="google",
            google_api_key="test-key",
            google_model="gemini-2.0-flash",
        )
    )
    session = provider.create_session(
        SessionConfig(name="google-analysis", system_prompt="system")
    )

    result = await _run_analysis_smoke(session, "google", tmp_path)

    assert result.status == "complete"
    assert result.response_text == "google ok"
    assert fake_google.configured == ["test-key"]
    assert fake_google.model_calls == [
        {
            "model_name": "gemini-2.0-flash",
            "system_instruction": "system",
        }
    ]
    assert fake_google.sent_messages == ["say smoke"]


@pytest.mark.asyncio
async def test_zhipuai_provider_supports_analysis_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    fake_zai = _install_fake_zai(monkeypatch, ["zhipuai ", "ok"])
    provider = ZhipuAIProvider(
        ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4-flash",
        )
    )
    session = provider.create_session(
        SessionConfig(name="zhipuai-analysis", system_prompt="system")
    )

    result = await _run_analysis_smoke(session, "zhipuai", tmp_path)

    assert result.status == "complete"
    assert result.response_text == "zhipuai ok"
    assert fake_zai.api_keys == ["test-key"]
    assert fake_zai.calls[0]["model"] == "glm-4-flash"


def _init_git_repo(path: Path) -> None:
    run_process(["git", "init"], cwd=path, capture_output=True, check=True)
    run_process(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    run_process(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        capture_output=True,
        check=True,
    )


@pytest.mark.asyncio
async def test_openai_provider_supports_patch_proposal_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    _init_git_repo(tmp_path)
    target = tmp_path / "smoke.txt"
    target.write_text("old\n", encoding="utf-8")
    proposal = {
        "summary": "OpenAI provider patch smoke",
        "files": [
            {
                "path": "smoke.txt",
                "operation": "modify",
                "patch": """diff --git a/smoke.txt b/smoke.txt
--- a/smoke.txt
+++ b/smoke.txt
@@ -1 +1 @@
-old
+new
""",
            }
        ],
        "tests": ["pytest tests/test_agent_runtime_provider_smoke.py"],
        "risks": [],
    }
    _install_fake_openai(monkeypatch, [json.dumps(proposal)])
    provider = OpenAIProvider(
        ProviderConfig(provider="openai", openai_api_key="test-key")
    )
    session = provider.create_session(SessionConfig(name="openai-patch"))
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="patch_proposal",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "update smoke.txt",
        tmp_path,
        requirements=RuntimeRequirements.patch_proposal(),
        subtask_id="1.1",
    )

    assert result.status == "continue"
    assert "OpenAI provider patch smoke" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "patch_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "applied"
    assert result_artifact["subtask_id"] == "1.1"


@pytest.mark.asyncio
async def test_openai_provider_supports_generic_edit_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    target = tmp_path / "generic.txt"
    target.write_text("old\n", encoding="utf-8")
    fake_openai = _install_fake_openai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_write",
                name="write_file",
                arguments={"path": "generic.txt", "content": "new\n"},
            ),
            _openai_tool_call_response(
                tool_call_id="call_finish",
                name="finish",
                arguments={
                    "summary": "OpenAI provider generic edit smoke",
                    "tests": [],
                    "risks": [],
                },
            ),
        ],
    )
    provider = OpenAIProvider(
        ProviderConfig(provider="openai", openai_api_key="test-key")
    )
    session = provider.create_session(SessionConfig(name="openai-generic-edit"))
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "update generic.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.2",
    )

    assert result.status == "continue"
    assert "OpenAI provider generic edit smoke" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(fake_openai.calls) == 2
    assert fake_openai.calls[0]["stream"] is False
    assert _submitted_tool_names(fake_openai.calls[0])[:4] == [
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
    ]
    assert fake_openai.calls[1]["messages"][-1]["role"] == "tool"
    assert fake_openai.calls[1]["messages"][-1]["tool_call_id"] == "call_write"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["subtask_id"] == "1.2"
    assert result_artifact["loop"] == "native_tool_calls"
    assert result_artifact["action_count"] == 2


@pytest.mark.asyncio
async def test_openai_provider_generic_edit_recovers_after_tool_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    target = tmp_path / "recover.txt"
    target.write_text("old\n", encoding="utf-8")
    fake_openai = _install_fake_openai_responses(
        monkeypatch,
        [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="",
                            tool_calls=[
                                SimpleNamespace(
                                    id="call_write",
                                    function=SimpleNamespace(
                                        name="write_file",
                                        arguments=json.dumps(
                                            {
                                                "path": "recover.txt",
                                                "content": "new\n",
                                            }
                                        ),
                                    ),
                                ),
                                SimpleNamespace(
                                    id="call_missing",
                                    function=SimpleNamespace(
                                        name="read_file",
                                        arguments=json.dumps({"path": "missing.txt"}),
                                    ),
                                ),
                            ],
                        )
                    )
                ]
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="",
                            tool_calls=[
                                SimpleNamespace(
                                    id="call_rollback",
                                    function=SimpleNamespace(
                                        name="rollback_transaction",
                                        arguments=json.dumps(
                                            {"transaction_id": "native_tool_calls-1"}
                                        ),
                                    ),
                                ),
                                SimpleNamespace(
                                    id="call_finish",
                                    function=SimpleNamespace(
                                        name="finish",
                                        arguments=json.dumps(
                                            {
                                                "summary": "Recovered provider tool loop",
                                                "tests": [],
                                                "risks": [],
                                            }
                                        ),
                                    ),
                                ),
                            ],
                        )
                    )
                ]
            ),
        ],
    )
    provider = OpenAIProvider(
        ProviderConfig(provider="openai", openai_api_key="test-key")
    )
    session = provider.create_session(SessionConfig(name="openai-recovery-loop"))
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "recover failed provider tool loop",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.8",
    )

    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )

    assert result.status == "continue"
    assert target.read_text(encoding="utf-8") == "old\n"
    assert len(fake_openai.calls) == 2
    assert fake_openai.calls[1]["messages"][-2]["tool_call_id"] == "call_missing"
    assert "File not found" in fake_openai.calls[1]["messages"][-2]["content"]
    assert result_artifact["recovery_resolved"] is True
    assert result_artifact["transaction_status_counts"] == {
        "partial_failure": 1,
        "complete": 1,
    }
    assert result_artifact["recovery_outcomes"][0]["strategy"] == (
        "rollback_transaction"
    )


@pytest.mark.asyncio
async def test_openai_provider_generic_edit_reports_unsupported_tool_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    fake_openai = _install_fake_openai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_unknown",
                name="unsupported_local_tool",
                arguments={"path": "README.md"},
            ),
            _openai_tool_call_response(
                tool_call_id="call_finish",
                name="finish",
                arguments={
                    "summary": "Recovered after unsupported tool",
                    "tests": [],
                    "risks": [],
                },
            ),
        ],
    )
    provider = OpenAIProvider(
        ProviderConfig(provider="openai", openai_api_key="test-key")
    )
    session = provider.create_session(SessionConfig(name="openai-unsupported-tool"))
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "handle unsupported provider tool",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.9",
    )

    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )

    assert result.status == "continue"
    assert fake_openai.calls[1]["messages"][-1]["tool_call_id"] == "call_unknown"
    assert "Unknown tool" in fake_openai.calls[1]["messages"][-1]["content"]
    assert result_artifact["transaction_status_counts"] == {
        "failed": 1,
        "complete": 1,
    }
    assert result_artifact["failed_tools"] == {"unsupported_local_tool": 1}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_name", "subtask_id"),
    [
        ("openai", "1.10"),
        ("openrouter", "1.11"),
        ("ollama", "1.12"),
        ("litellm", "1.13"),
        ("zhipuai", "1.14"),
    ],
)
async def test_openai_compatible_providers_generic_edit_recover_after_tool_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    provider_name: str,
    subtask_id: str,
):
    target = tmp_path / f"{provider_name}-recover.txt"
    target.write_text("old\n", encoding="utf-8")
    responses = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            SimpleNamespace(
                                id="call_write",
                                function=SimpleNamespace(
                                    name="write_file",
                                    arguments=json.dumps(
                                        {
                                            "path": target.name,
                                            "content": "new\n",
                                        }
                                    ),
                                ),
                            ),
                            SimpleNamespace(
                                id="call_missing",
                                function=SimpleNamespace(
                                    name="read_file",
                                    arguments=json.dumps({"path": "missing.txt"}),
                                ),
                            ),
                        ],
                    )
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            SimpleNamespace(
                                id="call_rollback",
                                function=SimpleNamespace(
                                    name="rollback_transaction",
                                    arguments=json.dumps(
                                        {"transaction_id": "native_tool_calls-1"}
                                    ),
                                ),
                            ),
                            SimpleNamespace(
                                id="call_finish",
                                function=SimpleNamespace(
                                    name="finish",
                                    arguments=json.dumps(
                                        {
                                            "summary": (
                                                f"{provider_name} recovered provider "
                                                "tool loop"
                                            ),
                                            "tests": [],
                                            "risks": [],
                                        }
                                    ),
                                ),
                            ),
                        ],
                    )
                )
            ]
        ),
    ]
    provider, calls = _provider_with_fake_openai_compatible_responses(
        monkeypatch,
        provider_name,
        responses,
    )
    session = provider.create_session(SessionConfig(name=f"{provider_name}-recovery"))
    runtime_session = create_runtime_session(
        provider_name=provider_name,
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        f"recover failed {provider_name} provider tool loop",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id=subtask_id,
    )

    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )

    assert result.status == "continue"
    assert target.read_text(encoding="utf-8") == "old\n"
    assert len(calls) == 2
    assert calls[1]["messages"][-2]["tool_call_id"] == "call_missing"
    assert "File not found" in calls[1]["messages"][-2]["content"]
    assert result_artifact["recovery_resolved"] is True
    assert result_artifact["transaction_status_counts"] == {
        "partial_failure": 1,
        "complete": 1,
    }
    assert result_artifact["recovery_outcomes"][0]["strategy"] == (
        "rollback_transaction"
    )


def _provider_with_fake_openai_compatible_responses(
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    responses: list[SimpleNamespace],
):
    if provider_name == "openai":
        fake_openai = _install_fake_openai_responses(monkeypatch, responses)
        return (
            OpenAIProvider(
                ProviderConfig(provider="openai", openai_api_key="test-key")
            ),
            fake_openai.calls,
        )
    if provider_name == "openrouter":
        fake_openai = _install_fake_openai_responses(monkeypatch, responses)
        return (
            OpenRouterProvider(
                ProviderConfig(provider="openrouter", openrouter_api_key="test-key")
            ),
            fake_openai.calls,
        )
    if provider_name == "ollama":
        fake_openai = _install_fake_openai_responses(monkeypatch, responses)
        return (
            OllamaProvider(ProviderConfig(provider="ollama", ollama_model="llama3.1")),
            fake_openai.calls,
        )
    if provider_name == "litellm":
        fake_litellm = _install_fake_litellm_responses(monkeypatch, responses)
        return (
            LiteLLMProvider(
                ProviderConfig(provider="litellm", litellm_model="openai/gpt-4o")
            ),
            fake_litellm.calls,
        )
    if provider_name == "zhipuai":
        fake_zai = _install_fake_zai_responses(monkeypatch, responses)
        return (
            ZhipuAIProvider(
                ProviderConfig(
                    provider="zhipuai",
                    zhipuai_api_key="test-key",
                    zhipuai_model="glm-4-flash",
                )
            ),
            fake_zai.calls,
        )
    raise AssertionError(f"Unsupported provider fixture: {provider_name}")


@pytest.mark.asyncio
async def test_google_provider_generic_edit_recovers_after_tool_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    target = tmp_path / "google-recover.txt"
    target.write_text("old\n", encoding="utf-8")
    fake_google = _install_fake_google_tool_responses(
        monkeypatch,
        [
            _google_tool_batch_response(
                [
                    ("write_file", {"path": target.name, "content": "new\n"}),
                    ("read_file", {"path": "missing.txt"}),
                ]
            ),
            _google_tool_batch_response(
                [
                    (
                        "rollback_transaction",
                        {"transaction_id": "native_tool_calls-1"},
                    ),
                    (
                        "finish",
                        {
                            "summary": "Google recovered provider tool loop",
                            "tests": [],
                            "risks": [],
                        },
                    ),
                ]
            ),
        ],
    )
    provider = GoogleProvider(
        ProviderConfig(
            provider="google",
            google_api_key="test-key",
            google_model="gemini-2.0-flash",
        )
    )
    session = provider.create_session(SessionConfig(name="google-recovery-loop"))
    runtime_session = create_runtime_session(
        provider_name="google",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "recover failed google provider tool loop",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.15",
    )

    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    function_responses = [
        part["function_response"]
        for content in fake_google.generate_calls[1]["contents"]
        for part in content["parts"]
        if "function_response" in part
    ]
    missing_tool_response = next(
        response for response in function_responses if response["name"] == "read_file"
    )

    assert result.status == "continue"
    assert target.read_text(encoding="utf-8") == "old\n"
    assert missing_tool_response["name"] == "read_file"
    assert "File not found" in json.dumps(missing_tool_response["response"])
    assert result_artifact["recovery_resolved"] is True
    assert result_artifact["transaction_status_counts"] == {
        "partial_failure": 1,
        "complete": 1,
    }
    assert result_artifact["recovery_outcomes"][0]["strategy"] == (
        "rollback_transaction"
    )


@pytest.mark.asyncio
async def test_google_provider_supports_generic_edit_native_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    target = tmp_path / "google-generic.txt"
    target.write_text("old\n", encoding="utf-8")
    fake_google = _install_fake_google_tool_responses(
        monkeypatch,
        [
            _google_tool_response(
                "write_file",
                {"path": "google-generic.txt", "content": "new\n"},
            ),
            _google_tool_response(
                "finish",
                {
                    "summary": "Google provider generic edit smoke",
                    "tests": [],
                    "risks": [],
                },
            ),
        ],
    )
    provider = GoogleProvider(
        ProviderConfig(
            provider="google",
            google_api_key="test-key",
            google_model="gemini-2.0-flash",
        )
    )
    session = provider.create_session(SessionConfig(name="google-generic-edit"))
    runtime_session = create_runtime_session(
        provider_name="google",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "update google-generic.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.3",
    )

    assert result.status == "continue"
    assert "Google provider generic edit smoke" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(fake_google.generate_calls) == 2
    function_response = fake_google.generate_calls[1]["contents"][-1]["parts"][0][
        "function_response"
    ]
    assert function_response["name"] == "write_file"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["subtask_id"] == "1.3"
    assert result_artifact["loop"] == "native_tool_calls"
    assert result_artifact["action_count"] == 2


@pytest.mark.asyncio
async def test_ollama_provider_supports_generic_edit_native_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    target = tmp_path / "ollama-generic.txt"
    target.write_text("old\n", encoding="utf-8")
    fake_openai = _install_fake_openai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_write",
                name="write_file",
                arguments={"path": "ollama-generic.txt", "content": "new\n"},
            ),
            _openai_tool_call_response(
                tool_call_id="call_finish",
                name="finish",
                arguments={
                    "summary": "Ollama provider generic edit smoke",
                    "tests": [],
                    "risks": [],
                },
            ),
        ],
    )
    provider = OllamaProvider(
        ProviderConfig(provider="ollama", ollama_model="llama3.1")
    )
    session = provider.create_session(SessionConfig(name="ollama-generic-edit"))
    runtime_session = create_runtime_session(
        provider_name="ollama",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "update ollama-generic.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.4",
    )

    assert result.status == "continue"
    assert "Ollama provider generic edit smoke" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(fake_openai.calls) == 2
    assert fake_openai.calls[1]["messages"][-1]["role"] == "tool"
    assert fake_openai.calls[1]["messages"][-1]["tool_call_id"] == "call_write"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["subtask_id"] == "1.4"
    assert result_artifact["loop"] == "native_tool_calls"
    assert result_artifact["action_count"] == 2


@pytest.mark.asyncio
async def test_openrouter_provider_supports_generic_edit_native_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    target = tmp_path / "openrouter-generic.txt"
    target.write_text("old\n", encoding="utf-8")
    fake_openai = _install_fake_openai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_write",
                name="write_file",
                arguments={"path": "openrouter-generic.txt", "content": "new\n"},
            ),
            _openai_tool_call_response(
                tool_call_id="call_finish",
                name="finish",
                arguments={
                    "summary": "OpenRouter provider generic edit smoke",
                    "tests": [],
                    "risks": [],
                },
            ),
        ],
    )
    provider = OpenRouterProvider(
        ProviderConfig(provider="openrouter", openrouter_api_key="test-key")
    )
    session = provider.create_session(SessionConfig(name="openrouter-generic-edit"))
    runtime_session = create_runtime_session(
        provider_name="openrouter",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "update openrouter-generic.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.5",
    )

    assert result.status == "continue"
    assert "OpenRouter provider generic edit smoke" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(fake_openai.calls) == 2
    assert fake_openai.calls[0]["stream"] is False
    assert fake_openai.calls[1]["messages"][-1]["tool_call_id"] == "call_write"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["subtask_id"] == "1.5"
    assert result_artifact["loop"] == "native_tool_calls"
    assert result_artifact["action_count"] == 2


@pytest.mark.asyncio
async def test_litellm_provider_supports_generic_edit_native_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    target = tmp_path / "litellm-generic.txt"
    target.write_text("old\n", encoding="utf-8")
    fake_litellm = _install_fake_litellm_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_write",
                name="write_file",
                arguments={"path": "litellm-generic.txt", "content": "new\n"},
            ),
            _openai_tool_call_response(
                tool_call_id="call_finish",
                name="finish",
                arguments={
                    "summary": "LiteLLM provider generic edit smoke",
                    "tests": [],
                    "risks": [],
                },
            ),
        ],
    )
    provider = LiteLLMProvider(
        ProviderConfig(provider="litellm", litellm_model="openai/gpt-4o")
    )
    session = provider.create_session(SessionConfig(name="litellm-generic-edit"))
    runtime_session = create_runtime_session(
        provider_name="litellm",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "update litellm-generic.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.6",
    )

    assert result.status == "continue"
    assert "LiteLLM provider generic edit smoke" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(fake_litellm.calls) == 2
    assert fake_litellm.calls[0]["tool_choice"] == "auto"
    assert fake_litellm.calls[1]["messages"][-1]["tool_call_id"] == "call_write"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["subtask_id"] == "1.6"
    assert result_artifact["loop"] == "native_tool_calls"
    assert result_artifact["action_count"] == 2


@pytest.mark.asyncio
async def test_zhipuai_provider_supports_generic_edit_native_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    target = tmp_path / "zhipuai-generic.txt"
    target.write_text("old\n", encoding="utf-8")
    fake_zai = _install_fake_zai_responses(
        monkeypatch,
        [
            _openai_tool_call_response(
                tool_call_id="call_write",
                name="write_file",
                arguments={"path": "zhipuai-generic.txt", "content": "new\n"},
            ),
            _openai_tool_call_response(
                tool_call_id="call_finish",
                name="finish",
                arguments={
                    "summary": "ZhipuAI provider generic edit smoke",
                    "tests": [],
                    "risks": [],
                },
            ),
        ],
    )
    provider = ZhipuAIProvider(
        ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4-flash",
        )
    )
    session = provider.create_session(SessionConfig(name="zhipuai-generic-edit"))
    runtime_session = create_runtime_session(
        provider_name="zhipuai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "update zhipuai-generic.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.7",
    )

    assert result.status == "continue"
    assert "ZhipuAI provider generic edit smoke" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert fake_zai.api_keys == ["test-key"]
    assert len(fake_zai.calls) == 2
    assert fake_zai.calls[0]["tool_choice"] == "auto"
    assert fake_zai.calls[1]["messages"][-1]["tool_call_id"] == "call_write"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["subtask_id"] == "1.7"
    assert result_artifact["loop"] == "native_tool_calls"
    assert result_artifact["action_count"] == 2
