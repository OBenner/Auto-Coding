"""
Shared Error Utilities (DEPRECATED)
====================================

.. deprecated::
    **This module is deprecated.** Use typed error classes from ``core.typed_errors``
    and error detection functions from ``core.error_detection`` instead.

    String-based error detection is being phased out in favor of a robust typed
    error system. All functions in this module will be removed in a future version.

**Migration Guide:**

Old pattern (string-based detection)::

    from core.error_utils import is_authentication_error, is_rate_limit_error

    if is_authentication_error(exc):
        # Handle auth error
        pass
    elif is_rate_limit_error(exc):
        # Handle rate limit
        pass

New pattern (typed errors)::

    from core.typed_errors import AuthError, RateLimitError
    from core.error_detection import get_error_code
    from core.error_codes import ErrorCode

    # Option 1: Direct isinstance checks
    if isinstance(exc, AuthError):
        # Handle auth error
        pass
    elif isinstance(exc, RateLimitError):
        # Handle rate limit
        pass

    # Option 2: Using error_code enum for more control
    error_code = get_error_code(exc)
    if error_code == ErrorCode.AUTH_INVALID:
        # Handle invalid auth
        pass
    elif error_code == ErrorCode.RATE_LIMITED:
        # Handle rate limit
        pass

**Benefits of the new system:**
- Type-safe error detection via ``isinstance()`` checks
- Structured error codes (``ErrorCode`` enum) for programmatic handling
- Rich metadata attached to errors (retry hints, user-friendly messages)
- Better IDE support and autocomplete
- Consistent error handling across the codebase

**Remaining functions:**
- ``is_tool_concurrency_error()`` - Deprecated, use ``ToolConcurrencyError``
- ``is_rate_limit_error()`` - Deprecated, use ``RateLimitError``
- ``is_authentication_error()`` - Deprecated, use ``AuthError``
- ``safe_receive_messages()`` - Not deprecated (SDK resilience helper)
"""

from __future__ import annotations

import logging
import re
import warnings
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from core.typed_errors import AuthError, RateLimitError

if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeSDKClient
    from claude_agent_sdk.types import Message

logger = logging.getLogger(__name__)


