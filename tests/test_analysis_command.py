import json
import sys
from pathlib import Path

import pytest
from core.providers.config import ProviderConfig


def test_parse_args_with_analyze_and_analysis_prompt():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = [
        "run.py",
        "--spec",
        "001",
        "--provider",
        "openai",
        "--analyze",
        "--analysis-prompt",
        "Focus on risk",
    ]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.provider == "openai"
    assert args.analyze is True
    assert args.analysis_prompt == "Focus on risk"


@pytest.mark.asyncio
async def test_run_analysis_only_session_saves_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from cli.analysis_commands import run_analysis_only_session

    spec_dir = tmp_path / ".auto-claude" / "specs" / "001-analysis"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# Spec\nBuild the thing.\n", encoding="utf-8")
    (spec_dir / "implementation_plan.json").write_text(
        json.dumps({"phases": []}),
        encoding="utf-8",
    )

    class FakeAnalysisSession:
        provider_name = "openai"

        async def complete(self, message: str, stream: bool = True):
            assert "Build the thing" in message
            assert "Focus on risk" in message
            assert stream is True
            yield "Risk: no implementation plan yet."

    class FakeProvider:
        name = "openai"

        def create_session(self, _session_config):
            return FakeAnalysisSession()

    monkeypatch.setattr(
        "cli.analysis_commands.ProviderConfig.from_env",
        lambda agent_type=None: ProviderConfig(
            provider="openai",
            openai_model="gpt-4o",
        ),
    )
    monkeypatch.setattr(
        "cli.analysis_commands.create_engine_provider",
        lambda _config: FakeProvider(),
    )

    result = await run_analysis_only_session(
        project_dir=tmp_path,
        spec_dir=spec_dir,
        model="gpt-4o",
        user_prompt="Focus on risk",
        verbose=False,
    )

    artifact_path = Path(result["artifact"])
    metadata_path = artifact_path.with_suffix(".json")
    assert result["status"] == "complete"
    assert result["provider"] == "openai"
    assert artifact_path.exists()
    assert metadata_path.exists()
    assert "Risk: no implementation plan" in artifact_path.read_text(encoding="utf-8")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["phase"] == "analysis"
    assert metadata["subtask_id"] is None
