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
    assert runner_rows["generic_cli_pool"]["tier"] == "generic_pool"
    assert (
        runner_rows["generic_cli_pool"]["availability"]["status"] == "not_configurable"
    )
    assert "generic_edit" in payload["recommendations"]
    assert "provider_smoke" in payload["recommendations"]
