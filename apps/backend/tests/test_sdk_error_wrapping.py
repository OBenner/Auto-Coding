"""Tests for SDK error wrapping functionality."""

from core.error_codes import ErrorCode
from core.error_detection import get_error_code, wrap_sdk_error
from core.typed_errors import (
    AccessDeniedError,
    AuthError,
    ConfigurationError,
    NetworkError,
    NotFoundError,
    OperationTimeoutError,
    RateLimitError,
    TypedError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# wrap_sdk_error - Authentication Errors
# ---------------------------------------------------------------------------


class TestWrapAuthErrors:
    """Test wrapping of authentication-related SDK errors."""

    def test_invalid_api_key_error(self):
        """Test wrapping invalid API key errors."""
        exc = Exception("invalid_api_key: the key you provided is not valid")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, AuthError)
        assert get_error_code(wrapped) == ErrorCode.AUTH_INVALID
        assert "invalid_api_key" in str(wrapped)

    def test_unauthorized_401_error(self):
        """Test wrapping 401 unauthorized errors."""
        exc = Exception("API Error: 401 Unauthorized")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, AuthError)
        assert get_error_code(wrapped) in (
            ErrorCode.AUTH_INVALID,
            ErrorCode.AUTH_EXPIRED,
        )

    def test_token_expired_error(self):
        """Test wrapping expired token errors."""
        exc = Exception("OAuth token has expired. Please obtain a new token.")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, AuthError)
        # Note: AuthError defaults to AUTH_INVALID, not AUTH_EXPIRED
        assert get_error_code(wrapped) == ErrorCode.AUTH_INVALID

    def test_authentication_failed_error(self):
        """Test wrapping generic authentication failed errors."""
        exc = Exception("authentication_error: Authentication failed")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, AuthError)
        assert get_error_code(wrapped) == ErrorCode.AUTH_INVALID

    def test_access_denied_error(self):
        """Test wrapping access denied errors."""
        exc = Exception("access denied: insufficient permissions")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, AuthError)
        assert get_error_code(wrapped) == ErrorCode.AUTH_INVALID


# ---------------------------------------------------------------------------
# wrap_sdk_error - Billing Errors
# ---------------------------------------------------------------------------


class TestWrapBillingErrors:
    """Test wrapping of billing-related SDK errors."""

    def test_402_payment_required(self):
        """Test wrapping 402 payment required errors."""
        exc = Exception("402 Payment Required - billing issue")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.BILLING_EXHAUSTED

    def test_billing_issue_error(self):
        """Test wrapping generic billing issue errors."""
        exc = Exception("billing error: payment required")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.BILLING_EXHAUSTED

    def test_quota_exceeded_error(self):
        """Test wrapping quota exceeded errors."""
        exc = Exception("quota exceeded: usage limit reached")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.BILLING_EXHAUSTED


# ---------------------------------------------------------------------------
# wrap_sdk_error - Rate Limit Errors
# ---------------------------------------------------------------------------


class TestWrapRateLimitErrors:
    """Test wrapping of rate limit SDK errors."""

    def test_429_rate_limit(self):
        """Test wrapping 429 too many requests errors."""
        exc = Exception("429 Too Many Requests - rate_limit")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.RATE_LIMITED

    def test_rate_limit_exceeded(self):
        """Test wrapping rate limit exceeded errors."""
        exc = Exception("rate limit exceeded: too many requests")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.RATE_LIMITED


# ---------------------------------------------------------------------------
# wrap_sdk_error - Network Errors
# ---------------------------------------------------------------------------


