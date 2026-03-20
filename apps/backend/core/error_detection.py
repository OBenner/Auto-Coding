"""
Error Detection and Introspection
==================================

Helper functions for extracting error codes from exceptions
and performing structured error analysis.
"""

from __future__ import annotations

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
