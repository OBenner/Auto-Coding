"""
Error Classifier (DEPRECATED)
=============================

.. deprecated::
    **String-based error classification is deprecated.** Use typed error classes
    from ``core.typed_errors`` combined with error codes from ``core.error_codes``
    instead. The pattern-based classification system has been removed in favor of
    the typed error system.

This module now only provides typed error classification and stuck loop detection.
The string-based pattern matching has been completely removed.

**Migration Guide:**

New pattern (typed errors with error codes)::

    from core.typed_errors import AuthError, RateLimitError
    from core.error_detection import get_error_code
    from core.error_codes import ErrorCode

    # Option 1: Direct isinstance checks (fastest, most type-safe)
    if isinstance(exc, AuthError):
        # exc.retry_hint, exc.user_message, exc.error_code available
        pass
    elif isinstance(exc, RateLimitError):
        # exc.retry_after_seconds, exc.user_message available
        pass

    # Option 2: Using error_code for structured handling
    error_code = get_error_code(exc)
    if error_code == ErrorCode.AUTH_INVALID:
        # Handle invalid auth
        pass
    elif error_code == ErrorCode.RATE_LIMITED:
        # Handle rate limit (retry_after available via error_code.metadata)
        pass

**Benefits of the new system:**
- Type-safe via ``isinstance()`` checks - no regex false positives
- Rich metadata: ``retry_hint``, ``user_message``, ``retry_after_seconds``
- Structured error codes (``ErrorCode`` enum) for programmatic handling
- Better IDE support (autocomplete, type hints)
- Consistent with Python best practices (exceptions over patterns)
- Easier to test and maintain

**Migration timeline:**
- ``ErrorClassifier`` class - Deprecated, use ``isinstance()`` checks instead
- ``SDKErrorCategory`` enum - Deprecated, use ``ErrorCode`` enum instead
- ``ClassifiedError`` dataclass - Deprecated, use ``TypedError`` attributes instead

**For stuck loop detection:**
The ``check_stuck_loop()`` functionality is not deprecated and will be moved
to a separate utility module in a future update.
"""

import re
from collections import deque
from dataclasses import dataclass
from enum import Enum

from core.error_codes import ErrorCode
from core.error_detection import get_error_code


class SDKErrorCategory(Enum):
    """Categories of errors encountered during SDK interactions."""

    AUTH_INVALID = "auth_invalid"
    AUTH_EXPIRED = "auth_expired"
    BILLING_EXHAUSTED = "billing_exhausted"
    RATE_LIMITED = "rate_limited"
    OVERLOADED = "overloaded"
    NETWORK = "network"
    CONTEXT_OVERFLOW = "context_overflow"
    STUCK_LOOP = "stuck_loop"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedError:
    """A classified error with actionable metadata."""

    category: SDKErrorCategory
    message: str
    is_fatal: bool = False
    is_retryable: bool = False
    retry_after_seconds: float = 0.0
    action_hint: str = ""


# Default retry hints per category (only for typed errors)
_CATEGORY_DEFAULTS: dict[SDKErrorCategory, dict] = {
    SDKErrorCategory.AUTH_INVALID: {
        "is_fatal": True,
        "is_retryable": False,
        "action_hint": "Check your API key or run `claude /login` to re-authenticate.",
    },
    SDKErrorCategory.AUTH_EXPIRED: {
        "is_fatal": True,
        "is_retryable": False,
        "action_hint": (
            "Your OAuth token has expired. "
            "Please obtain a new token by running `claude /login`."
        ),
    },
    SDKErrorCategory.BILLING_EXHAUSTED: {
        "is_fatal": True,
        "is_retryable": False,
        "action_hint": "Check your billing status and add credits.",
    },
    SDKErrorCategory.RATE_LIMITED: {
        "is_fatal": False,
        "is_retryable": True,
        "retry_after_seconds": 60.0,
        "action_hint": "Rate limited. Will retry after backoff.",
    },
    SDKErrorCategory.OVERLOADED: {
        "is_fatal": False,
        "is_retryable": True,
        "retry_after_seconds": 30.0,
        "action_hint": "API is overloaded. Will retry shortly.",
    },
    SDKErrorCategory.NETWORK: {
        "is_fatal": False,
        "is_retryable": True,
        "retry_after_seconds": 10.0,
        "action_hint": "Network error. Check connectivity.",
    },
    SDKErrorCategory.CONTEXT_OVERFLOW: {
        "is_fatal": True,
        "is_retryable": False,
        "action_hint": "Context window exceeded. Reduce input size or split the task.",
    },
    SDKErrorCategory.STUCK_LOOP: {
        "is_fatal": True,
        "is_retryable": False,
        "action_hint": "Agent appears stuck in a loop. Session will be terminated.",
    },
    SDKErrorCategory.UNKNOWN: {
        "is_fatal": False,
        "is_retryable": False,
        "action_hint": "",
    },
}

