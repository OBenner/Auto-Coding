"""
GitHub PR Command Parser
========================

Parser for extracting commands from PR comment text.

Supports command extraction with keyword syntax (e.g., /merge, /resolve, /process).
Handles various formats including commands with/without arguments and mixed with other text.

Usage:
    parser = CommandParser()

    # Parse a single command
    commands = parser.parse("/merge main")
    # Returns: [Command(type="merge", args=["main"], position=0)]

    # Parse multiple commands
    commands = parser.parse("Please /merge and then /resolve dependencies")
    # Returns: [Command(type="merge", args=[], position=7), Command(type="resolve", args=["dependencies"], position=22)]
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

# Configure logger
logger = logging.getLogger(__name__)


class CommandParseError(Exception):
    """Raised when command parsing fails."""

    pass


@dataclass
class Command:
    """
    Represents a parsed command from a PR comment.

    Attributes:
        type: Command type (e.g., "merge", "resolve", "process")
        args: List of command arguments
        position: Character position where command starts in original text
        raw_text: Raw command text as it appears in the comment
    """

    type: str
    args: list[str]
    position: int
    raw_text: str


class CommandParser:
    """
    Parser for extracting commands from PR comment text.

    Supported commands:
    - /merge [branch] - Merge specified branch or current PR
    - /resolve - Attempt to resolve dependency conflicts
    - /process - Process/reply to outstanding comments

    The parser:
    - Recognizes commands starting with "/" prefix
    - Extracts command type and arguments
    - Handles multiple commands in a single comment
    - Ignores unknown commands gracefully
    - Tracks command positions for error reporting

    Usage:
        parser = CommandParser()

        # Simple command
        commands = parser.parse("/merge")
        # [Command(type="merge", args=[], position=0, raw_text="/merge")]

        # Command with arguments
        commands = parser.parse("/merge main")
        # [Command(type="merge", args=["main"], position=0, raw_text="/merge main")]

        # Multiple commands
        commands = parser.parse("LGTM /merge and /resolve")
        # [Command(type="merge", args=[], position=5, raw_text="/merge"),
        #  Command(type="resolve", args=[], position=20, raw_text="/resolve")]

        # Empty/unknown commands handled gracefully
        commands = parser.parse("No commands here")
        # []
        commands = parser.parse("/unknown")
        # []  # Unknown commands are ignored
    """

    # Supported command types
    SUPPORTED_COMMANDS = ["merge", "resolve", "process"]

    # Regex pattern to match commands: /command [args...]
    # Captures the command name and optional arguments
    COMMAND_PATTERN = re.compile(r"/(\w+)(?:\s+([^\n]*?))?(?=\s|$|/)")

    def __init__(self, allowed_commands: list[str] | None = None):
        """
        Initialize the command parser.

        Args:
            allowed_commands: Optional list of allowed command types.
                            If None, uses SUPPORTED_COMMANDS.
                            Useful for restricting to specific commands in certain contexts.
        """
        self.allowed_commands = allowed_commands or self.SUPPORTED_COMMANDS

    def parse(self, text: str) -> list[Command]:
        """
        Extract commands from PR comment text.

        Args:
            text: The comment text to parse

        Returns:
            List of Command objects in order of appearance

        Raises:
            CommandParseError: If text is not a string or other parsing error occurs

        Examples:
            >>> parser = CommandParser()
            >>> parser.parse("/merge")
            [Command(type='merge', args=[], position=0, raw_text='/merge')]
            >>> parser.parse("/merge main")
            [Command(type='merge', args=['main'], position=0, raw_text='/merge main')]
            >>> parser.parse("Please /merge and /process")
            [Command(type='merge', args=[], position=6, raw_text='/merge'), Command(type='process', args=[], position=20, raw_text='/process')]
        """
        if not isinstance(text, str):
            raise CommandParseError(f"Expected string input, got {type(text).__name__}")

        if not text or not text.strip():
            logger.debug("Empty text provided to parser")
            return []

        commands = []

        # Find all command matches in the text
        for match in self.COMMAND_PATTERN.finditer(text):
            command_type = match.group(1).lower()
            args_text = match.group(2) or ""
            position = match.start()
            raw_text = match.group(0)

            # Only process supported commands
            if command_type not in self.allowed_commands:
                logger.debug(f"Ignoring unknown command: {command_type}")
                continue

            # Parse arguments
            args = self._parse_args(args_text)

            command = Command(
                type=command_type,
                args=args,
                position=position,
                raw_text=raw_text,
            )
            commands.append(command)
            logger.debug(f"Parsed command: {command}")

        return commands

    def _parse_args(self, args_text: str) -> list[str]:
        """
        Parse command arguments from text.

        Args:
            args_text: The arguments string to parse

        Returns:
            List of argument strings

        Examples:
            >>> parser = CommandParser()
            >>> parser._parse_args("")
            []
            >>> parser._parse_args("main")
            ['main']
            >>> parser._parse_args("main feature-branch")
            ['main', 'feature-branch']
        """
        if not args_text or not args_text.strip():
            return []

        # Split on whitespace and filter empty strings
        args = [arg.strip() for arg in args_text.split() if arg.strip()]
        return args

    def is_supported_command(self, command_type: str) -> bool:
        """
        Check if a command type is supported.

        Args:
            command_type: The command type to check

        Returns:
            True if command is in allowed_commands, False otherwise
        """
        return command_type.lower() in self.allowed_commands
