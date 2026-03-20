"""
Error Detection and Introspection
==================================

Helper functions for extracting error codes from exceptions
and performing structured error analysis.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.error_codes import ErrorCode


def get_error_code(error: Exception) -> ErrorCode | None:
    """
    Extract error code from a typed exception.

    This function performs introspection on exceptions to determine if they
    are typed errors (instances of TypedError) and extracts the associated
    ErrorCode enum value. For non-typed exceptions, it returns None.

    This enables structured error handling and pattern matching based on
    error types rather than string-based error message parsing.

    Args:
        error: The exception to inspect

    Returns:
        ErrorCode enum value if the exception is a TypedError, None otherwise

    Example:
        >>> from core.typed_errors import AuthError
        >>> get_error_code(AuthError())
        ErrorCode.AUTH_INVALID

        >>> get_error_code(Exception("generic error"))
        None
    """
    # Check if exception has an error_code attribute (TypedError instances)
    if hasattr(error, "error_code"):
        from core.error_codes import ErrorCode

        error_code = getattr(error, "error_code")
        # Validate that it's actually an ErrorCode enum value
        if isinstance(error_code, ErrorCode):
            return error_code

    return None


# --- Pattern matching for SDK error classification -------------------------

_AUTH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"invalid[_\s]?api[_\s]?key", re.IGNORECASE),
    re.compile(r"invalid[_\s]?credentials", re.IGNORECASE),
    re.compile(r"invalid[_\s]?token", re.IGNORECASE),
    re.compile(r"authentication[_\s]?(error|failed|failure)", re.IGNORECASE),
    re.compile(r"unauthorized", re.IGNORECASE),
    re.compile(r"\b401\b"),
    re.compile(r"not\s+(yet\s+)?authenticated", re.IGNORECASE),
    re.compile(r"access\s+denied", re.IGNORECASE),
    re.compile(r"permission\s+denied", re.IGNORECASE),
]

_AUTH_EXPIRED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"oauth\s*token\s*(is\s*)?(expired|invalid)", re.IGNORECASE),
    re.compile(r"oauth\s*token\s+has\s+expired", re.IGNORECASE),
    re.compile(r"session\s*(expired|invalid)", re.IGNORECASE),
    re.compile(r"credentials\s*(are\s*)?(expired)", re.IGNORECASE),
    re.compile(r"token\s*(has\s*)?expired", re.IGNORECASE),
]

_BILLING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b402\b"),
    re.compile(r"payment\s+required", re.IGNORECASE),
    re.compile(r"billing\s+(issue|error|required|problem)", re.IGNORECASE),
    re.compile(r"credit\s+card\s+(declined|expired|invalid|limit)", re.IGNORECASE),
    re.compile(r"quota\s+exceeded", re.IGNORECASE),
]

_RATE_LIMIT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b429\b"),
    re.compile(r"rate[_\s]?limit", re.IGNORECASE),
    re.compile(r"too\s+many\s+requests", re.IGNORECASE),
]

_OVERLOADED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b503\b"),
    re.compile(r"\b529\b"),
    re.compile(r"overloaded", re.IGNORECASE),
    re.compile(r"temporarily\s+unavailable", re.IGNORECASE),
]

_NETWORK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"connection\s*(refused|reset|error|timed?\s*out)", re.IGNORECASE),
    re.compile(r"timeout", re.IGNORECASE),
    re.compile(r"network\s*(error|unreachable)", re.IGNORECASE),
    re.compile(r"\b502\b"),
    re.compile(r"\b500\b"),
]

_CONTEXT_OVERFLOW_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"context\s*(window|length)\s*(exceeded|overflow|too\s+long)", re.I),
    re.compile(r"max(imum)?\s*tokens?\s*exceeded", re.IGNORECASE),
    re.compile(r"prompt\s+is\s+too\s+long", re.IGNORECASE),
    re.compile(r"token\s+limit", re.IGNORECASE),
]


def _classify_error_message(error_message: str) -> ErrorCode:
    """
    Classify an error message into an ErrorCode.

    Uses pattern matching to determine the appropriate error code
    based on the error message content.

    Args:
        error_message: The error message to classify

    Returns:
        ErrorCode enum value matching the error pattern

    Note:
        Returns ErrorCode.UNKNOWN if no pattern matches
    """
    from core.error_codes import ErrorCode

    error_lower = error_message.lower()

    # Try each pattern category in order of specificity
    pattern_groups = [
        (_AUTH_EXPIRED_PATTERNS, ErrorCode.AUTH_EXPIRED),
        (_AUTH_PATTERNS, ErrorCode.AUTH_INVALID),
        (_BILLING_PATTERNS, ErrorCode.BILLING_EXHAUSTED),
        (_RATE_LIMIT_PATTERNS, ErrorCode.RATE_LIMITED),
        (_OVERLOADED_PATTERNS, ErrorCode.OVERLOADED),
        (_NETWORK_PATTERNS, ErrorCode.NETWORK),
        (_CONTEXT_OVERFLOW_PATTERNS, ErrorCode.CONTEXT_OVERFLOW),
    ]

    for patterns, error_code in pattern_groups:
        for pattern in patterns:
            if pattern.search(error_message):
                return error_code

    return ErrorCode.UNKNOWN


def wrap_sdk_error(error: Exception) -> Exception:
    """
    Wrap a raw SDK exception in a TypedError.

    This function converts raw SDK exceptions (from the Claude Agent SDK,
    Anthropic API, or other sources) into structured TypedError instances
    with appropriate error codes. This enables consistent error handling
    and programmatic error classification throughout the system.

    If the exception is already a TypedError instance, it is returned
    unchanged. Otherwise, the error message is analyzed to determine
    the appropriate error category and a new TypedError is created.

    Args:
        error: The exception to wrap

    Returns:
        A TypedError instance with the appropriate error code.
        Returns the original error if it's already a TypedError.

    Example:
        >>> try:
        ...     # Some SDK call that raises an exception
        ...     pass
        ... except Exception as e:
        ...     typed_error = wrap_sdk_error(e)
        ...     if hasattr(typed_error, 'error_code'):
        ...         print(f"Error code: {typed_error.error_code}")
        ...
        Error code: ErrorCode.AUTH_INVALID

    Note:
        This function uses pattern matching on error messages to classify
        errors. For best results, ensure error messages are descriptive
        and include relevant keywords (e.g., "authentication failed",
        "rate limit exceeded", etc.).
    """
    from core.error_codes import ErrorCode
    from core.typed_errors import (
        AuthError,
        NetworkError,
        TypedError,
        TimeoutError,
    )

    # If it's already a TypedError, return as-is
    if get_error_code(error) is not None:
        return error

    # Extract error message
    error_message = str(error)

    # Classify the error
    error_code = _classify_error_message(error_message)

    # Map ErrorCode to appropriate TypedError subclass
    error_class_mapping: dict[ErrorCode, type[TypedError]] = {
        ErrorCode.AUTH_INVALID: AuthError,
        ErrorCode.AUTH_EXPIRED: AuthError,
        ErrorCode.AUTH_MISSING: AuthError,
        ErrorCode.BILLING_EXHAUSTED: TypedError,
        ErrorCode.QUOTA_EXCEEDED: TypedError,
        ErrorCode.RATE_LIMITED: TypedError,
        ErrorCode.RATE_LIMIT_HARD: TypedError,
        ErrorCode.NETWORK: NetworkError,
        ErrorCode.NETWORK_UNREACHABLE: NetworkError,
        ErrorCode.NETWORK_TIMEOUT: TimeoutError,
        ErrorCode.OVERLOADED: TypedError,
        ErrorCode.SERVICE_UNAVAILABLE: TypedError,
        ErrorCode.INTERNAL_ERROR: TypedError,
        ErrorCode.BAD_GATEWAY: NetworkError,
        ErrorCode.CONTEXT_OVERFLOW: TypedError,
        ErrorCode.PROMPT_TOO_LONG: TypedError,
        ErrorCode.TOKEN_LIMIT_EXCEEDED: TypedError,
        ErrorCode.UNKNOWN: TypedError,
    }

    # Get the appropriate error class, default to TypedError
    error_class = error_class_mapping.get(error_code, TypedError)

    # Create and return the typed error
    # Specific TypedError subclasses (AuthError, NetworkError, etc.) only take message
    # The base TypedError class takes both error_code and message
    if error_class is TypedError:
        return error_class(error_code, error_message)
    else:
        # Subclasses have their own error_code defaults, just pass message
        return error_class(error_message)