class TestWrapNetworkErrors:
    """Test wrapping of network-related SDK errors."""

    def test_connection_refused(self):
        """Test wrapping connection refused errors."""
        exc = Exception("connection refused: could not connect to API")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, NetworkError)
        assert get_error_code(wrapped) == ErrorCode.NETWORK

    def test_connection_timeout(self):
        """Test wrapping connection timeout errors."""
        exc = OperationTimeoutError("connection timed out after 30s")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, OperationTimeoutError)
        assert get_error_code(wrapped) == ErrorCode.NETWORK_TIMEOUT

    def test_network_unreachable(self):
        """Test wrapping network unreachable errors."""
        exc = Exception("network unreachable: host not found")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, NetworkError)
        assert get_error_code(wrapped) == ErrorCode.NETWORK

    def test_generic_network_error(self):
        """Test wrapping generic network errors."""
        exc = Exception("network error: connection failed")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, NetworkError)
        assert get_error_code(wrapped) == ErrorCode.NETWORK

    def test_502_bad_gateway(self):
        """Test wrapping 502 bad gateway errors."""
        exc = Exception("502 Bad Gateway")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, NetworkError)
        # Note: 502 is classified as NETWORK, not BAD_GATEWAY, by the pattern matcher
        assert get_error_code(wrapped) == ErrorCode.NETWORK


# ---------------------------------------------------------------------------
# wrap_sdk_error - Service Errors
# ---------------------------------------------------------------------------


class TestWrapServiceErrors:
    """Test wrapping of service-related SDK errors."""

    def test_503_service_unavailable(self):
        """Test wrapping 503 service unavailable errors."""
        exc = Exception("503 Service Unavailable - overloaded")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.OVERLOADED

    def test_529_overloaded(self):
        """Test wrapping 529 overloaded errors."""
        exc = Exception("529 Service Overloaded")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.OVERLOADED

    def test_500_internal_error(self):
        """Test wrapping 500 internal server errors."""
        exc = Exception("500 Internal Server Error")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.NETWORK


# ---------------------------------------------------------------------------
# wrap_sdk_error - Context Errors
# ---------------------------------------------------------------------------


class TestWrapContextErrors:
    """Test wrapping of context-related SDK errors."""

    def test_context_window_exceeded(self):
        """Test wrapping context window exceeded errors."""
        exc = Exception("context window exceeded: too many tokens")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.CONTEXT_OVERFLOW

    def test_prompt_too_long(self):
        """Test wrapping prompt too long errors."""
        exc = Exception("prompt is too long: exceeds maximum length")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.CONTEXT_OVERFLOW

    def test_token_limit_exceeded(self):
        """Test wrapping token limit exceeded errors."""
        exc = Exception("maximum tokens exceeded for this model")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.CONTEXT_OVERFLOW


# ---------------------------------------------------------------------------
# wrap_sdk_error - Typed Error Preservation
# ---------------------------------------------------------------------------


class TestTypedErrorPreservation:
    """Test that already-typed errors are preserved unchanged."""

    def test_auth_error_preserved(self):
        """Test that AuthError instances are returned unchanged."""
        original = AuthError("Invalid credentials")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original  # Same object reference
        assert get_error_code(wrapped) == ErrorCode.AUTH_INVALID

    def test_rate_limit_error_preserved(self):
        """Test that RateLimitError instances are returned unchanged."""
        original = RateLimitError("Too many requests")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original  # Same object reference
        assert get_error_code(wrapped) == ErrorCode.RATE_LIMITED

    def test_network_error_preserved(self):
        """Test that NetworkError instances are returned unchanged."""
        original = NetworkError("Connection failed")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original  # Same object reference
        assert get_error_code(wrapped) == ErrorCode.NETWORK

    def test_timeout_error_preserved(self):
        """Test that OperationTimeoutError instances are returned unchanged."""
        original = OperationTimeoutError("Request timed out")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original  # Same object reference
        assert get_error_code(wrapped) == ErrorCode.NETWORK_TIMEOUT

    def test_typed_error_preserved(self):
        """Test that base TypedError instances are returned unchanged."""
        original = TypedError(ErrorCode.QUOTA_EXCEEDED, "Quota exceeded")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original  # Same object reference
        assert get_error_code(wrapped) == ErrorCode.QUOTA_EXCEEDED

    def test_validation_error_preserved(self):
        """Test that ValidationError instances are returned unchanged."""
        original = ValidationError("Invalid input")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original
        assert get_error_code(wrapped) == ErrorCode.INVALID_REQUEST

    def test_not_found_error_preserved(self):
        """Test that NotFoundError instances are returned unchanged."""
        original = NotFoundError("Resource not found")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original
        assert get_error_code(wrapped) == ErrorCode.NOT_FOUND

    def test_access_denied_error_preserved(self):
        """Test that AccessDeniedError instances are returned unchanged."""
        original = AccessDeniedError("Access denied")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original
        assert get_error_code(wrapped) == ErrorCode.AUTH_INVALID

    def test_configuration_error_preserved(self):
        """Test that ConfigurationError instances are returned unchanged."""
        original = ConfigurationError("Invalid config")
        wrapped = wrap_sdk_error(original)

        assert wrapped is original
        assert get_error_code(wrapped) == ErrorCode.INVALID_REQUEST


