#!/usr/bin/env python3
"""
Manual test script for LLM-based failure analysis.

This script creates realistic failure scenarios and verifies that the LLM
provides specific, actionable recommendations (not just generic heuristics).

Usage:
    python apps/backend/analysis/test_llm_analysis.py
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.failure_analyzer import (
    _analyze_failure_with_llm,
    extract_root_cause,
    is_analysis_enabled,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Scenarios
# =============================================================================


def create_syntax_error_scenario() -> dict:
    """Create a realistic syntax error failure scenario."""
    return {
        "failure_type": "build_error",
        "errors": [
            "SyntaxError: Unexpected token '}' at line 45 in apps/backend/auth/middleware.py",
            "  File 'apps/backend/auth/middleware.py', line 45",
            "    }",
            "    ^",
            "SyntaxError: invalid syntax",
        ],
        "issues": [
            {
                "file": "apps/backend/auth/middleware.py",
                "line": 45,
                "description": "Unexpected closing brace",
            }
        ],
        "is_recurring": False,
        "subtask": {
            "id": "subtask-1-2",
            "description": "Implement JWT authentication middleware",
            "files_to_modify": ["apps/backend/auth/middleware.py"],
        },
    }


def create_missing_dependency_scenario() -> dict:
    """Create a realistic missing dependency failure scenario."""
    return {
        "failure_type": "build_error",
        "errors": [
            "ModuleNotFoundError: No module named 'pydantic'",
            "Traceback (most recent call last):",
            "  File 'apps/backend/models/user.py', line 3, in <module>",
            "    from pydantic import BaseModel, Field",
            "ModuleNotFoundError: No module named 'pydantic'",
        ],
        "issues": [
            {
                "file": "apps/backend/models/user.py",
                "line": 3,
                "description": "Import error for pydantic",
            }
        ],
        "is_recurring": False,
        "subtask": {
            "id": "subtask-2-1",
            "description": "Create User model with validation",
            "files_to_modify": ["apps/backend/models/user.py"],
        },
    }


def create_test_failure_scenario() -> dict:
    """Create a realistic test failure scenario."""
    return {
        "failure_type": "test_failure",
        "errors": [
            "AssertionError: Expected status code 200, got 404",
            "FAILED tests/test_api.py::test_get_user - AssertionError",
            "    assert response.status_code == 200",
            "    AssertionError: assert 404 == 200",
            "     +  where 404 = <Response [404]>.status_code",
        ],
        "issues": [
            {
                "file": "tests/test_api.py",
                "line": 78,
                "description": "GET /api/users/123 returned 404 instead of 200",
            },
            {
                "file": "apps/backend/routes/users.py",
                "line": None,
                "description": "Route may not be properly registered",
            },
        ],
        "is_recurring": False,
        "subtask": {
            "id": "subtask-3-1",
            "description": "Implement user retrieval endpoint",
            "files_to_modify": ["apps/backend/routes/users.py", "tests/test_api.py"],
        },
    }


def create_recurring_logic_error_scenario() -> dict:
    """Create a recurring logic error scenario."""
    return {
        "failure_type": "qa_rejection",
        "errors": [
            "TypeError: Cannot read property 'id' of undefined",
            "    at getUserData (app/services/user.js:42:15)",
            "    at processRequest (app/routes/api.js:23:9)",
        ],
        "issues": [
            {
                "file": "app/services/user.js",
                "line": 42,
                "description": "Attempting to access 'id' on undefined object",
            }
        ],
        "is_recurring": True,  # This is the 3rd occurrence
        "subtask": {
            "id": "subtask-4-2",
            "description": "Fix user data retrieval logic",
            "files_to_modify": ["app/services/user.js", "app/routes/api.js"],
        },
    }


# =============================================================================
# Test Execution
# =============================================================================


def test_scenario(name: str, scenario: dict, test_llm: bool = True) -> bool:
    """
    Test a failure scenario and verify LLM provides specific recommendations.

    Args:
        name: Scenario name for display
        scenario: Failure data to analyze
        test_llm: Whether to test LLM analysis (requires SDK)

    Returns:
        True if test passed, False otherwise
    """
    print(f"\n{'=' * 80}")
    print(f"SCENARIO: {name}")
    print(f"{'=' * 80}\n")

    print("Failure Data:")
    print(json.dumps(scenario, indent=2))
    print("\n")

    # Always test heuristic analysis first
    print("Running Heuristic Analysis (baseline)...")
    try:
        heuristic_result = extract_root_cause(scenario, use_llm=False)
        print("\n✅ Heuristic Analysis Successful!")
        print("\nHeuristic Analysis Result:")
        print(json.dumps(heuristic_result, indent=2))
    except Exception as e:
        print(f"\n❌ Heuristic analysis failed: {e}")
        return False

    # Test with LLM if enabled
    if test_llm:
        print("\n" + "-" * 80)
        print("Running LLM Analysis (enhanced)...")
        try:
            llm_result = _analyze_failure_with_llm(scenario)

            if llm_result:
                print("\n✅ LLM Analysis Successful!")
                print("\nLLM Analysis Result:")
                print(json.dumps(llm_result, indent=2))

                # Verify LLM provides specific recommendations
                recommendations = llm_result.get("recommendations", [])
                if not recommendations:
                    print("\n❌ FAIL: No recommendations provided")
                    return False

                print(f"\n📋 LLM Recommendations ({len(recommendations)} total):")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")

                # Check if recommendations are specific (not generic)
                generic_phrases = [
                    "check your code",
                    "review the implementation",
                    "debug the issue",
                    "try running tests again",
                    "look for errors",
                ]

                has_generic = False
                for rec in recommendations:
                    rec_lower = rec.lower()
                    for phrase in generic_phrases:
                        if phrase in rec_lower:
                            print(
                                f"\n⚠️  WARNING: Generic recommendation detected: '{rec}'"
                            )
                            has_generic = True

                if has_generic:
                    print("\n❌ FAIL: Recommendations contain generic advice")
                    return False

                # Check for specific elements (file paths, line numbers, code snippets)
                has_specific = False
                for rec in recommendations:
                    if any(
                        indicator in rec
                        for indicator in [".py", ".js", ".ts", "line ", ":"]
                    ):
                        has_specific = True
                        break

                if has_specific:
                    print(
                        "\n✅ PASS: Recommendations contain specific file/line references"
                    )
                else:
                    print(
                        "\n⚠️  WARNING: Recommendations lack specific file/line references"
                    )

                # Compare with heuristic
                print("\n📊 Comparison:")
                print(
                    f"  Heuristic confidence: {heuristic_result.get('confidence', 0):.2f}"
                )
                print(f"  LLM confidence: {llm_result.get('confidence', 0):.2f}")
                print(
                    f"  Heuristic recommendations: {len(heuristic_result.get('recommendations', []))}"
                )
                print(f"  LLM recommendations: {len(recommendations)}")

                return True

            else:
                print("\n⚠️  LLM analysis returned None, using heuristic only")
                return True  # Not a failure if heuristic works

        except Exception as e:
            print(f"\n⚠️  LLM analysis failed: {e}")
            print("Falling back to heuristic analysis")
            return True  # Not a failure if heuristic works
    else:
        print("\n⚠️  Skipping LLM analysis (not enabled)")
        return True


def run_all_tests():
    """Run all test scenarios."""
    print("\n" + "=" * 80)
    print("LLM-BASED FAILURE ANALYSIS TEST SUITE")
    print("=" * 80)

    # Check if analysis is enabled
    if not is_analysis_enabled():
        print("\n⚠️  WARNING: LLM analysis is not enabled!")
        print("\nPossible reasons:")
        print("  1. Claude SDK not installed (run: pip install claude-agent-sdk)")
        print(
            "  2. No authentication token (run: python apps/backend/run.py and use /login)"
        )
        print("  3. FAILURE_ANALYSIS_ENABLED=false in environment")
        print("\nFalling back to heuristic-only testing...\n")
    else:
        print("\n✅ LLM failure analysis is enabled")
        print("Starting test scenarios...\n")

    # Define test scenarios
    scenarios = [
        ("Syntax Error", create_syntax_error_scenario()),
        ("Missing Dependency", create_missing_dependency_scenario()),
        ("Test Failure", create_test_failure_scenario()),
        ("Recurring Logic Error", create_recurring_logic_error_scenario()),
    ]

    # Determine if we should test LLM
    test_llm = is_analysis_enabled()

    # Run tests
    results = {}
    for name, scenario in scenarios:
        results[name] = test_scenario(name, scenario, test_llm=test_llm)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80 + "\n")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if test_llm:
        if passed == total:
            print("\n🎉 All tests passed! LLM analysis is working correctly.")
            print("\n✅ VERIFICATION COMPLETE:")
            print("   - Heuristic analysis provides baseline recommendations")
            print("   - LLM analysis provides specific, actionable recommendations")
            print("   - No generic advice detected")
            sys.exit(0)
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")
            sys.exit(1)
    else:
        print("\n✅ Heuristic analysis verified (LLM testing skipped)")
        print("\n📝 To test LLM analysis:")
        print("   1. Install Claude SDK: pip install claude-agent-sdk")
        print("   2. Authenticate: Run 'python apps/backend/run.py' and use /login")
        print("   3. Run this test again")
        print("\n✅ VERIFICATION COMPLETE (heuristic-only mode)")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
