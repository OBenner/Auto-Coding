"""Tests for the error classifier module."""

import pytest
from core.error_classifier import (
    ClassifiedError,
    ErrorClassifier,
    SDKErrorCategory,
)


@pytest.fixture
def classifier():
    return ErrorClassifier()


# ---------------------------------------------------------------------------
# classify_exception
# ---------------------------------------------------------------------------


class TestClassifyException:
    def test_auth_invalid_key(self, classifier):
        exc = Exception("invalid_api_key: the key you provided is not valid")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.AUTH_INVALID
        assert result.is_fatal is True
        assert result.is_retryable is False

    def test_401_unauthorized(self, classifier):
        exc = Exception("API Error: 401 Unauthorized")
        result = classifier.classify_exception(exc)
        assert result.category in (
            SDKErrorCategory.AUTH_INVALID,
            SDKErrorCategory.AUTH_EXPIRED,
        )
        assert result.is_fatal is True

    def test_token_expired(self, classifier):
        exc = Exception("OAuth token has expired. Please obtain a new token.")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.AUTH_EXPIRED
        assert result.is_fatal is True

    def test_billing_402(self, classifier):
        exc = Exception("402 Payment Required - billing issue")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.BILLING_EXHAUSTED
        assert result.is_fatal is True

    def test_rate_limited_429(self, classifier):
        exc = Exception("429 Too Many Requests - rate_limit")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.RATE_LIMITED
        assert result.is_retryable is True
        assert result.retry_after_seconds > 0

    def test_overloaded_503(self, classifier):
        exc = Exception("503 Service Unavailable - overloaded")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.OVERLOADED
        assert result.is_retryable is True

    def test_network_timeout(self, classifier):
        exc = TimeoutError("Connection timed out")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.NETWORK
        assert result.is_retryable is True

    def test_context_overflow(self, classifier):
        exc = Exception("maximum tokens exceeded for this model")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.CONTEXT_OVERFLOW
        assert result.is_fatal is True

    def test_unknown_error(self, classifier):
        exc = ValueError("something completely unexpected")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.UNKNOWN


# ---------------------------------------------------------------------------
# classify_response
# ---------------------------------------------------------------------------


class TestClassifyResponse:
    def test_none_for_normal_text(self, classifier):
        assert classifier.classify_response("The code looks good!") is None

    def test_none_for_empty(self, classifier):
        assert classifier.classify_response("") is None

    def test_auth_error_in_response(self, classifier):
        result = classifier.classify_response(
            'Error: {"type": "authentication_error", "message": "invalid key"}'
        )
        assert result is not None
        assert result.category == SDKErrorCategory.AUTH_INVALID

    def test_normal_long_text_not_classified(self, classifier):
        long_text = "All good. " * 200
        assert classifier.classify_response(long_text) is None


# ---------------------------------------------------------------------------
# check_stuck_loop
# ---------------------------------------------------------------------------


class TestStuckLoop:
    def test_not_stuck_with_varied_responses(self, classifier):
        assert not classifier.check_stuck_loop("response A")
        assert not classifier.check_stuck_loop("response B")
        assert not classifier.check_stuck_loop("response C")

    def test_stuck_with_identical_responses(self, classifier):
        assert not classifier.check_stuck_loop("I'll try again")
        assert not classifier.check_stuck_loop("I'll try again")
        assert classifier.check_stuck_loop("I'll try again")

    def test_reset_clears_history(self, classifier):
        classifier.check_stuck_loop("same")
        classifier.check_stuck_loop("same")
        classifier.reset()
        assert not classifier.check_stuck_loop("same")

    def test_stuck_detected_via_classify_response(self, classifier):
        classifier.check_stuck_loop("short error msg")
        classifier.check_stuck_loop("short error msg")
        result = classifier.classify_response("short error msg")
        assert result is not None
        assert result.category == SDKErrorCategory.STUCK_LOOP
