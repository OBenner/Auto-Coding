"""
Agent Subprocess Entry Point
==============================

Standalone script for running agent sessions in isolated subprocesses.

This module provides a command-line interface for executing agent sessions
in isolation. It is designed to be invoked by AgentProcessIsolator and
communicates results via JSON over stdout.

Usage:
    python agent_subprocess.py \
        --project-dir /path/to/project \
        --spec-dir /path/to/spec \
        --agent-type coder \
        --model claude-sonnet-4 \
        --message "Implement feature X"

Output Format:
    JSON object written to stdout with structure:
    {
        "success": true,
        "output": {...},  # Agent-specific output
        "error": null,
        "execution_time": 123.45
    }
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Configure logging to stderr only (stdout reserved for JSON output)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Import debug utilities - wrapped with source module name for CodeQL compliance
_SOURCE = "agents.agent_subprocess"
try:
    from debug import (
        debug as _raw_debug,
    )
    from debug import (
        debug_error as _raw_debug_error,
    )
    from debug import (
        debug_success as _raw_debug_success,
    )
    from debug import (
        debug_verbose as _raw_debug_verbose,
    )
    from debug import (
        debug_warning as _raw_debug_warning,
    )
except ImportError:

    def _raw_debug(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_error(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_success(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_verbose(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_warning(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""


def _debug(msg: str, **kwargs) -> None:
    """Debug log with source module."""
    _raw_debug(_SOURCE, msg, **kwargs)


def _debug_verbose(msg: str, **kwargs) -> None:
    """Verbose debug log with source module."""
    _raw_debug_verbose(_SOURCE, msg, **kwargs)


def _debug_success(msg: str, **kwargs) -> None:
    """Success debug log with source module."""
    _raw_debug_success(_SOURCE, msg, **kwargs)


def _debug_error(msg: str, **kwargs) -> None:
    """Error debug log with source module."""
    _raw_debug_error(_SOURCE, msg, **kwargs)


def _debug_warning(msg: str, **kwargs) -> None:
    """Warning debug log with source module."""
    _raw_debug_warning(_SOURCE, msg, **kwargs)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for agent subprocess.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Run an agent session in isolated subprocess"
    )

    parser.add_argument(
        "--project-dir",
        type=str,
        required=True,
        help="Root directory of the project",
    )
    parser.add_argument(
        "--spec-dir",
        type=str,
        required=True,
        help="Directory containing the spec",
    )
    parser.add_argument(
        "--agent-type",
        type=str,
        required=True,
        help="Agent type (coder, planner, qa_reviewer, qa_fixer)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-5-20250929",
        help="Claude model to use",
    )
    parser.add_argument(
        "--message",
        type=str,
        default=None,
        help="Starting message for the agent session",
    )
    parser.add_argument(
        "--message-file",
        type=str,
        default=None,
        help="Path to file containing the starting message (alternative to --message)",
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default=None,
        help="Optional custom system prompt",
    )
    parser.add_argument(
        "--max-thinking-tokens",
        type=int,
        default=None,
        help="Maximum thinking tokens (optional)",
    )
    parser.add_argument(
        "--session-name",
        type=str,
        default="agent-session",
        help="Name for the agent session",
    )

    return parser.parse_args()


async def run_agent_session(
    project_dir: Path,
    spec_dir: Path,
    agent_type: str,
    model: str,
    starting_message: str,
    system_prompt: str | None = None,
    max_thinking_tokens: int | None = None,
    session_name: str = "agent-session",
) -> dict[str, Any]:
    """
    Run an agent session and return results.

    Args:
        project_dir: Root directory of the project
        spec_dir: Directory containing the spec
        agent_type: Type of agent to run
        model: Claude model to use
        starting_message: Initial message to send to agent
        system_prompt: Optional custom system prompt
        max_thinking_tokens: Optional thinking token limit
        session_name: Name for the session

    Returns:
        Dictionary with session results
    """
    from core.client import create_client

    _debug(f"Starting {agent_type} agent session in subprocess")
    _debug_verbose(f"Project: {project_dir}")
    _debug_verbose(f"Spec: {spec_dir}")
    _debug_verbose(f"Model: {model}")

    try:
        # Create client with security and MCP integration
        client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            agent_type=agent_type,
            max_thinking_tokens=max_thinking_tokens,
        )

        _debug(f"Client created, starting agent session: {session_name}")

        # Run the agent session
        session_kwargs = {
            "name": session_name,
            "starting_message": starting_message,
        }

        if system_prompt:
            session_kwargs["system_prompt"] = system_prompt

        response = await client.create_agent_session(**session_kwargs)

        _debug_success("Agent session completed successfully")

        return {
            "success": True,
            "output": {
                "response": str(response) if response else None,
                "agent_type": agent_type,
                "session_name": session_name,
            },
            "error": None,
        }

    except Exception as e:
        error_msg = f"Agent session failed: {str(e)}"
        _debug_error(error_msg)
        _debug_verbose(f"Traceback: {traceback.format_exc()}")

        return {
            "success": False,
            "output": None,
            "error": error_msg,
        }


def output_result(result: dict[str, Any], execution_time: float) -> None:
    """
    Output result as JSON to stdout.

    Args:
        result: Result dictionary from agent execution
        execution_time: Time taken for execution in seconds
    """
    output = {
        **result,
        "execution_time": execution_time,
    }

    # Write JSON to stdout (single line for easy parsing)
    try:
        json_output = json.dumps(output, indent=None, default=str)
    except TypeError:
        # Fallback: serialize with minimal info if output contains non-serializable objects
        json_output = json.dumps(
            {"success": False, "error": "Failed to serialize output", "output": None},
            indent=None,
        )
    print(json_output, file=sys.stdout, flush=True)


def run_isolated_agent() -> int:
    """
    Main entry point for isolated agent execution.

    Parses arguments, runs agent session, outputs results as JSON.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    start_time = time.time()

    try:
        # Parse arguments
        args = parse_args()

        # Convert paths
        project_dir = Path(args.project_dir).resolve()
        spec_dir = Path(args.spec_dir).resolve()

        # Validate paths
        if not project_dir.exists():
            raise ValueError(f"Project directory not found: {project_dir}")
        if not spec_dir.exists():
            raise ValueError(f"Spec directory not found: {spec_dir}")

        _debug(f"Running isolated agent: {args.agent_type}")

        # Resolve starting message from --message or --message-file
        starting_message = args.message
        if args.message_file:
            message_path = Path(args.message_file)
            if not message_path.exists():
                raise ValueError(f"Message file not found: {message_path}")
            starting_message = message_path.read_text(encoding="utf-8")
        if not starting_message:
            raise ValueError("Either --message or --message-file is required")

        # Run agent session
        result = asyncio.run(
            run_agent_session(
                project_dir=project_dir,
                spec_dir=spec_dir,
                agent_type=args.agent_type,
                model=args.model,
                starting_message=starting_message,
                system_prompt=args.system_prompt,
                max_thinking_tokens=args.max_thinking_tokens,
                session_name=args.session_name,
            )
        )

        execution_time = time.time() - start_time

        # Output result as JSON to stdout
        output_result(result, execution_time)

        # Return exit code based on success
        return 0 if result["success"] else 1

    except Exception as e:
        # Fatal error - output error result
        execution_time = time.time() - start_time
        error_result = {
            "success": False,
            "output": None,
            "error": f"Fatal error: {str(e)}",
        }

        logger.error(f"Fatal error in agent subprocess: {e}")
        logger.error(traceback.format_exc())

        output_result(error_result, execution_time)

        return 1


if __name__ == "__main__":
    sys.exit(run_isolated_agent())
