"""
Security Hooks
==============

Pre-tool-use hooks that validate bash commands for security.
Main enforcement point for the security system.
"""

import os
from pathlib import Path
from typing import Any

from project_analyzer import BASE_COMMANDS, SecurityProfile, is_command_allowed

from .audit_logger import (
    CATEGORY_COMMAND_EXECUTION,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    log_security_event,
)
from .parser import extract_commands, get_command_for_validation, split_command_segments
from .profile import get_security_profile
from .validator import VALIDATORS


async def bash_security_hook(
    input_data: dict[str, Any],
    tool_use_id: str | None = None,
    context: Any | None = None,
) -> dict[str, Any]:
    """
    Pre-tool-use hook that validates bash commands using dynamic allowlist.

    This is the main security enforcement point. It:
    1. Validates tool_input structure (must be dict with 'command' key)
    2. Extracts command names from the command string
    3. Checks each command against the project's security profile
    4. Runs additional validation for sensitive commands
    5. Blocks disallowed commands with clear error messages

    Args:
        input_data: Dict containing tool_name and tool_input
        tool_use_id: Optional tool use ID
        context: Optional context

    Returns:
        Empty dict to allow, or {"decision": "block", "reason": "..."} to block
    """
    if input_data.get("tool_name") != "Bash":
        return {}

    # Validate tool_input structure before accessing
    tool_input = input_data.get("tool_input")

    # Check if tool_input is None (malformed tool call)
    if tool_input is None:
        return {
            "decision": "block",
            "reason": "Bash tool_input is None - malformed tool call from SDK",
        }

    # Check if tool_input is a dict
    if not isinstance(tool_input, dict):
        return {
            "decision": "block",
            "reason": f"Bash tool_input must be dict, got {type(tool_input).__name__}",
        }

    # Now safe to access command
    command = tool_input.get("command", "")
    if not command:
        return {}

    # Get the working directory from context or use current directory
    # Priority:
    # 1. Environment variable PROJECT_DIR_ENV_VAR (set by agent on startup)
    # 2. input_data cwd (passed by SDK in the tool call)
    # 3. Context cwd (should be set by ClaudeSDKClient but sometimes isn't)
    # 4. Current working directory (fallback, may be incorrect in worktree mode)
    from .constants import PROJECT_DIR_ENV_VAR

    cwd = os.environ.get(PROJECT_DIR_ENV_VAR)
    if not cwd:
        cwd = input_data.get("cwd")
    if not cwd and context and hasattr(context, "cwd"):
        cwd = context.cwd
    if not cwd:
        cwd = os.getcwd()

    # Get or create security profile
    # Note: In actual use, spec_dir would be passed through context
    try:
        profile = get_security_profile(Path(cwd))
    except Exception as e:
        # If profile creation fails, fall back to base commands only
        print(f"Warning: Could not load security profile: {e}")
        profile = SecurityProfile()
        profile.base_commands = BASE_COMMANDS.copy()

    # Extract all commands from the command string
    commands = extract_commands(command)

    if not commands:
        # Could not parse - fail safe by blocking
        log_security_event(
            project_dir=Path(cwd),
            category=CATEGORY_COMMAND_EXECUTION,
            message=f"Could not parse command for security validation: {command}",
            severity=SEVERITY_CRITICAL,
            allowed=False,
            command=command[:500],  # Truncate long commands
            agent_type=_extract_agent_type(context),
            session_id=_extract_session_id(context),
        )
        return {
            "decision": "block",
            "reason": f"Could not parse command for security validation: {command}",
        }

    # Split into segments for per-command validation
    segments = split_command_segments(command)

    # Check each command against the allowlist
    for cmd in commands:
        # Check if command is allowed
        is_allowed, reason = is_command_allowed(cmd, profile)

        if not is_allowed:
            log_security_event(
                project_dir=Path(cwd),
                category=CATEGORY_COMMAND_EXECUTION,
                message=f"Command blocked by allowlist: {cmd}",
                severity=SEVERITY_WARNING,
                allowed=False,
                command=cmd,
                agent_type=_extract_agent_type(context),
                session_id=_extract_session_id(context),
                context={"reason": reason},
            )
            return {
                "decision": "block",
                "reason": reason,
            }

        # Additional validation for sensitive commands
        if cmd in VALIDATORS:
            cmd_segment = get_command_for_validation(cmd, segments)
            if not cmd_segment:
                cmd_segment = command

            validator = VALIDATORS[cmd]
            validation_ok, validation_reason = validator(cmd_segment)
            if not validation_ok:
                log_security_event(
                    project_dir=Path(cwd),
                    category=CATEGORY_COMMAND_EXECUTION,
                    message=f"Command blocked by validator: {cmd}",
                    severity=SEVERITY_WARNING,
                    allowed=False,
                    command=cmd_segment[:500],  # Truncate long commands
                    agent_type=_extract_agent_type(context),
                    session_id=_extract_session_id(context),
                    context={"reason": validation_reason},
                )
                return {"decision": "block", "reason": validation_reason}

    # All commands passed validation - log the successful execution
    log_security_event(
        project_dir=Path(cwd),
        category=CATEGORY_COMMAND_EXECUTION,
        message=f"Command validated successfully: {commands[0]}"
        if len(commands) == 1
        else f"Commands validated successfully: {', '.join(commands)}",
        severity=SEVERITY_INFO,
        allowed=True,
        command=command[:500],  # Truncate long commands
        agent_type=_extract_agent_type(context),
        session_id=_extract_session_id(context),
    )
    return {}


