"""Tests for the error classifier module."""

import pytest
from core.error_classifier import (
    ErrorClassifier,
    SDKErrorCategory,
)
from core.error_codes import ErrorCode
from core.error_detection import get_error_code
from core.typed_errors import (
    AuthError,
    NetworkError,
    OperationTimeoutError,
    RateLimitError,
    TypedError,
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
        exc = OperationTimeoutError("Connection timed out")
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


# ---------------------------------------------------------------------------
# typed errors
# ---------------------------------------------------------------------------


class TestTypedErrors:
    """Test classification of typed errors with error_code attribute."""

    def test_auth_error_classification(self, classifier):
        """Test AuthError is classified as AUTH_INVALID."""
        exc = AuthError("Invalid API key provided")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.AUTH_INVALID
        assert result.is_fatal is True
        assert result.is_retryable is False
        assert "Invalid API key provided" in result.message

    def test_rate_limit_error_classification(self, classifier):
        """Test RateLimitError is classified as RATE_LIMITED."""
        exc = RateLimitError("Too many requests")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.RATE_LIMITED
        assert result.is_fatal is False
        assert result.is_retryable is True
        assert result.retry_after_seconds > 0

    def test_network_error_classification(self, classifier):
        """Test NetworkError is classified as NETWORK."""
        exc = NetworkError("Connection failed")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.NETWORK
        assert result.is_fatal is False
        assert result.is_retryable is True

    def test_timeout_error_classification(self, classifier):
        """Test OperationTimeoutError is classified as NETWORK."""
        exc = OperationTimeoutError("Request timed out")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.NETWORK
        assert result.is_fatal is False
        assert result.is_retryable is True

    def test_typed_error_with_auth_expired_code(self, classifier):
        """Test typed error with AUTH_EXPIRED code."""
        exc = TypedError(ErrorCode.AUTH_EXPIRED, "Token has expired")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.AUTH_EXPIRED
        assert result.is_fatal is True

    def test_typed_error_with_billing_code(self, classifier):
        """Test typed error with BILLING_EXHAUSTED code."""
        exc = TypedError(ErrorCode.BILLING_EXHAUSTED, "Credits exhausted")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.BILLING_EXHAUSTED
        assert result.is_fatal is True

    def test_typed_error_with_quota_exceeded_code(self, classifier):
        """Test typed error with QUOTA_EXCEEDED code maps to billing."""
        exc = TypedError(ErrorCode.QUOTA_EXCEEDED, "Usage quota exceeded")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.BILLING_EXHAUSTED
        assert result.is_fatal is True

    def test_typed_error_with_context_overflow_code(self, classifier):
        """Test typed error with CONTEXT_OVERFLOW code."""
        exc = TypedError(ErrorCode.CONTEXT_OVERFLOW, "Prompt too long")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.CONTEXT_OVERFLOW
        assert result.is_fatal is True

    def test_typed_error_with_overloaded_code(self, classifier):
        """Test typed error with OVERLOADED code."""
        exc = TypedError(ErrorCode.OVERLOADED, "API overloaded")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.OVERLOADED
        assert result.is_fatal is False
        assert result.is_retryable is True

    def test_typed_error_with_stuck_loop_code(self, classifier):
        """Test typed error with STUCK_LOOP code."""
        exc = TypedError(ErrorCode.STUCK_LOOP, "Agent stuck in loop")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.STUCK_LOOP
        assert result.is_fatal is True

    def test_typed_error_with_unknown_code(self, classifier):
        """Test typed error with UNKNOWN code."""
        exc = TypedError(ErrorCode.UNKNOWN, "Unknown error occurred")
        result = classifier.classify_exception(exc)
        assert result.category == SDKErrorCategory.UNKNOWN
        assert result.is_fatal is False

    def test_typed_error_bypasses_pattern_matching(self, classifier):
        """Test that typed errors use error_code, not string pattern matching."""
        # Create an AuthError but with a message that would match network patterns
        # This should still be classified as AUTH_INVALID because of the error_code
        exc = AuthError("Connection timeout - invalid credentials")
        result = classifier.classify_exception(exc)
        # Should use the error_code (AUTH_INVALID) not the "timeout" pattern (NETWORK)
        assert result.category == SDKErrorCategory.AUTH_INVALID
        assert result.is_fatal is True

    def test_get_error_code_from_typed_error(self):
        """Test get_error_code extracts ErrorCode from TypedError."""
        exc = AuthError("Test error")
        error_code = get_error_code(exc)
        assert error_code == ErrorCode.AUTH_INVALID

    def test_get_error_code_from_generic_exception(self):
        """Test get_error_code returns None for generic exceptions."""
        exc = Exception("Generic error")
        error_code = get_error_code(exc)
        assert error_code is None

    def test_get_error_code_from_typed_error_custom_code(self):
        """Test get_error_code extracts custom ErrorCode from TypedError."""
        exc = TypedError(ErrorCode.RATE_LIMIT_HARD, "Hard rate limit")
        error_code = get_error_code(exc)
        assert error_code == ErrorCode.RATE_LIMIT_HARD

    def test_typed_error_message_in_classification(self, classifier):
        """Test that the TypedError message is preserved in classification."""
        custom_message = "Custom authentication failure message"
        exc = AuthError(custom_message)
        result = classifier.classify_exception(exc)
        assert custom_message in result.message
        assert "AuthError" in result.message

    def test_multiple_typed_errors_same_category(self, classifier):
        """Test that multiple ErrorCodes can map to the same category."""
        exc1 = TypedError(ErrorCode.RATE_LIMITED, "Rate limit")
        exc2 = TypedError(ErrorCode.RATE_LIMIT_HARD, "Hard rate limit")

        result1 = classifier.classify_exception(exc1)
        result2 = classifier.classify_exception(exc2)

        # Both should map to RATE_LIMITED category
        assert result1.category == SDKErrorCategory.RATE_LIMITED
        assert result2.category == SDKErrorCategory.RATE_LIMITED
