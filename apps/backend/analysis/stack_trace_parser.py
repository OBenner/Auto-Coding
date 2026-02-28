"""
Stack Trace Parser
==================

Parses stack traces from various programming languages (Python, JavaScript, Rust, etc.)
to extract structured information including error type, file locations, and context.

Provides a unified interface for analyzing stack traces regardless of source language.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class StackFrame:
    """Represents a single frame in a stack trace."""

    file_path: str
    line_number: int | None
    function_name: str
    code_snippet: str | None = None

    def __str__(self) -> str:
        """String representation of the stack frame."""
        line_info = f":{self.line_number}" if self.line_number else ""
        return f"  at {self.function_name} ({self.file_path}{line_info})"


@dataclass
class ParsedStackTrace:
    """Structured representation of a parsed stack trace."""

    error_type: str
    error_message: str
    language: str
    frames: list[StackFrame]
    raw_trace: str

    def __str__(self) -> str:
        """String representation of the parsed trace."""
        return f"{self.error_type}: {self.error_message}\n" + "\n".join(
            str(frame) for frame in self.frames
        )


# =============================================================================
# Language-Specific Parsers
# =============================================================================


def parse_python_trace(trace: str) -> ParsedStackTrace | None:
    """
    Parse a Python stack trace.

    Args:
        trace: Raw stack trace string

    Returns:
        ParsedStackTrace or None if parsing fails
    """
    try:
        lines = trace.strip().split("\n")

        # Extract error type and message
        error_line = lines[-1] if lines else ""
        error_match = re.match(r"^(\w+(?:\[\w+\])?): (.+)$", error_line)

        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)
        else:
            error_type = "UnknownError"
            error_message = error_line

        frames: list[StackFrame] = []

        # Python frame pattern: "  File \"path\", line N, in function"
        frame_pattern = re.compile(r'\s+File "([^"]+)", line (\d+), in (\S+)')

        for line in lines:
            match = frame_pattern.match(line)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                function_name = match.group(3)
                frames.append(StackFrame(file_path, line_number, function_name))

        return ParsedStackTrace(
            error_type=error_type,
            error_message=error_message,
            language="python",
            frames=frames,
            raw_trace=trace,
        )

    except Exception as e:
        logger.warning(f"Failed to parse Python trace: {e}")
        return None


def parse_javascript_trace(trace: str) -> ParsedStackTrace | None:
    """
    Parse a JavaScript/Node.js stack trace.

    Args:
        trace: Raw stack trace string

    Returns:
        ParsedStackTrace or None if parsing fails
    """
    try:
        lines = trace.strip().split("\n")

        # Extract error type and message (first line usually)
        first_line = lines[0] if lines else ""

        # Common patterns: "TypeError: message", "Error: message", "ReferenceError: message"
        error_match = re.match(r"^(\w+Error|Error): (.+)$", first_line)

        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)
        else:
            # Fallback: try to find the error type somewhere
            if ":" in first_line:
                parts = first_line.split(":", 1)
                error_type = parts[0].strip()
                error_message = parts[1].strip()
            else:
                error_type = "Error"
                error_message = first_line

        frames: list[StackFrame] = []

        # JavaScript frame patterns:
        # "    at functionName (file:line:col)"
        # "    at file:line:col"
        # "    at functionName (https://...:line:col)"
        frame_patterns = [
            re.compile(
                r"\s+at (\S+) \(([^:]+):(\d+):\d+\)"
            ),  # function (file:line:col)
            re.compile(r"\s+at (\S+):(\d+):\d+"),  # file:line:col (anonymous)
            re.compile(r"\s+at ([^(]+) \(([^:]+):(\d+)\)"),  # function (file:line)
        ]

        for line in lines[1:]:
            for pattern in frame_patterns:
                match = pattern.match(line)
                if match:
                    groups = match.groups()

                    if len(groups) == 3:
                        # Pattern with function name
                        function_name = groups[0]
                        file_path = groups[1]
                        line_number = int(groups[2])
                    else:
                        # Pattern without function name
                        file_path = groups[0]
                        line_number = int(groups[1])
                        function_name = "<anonymous>"

                    frames.append(StackFrame(file_path, line_number, function_name))
                    break

        return ParsedStackTrace(
            error_type=error_type,
            error_message=error_message,
            language="javascript",
            frames=frames,
            raw_trace=trace,
        )

    except Exception as e:
        logger.warning(f"Failed to parse JavaScript trace: {e}")
        return None


def parse_rust_trace(trace: str) -> ParsedStackTrace | None:
    """
    Parse a Rust stack trace.

    Args:
        trace: Raw stack trace string

    Returns:
        ParsedStackTrace or None if parsing fails
    """
    try:
        lines = trace.strip().split("\n")

        # Find error message (usually starts with "Error: " or "panicked at")
        error_type = "Panic"
        error_message = ""

        for line in lines:
            if line.startswith("Error: "):
                error_type = "Error"
                error_message = line[7:].strip()
                break
            elif line.startswith("panicked at "):
                error_type = "Panic"
                # Extract message from: panicked at 'message', file:line:col
                match = re.search(r"panicked at '([^']+)'", line)
                if match:
                    error_message = match.group(1)
                break

        frames: list[StackFrame] = []

        # Rust frame patterns:
        # "   0: function_name at file:line:col"
        # "    at /path/to/file:line:col"
        frame_pattern = re.compile(r"\s+\d+:\s+(\S+)\s+at\s+([^:]+):(\d+):\d+")

        for line in lines:
            match = frame_pattern.match(line)
            if match:
                function_name = match.group(1)
                file_path = match.group(2)
                line_number = int(match.group(3))
                frames.append(StackFrame(file_path, line_number, function_name))

        return ParsedStackTrace(
            error_type=error_type,
            error_message=error_message,
            language="rust",
            frames=frames,
            raw_trace=trace,
        )

    except Exception as e:
        logger.warning(f"Failed to parse Rust trace: {e}")
        return None


def parse_generic_trace(trace: str) -> ParsedStackTrace | None:
    """
    Parse a generic/unknown stack trace using common patterns.

    Args:
        trace: Raw stack trace string

    Returns:
        ParsedStackTrace or None if parsing fails
    """
    try:
        lines = trace.strip().split("\n")

        # Try to extract error type from first line
        first_line = lines[0] if lines else ""
        error_type = "Error"
        error_message = first_line

        if ":" in first_line:
            parts = first_line.split(":", 1)
            error_type = parts[0].strip()
            error_message = parts[1].strip()

        # Try to extract frames with file paths and line numbers
        frames: list[StackFrame] = []

        # Generic patterns that match most stack traces
        # Look for lines containing "file:line" or "file(line)"
        frame_patterns = [
            re.compile(r"\(([^:]+):(\d+)\)"),  # (file:line)
            re.compile(r"at\s+([^:]+):(\d+)"),  # at file:line
            re.compile(r"([^:\s]+\.py):(\d+)"),  # file.py:line
            re.compile(r"([^:\s]+\.js):(\d+)"),  # file.js:line
            re.compile(r"([^:\s]+\.rs):(\d+)"),  # file.rs:line
        ]

        for line in lines[1:]:
            for pattern in frame_patterns:
                match = pattern.search(line)
                if match:
                    file_path = match.group(1)
                    line_number = int(match.group(2))
                    # Try to extract function name
                    function_match = re.search(r"at\s+(\w+)", line)
                    function_name = (
                        function_match.group(1) if function_match else "<unknown>"
                    )
                    frames.append(StackFrame(file_path, line_number, function_name))
                    break

        return ParsedStackTrace(
            error_type=error_type,
            error_message=error_message,
            language="unknown",
            frames=frames,
            raw_trace=trace,
        )

    except Exception as e:
        logger.warning(f"Failed to parse generic trace: {e}")
        return None


# =============================================================================
# Main Parser Interface
# =============================================================================


def parse_stack_trace(
    trace: str, language: str | None = None
) -> ParsedStackTrace | None:
    """
    Parse a stack trace and extract structured information.

    Automatically detects the language if not specified, or uses the provided language hint.

    Args:
        trace: Raw stack trace string
        language: Optional language hint ("python", "javascript", "rust", etc.)

    Returns:
        ParsedStackTrace with extracted information, or None if parsing fails
    """
    if not trace or not trace.strip():
        logger.warning("Cannot parse empty stack trace")
        return None

    # Normalize the trace
    trace = trace.strip()

    # Use language-specific parser if provided
    if language:
        language_lower = language.lower()
        parser_map = {
            "python": parse_python_trace,
            "javascript": parse_javascript_trace,
            "js": parse_javascript_trace,
            "node": parse_javascript_trace,
            "rust": parse_rust_trace,
        }

        parser = parser_map.get(language_lower)
        if parser:
            result = parser(trace)
            if result:
                return result
            logger.warning(
                f"Failed to parse as {language}, falling back to auto-detection"
            )

    # Auto-detect language based on trace patterns
    # Python patterns: "File \".py\", line", "Traceback (most recent call last)"
    if "Traceback" in trace or re.search(r'File\s+"[^"]+\.py"', trace):
        result = parse_python_trace(trace)
        if result:
            return result

    # JavaScript patterns: "at function (file:line:col)", ".js:"
    if re.search(r"\bat\s+\S+\s+\([^:]+:\d+:\d+\)", trace) or re.search(
        r"\.js:\d+:\d+", trace
    ):
        result = parse_javascript_trace(trace)
        if result:
            return result

    # Rust patterns: "panicked at", "rs:"
    if "panicked at" in trace or re.search(r"\.rs:\d+:\d+", trace):
        result = parse_rust_trace(trace)
        if result:
            return result

    # Fall back to generic parser
    return parse_generic_trace(trace)


def extract_error_type(trace: str) -> str:
    """
    Extract just the error type from a stack trace.

    This is a lightweight alternative to full parsing when you only need the error type.

    Args:
        trace: Raw stack trace string

    Returns:
        Error type string (e.g., "TypeError", "ValueError", "Panic")
    """
    parsed = parse_stack_trace(trace)
    if parsed:
        return parsed.error_type

    # Fallback: try to extract error type from first line
    first_line = trace.strip().split("\n")[0] if trace else ""
    error_match = re.match(r"^(\w+(?:\[\w+\])?|[\w]+Error):", first_line)

    if error_match:
        return error_match.group(1)

    return "UnknownError"


def get_failing_file(parsed_trace: ParsedStackTrace | None) -> str | None:
    """
    Get the file path where the error originated (deepest frame).

    Args:
        parsed_trace: Parsed stack trace

    Returns:
        File path or None if no frames available
    """
    if not parsed_trace or not parsed_trace.frames:
        return None

    # Return the last frame (where the error occurred)
    return parsed_trace.frames[-1].file_path


def get_failing_line(parsed_trace: ParsedStackTrace | None) -> int | None:
    """
    Get the line number where the error originated (deepest frame).

    Args:
        parsed_trace: Parsed stack trace

    Returns:
        Line number or None if no frames available
    """
    if not parsed_trace or not parsed_trace.frames:
        return None

    # Return the last frame (where the error occurred)
    return parsed_trace.frames[-1].line_number


def summarize_trace(trace: str) -> dict[str, Any]:
    """
    Summarize a stack trace into key information.

    Args:
        trace: Raw stack trace string

    Returns:
        Dict with summary:
        {
            "error_type": str,
            "error_message": str,
            "language": str,
            "failing_file": str | None,
            "failing_line": int | None,
            "frame_count": int,
        }
    """
    parsed = parse_stack_trace(trace)

    if not parsed:
        return {
            "error_type": "UnknownError",
            "error_message": trace[:100] if trace else "",
            "language": "unknown",
            "failing_file": None,
            "failing_line": None,
            "frame_count": 0,
        }

    return {
        "error_type": parsed.error_type,
        "error_message": parsed.error_message,
        "language": parsed.language,
        "failing_file": get_failing_file(parsed),
        "failing_line": get_failing_line(parsed),
        "frame_count": len(parsed.frames),
    }
