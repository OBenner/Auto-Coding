#!/usr/bin/env python3
"""Verification script for typed error imports in session.py"""

import sys

# Add backend to path
sys.path.insert(0, 'apps/backend')

try:
    from agents.session import run_agent_session, run_agent_session_isolated
    print("✓ session.py imports successfully")

    # Check that the module has the expected functions
    assert callable(run_agent_session), "run_agent_session should be callable"
    assert callable(run_agent_session_isolated), "run_agent_session_isolated should be callable"
    print("✓ Session functions are callable")

    # Verify typed errors are imported in the module
    import agents.session as session_module
    import inspect
    source = inspect.getsource(session_module)

    # Check for typed error imports
    assert 'from core.typed_errors import' in source, "Should import from core.typed_errors"
    assert 'AuthError' in source, "Should import AuthError"
    assert 'NetworkError' in source, "Should import NetworkError"
    assert 'NotFoundError' in source, "Should import NotFoundError"
    assert 'TimeoutError' in source, "Should import TimeoutError"
    assert 'TypedError' in source, "Should import TypedError"
    print("✓ Typed errors are imported")

    # Check for typed error usage
    assert 'raise TypedError(ErrorCode.MEMORY_ERROR' in source, "Should raise TypedError for memory errors"
    assert 'raise NetworkError' in source, "Should raise NetworkError for circuit breaker"
    assert 'raise TimeoutError' in source, "Should raise TimeoutError for session bounds"
    assert 'raise NotFoundError' in source, "Should raise NotFoundError for missing files"
    assert 'raise AuthError' in source, "Should raise AuthError for auth failures"
    print("✓ Typed errors are raised in appropriate places")

    print("\n✓ All verifications passed!")
    sys.exit(0)

except Exception as e:
    print(f"✗ Verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
