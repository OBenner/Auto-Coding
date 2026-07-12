#!/usr/bin/env python3
"""
Tests for the CLI session runner and harness tool registration.

Tests cover:
- Output capture and exit codes
- Scripted stdin input
- Timeout enforcement
- Output size capping
- Tool registration for QA agents
"""

# Add auto-claude to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from core.cli_session import MAX_OUTPUT_CHARS, run_cli_session

PYTHON = sys.executable


class TestRunCliSession:
    """Tests for run_cli_session."""

    def test_captures_output_and_exit_code(self, tmp_path):
        """Captures stdout and reports a zero exit code."""
        result = run_cli_session(
            f"{PYTHON} -c \"print('hello from cli')\"",
            cwd=str(tmp_path),
        )

        assert result.exit_code == 0
        assert result.timed_out is False
        assert "hello from cli" in result.output

    def test_nonzero_exit_code(self, tmp_path):
        """Reports non-zero exit codes."""
        result = run_cli_session(
            f'{PYTHON} -c "import sys; sys.exit(3)"',
            cwd=str(tmp_path),
        )

        assert result.exit_code == 3

    def test_captures_stderr(self, tmp_path):
        """stderr is captured in combined output."""
        result = run_cli_session(
            f"{PYTHON} -c \"import sys; print('oops', file=sys.stderr)\"",
            cwd=str(tmp_path),
        )

        assert "oops" in result.output

    def test_feeds_stdin_inputs(self, tmp_path):
        """Scripted stdin lines reach the application."""
        script = tmp_path / "prompt.py"
        script.write_text(
            "name = input('name? ')\nprint('hi ' + name)\n",
            encoding="utf-8",
        )

        result = run_cli_session(
            f"{PYTHON} {script}",
            cwd=str(tmp_path),
            inputs=["world"],
            timeout_seconds=15,
        )

        assert result.exit_code == 0
        assert "hi world" in result.output

    def test_timeout_kills_process(self, tmp_path):
        """A hung process is killed and flagged."""
        result = run_cli_session(
            f'{PYTHON} -c "import time; time.sleep(60)"',
            cwd=str(tmp_path),
            timeout_seconds=2,
        )

        assert result.timed_out is True

    def test_output_is_capped(self, tmp_path):
        """Runaway output is truncated to the cap."""
        result = run_cli_session(
            f"{PYTHON} -c \"print('x' * 300000)\"",
            cwd=str(tmp_path),
            timeout_seconds=30,
        )

        assert len(result.output) <= MAX_OUTPUT_CHARS

    def test_empty_command_is_noop(self, tmp_path):
        """Empty command returns an empty result instead of raising."""
        result = run_cli_session("", cwd=str(tmp_path))

        assert result.exit_code is None
        assert result.output == ""

    def test_runs_in_given_cwd(self, tmp_path):
        """The process runs in the requested working directory."""
        result = run_cli_session(
            f'{PYTHON} -c "import os; print(os.getcwd())"',
            cwd=str(tmp_path),
        )

        assert tmp_path.name in result.output


class TestToolRegistration:
    """Tests for QA agent access to the harness tool."""

    def test_qa_agents_have_cli_session_tool(self):
        """QA reviewer and fixer configs include run_cli_session."""
        from agents.tools_pkg.models import (
            TOOL_RUN_CLI_SESSION,
            get_agent_config,
        )

        for agent_type in ("qa_reviewer", "qa_fixer"):
            config = get_agent_config(agent_type)
            assert TOOL_RUN_CLI_SESSION in config["auto_claude_tools"]

    def test_coder_does_not_have_cli_session_tool(self):
        """Coder agents are not given the harness (QA-only)."""
        from agents.tools_pkg.models import (
            TOOL_RUN_CLI_SESSION,
            get_agent_config,
        )

        config = get_agent_config("coder")
        assert TOOL_RUN_CLI_SESSION not in config.get("auto_claude_tools", [])