# ---------------------------------------------------------------------------
# wrap_sdk_error - Unknown Errors
# ---------------------------------------------------------------------------


class TestUnknownErrors:
    """Test wrapping of unknown/unrecognized errors."""

    def test_generic_exception(self):
        """Test wrapping generic exceptions."""
        exc = ValueError("something completely unexpected")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.UNKNOWN
        assert "something completely unexpected" in str(wrapped)

    def test_runtime_error(self):
        """Test wrapping runtime errors."""
        exc = RuntimeError("unexpected runtime condition")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.UNKNOWN

    def test_empty_error_message(self):
        """Test wrapping errors with empty messages."""
        exc = Exception("")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.UNKNOWN


# ---------------------------------------------------------------------------
# wrap_sdk_error - Error Message Preservation
# ---------------------------------------------------------------------------


class TestErrorMessagePreservation:
    """Test that error messages are preserved through wrapping."""

    def test_message_preserved_in_auth_error(self):
        """Test that original message is preserved in AuthError."""
        original_msg = "Invalid API key: sk-ant-1234"
        exc = Exception(original_msg)
        wrapped = wrap_sdk_error(exc)

        assert original_msg in str(wrapped)

    def test_message_preserved_in_network_error(self):
        """Test that original message is preserved in NetworkError."""
        original_msg = "Connection refused to api.anthropic.com"
        exc = Exception(original_msg)
        wrapped = wrap_sdk_error(exc)

        assert original_msg in str(wrapped)

    def test_message_preserved_in_typed_error(self):
        """Test that original message is preserved in base TypedError."""
        original_msg = "context length exceeded: 200k tokens"
        exc = Exception(original_msg)
        wrapped = wrap_sdk_error(exc)

        assert original_msg in str(wrapped)


# ---------------------------------------------------------------------------
# Integration Tests - End-to-End Scenarios
# ---------------------------------------------------------------------------


