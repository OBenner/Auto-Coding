"""
CLI E2E Harness Tool
====================

MCP tool that lets QA agents verify command-line applications end-to-end:
spawn the app (in a pseudo-terminal on POSIX), feed scripted stdin lines,
capture output, and check expected substrings.

Commands run through the same security allowlist as Bash commands and are
always executed inside the project directory.
"""

import logging
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import tool

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# How much output to echo back to the agent
OUTPUT_TAIL_CHARS = 4_000

MAX_TIMEOUT_SECONDS = 300


def create_cli_harness_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create CLI harness tools bound to the given project directory.

    Args:
        spec_dir: Path to the spec directory (unused, kept for registry symmetry)
        project_dir: Path to the project root; commands run here

    Returns:
        List of tool functions
    """
    if not SDK_AVAILABLE:
        return []

    tools = []

    @tool(
        "run_cli_session",
        "Run a command-line application end-to-end and verify its behavior. "
        "Spawns the command inside a pseudo-terminal (so prompts, colors, and "
        "isatty() checks behave like a real terminal), optionally sends "
        "scripted stdin lines, captures combined output, and checks that "
        "expected substrings appear. Use this to E2E-test CLI apps the same "
        "way Electron MCP is used for desktop apps. The command must be "
        "allowed by the project security profile and runs in the project "
        "directory.",
        {
            "command": str,
            "inputs": str,
            "expect_substrings": str,
            "timeout_seconds": int,
        },
    )
    async def run_cli_session_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Run a CLI session and report the outcome."""
        command = (args.get("command") or "").strip()
        if not command:
            return _text_result("Error: command parameter is required")

        inputs_raw = args.get("inputs") or ""
        inputs = [line for line in inputs_raw.splitlines() if line != ""]

        expect_raw = args.get("expect_substrings") or ""
        expectations = [line for line in expect_raw.splitlines() if line.strip()]

        timeout_seconds = args.get("timeout_seconds") or 30
        timeout_seconds = max(1, min(int(timeout_seconds), MAX_TIMEOUT_SECONDS))

        try:
            from security import validate_command

            allowed, reason = validate_command(command, project_dir)
            if not allowed:
                return _text_result(f"Command blocked by security profile: {reason}")

            from core.cli_session import run_cli_session

            result = run_cli_session(
                command=command,
                cwd=str(project_dir),
                inputs=inputs,
                timeout_seconds=timeout_seconds,
            )
        except ImportError as e:
            return _text_result(f"Error: CLI harness not available: {e}")
        except Exception as e:
            logging.exception("Error during run_cli_session tool execution")
            return _text_result(f"Error running CLI session: {e}")

        return _text_result(_format_report(result, expectations))

    tools.append(run_cli_session_tool)

    return tools


def _format_report(result, expectations: list[str]) -> str:
    """Build a human-readable verification report."""
    missing = [e for e in expectations if e not in result.output]
    found = [e for e in expectations if e in result.output]

    lines = []
    if result.timed_out:
        lines.append("TIMED OUT: process was killed after the timeout")
    lines.append(f"Exit code: {result.exit_code}")

    if expectations:
        status = "PASS" if not missing else "FAIL"
        lines.append(f"Expectations: {status} ({len(found)}/{len(expectations)})")
        for item in found:
            lines.append(f"  [found] {item}")
        for item in missing:
            lines.append(f"  [MISSING] {item}")

    output_tail = result.output[-OUTPUT_TAIL_CHARS:]
    if len(result.output) > OUTPUT_TAIL_CHARS:
        lines.append(f"Output (last {OUTPUT_TAIL_CHARS} chars):")
    else:
        lines.append("Output:")
    lines.append(output_tail if output_tail else "(no output)")

    return "\n".join(lines)


def _text_result(text: str) -> dict[str, Any]:
    """Wrap text in the MCP tool result envelope."""
    return {"content": [{"type": "text", "text": text}]}


__all__ = ["create_cli_harness_tools"]