def is_tool_concurrency_error(error: Exception) -> bool:
    """
    Check if an error is a 400 tool concurrency error from Claude API.

    Tool concurrency errors occur when too many tools are used simultaneously
    in a single API request, hitting Claude's concurrent tool use limit.

    .. deprecated::
        String-based error detection is deprecated. Use typed error classes
        from ``core.typed_errors`` instead. This function will be removed in
        a future version.

    Args:
        error: The exception to check

    Returns:
        True if this is a tool concurrency error, False otherwise
    """
    warnings.warn(
        "is_tool_concurrency_error() is deprecated and will be removed in a "
        "future version. Use typed error classes from core.typed_errors instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    error_str = str(error).lower()
    # Check for 400 status AND tool concurrency keywords
    return "400" in error_str and (
        ("tool" in error_str and "concurrency" in error_str)
        or "too many tools" in error_str
        or "concurrent tool" in error_str
    )


def is_rate_limit_error(error: Exception) -> bool:
    """
    Check if an error is a rate limit error (429 or similar).

    Rate limit errors occur when the API usage quota is exceeded,
    either for session limits or weekly limits.

    This function first checks for typed RateLimitError instances,
    then falls back to string-based detection for backward compatibility.

    .. deprecated::
        String-based error detection is deprecated. Use typed ``RateLimitError``
        from ``core.typed_errors`` instead. The string-based fallback will be
        removed in a future version.

    Args:
        error: The exception to check

    Returns:
        True if this is a rate limit error, False otherwise
    """
    # Check for typed RateLimitError first
    if isinstance(error, RateLimitError):
        return True

    # Fall back to string-based detection for backward compatibility
    warnings.warn(
        "String-based rate limit error detection in is_rate_limit_error() is "
        "deprecated and will be removed in a future version. Use typed "
        "RateLimitError from core.typed_errors instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    error_str = str(error).lower()

    # Check for HTTP 429 with word boundaries to avoid false positives
    if re.search(r"\b429\b", error_str):
        return True

    # Check for other rate limit indicators
    return any(
        p in error_str
        for p in [
            "limit reached",
            "rate limit",
            "too many requests",
            "usage limit",
            "quota exceeded",
        ]
    )


def is_authentication_error(error: Exception) -> bool:
    """
    Check if an error is an authentication error (401, token expired, etc.).

    Authentication errors occur when OAuth tokens are invalid, expired,
    or have been revoked (e.g., after token refresh on another process).

    This function first checks for typed AuthError instances,
    then falls back to string-based detection for backward compatibility.

    .. deprecated::
        String-based error detection is deprecated. Use typed ``AuthError``
        from ``core.typed_errors`` instead. The string-based fallback will be
        removed in a future version.

    Validation approach:
    - Typed AuthError instances are detected via isinstance() check
    - HTTP 401 status code is checked with word boundaries to minimize false positives
    - Additional string patterns are validated against lowercase error messages
    - Patterns are designed to match known Claude API and OAuth error formats

    Known false positive risks:
    - Generic error messages containing "unauthorized" or "access denied" may match
      even if not related to authentication (e.g., file permission errors)
    - Error messages containing these keywords in user-provided content could match
    - Mitigation: HTTP 401 check provides strong signal; string patterns are secondary

    Real-world validation:
    - Pattern matching has been tested against actual Claude API error responses
    - False positive rate is acceptable given the recovery mechanism (prompt user to re-auth)
    - If false positive occurs, user can simply resume without re-authenticating

    Args:
        error: The exception to check

    Returns:
        True if this is an authentication error, False otherwise
    """
    # Check for typed AuthError first
    if isinstance(error, AuthError):
        return True

    # Fall back to string-based detection for backward compatibility
    warnings.warn(
        "String-based authentication error detection in is_authentication_error() "
        "is deprecated and will be removed in a future version. Use typed "
        "AuthError from core.typed_errors instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    error_str = str(error).lower()

    # Check for HTTP 401 with word boundaries to avoid false positives
    if re.search(r"\b401\b", error_str):
        return True

    # Check for other authentication indicators
    # NOTE: "authentication failed" and "authentication error" are more specific patterns
    # to reduce false positives from generic "authentication" mentions
    return any(
        p in error_str
        for p in [
            "authentication failed",
            "authentication error",
            "unauthorized",
            "invalid token",
            "token expired",
            "authentication_error",
            "invalid_token",
            "token_expired",
            "not authenticated",
            "http 401",
            "does not have access to claude",
            "please login again",
        ]
    )


async def safe_receive_messages(
    client: ClaudeSDKClient,
    *,
    caller: str = "agent",
) -> AsyncIterator[Message]:
    """Iterate over SDK messages with resilience against unexpected errors.

    The SDK's ``receive_response()`` async generator can terminate early if:
    1. An unhandled message type slips past the monkey-patch (e.g., SDK upgrade
       removes the patch surface).
    2. A transient parse error corrupts a single message in the stream.
    3. An unexpected ``StopAsyncIteration`` or runtime error occurs mid-stream.

    This wrapper catches per-message errors, logs them, and continues yielding
    subsequent messages so the agent session can complete its work.

    It also detects rate-limit events (surfaced as ``SystemMessage`` with
    subtype ``unknown_rate_limit_event``) and logs a user-visible warning.

    Args:
        client: A ``ClaudeSDKClient`` instance (must be inside ``async with``).
        caller: Label for log messages (e.g., "session", "agent_runner").

    Yields:
        Parsed ``Message`` objects from the SDK response stream.
    """
    try:
        async for msg in client.receive_response():
            # Detect rate-limit events surfaced by the monkey-patch
            msg_type = type(msg).__name__
            if msg_type == "SystemMessage":
                subtype = getattr(msg, "subtype", "")
                if subtype.startswith("unknown_"):
                    original_type = subtype[len("unknown_") :]
                    if "rate_limit" in original_type:
                        data = getattr(msg, "data", {})
                        retry_after = data.get("retry_after") or data.get(
                            "data", {}
                        ).get("retry_after")
                        retry_info = (
                            f" (retry in {retry_after}s)" if retry_after else ""
                        )
                        logger.warning("[%s] Rate limit event%s", caller, retry_info)
                    else:
                        logger.debug(
                            "[%s] Skipping unknown SDK message type: %s",
                            caller,
                            original_type,
                        )
                    continue
            yield msg
    except GeneratorExit:
        return
    except Exception as e:
        # If the generator itself raises (e.g., transport error), log and stop
        # gracefully so callers can process whatever was collected so far.
        logger.error("[%s] SDK response stream terminated unexpectedly: %s", caller, e)
        return
