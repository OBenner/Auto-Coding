#!/usr/bin/env python3
"""Verify test setup for collaboration E2E tests."""

import sys
from pathlib import Path

# Add apps/backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def check_dependencies():
    """Check if required dependencies are available."""
    print("Checking dependencies...")

    missing = []

    # Check websockets
    try:
        import websockets
        print("  ✓ websockets is installed")
    except ImportError:
        print("  ✗ websockets is NOT installed")
        missing.append("websockets")

    # Check pytest
    try:
        import pytest
        print(f"  ✓ pytest is installed (version {pytest.__version__})")
    except ImportError:
        print("  ✗ pytest is NOT installed")
        missing.append("pytest")

    # Check pytest-asyncio
    try:
        import pytest_asyncio
        print("  ✓ pytest-asyncio is installed")
    except ImportError:
        print("  ✗ pytest-asyncio is NOT installed")
        missing.append("pytest-asyncio")

    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install websockets pytest pytest-asyncio")
        return False

    print("\n✅ All dependencies are installed")
    return True


def check_collaboration_module():
    """Check if collaboration module can be imported."""
    print("\nChecking collaboration module...")

    try:
        from collaboration import server, models, crdt_store, comments
        print("  ✓ collaboration.server")
        print("  ✓ collaboration.models")
        print("  ✓ collaboration.crdt_store")
        print("  ✓ collaboration.comments")
        print("\n✅ Collaboration module imports successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed to import collaboration module: {e}")
        return False


def check_test_files():
    """Check if test files exist."""
    print("\nChecking test files...")

    tests_dir = Path(__file__).parent
    required_files = [
        "conftest.py",
        "test_collaboration_e2e.py",
        "run_e2e_tests.py",
    ]

    all_exist = True
    for filename in required_files:
        filepath = tests_dir / filename
        if filepath.exists():
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} NOT found")
            all_exist = False

    if all_exist:
        print("\n✅ All test files exist")
    else:
        print("\n❌ Some test files are missing")

    return all_exist


def main():
    """Run all checks."""
    print("=" * 60)
    print("Collaboration E2E Test Setup Verification")
    print("=" * 60)

    checks = [
        check_dependencies(),
        check_collaboration_module(),
        check_test_files(),
    ]

    print("\n" + "=" * 60)
    if all(checks):
        print("✅ ALL CHECKS PASSED - Tests are ready to run!")
        print("=" * 60)
        print("\nRun tests with:")
        print("  pytest apps/backend/tests/collaboration/test_collaboration_e2e.py -v")
        print("\nOr use the test runner:")
        print("  python apps/backend/tests/collaboration/run_e2e_tests.py -v")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Please fix the issues above")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
