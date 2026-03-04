#!/usr/bin/env python3
"""
Test script for auto-fix generation functionality.
"""

import sys
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.predictive_scanner import PredictiveIssue, generate_auto_fix


def test_auto_fix_generation():
    """Test auto-fix generation for a sample issue."""

    # Create a sample issue
    sample_issue = PredictiveIssue(
        issue_type="bug",
        severity="critical",
        category="NoneType error",
        source="bug_detector",
        title="Potential attribute access on None value",
        description="Variable 'user' may be None when accessing 'user.id'",
        file="apps/backend/auth/middleware.py",
        line=42,
        code_snippet="""def get_user_id(request):
    user = get_user(request)
    user_id = user.id  # Line 42: user may be None
    return user_id""",
        suggestion="Add null check before accessing user.id",
        confidence=0.9,
    )

    print("=" * 60)
    print("Testing Auto-Fix Generation")
    print("=" * 60)
    print(f"\nIssue: {sample_issue.title}")
    print(f"Category: {sample_issue.category}")
    print(f"File: {sample_issue.file}:{sample_issue.line}")
    print("\nCode Snippet:")
    print("-" * 60)
    print(sample_issue.code_snippet)
    print("-" * 60)

    print("\nGenerating auto-fix...")
    auto_fix = generate_auto_fix(sample_issue)

    if auto_fix:
        print("\n✅ Auto-fix generated successfully!")
        print(f"\nFix Type: {auto_fix.get('fix_type')}")
        print(f"Description: {auto_fix.get('description')}")
        print(f"Scope: {auto_fix.get('scope')}")
        print(f"Confidence: {auto_fix.get('confidence', 0):.2%}")

        print("\nOriginal Code:")
        print("-" * 60)
        print(auto_fix.get("original_code"))
        print("-" * 60)

        print("\nFixed Code:")
        print("-" * 60)
        print(auto_fix.get("fixed_code"))
        print("-" * 60)

        if auto_fix.get("risks"):
            print("\nRisks:")
            for risk in auto_fix.get("risks", []):
                print(f"  - {risk}")

        if auto_fix.get("testing_advice"):
            print("\nTesting Advice:")
            print(f"  {auto_fix.get('testing_advice')}")

        if auto_fix.get("alternate_fixes"):
            print("\nAlternate Fixes:")
            for alt in auto_fix.get("alternate_fixes", []):
                print(f"  - Approach: {alt.get('approach')}")
                print(f"    When to use: {alt.get('when_to_use')}")

        return True
    else:
        print("\n❌ Auto-fix generation failed")
        print("\nPossible reasons:")
        print("  - Claude SDK not available")
        print("  - No authentication token found")
        print("  - LLM parsing failed")
        print("  - Network/API error")
        return False


if __name__ == "__main__":
    success = test_auto_fix_generation()
    sys.exit(0 if success else 1)
