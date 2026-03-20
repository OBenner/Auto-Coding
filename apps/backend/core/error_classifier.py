"""
Error Classifier (DEPRECATED)
=============================

.. deprecated::
    **String-based error classification is deprecated.** Use typed error classes
    from ``core.typed_errors`` combined with error codes from ``core.error_codes``
    instead. The pattern-based classification system will be removed in a future
    version.

This module provides legacy string-based error classification using regex patterns.
It has been superseded by the typed error system (``core.typed_errors``) which
provides type-safe error detection via ``isinstance()`` checks.

**Migration Guide:**

Old pattern (string-based classification)::

    from core.error_classifier import ErrorClassifier, SDKErrorCategory

    classifier = ErrorClassifier()
    error = classifier.classify_exception(exc)

    if error.category == SDKErrorCategory.AUTH_INVALID:
        # Handle auth error
        pass
    elif error.category == SDKErrorCategory.RATE_LIMITED:
        # Handle rate limit
        pass

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


# --- Pattern groups --------------------------------------------------------

_AUTH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"invalid[_\s]?api[_\s]?key", re.IGNORECASE),
    re.compile(r"invalid[_\s]?credentials", re.IGNORECASE),
    re.compile(r"invalid[_\s]?token", re.IGNORECASE),
    re.compile(r"authentication[_\s]?(error|failed|failure)", re.IGNORECASE),
    re.compile(r"unauthorized", re.IGNORECASE),
    re.compile(r"\b401\b"),
    re.compile(r"not\s+(yet\s+)?authenticated", re.IGNORECASE),
    re.compile(r"login\s+(is\s+)?required", re.IGNORECASE),
    re.compile(r"authentication\s+(is\s+)?required", re.IGNORECASE),
    re.compile(r"please\s+(log\s*in|authenticate)", re.IGNORECASE),
    re.compile(r"access\s+denied", re.IGNORECASE),
    re.compile(r"permission\s+denied", re.IGNORECASE),
    re.compile(r"API\s*Error:\s*401", re.IGNORECASE),
    re.compile(
        r"""["']?type["']?\s*:\s*["']?authentication_error["']?""", re.IGNORECASE
    ),
]

_AUTH_EXPIRED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"oauth\s*token\s*(is\s*)?(expired|invalid)", re.IGNORECASE),
    re.compile(r"oauth\s*token\s+has\s+expired", re.IGNORECASE),
    re.compile(r"session\s*(expired|invalid)", re.IGNORECASE),
    re.compile(r"credentials\s*(are\s*)?(expired)", re.IGNORECASE),
    re.compile(r"please\s*(obtain|get|refresh)\s*(a\s*)?new\s*token", re.IGNORECASE),
    re.compile(r"token\s*(has\s*)?expired", re.IGNORECASE),
]

_BILLING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b402\b"),
    re.compile(r"payment\s+required", re.IGNORECASE),
    re.compile(r"billing\s+(issue|error|required|problem)", re.IGNORECASE),
    re.compile(r"credit\s+card\s+(declined|expired|invalid|limit)", re.IGNORECASE),
    re.compile(r"card\s+(declined|expired)", re.IGNORECASE),
    re.compile(r"insufficient\s+funds", re.IGNORECASE),
    re.compile(r"quota\s+exceeded", re.IGNORECASE),
]

_RATE_LIMIT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b429\b"),
    re.compile(r"rate[_\s]?limit", re.IGNORECASE),
    re.compile(r"too\s+many\s+requests", re.IGNORECASE),
    re.compile(r"ratelimit", re.IGNORECASE),
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

# Default retry hints per category
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


def _match_patterns(text: str, patterns: list[re.Pattern[str]]) -> re.Match[str] | None:
    for pattern in patterns:
        m = pattern.search(text)
        if m:
            return m
    return None


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
        If so, maps the ErrorCode to the appropriate SDKErrorCategory.
        Otherwise, falls back to string-based pattern matching for backward compatibility.

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

        # Fall back to string-based pattern matching for backward compatibility
        text = f"{type(exc).__name__}: {exc}"
        return self._classify_text(text)

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

        # Only classify if the text looks like an error (short text or error keywords)
        error_keywords = re.compile(
            r"(error|fail|exception|denied|unauthorized|expired|refused)", re.I
        )
        if len(text) > 500 and not error_keywords.search(text[:500]):
            return None

        result = self._classify_text(text)
        if result.category == SDKErrorCategory.UNKNOWN:
            return None
        return result

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

    def _classify_text(self, text: str) -> ClassifiedError:
        # Order matters — check most specific first

        # Auth expired (subset of auth but more specific)
        if _match_patterns(text, _AUTH_EXPIRED_PATTERNS):
            return _build_classified(
                SDKErrorCategory.AUTH_EXPIRED,
                f"authentication error: {self._excerpt(text)}",
            )

        # Auth invalid
        if _match_patterns(text, _AUTH_PATTERNS):
            return _build_classified(
                SDKErrorCategory.AUTH_INVALID,
                f"authentication error: {self._excerpt(text)}",
            )

        # Billing
        if _match_patterns(text, _BILLING_PATTERNS):
            return _build_classified(
                SDKErrorCategory.BILLING_EXHAUSTED,
                f"billing error: {self._excerpt(text)}",
            )

        # Rate limit
        if _match_patterns(text, _RATE_LIMIT_PATTERNS):
            return _build_classified(
                SDKErrorCategory.RATE_LIMITED,
                f"rate limited: {self._excerpt(text)}",
            )

        # Overloaded
        if _match_patterns(text, _OVERLOADED_PATTERNS):
            return _build_classified(
                SDKErrorCategory.OVERLOADED,
                f"API overloaded: {self._excerpt(text)}",
            )

        # Network
        if _match_patterns(text, _NETWORK_PATTERNS):
            return _build_classified(
                SDKErrorCategory.NETWORK,
                f"network error: {self._excerpt(text)}",
            )

        # Context overflow
        if _match_patterns(text, _CONTEXT_OVERFLOW_PATTERNS):
            return _build_classified(
                SDKErrorCategory.CONTEXT_OVERFLOW,
                f"context overflow: {self._excerpt(text)}",
            )

        return _build_classified(
            SDKErrorCategory.UNKNOWN,
            self._excerpt(text),
        )

    @staticmethod
    def _excerpt(text: str, max_len: int = 200) -> str:
        text = text.strip()
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."
