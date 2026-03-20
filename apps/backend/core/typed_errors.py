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
