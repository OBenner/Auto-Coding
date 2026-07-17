"""
Tests for error classification helpers
======================================

Pins the current contract of ``is_rate_limit_error`` and
``is_authentication_error`` in ``core.error_utils``: they classify by the typed
error hierarchy only. The string-matching fallback they once had was removed in
favour of ``core.typed_errors``, and both helpers are now deprecated.

Replaces the root-level ``test_verify_subtask_2_2.py`` verification script left
behind by #154. That script was never collected by pytest (wrong location, and
its imports only resolve from apps/backend), and it had gone stale: it asserted
the string-based detection that has since been removed, so it would fail today.
"""

import pytest

from core.error_utils import is_authentication_error, is_rate_limit_error
from core.typed_errors import AuthError, RateLimitError


def _is_rate_limit(error: Exception) -> bool:
    """Call the deprecated helper, asserting it still warns."""
    with pytest.warns(DeprecationWarning):
        return is_rate_limit_error(error)


def _is_auth(error: Exception) -> bool:
    """Call the deprecated helper, asserting it still warns."""
    with pytest.warns(DeprecationWarning):
        return is_authentication_error(error)


class TestTypedErrorsAreDetected:
    def test_rate_limit_error_is_detected(self):
        assert _is_rate_limit(RateLimitError("Test rate limit error"))

    def test_auth_error_is_detected(self):
        assert _is_auth(AuthError("Test auth error"))


class TestStringMatchingIsGone:
    """Detection is typed-only: message text must not classify an error."""

    @pytest.mark.parametrize(
        "message",
        ["429 rate limit exceeded", "Rate limit exceeded", "rate_limit_error"],
    )
    def test_rate_limit_strings_are_not_detected(self, message):
        assert not _is_rate_limit(Exception(message))

    @pytest.mark.parametrize(
        "message",
        ["401 unauthorized", "Unauthorized", "authentication_error"],
    )
    def test_auth_strings_are_not_detected(self, message):
        assert not _is_auth(Exception(message))


class TestNegativeCases:
    def test_generic_error_is_not_rate_limit(self):
        assert not _is_rate_limit(Exception("some other error"))

    def test_generic_error_is_not_auth(self):
        assert not _is_auth(Exception("some other error"))

    def test_classifications_do_not_overlap(self):
        assert not _is_auth(RateLimitError("Test rate limit error"))
        assert not _is_rate_limit(AuthError("Test auth error"))
