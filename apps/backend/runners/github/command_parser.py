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

    # Maximum comment length to parse — guards against ReDoS on pathological input
    MAX_INPUT_LENGTH = 20_000

    # Regex pattern to match commands: /command [args...]
    # Captures the command name (including trailing special chars) and optional arguments
    # Pattern: / followed by non-whitespace chars (command), then optional args, stops at whitespace, end, or another /
    # Negative lookbehind (?<!/) prevents matching commands after another slash (e.g., //merge)
    # [^\n#/]*? on the args side avoids catastrophic backtracking
    COMMAND_PATTERN = re.compile(r"(?<!/)/(\S+?)(?:\s+([^\n#/]*?))?(?=\s|$|/)")

    # Pattern for detecting malformed commands (e.g., /@merge, /123, //merge)
    # Matches: slash followed by non-word non-space, slash followed by digits, double slash
    MALFORMED_PATTERN = re.compile(r"/[^\w\s]|/\d+|//+")

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

        # Guard against extremely long inputs to avoid ReDoS
        if len(text) > self.MAX_INPUT_LENGTH:
            logger.warning(
                "Comment text too long for command parsing (len=%d, max=%d); truncating",
                len(text),
                self.MAX_INPUT_LENGTH,
            )
            text = text[: self.MAX_INPUT_LENGTH]

        # Check for malformed command patterns and log warnings (metadata only, no raw text)
        if self.MALFORMED_PATTERN.search(text):
            logger.debug(
                "Detected potentially malformed command patterns in input",
                extra={"event": "malformed_command_detected", "length": len(text)},
            )

        commands = []

        # Find all command matches in the text
        for match in self.COMMAND_PATTERN.finditer(text):
            command_type = match.group(1).lower()
            args_text = match.group(2) or ""
            position = match.start()
            raw_text = match.group(0)

            # Sanitize command type: remove trailing non-word characters
            # This handles cases like "/merge!" or "/merge." by extracting "merge"
            command_type = self._sanitize_command_type(command_type)

            # Skip if command type is empty after sanitization
            if not command_type:
                logger.debug(f"Skipping empty command type at position {position}")
                continue

            # Only process supported commands
            if command_type not in self.allowed_commands:
                logger.debug(f"Ignoring unknown command: {command_type}")
                continue

            # Parse arguments with validation
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

    def _sanitize_command_type(self, command_type: str) -> str:
        """
        Sanitize command type by removing trailing special characters.

        This handles edge cases like "/merge!" or "/merge." by extracting "merge".

        Args:
            command_type: The raw command type to sanitize

        Returns:
            Sanitized command type containing only word characters

        Examples:
            >>> parser = CommandParser()
            >>> parser._sanitize_command_type("merge")
            'merge'
            >>> parser._sanitize_command_type("merge!")
            'merge'
            >>> parser._sanitize_command_type("merge.")
            'merge'
            >>> parser._sanitize_command_type("123")
            ''
        """
        if not command_type:
            return ""

        # Remove any trailing non-word characters (anything that's not a-z, A-Z, 0-9, _, or unicode letters)
        # Also remove purely numeric commands
        sanitized = re.sub(r"\W+$", "", command_type, flags=re.UNICODE)

        # Skip purely numeric commands (e.g., /123)
        if sanitized.isdigit():
            logger.debug(f"Skipping numeric command: {command_type}")
            return ""

        return sanitized

    def _parse_args(self, args_text: str) -> list[str]:
        """
        Parse command arguments from text with validation.

        Handles special characters, empty arguments, and malformed input gracefully.

        Args:
            args_text: The arguments string to parse

        Returns:
            List of validated argument strings

        Examples:
            >>> parser = CommandParser()
            >>> parser._parse_args("")
            []
            >>> parser._parse_args("main")
            ['main']
            >>> parser._parse_args("main feature-branch")
            ['main', 'feature-branch']
            >>> parser._parse_args("main! branch.")
            ['main', 'branch']
        """
        if not args_text or not args_text.strip():
            return []

        # Split on whitespace and filter empty strings
        args = [arg.strip() for arg in args_text.split() if arg.strip()]

        # Sanitize each argument by removing trailing punctuation/special chars
        # This handles cases like "main!" or "branch." by extracting "main", "branch"
        sanitized_args = []
        for arg in args:
            # Remove trailing punctuation (but keep internal punctuation like hyphens, underscores)
            sanitized = re.sub(r"[^\w-]+$", "", arg, flags=re.UNICODE)
            if sanitized:  # Only add non-empty args
                sanitized_args.append(sanitized)

        return sanitized_args

    def is_supported_command(self, command_type: str) -> bool:
        """
        Check if a command type is supported.

        Args:
            command_type: The command type to check

        Returns:
            True if command is in allowed_commands, False otherwise
        """
        return command_type.lower() in self.allowed_commands
