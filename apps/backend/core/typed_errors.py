"""
Typed Errors
============

Exception classes with typed error codes for structured error handling.
"""


import json
from typing import Any

from core.error_codes import ErrorCode


class TypedError(Exception):
    """Base exception class with typed error code field.

    Provides structured error handling with error codes that can be
    programmatically inspected and matched.

    Args:
        error_code: ErrorCode enum value identifying the error type
        message: Human-readable error message

    Example:
        >>> raise TypedError(ErrorCode.AUTH_INVALID, "Invalid API key")
    """

    def __init__(self, error_code: ErrorCode, message: str):
        """Initialize TypedError with error code and message."""
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation including error code."""
        return f"[{self.error_code.name}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization.

        Returns:
            Dictionary with error_code and message keys
        """
        return {
            "error_code": self.error_code.name,
            "message": self.message
        }

    def to_json(self) -> str:
        """Convert error to JSON string.

        Returns:
            JSON string representation of the error
        """
        return json.dumps(self.to_dict())


class AuthError(TypedError):
    """Raised when authentication fails or credentials are invalid."""

    def __init__(self, message: str = "Authentication failed"):
        """Initialize AuthError with default error code."""
        super().__init__(ErrorCode.AUTH_INVALID, message)


class RateLimitError(TypedError):
    """Raised when API rate limits are exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        """Initialize RateLimitError with default error code."""
        super().__init__(ErrorCode.RATE_LIMIT_ERROR, message)


class ValidationError(TypedError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed"):
        """Initialize ValidationError with default error code."""
        super().__init__(ErrorCode.INVALID_REQUEST, message)


class NotFoundError(TypedError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        """Initialize NotFoundError with default error code."""
        super().__init__(ErrorCode.INVALID_REQUEST, message)


class PermissionError(TypedError):
    """Raised when user lacks permission to perform an action."""

    def __init__(self, message: str = "Permission denied"):
        """Initialize PermissionError with default error code."""
        super().__init__(ErrorCode.AUTH_INVALID, message)


class ConfigurationError(TypedError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str = "Configuration error"):
        """Initialize ConfigurationError with default error code."""
        super().__init__(ErrorCode.INVALID_REQUEST, message)


class NetworkError(TypedError):
    """Raised when network operations fail."""

    def __init__(self, message: str = "Network error"):
        """Initialize NetworkError with default error code."""
        super().__init__(ErrorCode.NETWORK_ERROR, message)


class TimeoutError(TypedError):
    """Raised when an operation times out."""

    def __init__(self, message: str = "Operation timed out"):
        """Initialize TimeoutError with default error code."""
        super().__init__(ErrorCode.TIMEOUT, message)
