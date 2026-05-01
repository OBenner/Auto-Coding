import asyncio
import json
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from agents.runtime import (
    LocalActionExecutor,
    RuntimeCapabilityError,
    RuntimeRequirements,
    create_runtime_session,
    get_runtime_mode,
    local_action_response_schema,
    local_action_tool_schemas,
    local_action_tool_specs,
    normalize_runtime_mode,
    render_local_action_prompt,
    requirements_for_runtime_mode,
    resolve_runtime_mode_with_fallback,
    run_runtime_session,
    runtime_fallback_enabled,
    save_runtime_fallback_artifact,
)
from agents.runtime.adapters.patch_proposal import (
    PatchProposalError,
    parse_patch_proposal,
    validate_workspace_relative_path,
)
from agents.runtime.local_actions import (
    MAX_TOOL_OUTPUT_CHARS,
    ToolActionResult,
    safe_action_for_trace,
    safe_result_for_trace,
)
from core.platform import run_process
from core.providers.config import ProviderConfig


class FakeClaudeClient:
    def __init__(self):
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return False


@pytest.mark.asyncio
async def test_claude_runtime_wraps_existing_session_runner(tmp_path: Path):
    client = FakeClaudeClient()
    agent_session = SimpleNamespace(client=client)

    async def runner(
        received_client,
        message,
        spec_dir,
        verbose,
        phase,
        subtask_id=None,
    ):
        await asyncio.sleep(0)
        assert received_client is client
        assert message == "do work"
        assert spec_dir == tmp_path
        assert verbose is True
        assert subtask_id == "1.1"
        return "complete", "done", {"input_tokens": 1, "output_tokens": 2}, "tracker"

    runtime_session = create_runtime_session(
        provider_name="claude",
        agent_session=agent_session,
        claude_session_runner=runner,
    )

    result = await run_runtime_session(
        runtime_session,
        "do work",
        tmp_path,
        verbose=True,
        requirements=RuntimeRequirements.full_coder(),
        subtask_id="1.1",
    )

    assert result.status == "complete"
    assert result.response_text == "done"
    assert result.usage_metadata == {"input_tokens": 1, "output_tokens": 2}
    assert result.decision_tracker == "tracker"
    assert client.entered is True
    assert client.exited is True