# Mapping from ErrorCode to SDKErrorCategory
_ERROR_CODE_TO_CATEGORY: dict[ErrorCode, SDKErrorCategory] = {
    ErrorCode.AUTH_INVALID: SDKErrorCategory.AUTH_INVALID,
    ErrorCode.AUTH_EXPIRED: SDKErrorCategory.AUTH_EXPIRED,
    ErrorCode.AUTH_MISSING: SDKErrorCategory.AUTH_INVALID,
    ErrorCode.BILLING_EXHAUSTED: SDKErrorCategory.BILLING_EXHAUSTED,
    ErrorCode.QUOTA_EXCEEDED: SDKErrorCategory.BILLING_EXHAUSTED,
    ErrorCode.RATE_LIMITED: SDKErrorCategory.RATE_LIMITED,
    ErrorCode.RATE_LIMIT_HARD: SDKErrorCategory.RATE_LIMITED,
    ErrorCode.NETWORK: SDKErrorCategory.NETWORK,
    ErrorCode.NETWORK_UNREACHABLE: SDKErrorCategory.NETWORK,
    ErrorCode.NETWORK_TIMEOUT: SDKErrorCategory.NETWORK,
    ErrorCode.OVERLOADED: SDKErrorCategory.OVERLOADED,
    ErrorCode.SERVICE_UNAVAILABLE: SDKErrorCategory.OVERLOADED,
    ErrorCode.INTERNAL_ERROR: SDKErrorCategory.NETWORK,
    ErrorCode.BAD_GATEWAY: SDKErrorCategory.NETWORK,
    ErrorCode.CONTEXT_OVERFLOW: SDKErrorCategory.CONTEXT_OVERFLOW,
    ErrorCode.PROMPT_TOO_LONG: SDKErrorCategory.CONTEXT_OVERFLOW,
    ErrorCode.TOKEN_LIMIT_EXCEEDED: SDKErrorCategory.CONTEXT_OVERFLOW,
    ErrorCode.STUCK_LOOP: SDKErrorCategory.STUCK_LOOP,
    ErrorCode.UNKNOWN: SDKErrorCategory.UNKNOWN,
}


# String pattern matching removed - only typed errors are supported


def _build_classified(category: SDKErrorCategory, message: str) -> ClassifiedError:
    defaults = _CATEGORY_DEFAULTS[category]
    return ClassifiedError(
        category=category,
        message=message,
        is_fatal=defaults["is_fatal"],
        is_retryable=defaults["is_retryable"],
        retry_after_seconds=defaults.get("retry_after_seconds", 0.0),
        action_hint=defaults["action_hint"],
    )


