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
from core.providers.adapters.google import GoogleProvider
from core.providers.adapters.litellm import LiteLLMProvider
from core.providers.adapters.ollama import OllamaProvider
from core.providers.adapters.openai import OpenAIProvider
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