@pytest.mark.asyncio
async def test_codex_cli_runtime_uses_output_last_message(tmp_path: Path):
    fake_codex_script = tmp_path / "codex.py"
    fake_codex_script.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import pathlib
            import sys

            args = sys.argv[1:]
            assert args[0] == "exec"
            assert "--cd" in args
            assert "--sandbox" in args
            assert "--color" in args
            output_path = pathlib.Path(args[args.index("--output-last-message") + 1])
            message = sys.stdin.read().strip()
            output_path.write_text(f"final response: {message}", encoding="utf-8")
            print("codex event log")
            """
        ),
        encoding="utf-8",
    )
    if sys.platform == "win32":
        fake_codex = tmp_path / "codex.cmd"
        fake_codex.write_text(
            f'@echo off\r\n"{sys.executable}" "{fake_codex_script}" %*\r\n',
            encoding="utf-8",
        )
    else:
        fake_codex = tmp_path / "codex"
        fake_codex.write_text(
            fake_codex_script.read_text(encoding="utf-8"), encoding="utf-8"
        )
        fake_codex.chmod(0o755)

    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    session = SimpleNamespace(
        codex_command=str(fake_codex),
        codex_home=codex_home,
        model="codex-default",
    )
    runtime_session = create_runtime_session(
        provider_name="codex",
        agent_session=session,
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "do codex work",
        tmp_path,
        requirements=RuntimeRequirements.full_coder(),
    )

    assert result.status == "complete"
    assert result.response_text == "final response: do codex work"


class FakeCompletionSession:
    provider_name = "openai"

    async def complete(self, message: str, stream: bool = True):
        await asyncio.sleep(0)
        assert message == "analyze"
        assert stream is True
        yield "hello"
        yield " world"


class FakeClaudeCompletionSession:
    provider_name = "claude"

    async def complete(self, message: str, stream: bool = True):
        await asyncio.sleep(0)
        assert message == "analyze"
        assert stream is True
        yield "claude limited analysis"


class FakeClaudeQuerySession:
    provider_name = "claude"

    def __init__(self):
        self.client = FakeClaudeClient()
        self.query_message = None

    async def query(self, message: str):
        await asyncio.sleep(0)
        self.query_message = message

    async def receive_response(self):
        await asyncio.sleep(0)
        yield "query limited analysis"


@pytest.mark.asyncio
async def test_completion_runtime_supports_text_only(tmp_path: Path):
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakeCompletionSession(),
    )

    result = await run_runtime_session(
        runtime_session,
        "analyze",
        tmp_path,
        requirements=RuntimeRequirements.text_only(),
    )

    assert result.status == "complete"
    assert result.response_text == "hello world"


@pytest.mark.asyncio
async def test_claude_explicit_analysis_mode_uses_limited_runtime(tmp_path: Path):
    runtime_session = create_runtime_session(
        provider_name="claude",
        agent_session=FakeClaudeCompletionSession(),
        runtime_mode="analysis_only",
    )

    result = await run_runtime_session(
        runtime_session,
        "analyze",
        tmp_path,
        requirements=RuntimeRequirements.text_only(),
    )

    assert runtime_session.name == "completion"
    assert result.status == "complete"
    assert result.response_text == "claude limited analysis"


@pytest.mark.asyncio
async def test_claude_limited_runtime_manages_query_client_context(tmp_path: Path):
    session = FakeClaudeQuerySession()
    runtime_session = create_runtime_session(
        provider_name="claude",
        agent_session=session,
        runtime_mode="analysis_only",
    )

    result = await run_runtime_session(
        runtime_session,
        "analyze",
        tmp_path,
        requirements=RuntimeRequirements.text_only(),
    )

    assert result.response_text == "query limited analysis"
    assert session.query_message == "analyze"
    assert session.client.entered is True
    assert session.client.exited is True


@pytest.mark.asyncio
async def test_completion_runtime_fails_fast_for_full_coder(tmp_path: Path):
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakeCompletionSession(),
    )

    with pytest.raises(RuntimeCapabilityError) as exc:
        await run_runtime_session(
            runtime_session,
            "edit files",
            tmp_path,
            requirements=RuntimeRequirements.full_coder(),
        )

    message = str(exc.value)
    assert "provider=openai" in message
    assert "filesystem_edit" in message
    assert "native_tool_loop" in message
    assert "shell" in message


def test_create_agent_session_no_longer_requires_client(tmp_path: Path):
    from core.providers import factory

    class DummyProvider:
        name = "openai"

        def create_session(self, session_config):
            return SimpleNamespace(config=session_config, provider_name="openai")

    with (
        patch.object(
            factory.ProviderConfig,
            "from_env",
            return_value=ProviderConfig(provider="openai", openai_model="gpt-4o"),
        ),
        patch.object(factory, "create_engine_provider", return_value=DummyProvider()),
    ):
        session = factory.create_agent_session(
            agent_type="coder",
            project_dir=tmp_path,
            spec_dir=tmp_path / ".auto-claude" / "specs" / "001",
        )

    assert session.provider_name == "openai"
    assert session.config.model is None


class FakePatchProposalSession:
    provider_name = "openai"

    def __init__(self, proposal: dict):
        self.proposal = proposal

    async def complete(self, message: str, stream: bool = True):
        assert "patch proposal mode" in message
        assert stream is True
        yield json.dumps(self.proposal)


class FakeGenericEditSession:
    provider_name = "openai"

    def __init__(self, responses: list[dict]):
        self.responses = [json.dumps(response) for response in responses]
        self.messages: list[str] = []

    async def complete(self, message: str, stream: bool = True):
        assert stream is True
        self.messages.append(message)
        yield self.responses.pop(0)


class FakeNativeToolCallSession:
    provider_name = "openai"

    def __init__(self, responses: list[list[dict]]):
        self.responses = responses
        self.messages: list[str | None] = []
        self.tool_schemas: list[list[dict]] = []
        self.tool_results: list[dict] = []

    async def complete_with_tool_calls(self, message: str | None, tools: list[dict]):
        await asyncio.sleep(0)
        self.messages.append(message)
        self.tool_schemas.append(tools)
        tool_calls = [
            SimpleNamespace(
                id=f"call_{len(self.messages)}_{index}",
                name=call["name"],
                arguments=call.get("arguments", {}),
            )
            for index, call in enumerate(self.responses.pop(0), start=1)
        ]
        return SimpleNamespace(content="", tool_calls=tuple(tool_calls))

    def add_tool_result(self, tool_call_id: str, name: str, result: dict):
        self.tool_results.append(
            {"tool_call_id": tool_call_id, "name": name, "result": result}
        )


class FakeNativeToolFailureSession(FakeGenericEditSession):
    async def complete_with_tool_calls(self, message: str | None, tools: list[dict]):
        await asyncio.sleep(0)
        raise RuntimeError("provider rejected tool calls")

    def add_tool_result(self, tool_call_id: str, name: str, result: dict):
        raise AssertionError("tool results should not be added after fallback")


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
async def test_patch_proposal_runtime_applies_valid_unified_diff(tmp_path: Path):
    _init_git_repo(tmp_path)
    target = tmp_path / "hello.txt"
    target.write_text("old\n", encoding="utf-8")

    proposal = {
        "summary": "Update greeting fixture",
        "files": [
            {
                "path": "hello.txt",
                "operation": "modify",
                "patch": """diff --git a/hello.txt b/hello.txt
