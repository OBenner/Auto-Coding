"""
Shared Error Utilities (DEPRECATED)
====================================

.. deprecated::
    **This module is deprecated.** Use typed error classes from ``core.typed_errors``
    and error detection functions from ``core.error_detection`` instead.

    String-based error detection has been completely removed in favor of a robust typed
    error system. All functions in this module will be removed in a future version.

**Migration Guide:**

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

    .. deprecated::
        This function is deprecated. Use ``ToolConcurrencyError`` from
        ``core.typed_errors`` instead. This function will be removed in
        a future version.

    Args:
        error: The exception to check

    Returns:
        True if this is a tool concurrency error, False otherwise
    """
    warnings.warn(
        "is_tool_concurrency_error() is deprecated and will be removed in a "
        "future version. Use ToolConcurrencyError from core.typed_errors instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # TODO: Remove this function in a future version
    return False


def is_rate_limit_error(error: Exception) -> bool:
    """
    Check if an error is a rate limit error.

    Rate limit errors occur when the API usage quota is exceeded,
    either for session limits or weekly limits.

    This function only checks for typed RateLimitError instances.
    String-based detection has been removed in favor of typed error classes.

    .. deprecated::
        This function is deprecated. Use ``RateLimitError`` from
        ``core.typed_errors`` instead. This function will be removed in
        a future version.

    Args:
        error: The exception to check

    Returns:
        True if this is a rate limit error, False otherwise
    """
    warnings.warn(
        "is_rate_limit_error() is deprecated and will be removed in a "
        "future version. Use RateLimitError from core.typed_errors instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Only check for typed RateLimitError
    return isinstance(error, RateLimitError)


def is_authentication_error(error: Exception) -> bool:
    """
    Check if an error is an authentication error (401, token expired, etc.).

    Authentication errors occur when OAuth tokens are invalid, expired,
    or have been revoked (e.g., after token refresh on another process).

    This function only checks for typed AuthError instances.
    String-based detection has been removed in favor of typed error classes.

    .. deprecated::
        This function is deprecated. Use ``AuthError`` from
        ``core.typed_errors`` instead. This function will be removed in
        a future version.

    Args:
        error: The exception to check

    Returns:
        True if this is an authentication error, False otherwise
    """
    warnings.warn(
        "is_authentication_error() is deprecated and will be removed in a "
        "future version. Use AuthError from core.typed_errors instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Only check for typed AuthError
    return isinstance(error, AuthError)


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