def validate_command(
    command: str,
    project_dir: Path | None = None,
) -> tuple[bool, str]:
    """
    Validate a command string (for testing/debugging).

    Args:
        command: Full command string to validate
        project_dir: Optional project directory (uses cwd if not provided)

    Returns:
        (is_allowed, reason) tuple
    """
    if project_dir is None:
        project_dir = Path.cwd()

    profile = get_security_profile(project_dir)
    commands = extract_commands(command)

    if not commands:
        return False, "Could not parse command"

    segments = split_command_segments(command)

    for cmd in commands:
        is_allowed_result, reason = is_command_allowed(cmd, profile)
        if not is_allowed_result:
            return False, reason

        if cmd in VALIDATORS:
            cmd_segment = get_command_for_validation(cmd, segments)
            if not cmd_segment:
                cmd_segment = command

            validator = VALIDATORS[cmd]
            validation_ok, validation_reason = validator(cmd_segment)
            if not validation_ok:
                return False, validation_reason

    return True, ""


def _extract_agent_type(context: Any | None) -> str | None:
    """
    Extract agent type from context for audit logging.

    Args:
        context: Optional context object from SDK

    Returns:
        Agent type string if available, None otherwise
    """
    if not context:
        return None

    # Try common attribute names
    if hasattr(context, "agent_type"):
        return str(context.agent_type)
    if hasattr(context, "agentType"):
        return str(context.agentType)
    if hasattr(context, "type"):
        return str(context.type)

    # Try dict-like access
    try:
        if isinstance(context, dict):
            return context.get("agent_type") or context.get("agentType")
    except (TypeError, AttributeError):
        # context may not support dict operations despite isinstance check
        pass

    return None


def _extract_session_id(context: Any | None) -> str | None:
    """
    Extract session ID from context for audit logging.

    Args:
        context: Optional context object from SDK

    Returns:
        Session ID string if available, None otherwise
    """
    if not context:
        return None

    # Try common attribute names
    if hasattr(context, "session_id"):
        return str(context.session_id)
    if hasattr(context, "sessionId"):
        return str(context.sessionId)
    if hasattr(context, "session"):
        return str(context.session)

    # Try dict-like access
    try:
        if isinstance(context, dict):
            return context.get("session_id") or context.get("sessionId")
    except (TypeError, AttributeError):
        # context may not support dict operations despite isinstance check
        pass

    return None