--- a/hello.txt
+++ b/hello.txt
@@ -1 +1 @@
-old
+new
""",
            }
        ],
        "tests": ["pytest tests/test_hello.py"],
        "risks": [],
    }

    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakePatchProposalSession(proposal),
        runtime_mode="patch_proposal",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change hello.txt",
        tmp_path,
        requirements=RuntimeRequirements.patch_proposal(),
    )

    assert result.status == "continue"
    assert "Update greeting fixture" in result.response_text
    assert "Files:" in result.response_text
    assert "modify: hello.txt" in result.response_text
    assert "patch_summary" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"

    artifact_dir = tmp_path / "artifacts"
    assert (artifact_dir / "patch_proposal.json").exists()
    assert (artifact_dir / "patch.diff").exists()
    assert (artifact_dir / "patch_result.json").exists()
    assert (artifact_dir / "patch_summary.md").exists()
    result_artifact = json.loads(
        (artifact_dir / "patch_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "applied"
    assert result_artifact["subtask_id"] is None
    assert result_artifact["files"] == [{"path": "hello.txt", "operation": "modify"}]
    assert result_artifact["file_count"] == 1
    assert result_artifact["tests"] == ["pytest tests/test_hello.py"]
    assert result_artifact["test_count"] == 1
    summary = (artifact_dir / "patch_summary.md").read_text(encoding="utf-8")
    assert "Patch Proposal Summary" in summary
    assert "`modify` `hello.txt`" in summary
    assert "`pytest tests/test_hello.py`" in summary


@pytest.mark.asyncio
async def test_patch_proposal_runtime_rejects_unsafe_paths(tmp_path: Path):
    _init_git_repo(tmp_path)
    proposal = {
        "summary": "Unsafe edit",
        "files": [
            {
                "path": "../evil.txt",
                "operation": "modify",
                "patch": """diff --git a/../evil.txt b/../evil.txt
