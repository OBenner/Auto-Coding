import json
import sys


def test_parse_args_with_runtime_modes():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = ["run.py", "--runtime-modes"]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.runtime_modes is True


def test_parse_args_with_generic_edit_runtime_mode():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = ["run.py", "--runtime-mode", "generic-edit", "--runtime-modes"]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.runtime_mode == "generic-edit"


def test_runtime_modes_command_outputs_text(capsys):
    from cli.runtime_commands import handle_runtime_modes_command

    payload = handle_runtime_modes_command(output_json=False)
    output = capsys.readouterr().out

    assert "Provider Compatibility" in output
    assert "claude" in output
    assert "openai" in output
    assert "generic_edit" in output
    assert "patch_proposal" in output
    assert "CLI Runner Profiles" in output
    assert "CLI Runner Selection" in output
    assert "codex_cli" in output
    assert "generic_cli_pool" in output
    assert "--provider-smoke" in output
    assert payload["providers"][0]["provider"] == "claude"


def test_runtime_modes_command_outputs_json(capsys):
    from cli.runtime_commands import handle_runtime_modes_command

    handle_runtime_modes_command(output_json=True)
    output = capsys.readouterr().out
    payload = json.loads(output)

    provider_rows = {row["provider"]: row for row in payload["providers"]}
    assert provider_rows["claude"]["full_autonomous"] == "yes"
    assert provider_rows["openai"]["full_autonomous"] == "no"
    assert provider_rows["openai"]["generic_edit"] == "experimental"
    assert provider_rows["openai"]["analysis_only"] == "yes"
    assert provider_rows["claude"]["mcp_tools"] == "native"
    assert provider_rows["openai"]["mcp_tools"] == "local_bridge"
    assert provider_rows["claude"]["subagents"] == "native"
    assert provider_rows["openai"]["subagents"] == "orchestrated"
    assert "runtime_modes" in payload
    runner_rows = {row["runner_id"]: row for row in payload["cli_runner_profiles"]}
    assert runner_rows["codex_cli"]["runner_status"] == "wired"
    assert "full_autonomous" in runner_rows["codex_cli"]["supported_runtime_modes"]
    assert "availability" in runner_rows["codex_cli"]
    assert "executable_present" in runner_rows["codex_cli"]["availability"]
    assert "codex" in runner_rows["codex_cli"]["executable_candidates"]
    assert runner_rows["coderabbit_cli"]["role"] == "review"
    assert runner_rows["zai_claude_code"]["runner_status"] == "planned"
    assert "anthropic_compatible" in runner_rows["zai_claude_code"]["capability_tags"]
    assert runner_rows["generic_cli_pool"]["tier"] == "generic_pool"
    assert (
        runner_rows["generic_cli_pool"]["availability"]["status"] == "not_configurable"
    )
    selection_rows = payload["cli_runner_selection"]
    assert selection_rows["full_autonomous"]["selected_runner_ids"] == [
        "codex_cli",
        "claude_code",
        "zai_claude_code",
    ]
    assert "gemini_cli" in selection_rows["analysis_only"]["selected_runner_ids"]
    assert "aider" in selection_rows["generic_edit"]["selected_runner_ids"]
    assert "generic_edit" in payload["recommendations"]
    assert "provider_smoke" in payload["recommendations"]


def test_cli_runner_selection_filters_runtime_mode():
    from agents.runtime.cli_profiles import select_cli_runner_profiles

    analysis_selection = select_cli_runner_profiles(runtime_mode="analysis-only")
    assert analysis_selection.selected_runner_ids == (
        "gemini_cli",
        "coderabbit_cli",
        "github_copilot_cli",
        "generic_cli_pool",
    )

    full_autonomous_selection = select_cli_runner_profiles(
        runtime_mode="full_autonomous",
    )
    assert full_autonomous_selection.selected_runner_ids == (
        "codex_cli",
        "claude_code",
        "zai_claude_code",
    )


def test_cli_runner_selection_filters_capability():
    from agents.runtime.cli_profiles import select_cli_runner_profiles

    selection = select_cli_runner_profiles(required_capabilities=("review_only",))

    assert selection.selected_runner_ids == ("coderabbit_cli",)
    rejected_reasons = {
        rejection.runner_id: rejection.reasons
        for rejection in selection.rejected_profiles
    }
    assert rejected_reasons["codex_cli"] == ("missing_capability:review_only",)

    anthropic_selection = select_cli_runner_profiles(
        required_capabilities=("anthropic_compatible",),
    )
    assert anthropic_selection.selected_runner_ids == ("zai_claude_code",)


def test_cli_runner_selection_can_require_installed_runner(monkeypatch):
    from agents.runtime import cli_profiles

    def fake_find_executable(candidate: str) -> str | None:
        if candidate == "gemini":
            return "/usr/local/bin/gemini"
        return None

    monkeypatch.setattr(cli_profiles, "find_executable", fake_find_executable)

    selection = cli_profiles.select_cli_runner_profiles(
        runtime_mode="analysis_only",
        installed_only=True,
    )

    assert selection.selected_runner_ids == ("gemini_cli",)
    rejected_reasons = {
        rejection.runner_id: rejection.reasons
        for rejection in selection.rejected_profiles
    }
    assert "not_found" in rejected_reasons["coderabbit_cli"]
    assert "not_configurable" in rejected_reasons["generic_cli_pool"]
