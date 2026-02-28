#!/usr/bin/env python3
"""
Error Pattern Matcher Module
==========================

Matches error messages and stack traces against known error patterns
to identify common issues and suggest fixes.

This module provides:
- Predefined error patterns for common programming errors
- Pattern matching based on error type and message content
- Category classification (syntax, import, type, etc.)
- Preliminary fix suggestions

The error pattern matcher results are used by:
- Fix Suggester: To provide targeted fix recommendations
- Debug Assistant: To categorize and explain errors
- QA Agent: To identify recurring error patterns

Usage:
    from error_pattern_matcher import match_error_pattern, get_common_patterns

    # Match a parsed stack trace against patterns
    from stack_trace_parser import parse_stack_trace

    parsed = parse_stack_trace(trace_string)
    pattern = match_error_pattern(parsed)

    if pattern:
        print(f"Matched pattern: {pattern['category']}")
        print(f"Suggestion: {pattern['suggestion']}")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

# Import stack trace types
from .stack_trace_parser import ParsedStackTrace

logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ErrorPattern:
    """
    Represents a known error pattern with matching rules and suggestions.

    Attributes:
        category: Error category (syntax, import, type, null_reference, etc.)
        name: Human-readable pattern name
        error_types: List of error types that match this pattern
        message_patterns: List of regex patterns to match in error messages
        description: Plain language description of the error
        suggestion: Suggested fix or debugging approach
        common_causes: List of common causes for this error
        severity: Error severity (error, warning, info)
    """

    category: str
    name: str
    error_types: list[str] = field(default_factory=list)
    message_patterns: list[str] = field(default_factory=list)
    description: str = ""
    suggestion: str = ""
    common_causes: list[str] = field(default_factory=list)
    severity: str = "error"

    def matches(self, error_type: str, error_message: str) -> bool:
        """
        Check if this pattern matches the given error.

        Args:
            error_type: Error type from stack trace
            error_message: Error message text

        Returns:
            True if pattern matches
        """
        # Check if error type matches
        if self.error_types:
            type_lower = error_type.lower()
            if any(et.lower() in type_lower for et in self.error_types):
                return True

        # Check if message matches any pattern
        if self.message_patterns:
            message_lower = error_message.lower()
            for pattern in self.message_patterns:
                try:
                    if re.search(pattern.lower(), message_lower):
                        return True
                except re.error:
                    # Invalid regex, skip this pattern
                    logger.warning(f"Invalid regex pattern: {pattern}")
                    continue

        return False


@dataclass
class PatternMatch:
    """
    Result of matching an error against known patterns.

    Attributes:
        pattern: The matched error pattern
        confidence: Confidence score (0.0 to 1.0)
        matched_details: Details about what matched (type, message, etc.)
        related_patterns: List of other patterns that might also apply
    """

    pattern: ErrorPattern
    confidence: float
    matched_details: dict[str, Any] = field(default_factory=dict)
    related_patterns: list[ErrorPattern] = field(default_factory=list)


# =============================================================================
# COMMON ERROR PATTERNS
# =============================================================================


def get_common_patterns() -> list[ErrorPattern]:
    """
    Get the list of common error patterns.

    Returns:
        List of ErrorPattern objects for known errors
    """
    return [
        # Import/Module Errors
        ErrorPattern(
            category="import_error",
            name="Module Not Found",
            error_types=["ModuleNotFoundError", "ImportError", "ImportError"],
            message_patterns=[
                r"no module named",
                r"cannot find module",
                r"module .* not found",
                r"unable to import",
            ],
            description=(
                "The code is trying to import a module or package that doesn't exist "
                "or isn't installed in the environment."
            ),
            suggestion=(
                "1. Check if the module is installed (pip install / npm install)\n"
                "2. Verify the import path is correct\n"
                "3. Check if the module name is spelled correctly\n"
                "4. Ensure the virtual environment is activated"
            ),
            common_causes=[
                "Missing dependency in requirements.txt or package.json",
                "Incorrect import path",
                "Virtual environment not activated",
                "Typo in module name",
            ],
            severity="error",
        ),
        # TypeError / Attribute Errors
        ErrorPattern(
            category="type_error",
            name="Type Mismatch",
            error_types=["TypeError", "AttributeError"],
            message_patterns=[
                r"unsupported operand type",
                r"must be .*, not",
                r"object has no attribute",
                r"'(NoneType|str|int|float|list|dict)' object has",
            ],
            description=(
                "The code is performing an operation on a value of the wrong type "
                "or accessing a property/attribute that doesn't exist."
            ),
            suggestion=(
                "1. Check the type of the variable causing the error\n"
                "2. Add type checking or validation before the operation\n"
                "3. Verify the object has the expected attributes\n"
                "4. Add type hints to catch these errors earlier"
            ),
            common_causes=[
                "Passing wrong type to a function",
                "Accessing undefined object property",
                "Missing null/None check",
                "Incorrect assumption about data type",
            ],
            severity="error",
        ),
        # None/Null Reference Errors
        ErrorPattern(
            category="null_reference",
            name="None/Null Reference",
            error_types=["TypeError", "AttributeError", "ReferenceError", "NoneType"],
            message_patterns=[
                r"NoneType.*object",
                r"None.*has no attribute",
                r"undefined is not",
                r"Cannot read properties of (undefined|null)",
                r"null reference",
            ],
            description=(
                "The code is trying to access a property or method on a None/null value. "
                "This usually means a variable wasn't properly initialized or a function "
                "returned None when an object was expected."
            ),
            suggestion=(
                "1. Add a check for None/null before accessing properties\n"
                "2. Ensure functions return valid values in all code paths\n"
                "3. Use optional chaining (?.) if available\n"
                "4. Provide default values for potentially missing data"
            ),
            common_causes=[
                "Function returns None without handling",
                "Missing else/finally branch",
                "Uninitialized variable",
                "API response missing expected field",
            ],
            severity="error",
        ),
        # KeyError/Index Errors
        ErrorPattern(
            category="lookup_error",
            name="Key or Index Not Found",
            error_types=["KeyError", "IndexError", "NotFoundError"],
            message_patterns=[
                r"key .* not found",
                r"list index out of range",
                r"list assignment index out of range",
                r"index .* out of bounds",
            ],
            description=(
                "The code is trying to access a dictionary key or list index that doesn't exist."
            ),
            suggestion=(
                "1. Check if the key/index exists before accessing\n"
                "2. Use .get() for dictionaries with a default value\n"
                "3. Validate list length before indexing\n"
                "4. Add error handling for missing keys"
            ),
            common_causes=[
                "Assuming key exists in dictionary",
                "Off-by-one error in list indexing",
                "Empty data structure",
                "Incorrect key name",
            ],
            severity="error",
        ),
        # Value Errors
        ErrorPattern(
            category="value_error",
            name="Invalid Value",
            error_types=["ValueError", "ValidationError"],
            message_patterns=[
                r"invalid literal",
                r"could not convert",
                r"validation error",
                r"invalid value",
            ],
            description=(
                "A function received an argument of the correct type but an inappropriate value."
            ),
            suggestion=(
                "1. Validate input values before passing to functions\n"
                "2. Add try/except around conversion operations\n"
                "3. Check value ranges and constraints\n"
                "4. Provide clear error messages for validation failures"
            ),
            common_causes=[
                "Invalid user input",
                "Empty string where value expected",
                "Negative value where positive required",
                "Value outside valid range",
            ],
            severity="error",
        ),
        # Syntax Errors
        ErrorPattern(
            category="syntax_error",
            name="Syntax Error",
            error_types=["SyntaxError", "IndentationError", "TabError"],
            message_patterns=[
                r"invalid syntax",
                r"unexpected EOF",
                r"unexpected indent",
                r"unindent does not match",
            ],
            description="The code contains invalid syntax that the parser cannot understand.",
            suggestion=(
                "1. Check for missing brackets, quotes, or parentheses\n"
                "2. Verify consistent indentation (spaces vs tabs)\n"
                "3. Check for missing colons after if/for/while/def\n"
                "4. Run a linter to catch syntax errors early"
            ),
            common_causes=[
                "Missing closing bracket/parenthesis",
                "Mismatched quotes",
                "Inconsistent indentation",
                "Invalid Python version syntax",
            ],
            severity="error",
        ),
        # Name Errors
        ErrorPattern(
            category="name_error",
            name="Name Not Defined",
            error_types=["NameError", "UnboundLocalError"],
            message_patterns=[
                r"name .* is not defined",
                r"local variable .* referenced before assignment",
                r".* is not defined",
            ],
            description="The code references a variable or function that doesn't exist.",
            suggestion=(
                "1. Check if the variable/func is defined before use\n"
                "2. Verify spelling of variable/function names\n"
                "3. Check import statements for missing imports\n"
                "4. Ensure proper scope for variables"
            ),
            common_causes=[
                "Typo in variable name",
                "Missing import statement",
                "Using variable before assignment",
                "Scope issue (local vs global)",
            ],
            severity="error",
        ),
        # Timeout Errors
        ErrorPattern(
            category="timeout",
            name="Operation Timeout",
            error_types=["TimeoutError", "ReadTimeout", "ConnectTimeout"],
            message_patterns=[
                r"timed out",
                r"timeout",
                r"deadline exceeded",
                r"operation took too long",
            ],
            description="An operation took longer than the allowed time limit.",
            suggestion=(
                "1. Increase timeout if operation is legitimately slow\n"
                "2. Optimize the slow operation\n"
                "3. Check for blocking operations or infinite loops\n"
                "4. Consider async alternatives for long-running tasks"
            ),
            common_causes=[
                "Slow network connection",
                "Large data processing",
                "Blocking I/O operation",
                "Infinite loop",
            ],
            severity="error",
        ),
        # Permission Errors
        ErrorPattern(
            category="permission_error",
            name="Permission Denied",
            error_types=["PermissionError", "AccessDenied", "Unauthorized"],
            message_patterns=[
                r"permission denied",
                r"access denied",
                r"unauthorized",
                r"insufficient permissions",
            ],
            description="The code lacks required permissions to perform an operation.",
            suggestion=(
                "1. Check file/directory permissions\n"
                "2. Run with appropriate user privileges\n"
                "3. Verify API credentials and tokens\n"
                "4. Check if resource is locked by another process"
            ),
            common_causes=[
                "Missing file read/write permissions",
                "Incorrect API credentials",
                "Resource locked by another process",
                "Attempting to write to read-only location",
            ],
            severity="error",
        ),
        # File/Path Errors
        ErrorPattern(
            category="file_error",
            name="File Not Found",
            error_types=["FileNotFoundError", "FileNotFoundError", "ENOENT"],
            message_patterns=[
                r"no such file",
                r"file not found",
                r"directory not found",
                r"cannot open",
            ],
            description="The code is trying to access a file or directory that doesn't exist.",
            suggestion=(
                "1. Check if the file path is correct\n"
                "2. Use absolute paths instead of relative paths\n"
                "3. Verify the file exists before accessing it\n"
                "4. Check for typos in file/directory names"
            ),
            common_causes=[
                "Incorrect file path",
                "File hasn't been created yet",
                "Wrong working directory",
                "Typo in filename",
            ],
            severity="error",
        ),
        # Network Errors
        ErrorPattern(
            category="network_error",
            name="Network Connection Error",
            error_types=["ConnectionError", "NetworkError", "HTTPError"],
            message_patterns=[
                r"connection refused",
                r"network unreachable",
                r"failed to establish connection",
                r"http error",
                r"502 bad gateway",
                r"503 service unavailable",
            ],
            description="Failed to establish or maintain a network connection.",
            suggestion=(
                "1. Check if the service/server is running\n"
                "2. Verify network connectivity\n"
                "3. Check firewall settings\n"
                "4. Add retry logic with exponential backoff"
            ),
            common_causes=[
                "Service is down or unreachable",
                "Network connectivity issue",
                "Incorrect URL/endpoint",
                "Firewall blocking connection",
            ],
            severity="error",
        ),
        # JSON/Serialization Errors
        ErrorPattern(
            category="serialization_error",
            name="JSON/Serialization Error",
            error_types=["JSONDecodeError", "SerializationError", "YAMLError"],
            message_patterns=[
                r"expecting.*json",
                r"invalid.*escape",
                r"unexpected character",
                r"not (valid|serializable)",
            ],
            description="Failed to parse or serialize JSON/data.",
            suggestion=(
                "1. Validate JSON format before parsing\n"
                "2. Handle encoding issues properly\n"
                "3. Check for trailing commas or missing quotes\n"
                "4. Use JSON validator tools for debugging"
            ),
            common_causes=[
                "Malformed JSON",
                "Encoding issue",
                "Non-serializable object (e.g., datetime)",
                "Trailing commas in JSON",
            ],
            severity="error",
        ),
        # Division by Zero
        ErrorPattern(
            category="math_error",
            name="Division by Zero",
            error_types=["ZeroDivisionError"],
            message_patterns=[
                r"division by zero",
                r"modulo by zero",
                r"float division by zero",
            ],
            description="Attempted to divide by zero, which is mathematically undefined.",
            suggestion=(
                "1. Check divisor is not zero before division\n"
                "2. Add error handling for division operations\n"
                "3. Use default values when division is not possible\n"
                "4. Consider using try/except for calculation blocks"
            ),
            common_causes=[
                "User input of zero",
                "Empty collection leading to zero denominator",
                "Missing validation",
                "Calculation error",
            ],
            severity="error",
        ),
    ]


# =============================================================================
# PATTERN MATCHING
# =============================================================================


def match_error_pattern(
    parsed_trace: ParsedStackTrace | None,
    patterns: list[ErrorPattern] | None = None,
) -> PatternMatch | None:
    """
    Match a parsed stack trace against known error patterns.

    Args:
        parsed_trace: Parsed stack trace from stack_trace_parser
        patterns: Optional list of patterns (uses common patterns if None)

    Returns:
        PatternMatch object with best match, or None if no match
    """
    if parsed_trace is None:
        return None

    # Use common patterns if not provided
    if patterns is None:
        patterns = get_common_patterns()

    error_type = parsed_trace.error_type
    error_message = parsed_trace.error_message

    best_match = None
    best_confidence = 0.0
    related_patterns = []

    # Score each pattern
    for pattern in patterns:
        if pattern.matches(error_type, error_message):
            # Calculate confidence score
            confidence = _calculate_confidence(pattern, error_type, error_message)

            if confidence > best_confidence:
                best_match = pattern
                best_confidence = confidence

            # Collect other potential matches
            if confidence > 0.5 and pattern is not best_match:
                related_patterns.append(pattern)

    if best_match:
        return PatternMatch(
            pattern=best_match,
            confidence=best_confidence,
            matched_details={
                "error_type": error_type,
                "error_message": error_message,
                "language": parsed_trace.language,
                "frame_count": len(parsed_trace.frames),
            },
            related_patterns=related_patterns,
        )

    return None


def _calculate_confidence(
    pattern: ErrorPattern,
    error_type: str,
    error_message: str,
) -> float:
    """
    Calculate confidence score for a pattern match.

    Args:
        pattern: Error pattern to check
        error_type: Error type from stack trace
        error_message: Error message text

    Returns:
        Confidence score between 0.0 and 1.0
    """
    confidence = 0.0

    # Check error type match (higher weight)
    if pattern.error_types:
        type_lower = error_type.lower()
        for et in pattern.error_types:
            if et.lower() == type_lower:
                confidence += 0.6
            elif et.lower() in type_lower:
                confidence += 0.4

    # Check message pattern matches
    if pattern.message_patterns:
        message_lower = error_message.lower()
        matches = 0
        for pat in pattern.message_patterns:
            try:
                if re.search(pat.lower(), message_lower):
                    matches += 1
            except re.error:
                continue

        # Score based on number of matching patterns
        if matches > 0:
            pattern_score = min(matches / len(pattern.message_patterns), 1.0)
            confidence += pattern_score * 0.4

    return min(confidence, 1.0)


def categorize_error(error_type: str, error_message: str) -> str:
    """
    Categorize an error by type and message.

    Args:
        error_type: Error type string
        error_message: Error message text

    Returns:
        Category string (import_error, type_error, null_reference, etc.)
    """
    # Try to match against patterns
    patterns = get_common_patterns()
    for pattern in patterns:
        if pattern.matches(error_type, error_message):
            return pattern.category

    # Fallback: simple categorization by error type
    type_lower = error_type.lower()

    if "import" in type_lower or "module" in type_lower:
        return "import_error"
    elif "type" in type_lower or "attribute" in type_lower:
        return "type_error"
    elif "syntax" in type_lower:
        return "syntax_error"
    elif "key" in type_lower or "index" in type_lower:
        return "lookup_error"
    elif "timeout" in type_lower:
        return "timeout"
    elif "permission" in type_lower or "access" in type_lower:
        return "permission_error"
    elif "file" in type_lower or "path" in type_lower:
        return "file_error"
    elif "connection" in type_lower or "network" in type_lower:
        return "network_error"
    else:
        return "unknown"


def get_pattern_by_category(category: str) -> ErrorPattern | None:
    """
    Get an error pattern by category name.

    Args:
        category: Pattern category (import_error, type_error, etc.)

    Returns:
        ErrorPattern object or None if not found
    """
    patterns = get_common_patterns()
    for pattern in patterns:
        if pattern.category == category:
            return pattern
    return None


def get_suggestion_for_error(
    error_type: str,
    error_message: str,
) -> str | None:
    """
    Get a fix suggestion for an error.

    This is a convenience function for quickly getting suggestions
    without dealing with full pattern matching.

    Args:
        error_type: Error type string
        error_message: Error message text

    Returns:
        Suggestion string or None if no match
    """
    # Create a minimal ParsedStackTrace for matching
    from .stack_trace_parser import ParsedStackTrace

    trace = ParsedStackTrace(
        error_type=error_type,
        error_message=error_message,
        language="unknown",
        frames=[],
        raw_trace="",
    )

    match = match_error_pattern(trace)
    if match:
        return match.pattern.suggestion

    return None