class ErrorClassifier:
    """Classifies SDK exceptions and response text into actionable categories."""

    def __init__(self, stuck_loop_threshold: int = 3) -> None:
        self._stuck_loop_threshold = stuck_loop_threshold
        self._recent_responses: deque[str] = deque(maxlen=stuck_loop_threshold + 1)

    def classify_exception(self, exc: Exception) -> ClassifiedError:
        """Classify a Python exception into an error category.

        First checks if the exception is a typed error (TypedError) with an error_code.
        For backward compatibility, falls back to minimal string-based matching for
        common error patterns that don't have typed equivalents yet.

        Args:
            exc: The exception to classify

        Returns:
            A ClassifiedError object with category and metadata
        """
        # First, check if this is a typed error with an error_code attribute
        error_code = get_error_code(exc)
        if error_code is not None:
            # Map ErrorCode to SDKErrorCategory
            category = _ERROR_CODE_TO_CATEGORY.get(
                error_code, SDKErrorCategory.UNKNOWN
            )
            return _build_classified(
                category,
                f"{type(exc).__name__}: {exc}",
            )

        # Fallback: minimal string-based matching for common patterns
        # This maintains backward compatibility while being much safer than
        # the previous extensive pattern matching system
        text = str(exc).lower()

        # Common HTTP status codes and patterns
        if "401" in text or "unauthorized" in text:
            return _build_classified(
                SDKErrorCategory.AUTH_INVALID,
                f"authentication error: {text[:100]}",
            )
        elif "402" in text or "payment" in text:
            return _build_classified(
                SDKErrorCategory.BILLING_EXHAUSTED,
                f"billing error: {text[:100]}",
            )
        elif "429" in text or "rate limit" in text or "too many requests" in text:
            return _build_classified(
                SDKErrorCategory.RATE_LIMITED,
                f"rate limited: {text[:100]}",
            )
        elif "503" in text or "overloaded" in text:
            return _build_classified(
                SDKErrorCategory.OVERLOADED,
                f"API overloaded: {text[:100]}",
            )
        elif "invalid_api_key" in text:
            return _build_classified(
                SDKErrorCategory.AUTH_INVALID,
                f"authentication error: {text[:100]}",
            )
        elif "oauth" in text and "expired" in text:
            return _build_classified(
                SDKErrorCategory.AUTH_EXPIRED,
                f"authentication error: {text[:100]}",
            )
        elif re.search(r"context\s*(window|length)\s*(exceeded|overflow)", text) or \
             "maximum tokens exceeded" in text or "token limit" in text:
            return _build_classified(
                SDKErrorCategory.CONTEXT_OVERFLOW,
                f"context overflow: {text[:100]}",
            )

        # For non-typed and non-matching errors, classify as unknown
        return _build_classified(
            SDKErrorCategory.UNKNOWN,
            f"{type(exc).__name__}: {exc}",
        )

    def classify_response(self, text: str) -> ClassifiedError | None:
        """Classify agent response text. Returns None if no error detected."""
        if not text:
            return None

        # Check stuck loop first
        if self.check_stuck_loop(text):
            return _build_classified(
                SDKErrorCategory.STUCK_LOOP,
                "Agent produced identical responses — likely stuck in a loop.",
            )

        # Check for JSON error responses
        if 'error' in text.lower():
            # Simple JSON error detection
            if 'authentication_error' in text.lower() or 'invalid_api_key' in text.lower():
                return _build_classified(
                    SDKErrorCategory.AUTH_INVALID,
                    f"authentication error: {text[:100]}",
                )

        return None

    def check_stuck_loop(self, text: str) -> bool:
        """Check if the agent is stuck producing identical responses."""
        # Normalise whitespace for comparison
        normalised = " ".join(text.split())[:200]
        self._recent_responses.append(normalised)

        if len(self._recent_responses) < self._stuck_loop_threshold:
            return False

        # Check if the last N responses are identical
        recent = list(self._recent_responses)[-self._stuck_loop_threshold :]
        return len(set(recent)) == 1

    def reset(self) -> None:
        """Reset internal state (e.g. between sessions)."""
        self._recent_responses.clear()

    # -- private helpers ----------------------------------------------------
    # String-based text classification removed - only typed errors and stuck loop detection remain

    