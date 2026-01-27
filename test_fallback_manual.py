#!/usr/bin/env python3
"""
Manual test script for model fallback behavior.
Tests fallback by simulating model unavailability.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

# Configure logging to see fallback messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s %(message)s'
)

from core.model_fallback import retry_with_fallback, MODEL_FALLBACK_CHAIN


def test_rate_limit_fallback():
    """Test fallback when opus hits rate limit."""
    print("\n" + "="*60)
    print("TEST 1: Rate limit error triggers fallback")
    print("="*60)

    call_count = 0

    def mock_api_call(model: str):
        nonlocal call_count
        call_count += 1

        if "opus" in model.lower():
            print(f"  ❌ Simulating rate limit error for {model}")
            raise Exception("RateLimitError: 429 Too Many Requests - opus unavailable")

        print(f"  ✅ {model} succeeded!")
        return f"Success with {model}"

    try:
        result = retry_with_fallback(mock_api_call, "opus", max_retries_per_model=1)
        print(f"\n✅ PASS: Fallback successful - {result}")
        assert "sonnet" in result.lower(), "Should fall back to sonnet"
        return True
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        return False


def test_connection_error_fallback():
    """Test fallback when connection error occurs."""
    print("\n" + "="*60)
    print("TEST 2: Connection error triggers fallback")
    print("="*60)

    def mock_api_call(model: str):
        if "opus" in model.lower():
            print(f"  ❌ Simulating connection timeout for {model}")
            raise ConnectionError("Connection timeout")

        print(f"  ✅ {model} succeeded!")
        return f"Success with {model}"

    try:
        result = retry_with_fallback(mock_api_call, "opus", max_retries_per_model=1)
        print(f"\n✅ PASS: Fallback successful - {result}")
        assert "sonnet" in result.lower(), "Should fall back to sonnet"
        return True
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        return False


def test_complete_fallback_chain():
    """Test complete fallback chain: opus -> sonnet -> haiku."""
    print("\n" + "="*60)
    print("TEST 3: Complete fallback chain (opus -> sonnet -> haiku)")
    print("="*60)

    def mock_api_call(model: str):
        if "opus" in model.lower():
            print(f"  ❌ opus unavailable (rate limit)")
            raise Exception("RateLimitError: opus unavailable")
        elif "sonnet" in model.lower():
            print(f"  ❌ sonnet unavailable (overloaded)")
            raise Exception("503 Service Temporarily Unavailable - sonnet overloaded")

        print(f"  ✅ haiku succeeded!")
        return f"Success with {model}"

    try:
        result = retry_with_fallback(mock_api_call, "opus", max_retries_per_model=1)
        print(f"\n✅ PASS: Complete fallback successful - {result}")
        assert "haiku" in result.lower(), "Should fall back to haiku"
        return True
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        return False


def test_non_retryable_error():
    """Test that non-retryable errors raise immediately without fallback."""
    print("\n" + "="*60)
    print("TEST 4: Non-retryable errors don't trigger fallback")
    print("="*60)

    def mock_api_call(model: str):
        print(f"  ❌ Simulating non-retryable error (invalid request)")
        raise ValueError("Invalid request format")

    try:
        result = retry_with_fallback(mock_api_call, "opus", max_retries_per_model=1)
        print(f"\n❌ FAIL: Should have raised ValueError, got result: {result}")
        return False
    except ValueError as e:
        print(f"\n✅ PASS: Non-retryable error raised immediately - {e}")
        return True
    except Exception as e:
        print(f"\n❌ FAIL: Wrong exception type: {e}")
        return False


def test_all_models_exhausted():
    """Test that all models exhausted raises final exception."""
    print("\n" + "="*60)
    print("TEST 5: All models exhausted raises exception")
    print("="*60)

    def mock_api_call(model: str):
        print(f"  ❌ {model} unavailable")
        raise Exception(f"RateLimitError: {model} unavailable")

    try:
        result = retry_with_fallback(mock_api_call, "opus", max_retries_per_model=1)
        print(f"\n❌ FAIL: Should have raised exception, got result: {result}")
        return False
    except Exception as e:
        print(f"\n✅ PASS: All models exhausted, final exception raised - {e}")
        return True


def test_sonnet_to_haiku_fallback():
    """Test fallback from sonnet (not starting with opus)."""
    print("\n" + "="*60)
    print("TEST 6: Fallback from sonnet to haiku")
    print("="*60)

    def mock_api_call(model: str):
        if "sonnet" in model.lower():
            print(f"  ❌ sonnet unavailable")
            raise Exception("RateLimitError: sonnet unavailable")

        print(f"  ✅ haiku succeeded!")
        return f"Success with {model}"

    try:
        result = retry_with_fallback(mock_api_call, "sonnet", max_retries_per_model=1)
        print(f"\n✅ PASS: Fallback successful - {result}")
        assert "haiku" in result.lower(), "Should fall back to haiku"
        return True
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        return False


def main():
    """Run all fallback tests."""
    print("\n" + "="*60)
    print("MODEL FALLBACK BEHAVIOR TEST SUITE")
    print("="*60)
    print(f"\nFallback chain configuration:")
    for model, fallbacks in MODEL_FALLBACK_CHAIN.items():
        print(f"  {model:8} -> {' -> '.join(fallbacks) if fallbacks else '(no fallback)'}")

    # Run all tests
    tests = [
        test_rate_limit_fallback,
        test_connection_error_fallback,
        test_complete_fallback_chain,
        test_non_retryable_error,
        test_all_models_exhausted,
        test_sonnet_to_haiku_fallback,
    ]

    results = []
    for test in tests:
        try:
            passed = test()
            results.append((test.__name__, passed))
        except Exception as e:
            print(f"\n❌ TEST EXCEPTION: {test.__name__} - {e}")
            results.append((test.__name__, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n✅ ALL TESTS PASSED - Fallback behavior verified successfully!")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
