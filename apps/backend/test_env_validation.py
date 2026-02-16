#!/usr/bin/env python
"""
Test script for environment variable validation functions.
Tests the real validation logic from core.client for Electron MCP environment variables.
"""

import os
import sys
from pathlib import Path

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.client import (
    get_electron_debug_port,
    get_electron_mcp_log_level,
    get_electron_mcp_mode,
)


def test_get_electron_mcp_mode():
    """Test get_electron_mcp_mode validation."""
    print("Testing get_electron_mcp_mode()...")

    # Test 1: Valid mode
    os.environ["ELECTRON_MCP_MODE"] = "embedded"
    assert get_electron_mcp_mode() == "embedded", "Valid mode test failed"
    print("  ✓ Valid mode (embedded)")

    # Test 2: Valid mode (cdp)
    os.environ["ELECTRON_MCP_MODE"] = "cdp"
    assert get_electron_mcp_mode() == "cdp", "Valid mode test failed"
    print("  ✓ Valid mode (cdp)")

    # Test 3: Invalid mode (should default to cdp)
    os.environ["ELECTRON_MCP_MODE"] = "invalid"
    assert get_electron_mcp_mode() == "cdp", "Invalid mode test failed"
    print("  ✓ Invalid mode defaults to cdp")

    # Test 4: Case insensitive
    os.environ["ELECTRON_MCP_MODE"] = "EMBEDDED"
    assert get_electron_mcp_mode() == "embedded", "Case insensitive test failed"
    print("  ✓ Case insensitive (EMBEDDED -> embedded)")

    # Test 5: Not set (should default to cdp)
    if "ELECTRON_MCP_MODE" in os.environ:
        del os.environ["ELECTRON_MCP_MODE"]
    assert get_electron_mcp_mode() == "cdp", "Default mode test failed"
    print("  ✓ Not set defaults to cdp")


def test_get_electron_mcp_log_level():
    """Test get_electron_mcp_log_level validation."""
    print("\nTesting get_electron_mcp_log_level()...")

    # Test 1: Valid log level
    for level in ["debug", "info", "warn", "error"]:
        os.environ["ELECTRON_MCP_LOG_LEVEL"] = level
        assert get_electron_mcp_log_level() == level, (
            f"Valid log level test failed for {level}"
        )
        print(f"  ✓ Valid log level ({level})")

    # Test 2: Invalid log level (should default to info)
    os.environ["ELECTRON_MCP_LOG_LEVEL"] = "invalid"
    assert get_electron_mcp_log_level() == "info", "Invalid log level test failed"
    print("  ✓ Invalid log level defaults to info")

    # Test 3: Case insensitive
    os.environ["ELECTRON_MCP_LOG_LEVEL"] = "DEBUG"
    assert get_electron_mcp_log_level() == "debug", "Case insensitive test failed"
    print("  ✓ Case insensitive (DEBUG -> debug)")

    # Test 4: Not set (should default to info)
    if "ELECTRON_MCP_LOG_LEVEL" in os.environ:
        del os.environ["ELECTRON_MCP_LOG_LEVEL"]
    assert get_electron_mcp_log_level() == "info", "Default log level test failed"
    print("  ✓ Not set defaults to info")


def test_get_electron_debug_port():
    """Test get_electron_debug_port validation."""
    print("\nTesting get_electron_debug_port()...")

    # Test 1: Valid port
    os.environ["ELECTRON_DEBUG_PORT"] = "9223"
    assert get_electron_debug_port() == 9223, "Valid port test failed"
    print("  ✓ Valid port (9223)")

    # Test 2: Default port
    if "ELECTRON_DEBUG_PORT" in os.environ:
        del os.environ["ELECTRON_DEBUG_PORT"]
    assert get_electron_debug_port() == 9222, "Default port test failed"
    print("  ✓ Not set defaults to 9222")

    # Test 3: Invalid port (non-numeric)
    os.environ["ELECTRON_DEBUG_PORT"] = "invalid"
    try:
        get_electron_debug_port()
        raise AssertionError("Should have raised ValueError for non-numeric port")
    except ValueError as e:
        assert "Must be a number" in str(e)
        print("  ✓ Non-numeric port raises ValueError")

    # Test 4: Invalid port (out of range - too low)
    os.environ["ELECTRON_DEBUG_PORT"] = "1023"
    try:
        get_electron_debug_port()
        raise AssertionError("Should have raised ValueError for port < 1024")
    except ValueError as e:
        assert "Must be between 1024 and 65535" in str(e)
        print("  ✓ Port < 1024 raises ValueError")

    # Test 5: Invalid port (out of range - too high)
    os.environ["ELECTRON_DEBUG_PORT"] = "65536"
    try:
        get_electron_debug_port()
        raise AssertionError("Should have raised ValueError for port > 65535")
    except ValueError as e:
        assert "Must be between 1024 and 65535" in str(e)
        print("  ✓ Port > 65535 raises ValueError")


if __name__ == "__main__":
    print("=" * 60)
    print("Environment Variable Validation Tests")
    print("=" * 60)

    try:
        test_get_electron_mcp_mode()
        test_get_electron_mcp_log_level()
        test_get_electron_debug_port()

        print("\n" + "=" * 60)
        print("All validation tests passed!")
        print("=" * 60)
        sys.exit(0)

    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
