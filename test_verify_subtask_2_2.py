#!/usr/bin/env python
"""Verification script for subtask 2-2"""

from core.error_utils import is_authentication_error, is_rate_limit_error
from core.typed_errors import AuthError, RateLimitError


def main():
    # Test RateLimitError detection
    rate_limit_err = RateLimitError("Test rate limit error")
    if not is_rate_limit_error(rate_limit_err):
        print("FAIL: RateLimitError not detected")
        exit(1)

    # Test AuthError detection
    auth_err = AuthError("Test auth error")
    if not is_authentication_error(auth_err):
        print("FAIL: AuthError not detected")
        exit(1)

    # Test backward compatibility with string-based errors
    string_rate_limit = Exception("429 rate limit exceeded")
    if not is_rate_limit_error(string_rate_limit):
        print("FAIL: String-based rate limit error not detected")
        exit(1)

    string_auth_err = Exception("401 unauthorized")
    if not is_authentication_error(string_auth_err):
        print("FAIL: String-based auth error not detected")
        exit(1)

    # Test that non-matching errors return False
    generic_error = Exception("some other error")
    if is_rate_limit_error(generic_error):
        print("FAIL: Generic error incorrectly identified as rate limit error")
        exit(1)

    if is_authentication_error(generic_error):
        print("FAIL: Generic error incorrectly identified as auth error")
        exit(1)

    print("OK: All verification tests passed")


if __name__ == "__main__":
    main()