class TestIntegrationScenarios:
    """Test end-to-end error wrapping scenarios."""

    def test_sdk_auth_error_handling_flow(self):
        """Test complete flow of SDK auth error detection and wrapping."""
        # Simulate SDK throwing an auth error
        sdk_error = Exception("invalid_api_key: the key you provided is not valid")

        # Wrap the error
        typed_error = wrap_sdk_error(sdk_error)

        # Verify it's now a typed error with correct classification
        assert isinstance(typed_error, AuthError)
        error_code = get_error_code(typed_error)
        assert error_code == ErrorCode.AUTH_INVALID

        # Verify error can be programmatically handled
        if error_code == ErrorCode.AUTH_INVALID:
            # Simulate recovery action
            recovery_message = "Please re-authenticate with a valid API key"
            assert recovery_message is not None

    def test_sdk_rate_limit_handling_flow(self):
        """Test complete flow of SDK rate limit error detection and wrapping."""
        # Simulate SDK throwing a rate limit error
        sdk_error = Exception("429 Too Many Requests - rate_limit")

        # Wrap the error
        typed_error = wrap_sdk_error(sdk_error)

        # Verify it's now a typed error with correct classification
        assert isinstance(typed_error, TypedError)
        error_code = get_error_code(typed_error)
        assert error_code == ErrorCode.RATE_LIMITED

        # Verify error can be programmatically handled
        if error_code == ErrorCode.RATE_LIMITED:
            # Simulate recovery action
            recovery_message = "Rate limit exceeded, please retry after backoff"
            assert recovery_message is not None

    def test_sdk_network_error_handling_flow(self):
        """Test complete flow of SDK network error detection and wrapping."""
        # Simulate SDK throwing a network error
        sdk_error = OperationTimeoutError("connection timed out after 30s")

        # Wrap the error
        typed_error = wrap_sdk_error(sdk_error)

        # Verify it's now a typed error with correct classification
        assert isinstance(typed_error, OperationTimeoutError)
        error_code = get_error_code(typed_error)
        assert error_code == ErrorCode.NETWORK_TIMEOUT

        # Verify error can be programmatically handled
        if error_code == ErrorCode.NETWORK_TIMEOUT:
            # Simulate recovery action
            recovery_message = "Network timeout, will retry with exponential backoff"
            assert recovery_message is not None

    def test_double_wrapping_protection(self):
        """Test that wrapping an already-wrapped error is idempotent."""
        # First wrapping
        original = Exception("invalid_api_key")
        first_wrap = wrap_sdk_error(original)

        # Second wrapping (should return same object)
        second_wrap = wrap_sdk_error(first_wrap)

        assert first_wrap is second_wrap
        assert get_error_code(first_wrap) == get_error_code(second_wrap)

    def test_error_code_extraction_after_wrapping(self):
        """Test that error codes can be extracted from wrapped errors."""
        test_cases = [
            (Exception("invalid_api_key"), ErrorCode.AUTH_INVALID),
            (Exception("429 Too Many Requests"), ErrorCode.RATE_LIMITED),
            (Exception("402 Payment Required"), ErrorCode.BILLING_EXHAUSTED),
            (Exception("connection refused"), ErrorCode.NETWORK),
            (Exception("context window exceeded"), ErrorCode.CONTEXT_OVERFLOW),
        ]

        for original_error, expected_code in test_cases:
            wrapped = wrap_sdk_error(original_error)
            extracted_code = get_error_code(wrapped)
            assert extracted_code == expected_code


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_none_value_error(self):
        """Test handling of errors with None values."""
        exc = Exception("None")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, TypedError)
        assert get_error_code(wrapped) == ErrorCode.UNKNOWN

    def test_unicode_error_message(self):
        """Test handling of unicode characters in error messages."""
        exc = Exception("invalid_api_key: 🔑 key is invalid")
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, AuthError)
        assert "🔑" in str(wrapped) or "key is invalid" in str(wrapped)

    def test_very_long_error_message(self):
        """Test handling of very long error messages."""
        long_msg = "invalid_api_key: " + "x" * 10000
        exc = Exception(long_msg)
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, AuthError)
        assert get_error_code(wrapped) == ErrorCode.AUTH_INVALID

    def test_multiline_error_message(self):
        """Test handling of multiline error messages."""
        exc = Exception(
            """Authentication failed
    Status: 401 Unauthorized
    Reason: invalid_api_key"""
        )
        wrapped = wrap_sdk_error(exc)

        assert isinstance(wrapped, AuthError)
        assert get_error_code(wrapped) == ErrorCode.AUTH_INVALID

    def test_case_insensitive_pattern_matching(self):
        """Test that pattern matching is case-insensitive."""
        test_cases = [
            "INVALID_API_KEY",
            "Invalid_Api_Key",
            "INVALID_api_KEY",
            "iNvAlId_aPi_KeY",
        ]

        for msg in test_cases:
            exc = Exception(msg)
            wrapped = wrap_sdk_error(exc)
            assert isinstance(wrapped, AuthError)
