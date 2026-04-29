import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from agents.runtime import (
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
        assert message == "analyze"
        assert stream is True
        yield "hello"
        yield " world"


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


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
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
    assert target.read_text(encoding="utf-8") == "new\n"

    artifact_dir = tmp_path / "artifacts"
    assert (artifact_dir / "patch_proposal.json").exists()
    assert (artifact_dir / "patch.diff").exists()
    assert (artifact_dir / "patch_result.json").exists()
    result_artifact = json.loads(
        (artifact_dir / "patch_result.json").read_text(encoding="utf-8")
    )
    assert result_artifact["status"] == "applied"
    assert result_artifact["subtask_id"] is None


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


def test_patch_path_validator_rejects_sensitive_paths():
    for path in (".env", ".env.development", "secrets/api-key.txt"):
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


def test_runtime_mode_env_resolution(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTO_CODE_RUNTIME_MODE", "patch-proposal")
    assert get_runtime_mode("coder") == "patch_proposal"
    monkeypatch.setenv("AGENT_RUNTIME_MODE_CODER", "analysis-only")
    assert get_runtime_mode("coder") == "analysis_only"
    assert normalize_runtime_mode("full-autonomous") == "full_autonomous"