--- a/../evil.txt
+++ b/../evil.txt
@@ -1 +1 @@
-old
+new
""",
            }
        ],
        "tests": [],
        "risks": [],
    }

    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=FakePatchProposalSession(proposal),
        runtime_mode="patch_proposal",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "unsafe edit",
        tmp_path,
        requirements=RuntimeRequirements.patch_proposal(),
    )

    assert result.status == "error"
    assert "unsafe segments" in result.response_text
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "patch_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "error"
    assert result_artifact["files"] == []
    assert result_artifact["file_count"] == 0


def test_patch_path_validator_rejects_sensitive_paths():
    for path in (
        ".env",
        ".env.development",
        ".ssh/id_rsa",
        ".npmrc",
        ".pypirc",
        ".zshrc",
        "secrets/api-key.txt",
    ):
        with pytest.raises(PatchProposalError):
            validate_workspace_relative_path(path)


def test_parse_patch_proposal_handles_braces_inside_strings():
    proposal = parse_patch_proposal(
        'prefix {"summary": "contains { braces }", "files": []} trailing {"ignored": true}'
    )

    assert proposal == {"summary": "contains { braces }", "files": []}


def test_parse_patch_proposal_strips_markdown_fence_without_regex():
    proposal = parse_patch_proposal(
        """```json
{"summary": "fenced", "files": []}
```"""
    )

    assert proposal == {"summary": "fenced", "files": []}


def test_parse_patch_proposal_requires_file_paths():
    with pytest.raises(PatchProposalError, match="field 'path'"):
        parse_patch_proposal(
            json.dumps(
                {
                    "summary": "missing path",
                    "files": [{"patch": "diff --git a/a.txt b/a.txt\n"}],
                }
            )
        )

    with pytest.raises(PatchProposalError, match="field 'path'"):
        parse_patch_proposal(
            json.dumps(
                {
                    "summary": "empty path",
                    "files": [{"path": "", "patch": "diff --git a/a.txt b/a.txt\n"}],
                }
            )
        )


def test_patch_mode_marks_subtask_completed(tmp_path: Path):
    from agents.coder import _mark_patch_subtask_completed

    spec_dir = tmp_path / ".auto-claude" / "specs" / "001-test"
    spec_dir.mkdir(parents=True)
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(
        json.dumps(
            {
                "feature": "Test",
                "workflow_type": "feature",
                "phases": [
                    {
                        "id": "1",
                        "name": "Phase 1",
                        "status": "in_progress",
                        "subtasks": [
                            {
                                "id": "1.1",
                                "description": "Edit file",
                                "status": "pending",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert _mark_patch_subtask_completed(spec_dir, "1.1") is True

    updated = json.loads(plan_file.read_text(encoding="utf-8"))
    subtask = updated["phases"][0]["subtasks"][0]
    assert subtask["status"] == "completed"
    assert subtask["completed_by"] == "patch_proposal"
    assert updated["phases"][0]["status"] == "completed"


def test_local_action_manifest_describes_generic_edit_contract():
    expected_tools = {
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
        "read_many_files",
        "write_file",
        "apply_patch",
        "run_command",
        "finish",
    }
    specs = local_action_tool_specs()
    assert {spec.name for spec in specs} == expected_tools

    prompt = render_local_action_prompt()
    for tool_name in expected_tools:
        assert f"- {tool_name}:" in prompt

    response_schema = local_action_response_schema()
    action_schemas = response_schema["properties"]["actions"]["items"]["oneOf"]
    assert {
        schema["properties"]["tool"]["enum"][0] for schema in action_schemas
    } == expected_tools

    provider_schemas = local_action_tool_schemas()
    stat_path_schema = next(
        schema for schema in provider_schemas if schema["name"] == "stat_path"
    )
    assert "path" in stat_path_schema["parameters"]["properties"]
    list_files_schema = next(
        schema for schema in provider_schemas if schema["name"] == "list_files"
    )
    assert "max_entries" in list_files_schema["parameters"]["properties"]
    search_text_schema = next(
        schema for schema in provider_schemas if schema["name"] == "search_text"
    )
    assert search_text_schema["parameters"]["required"] == ["query"]
    assert "max_matches" in search_text_schema["parameters"]["properties"]
    read_many_schema = next(
        schema for schema in provider_schemas if schema["name"] == "read_many_files"
    )
    assert read_many_schema["parameters"]["required"] == ["paths"]
    assert read_many_schema["parameters"]["properties"]["paths"]["maxItems"] == 10
    run_command_schema = next(
        schema for schema in provider_schemas if schema["name"] == "run_command"
    )
    assert run_command_schema["parameters"]["required"] == ["command"]
    assert "timeout" in run_command_schema["parameters"]["properties"]


@pytest.mark.asyncio
async def test_local_action_executor_stats_paths_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    file_result = await executor.execute(
        {
            "tool": "stat_path",
            "path": "src/app.py",
        }
    )

    assert file_result.ok is True
    assert file_result.data["exists"] is True
    assert file_result.data["type"] == "file"
    assert file_result.data["bytes"] > 0

    dir_result = await executor.execute(
        {
            "tool": "stat_path",
            "path": "src",
        }
    )
    assert dir_result.ok is True
    assert dir_result.data["type"] == "directory"
    assert "bytes" not in dir_result.data

    missing_result = await executor.execute(
        {
            "tool": "stat_path",
            "path": "src/missing.py",
        }
    )
    assert missing_result.ok is True
    assert missing_result.data["exists"] is False
    assert missing_result.data["type"] == "missing"

    sensitive_result = await executor.execute(
        {
            "tool": "stat_path",
            "path": ".env",
        }
    )
    assert sensitive_result.ok is False


@pytest.mark.asyncio
async def test_local_action_executor_lists_files_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "name: ci\n",
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "list_files",
            "recursive": True,
            "max_entries": 20,
        }
    )

    assert result.ok is True
    paths = [entry["path"] for entry in result.data["entries"]]
    assert "README.md" in paths
    assert "src" in paths
    assert "src/app.py" in paths
    assert ".env" not in paths
    assert ".github" not in paths
    assert ".github/workflows/ci.yml" not in paths
    assert "node_modules" not in paths
    app_entry = next(
        entry for entry in result.data["entries"] if entry["path"] == "src/app.py"
    )
    assert app_entry["type"] == "file"
    assert app_entry["bytes"] > 0

    hidden_result = await executor.execute(
        {
            "tool": "list_files",
            "path": ".github",
            "recursive": True,
            "include_hidden": True,
        }
    )
    hidden_paths = [entry["path"] for entry in hidden_result.data["entries"]]
    assert hidden_result.ok is True
    assert ".github/workflows/ci.yml" in hidden_paths

    truncated_result = await executor.execute(
        {
            "tool": "list_files",
            "recursive": True,
            "max_entries": 1,
        }
    )
    assert truncated_result.ok is True
    assert truncated_result.data["entry_count"] == 1
    assert truncated_result.data["truncated"] is True


@pytest.mark.asyncio
async def test_local_action_executor_searches_text_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "def target_handler():\n    return 'ok'\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("TARGET_HANDLER docs\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TARGET_HANDLER_SECRET=1\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "name: target_handler\n",
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text(
        "target_handler\n",
        encoding="utf-8",
    )
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "search_text",
            "query": "target_handler",
            "path": ".",
            "max_matches": 20,
        }
    )

    assert result.ok is True
    paths = [match["path"] for match in result.data["matches"]]
    assert "README.md" in paths
    assert "src/app.py" in paths
    assert ".env" not in paths
    assert ".github/workflows/ci.yml" not in paths
    assert "node_modules/pkg.js" not in paths
    app_match = next(
        match for match in result.data["matches"] if match["path"] == "src/app.py"
    )
    assert app_match["line"] == 1
    assert "target_handler" in app_match["excerpt"]

    hidden_result = await executor.execute(
        {
            "tool": "search_text",
            "query": "target_handler",
            "path": ".github",
            "include_hidden": True,
        }
    )
    hidden_paths = [match["path"] for match in hidden_result.data["matches"]]
    assert hidden_result.ok is True
    assert ".github/workflows/ci.yml" in hidden_paths

    truncated_result = await executor.execute(
        {
            "tool": "search_text",
            "query": "target_handler",
            "max_matches": 1,
        }
    )
    assert truncated_result.ok is True
    assert truncated_result.data["match_count"] == 1
    assert truncated_result.data["truncated"] is True


def test_search_text_trace_redacts_query_and_excerpts():
    request = safe_action_for_trace(
        {
            "tool": "search_text",
            "query": "SECRET_NEEDLE",
            "path": ".",
        }
    )
    result = safe_result_for_trace(
        ToolActionResult(
            tool="search_text",
            ok=True,
            message="Found 1 line match under .",
            data={
                "matches": [
                    {
                        "path": "src/app.py",
                        "line": 1,
                        "excerpt": "const token = 'SECRET_NEEDLE'",
                    }
                ],
            },
        )
    )

    assert request["query_redacted"] is True
    assert request["query_bytes"] == len("SECRET_NEEDLE")
    assert "query" not in request
    excerpt = result["data"]["matches"][0]["excerpt_redacted"]
    assert excerpt is True
    assert "SECRET_NEEDLE" not in json.dumps(result)


@pytest.mark.asyncio
async def test_local_action_executor_reads_many_files_safely(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "one.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "src" / "two.py").write_text("two line\n", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "read_many_files",
            "paths": ["src/one.py", "src/two.py", "src/missing.py"],
            "max_chars_per_file": 3,
        }
    )

    assert result.ok is False
    assert result.data["file_count"] == 3
    assert result.data["read_count"] == 2
    files_by_path = {file["path"]: file for file in result.data["files"]}
    assert files_by_path["src/one.py"]["content"] == "one"
    assert files_by_path["src/one.py"]["truncated"] is True
    assert files_by_path["src/two.py"]["content"] == "two"
    assert files_by_path["src/missing.py"]["ok"] is False
    assert "content" not in files_by_path["src/missing.py"]


@pytest.mark.asyncio
async def test_generic_edit_runtime_runs_local_action_loop(tmp_path: Path):
    target = tmp_path / "hello.txt"
    trace_marker = "TRACE_REDACTION_MARKER"
    target.write_text(f"old\n{trace_marker}\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "thought": "inspect target",
                "actions": [{"tool": "read_file", "path": "hello.txt"}],
            },
            {
                "thought": "replace content",
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "hello.txt",
                        "content": "new\n",
                    }
                ],
            },
            {
                "thought": "done",
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Updated greeting through generic edit",
                        "tests": ["not run"],
                        "risks": [],
                    }
                ],
            },
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change hello.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.1",
    )

    assert result.status == "continue"
    assert "Updated greeting through generic edit" in result.response_text
    assert "generic_edit_summary" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(session.messages) == 3
    assert "generic_edit mode" in session.messages[0]
    assert render_local_action_prompt() in session.messages[0]
    assert "observations" in session.messages[1]
    assert "generic_edit mode" in session.messages[1]
    assert "change hello.txt" in session.messages[1]

    artifact_dir = tmp_path / "artifacts"
    assert (artifact_dir / "generic_edit_trace.json").exists()
    assert (artifact_dir / "generic_edit_timeline.json").exists()
    assert (artifact_dir / "generic_edit_result.json").exists()
    assert (artifact_dir / "generic_edit_summary.md").exists()
    assert (artifact_dir / "generic_edit_observations.jsonl").exists()
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["stop_reason"] == "finish"
    assert result_artifact["subtask_id"] == "1.1"
    assert result_artifact["iteration_count"] == 3
    assert result_artifact["loop"] == "json_actions"
    assert result_artifact["action_count"] == 3
    assert result_artifact["failed_action_count"] == 0
    assert result_artifact["tool_counts"] == {
        "read_file": 1,
        "write_file": 1,
        "finish": 1,
    }
    assert result_artifact["failed_tools"] == {}
    assert result_artifact["observation_artifact"].endswith(
        "generic_edit_observations.jsonl"
    )
    assert result_artifact["action_timeline"] == [
        {
            "iteration": 1,
            "tool": "read_file",
            "ok": True,
            "message": "Read hello.txt",
            "path": "hello.txt",
            "truncated": False,
        },
        {
            "iteration": 2,
            "tool": "write_file",
            "ok": True,
            "message": "Wrote hello.txt",
            "path": "hello.txt",
        },
        {
            "iteration": 3,
            "tool": "finish",
            "ok": True,
            "message": "Updated greeting through generic edit",
        },
    ]
    assert result_artifact["tests"] == ["not run"]

    trace_text = (artifact_dir / "generic_edit_trace.json").read_text(encoding="utf-8")
    assert trace_marker not in trace_text
    trace = json.loads(trace_text)
    read_result = trace["trace"][0]["actions"][0]["result"]
    assert read_result["data"]["content_redacted"] is True
    assert read_result["data"]["content_bytes"] > 0
    assert "response_excerpt" in trace["trace"][0]
    assert "response" not in trace["trace"][0]
    timeline = json.loads(
        (artifact_dir / "generic_edit_timeline.json").read_text(encoding="utf-8")
    )
    assert timeline["stop_reason"] == "finish"
    assert timeline["timeline"] == result_artifact["action_timeline"]
    observation_lines = [
        json.loads(line)
        for line in (artifact_dir / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [line["result"]["tool"] for line in observation_lines] == [
        "read_file",
        "write_file",
        "finish",
    ]
    assert observation_lines[0]["loop"] == "json_actions"
    assert observation_lines[0]["result"]["data"]["content_redacted"] is True
    assert trace_marker not in (
        artifact_dir / "generic_edit_observations.jsonl"
    ).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_generic_edit_runtime_prefers_native_tool_call_loop(tmp_path: Path):
    target = tmp_path / "native.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeNativeToolCallSession(
        [
            [{"name": "read_file", "arguments": {"path": "native.txt"}}],
            [
                {
                    "name": "write_file",
                    "arguments": {
                        "path": "native.txt",
                        "content": "new\n",
                    },
                }
            ],
            [
                {
                    "name": "finish",
                    "arguments": {
                        "summary": "Updated through native tool calls",
                        "tests": ["not run"],
                        "risks": [],
                    },
                }
            ],
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change native.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
        subtask_id="1.3",
    )

    assert result.status == "continue"
    assert "Updated through native tool calls" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert session.messages[0] is not None
    assert "function calls" in session.messages[0]
    assert session.messages[1:] == [None, None]
    assert [schema["name"] for schema in session.tool_schemas[0]][:4] == [
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
    ]
    assert [result["name"] for result in session.tool_results] == [
        "read_file",
        "write_file",
        "finish",
    ]

    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    assert trace["trace"][0]["loop"] == "native_tool_calls"
    assert trace["trace"][0]["actions"][0]["request"]["tool"] == "read_file"
    assert trace["trace"][0]["actions"][0]["result"]["data"]["content_redacted"]
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["subtask_id"] == "1.3"
    assert result_artifact["stop_reason"] == "finish"
    assert result_artifact["iteration_count"] == 3
    assert result_artifact["loop"] == "native_tool_calls"
    assert result_artifact["action_count"] == 3
    assert result_artifact["tool_counts"]["finish"] == 1
    assert result_artifact["action_timeline"][0]["tool_call_id"] == "call_1_1"
    observation_lines = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "generic_edit_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert observation_lines[0]["loop"] == "native_tool_calls"
    assert observation_lines[0]["request"]["tool_call_id"] == "call_1_1"
    assert [line["result"]["tool"] for line in observation_lines] == [
        "read_file",
        "write_file",
        "finish",
    ]


@pytest.mark.asyncio
async def test_generic_edit_runtime_rejects_non_terminal_json_finish(tmp_path: Path):
    target = tmp_path / "after-finish.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeGenericEditSession(
        [
            {
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "done too early",
                    },
                    {
                        "tool": "write_file",
                        "path": "after-finish.txt",
                        "content": "new\n",
                    },
                ],
            }
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "reject non-terminal finish",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "finish" in result.response_text
    assert target.read_text(encoding="utf-8") == "old\n"
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["stop_reason"] == "non_terminal_finish"


@pytest.mark.asyncio
async def test_generic_edit_runtime_rejects_non_terminal_native_finish(
    tmp_path: Path,
):
    target = tmp_path / "after-native-finish.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeNativeToolCallSession(
        [
            [
                {
                    "name": "finish",
                    "arguments": {"summary": "done too early"},
                },
                {
                    "name": "write_file",
                    "arguments": {
                        "path": "after-native-finish.txt",
                        "content": "new\n",
                    },
                },
            ]
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "reject native non-terminal finish",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "finish" in result.response_text
    assert target.read_text(encoding="utf-8") == "old\n"
    assert session.tool_results == []
    result_artifact = json.loads(
        (tmp_path / "artifacts" / "generic_edit_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_artifact["stop_reason"] == "non_terminal_finish"


@pytest.mark.asyncio
async def test_generic_edit_runtime_falls_back_when_native_tools_rejected(
    tmp_path: Path,
):
    target = tmp_path / "fallback.txt"
    target.write_text("old\n", encoding="utf-8")
    session = FakeNativeToolFailureSession(
        [
            {
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "fallback.txt",
                        "content": "new\n",
                    },
                    {
                        "tool": "finish",
                        "summary": "Fallback JSON loop completed",
                        "tests": [],
                    },
                ],
            }
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "change fallback.txt",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    assert "Fallback JSON loop completed" in result.response_text
    assert target.read_text(encoding="utf-8") == "new\n"
    assert len(session.messages) == 1
    assert "Respond with exactly one JSON object" in session.messages[0]
    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    assert "loop" not in trace["trace"][0]


@pytest.mark.asyncio
async def test_local_action_executor_rejects_command_chaining(tmp_path: Path):
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "run_command",
            "command": "git status --short && git status --short",
        }
    )

    assert result.ok is False
    assert result.tool == "run_command"
    assert "one command at a time" in result.message


@pytest.mark.asyncio
async def test_local_action_executor_bounds_read_before_returning(tmp_path: Path):
    target = tmp_path / "large.txt"
    target.write_text("abcdef", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    result = await executor.execute(
        {
            "tool": "read_file",
            "path": "large.txt",
            "max_chars": 3,
        }
    )

    assert result.ok is True
    assert result.data["content"] == "abc"
    assert result.data["truncated"] is True


@pytest.mark.asyncio
async def test_local_action_executor_rejects_zero_limits(tmp_path: Path):
    target = tmp_path / "large.txt"
    target.write_text("abcdef", encoding="utf-8")
    executor = LocalActionExecutor(tmp_path)

    read_result = await executor.execute(
        {
            "tool": "read_file",
            "path": "large.txt",
            "max_chars": 0,
        }
    )
    command_result = await executor.execute(
        {
            "tool": "run_command",
            "command": "git status --short",
            "timeout": 0,
        }
    )

    assert read_result.ok is False
    assert "greater than 0" in read_result.message
    assert command_result.ok is False
    assert "greater than 0" in command_result.message


@pytest.mark.asyncio
async def test_local_action_executor_bounds_command_output(tmp_path: Path):
    executor = LocalActionExecutor(tmp_path)

    completed = await executor._run_subprocess_bounded(
        [sys.executable, "-c", "print('x' * 20000)"],
        timeout=10,
    )

    assert completed.truncated is True
    assert len(completed.output) <= MAX_TOOL_OUTPUT_CHARS


@pytest.mark.asyncio
async def test_generic_edit_runtime_runs_validated_single_command(tmp_path: Path):
    _init_git_repo(tmp_path)
    session = FakeGenericEditSession(
        [
            {
                "actions": [
                    {
                        "tool": "run_command",
                        "command": "git status --short",
                        "timeout": 10,
                    }
                ],
            },
            {
                "actions": [
                    {
                        "tool": "finish",
                        "summary": "Validated command completed",
                        "tests": ["git status --short"],
                    }
                ],
            },
        ]
    )
    runtime_session = create_runtime_session(
        provider_name="openai",
        agent_session=session,
        runtime_mode="generic_edit",
        project_dir=tmp_path,
    )

    result = await run_runtime_session(
        runtime_session,
        "check repository",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "continue"
    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    command_result = trace["trace"][0]["actions"][0]["result"]
    assert command_result["ok"] is True
    assert command_result["data"]["exit_code"] == 0


@pytest.mark.asyncio
async def test_generic_edit_runtime_rejects_unsafe_write_path(tmp_path: Path):
    from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession

    session = FakeGenericEditSession(
        [
            {
                "actions": [
                    {
                        "tool": "write_file",
                        "path": "../evil.txt",
                        "content": "bad\n",
                    },
                    {
                        "tool": "finish",
                        "summary": "should not finish while action failed",
                    },
                ],
            }
        ]
    )
    runtime_session = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=session,
        project_dir=tmp_path,
        max_iterations=1,
    )

    result = await run_runtime_session(
        runtime_session,
        "unsafe write",
        tmp_path,
        requirements=RuntimeRequirements.generic_edit(),
    )

    assert result.status == "error"
    assert "max iterations" in result.response_text
    assert not (tmp_path.parent / "evil.txt").exists()
    trace = json.loads(
        (tmp_path / "artifacts" / "generic_edit_trace.json").read_text(encoding="utf-8")
    )
    first_result = trace["trace"][0]["actions"][0]["result"]
    assert first_result["ok"] is False
    assert "unsafe segments" in first_result["message"]


def test_runtime_mode_env_resolution(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTO_CODE_RUNTIME_MODE", "patch-proposal")
    assert get_runtime_mode("coder") == "patch_proposal"
    monkeypatch.setenv("AGENT_RUNTIME_MODE_CODER", "analysis-only")
    assert get_runtime_mode("coder") == "analysis_only"
    assert normalize_runtime_mode("full-autonomous") == "full_autonomous"
    assert normalize_runtime_mode("generic-edit") == "generic_edit"


def test_runtime_fallback_is_explicit_and_capability_aware(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("AUTO_CODE_RUNTIME_FALLBACK", raising=False)
    assert runtime_fallback_enabled() is False

    fail_fast = resolve_runtime_mode_with_fallback(
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="coding",
    )
    assert fail_fast.selected_mode == "full_autonomous"
    assert fail_fast.fallback_applied is False
    assert "disabled" in fail_fast.reason
    assert fail_fast.missing_capabilities == (
        "native_tool_loop",
        "filesystem_edit",
        "shell",
    )
    assert fail_fast.compatible_fallbacks == (
        "generic_edit",
        "patch_proposal",
        "analysis_only",
    )

    monkeypatch.setenv("AUTO_CODE_RUNTIME_FALLBACK", "true")
    degraded = resolve_runtime_mode_with_fallback(
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="coding",
    )
    assert degraded.selected_mode == "generic_edit"
    assert degraded.fallback_applied is True
    assert "using generic_edit" in degraded.reason
    assert degraded.to_dict()["compatible_fallbacks"] == [
        "generic_edit",
        "patch_proposal",
        "analysis_only",
    ]

    claude = resolve_runtime_mode_with_fallback(
        provider_name="claude",
        requested_mode="full_autonomous",
        phase="coding",
    )
    assert claude.selected_mode == "full_autonomous"
    assert claude.fallback_applied is False

    analysis = resolve_runtime_mode_with_fallback(
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="analysis",
    )
    assert analysis.selected_mode == "full_autonomous"
    assert analysis.fallback_applied is False


def test_runtime_fallback_artifact_records_capability_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AUTO_CODE_RUNTIME_FALLBACK", "true")
    decision = resolve_runtime_mode_with_fallback(
        provider_name="openai",
        requested_mode="full_autonomous",
        phase="coding",
    )

    artifact_path = save_runtime_fallback_artifact(
        spec_dir=tmp_path,
        decision=decision,
        phase="coding",
        session_num=2,
        subtask_id="1.2",
    )

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "coding"
    assert payload["session"] == 2
    assert payload["subtask_id"] == "1.2"
    assert payload["decision"]["provider"] == "openai"
    assert payload["decision"]["requested_mode"] == "full_autonomous"
    assert payload["decision"]["selected_mode"] == "generic_edit"
    assert payload["decision"]["fallback_applied"] is True
    assert payload["decision"]["missing_capabilities"] == [
        "native_tool_loop",
        "filesystem_edit",
        "shell",
    ]


def test_runtime_requirements_follow_selected_runtime_mode():
    assert (
        requirements_for_runtime_mode(
            "full_autonomous",
            phase="planning",
        )
        == RuntimeRequirements.planner()
    )
    assert (
        requirements_for_runtime_mode(
            "generic_edit",
            phase="planning",
        )
        == RuntimeRequirements.generic_edit()
    )
    assert (
        requirements_for_runtime_mode(
            "patch_proposal",
            phase="coding",
        )
        == RuntimeRequirements.patch_proposal()
    )
    assert (
        requirements_for_runtime_mode(
            "analysis_only",
            phase="coding",
        )
        == RuntimeRequirements.text_only()
    )


@pytest.mark.asyncio
async def test_analysis_only_coding_saves_artifact_without_post_processing(
    temp_git_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from agents.coder import run_autonomous_agent

    spec_dir = temp_git_repo / ".auto-claude" / "specs" / "001-analysis"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# Analyze only\n", encoding="utf-8")
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(
        json.dumps(
            {
                "feature": "Analyze only",
                "workflow_type": "feature",
                "phases": [
                    {
                        "id": "1",
                        "name": "Phase 1",
                        "subtasks": [
                            {
                                "id": "1.1",
                                "description": "Explain the likely edit path",
                                "status": "pending",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    class FakeAnalysisSession:
        provider_name = "openai"

        async def complete(self, message: str, stream: bool = True):
            await asyncio.sleep(0)
            assert "Explain the likely edit path" in message
            assert stream is True
            yield "Inspect src/app.py before proposing edits."

    class FakeProvider:
        name = "openai"

        def create_session(self, _session_config):
            return FakeAnalysisSession()

    async def fake_get_graphiti_context(*_args, **_kwargs):
        await asyncio.sleep(0)
        return None

    async def fake_get_pattern_suggestions(*_args, **_kwargs):
        await asyncio.sleep(0)
        return None

    async def fail_post_session_processing(*_args, **_kwargs):
        await asyncio.sleep(0)
        raise AssertionError("analysis_only coding must not run post processing")

    monkeypatch.setenv("AI_ENGINE_PROVIDER", "openai")
    monkeypatch.setenv("AGENT_RUNTIME_MODE_CODER", "analysis_only")
    monkeypatch.setattr(
        "agents.coder.create_engine_provider", lambda *_a: FakeProvider()
    )
    monkeypatch.setattr("agents.coder.is_linear_enabled", lambda: False)
    monkeypatch.setattr("agents.coder.get_graphiti_context", fake_get_graphiti_context)
    monkeypatch.setattr(
        "agents.coder.get_pattern_suggestions",
        fake_get_pattern_suggestions,
    )
    monkeypatch.setattr("agents.coder.load_subtask_context", lambda *_a, **_k: {})
    monkeypatch.setattr(
        "agents.coder.post_session_processing",
        fail_post_session_processing,
    )
    monkeypatch.setattr("agents.coder.AUTO_CONTINUE_DELAY_SECONDS", 0)

    await run_autonomous_agent(
        project_dir=temp_git_repo,
        spec_dir=spec_dir,
        model="gpt-4o",
        max_iterations=1,
        verbose=False,
    )

    artifact_path = next(
        (spec_dir / "artifacts").glob("analysis_only_coding_session-1_1.1_openai_*.md")
    )
    metadata_path = artifact_path.with_suffix(".json")
    assert artifact_path.exists()
    assert metadata_path.exists()
    assert "Inspect src/app.py" in artifact_path.read_text(encoding="utf-8")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "analysis_only"
    assert metadata["provider"] == "openai"
    assert metadata["subtask_id"] == "1.1"

    updated_plan = json.loads(plan_file.read_text(encoding="utf-8"))
    subtask = updated_plan["phases"][0]["subtasks"][0]
    assert subtask["status"] == "pending"
