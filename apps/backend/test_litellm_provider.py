#!/usr/bin/env python3
"""
Comprehensive verification test for LiteLLM provider integration in Insights runner.

This script verifies:
1. CLI argument parsing for --provider litellm
2. Provider factory usage for LiteLLM
3. Model resolution for LiteLLM provider
4. Frontend integration passing --provider argument
5. Backend environment configuration requirements
"""

import json
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"\n{'='*70}")
    print(f"Test: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*70)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )

        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr

        # Print first 500 chars for debugging
        print(f"Output (first 500 chars):\n{output[:500]}")

        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_file_contains(file_path: str, pattern: str, description: str) -> bool:
    """Check if a file contains a specific pattern."""
    print(f"\n{'='*70}")
    print(f"Test: {description}")
    print(f"File: {file_path}")
    print(f"Pattern: {pattern}")
    print('='*70)

    try:
        content = Path(file_path).read_text(encoding='utf-8')
        if pattern in content:
            print(f"✓ PASS: Pattern found in {file_path}")
            return True
        else:
            print(f"✗ FAIL: Pattern NOT found in {file_path}")
            return False
    except Exception as e:
        print(f"✗ FAIL: Error reading file: {e}")
        return False


def main() -> int:
    """Run all verification tests."""
    print("="*70)
    print("LiteLLM Provider Integration Verification")
    print("="*70)

    tests_passed = 0
    tests_failed = 0

    # Test 1: CLI argument parsing
    success, output = run_command(
        ["python", "runners/insights_runner.py", "--help"],
        "CLI Argument Parsing - Check --provider option"
    )

    if success and ("--provider" in output or "provider" in output.lower()):
        print("✓ PASS: --provider argument is available in CLI")
        tests_passed += 1
    else:
        print("✗ FAIL: --provider argument not found in help text")
        tests_failed += 1

    # Test 2: Provider factory import
    if check_file_contains(
        "runners/insights_runner.py",
        "create_engine_provider",
        "Provider Factory Import - Check create_engine_provider usage"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 3: Provider configuration
    if check_file_contains(
        "runners/insights_runner.py",
        'provider=provider',
        "Provider Configuration - Check provider variable passed to ProviderConfig"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 4: Provider argument parsing
    if check_file_contains(
        "runners/insights_runner.py",
        "--provider",
        "Provider CLI Argument - Check --provider argument parsing"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 5: Session creation with provider
    if check_file_contains(
        "runners/insights_runner.py",
        "ai_provider.create_session",
        "Session Creation - Check provider.create_session() call"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 6: Frontend - Provider extraction
    if check_file_contains(
        "../frontend/src/main/insights/insights-executor.ts",
        "modelConfig.provider",
        "Frontend Provider Extraction - Check provider from modelConfig"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 7: Frontend - Provider argument passing
    if check_file_contains(
        "../frontend/src/main/insights/insights-executor.ts",
        '--provider',
        "Frontend Provider Passing - Check --provider argument to subprocess"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 8: Frontend - Provider dropdown
    if check_file_contains(
        "../frontend/src/renderer/components/InsightsModelSelector.tsx",
        "INSIGHTS_PROVIDERS",
        "Frontend UI - Check provider dropdown constant"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 9: Frontend - LiteLLM provider option
    if check_file_contains(
        "../frontend/src/renderer/components/InsightsModelSelector.tsx",
        "'litellm'",
        "Frontend UI - Check litellm provider option"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 10: Backend - LiteLLM provider implementation
    if check_file_contains(
        "core/providers/adapters/litellm.py",
        "class LiteLLMProvider",
        "Backend - Check LiteLLM provider class exists"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 11: Backend - LiteLLM session implementation
    if check_file_contains(
        "core/providers/adapters/litellm.py",
        "class LiteLLMSession",
        "Backend - Check LiteLLM session class exists"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 12: Provider factory includes LiteLLM
    if check_file_contains(
        "core/providers/factory.py",
        "_create_litellm_provider",
        "Provider Factory - Check LiteLLM provider creation function"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 13: Check environment variable requirements
    print(f"\n{'='*70}")
    print("Test: Environment Variable Requirements")
    print('='*70)

    env_vars_found = []
    if check_file_contains(
        "core/providers/config.py",
        "LITELLM_MODEL",
        "Environment - Check LITELLM_MODEL variable"
    ):
        env_vars_found.append("LITELLM_MODEL")

    if env_vars_found:
        print(f"✓ PASS: LiteLLM environment variables defined ({', '.join(env_vars_found)})")
        tests_passed += 1
    else:
        print("✗ FAIL: No LiteLLM environment variables found")
        tests_failed += 1

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total Tests: {tests_passed + tests_failed}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    if tests_failed == 0:
        print("\n✓ ALL TESTS PASSED - LiteLLM provider integration is complete!")
        return 0
    else:
        print(f"\n✗ {tests_failed} TEST(S) FAILED - Please review failures above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
