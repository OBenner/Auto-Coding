import asyncio
import json
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
    normalize_runtime_mode,
    run_runtime_session,
)
from agents.runtime.adapters.patch_proposal import (
    PatchProposalError,
    parse_patch_proposal,
    validate_workspace_relative_path,
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
    assert "observations" in session.messages[1]
    assert "generic_edit mode" in session.messages[1]
    assert "change hello.txt" in session.messages[1]

    artifact_dir = tmp_path / "artifacts"
    assert (artifact_dir / "generic_edit_trace.json").exists()
    assert (artifact_dir / "generic_edit_result.json").exists()
    assert (artifact_dir / "generic_edit_summary.md").exists()
    result_artifact = json.loads(
        (artifact_dir / "generic_edit_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "complete"
    assert result_artifact["subtask_id"] == "1.1"
    assert result_artifact["iteration_count"] == 3
    assert result_artifact["tests"] == ["not run"]

    trace_text = (artifact_dir / "generic_edit_trace.json").read_text(
        encoding="utf-8"
    )
    assert trace_marker not in trace_text
    trace = json.loads(trace_text)
    read_result = trace["trace"][0]["actions"][0]["result"]
    assert read_result["data"]["content_redacted"] is True
    assert read_result["data"]["content_bytes"] > 0
    assert "response_excerpt" in trace["trace"][0]
    assert "response" not in trace["trace"][0]


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

    artifact_path = (
        spec_dir
        / "artifacts"
        / "analysis_only_coding_session-1_1.1_openai.md"
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
