"""
Unit tests for agents/tools_pkg/models.py
"""
import os
import pytest


def test_is_searxng_enabled_true():
    """Test that is_searxng_enabled returns True when SEARXNG_ENABLED=true"""
    # Save original value
    original = os.environ.get("SEARXNG_ENABLED")
    try:
        os.environ["SEARXNG_ENABLED"] = "true"
        from agents.tools_pkg.models import is_searxng_enabled
        assert is_searxng_enabled() is True
    finally:
        # Restore original value
        if original is None:
            os.environ.pop("SEARXNG_ENABLED", None)
        else:
            os.environ["SEARXNG_ENABLED"] = original


def test_is_searxng_enabled_false():
    """Test that is_searxng_enabled returns False when unset or false"""
    from agents.tools_pkg.models import is_searxng_enabled

    # Test unset
    original = os.environ.get("SEARXNG_ENABLED")
    try:
        os.environ.pop("SEARXNG_ENABLED", None)
        assert is_searxng_enabled() is False

        # Test explicit false
        os.environ["SEARXNG_ENABLED"] = "false"
        assert is_searxng_enabled() is False
    finally:
        if original is not None:
            os.environ["SEARXNG_ENABLED"] = original


def test_searxng_tools_constant():
    """Test that SEARXNG_TOOLS contains expected tool names"""
    from agents.tools_pkg.models import SEARXNG_TOOLS

    expected_tools = [
        "mcp__searxng__web_search",
        "mcp__searxng__read_url",
    ]

    assert SEARXNG_TOOLS == expected_tools


def test_map_mcp_server_searxng():
    """Test that _map_mcp_server_name maps searxng correctly"""
    from agents.tools_pkg.models import _map_mcp_server_name

    assert _map_mcp_server_name("searxng") == "searxng"
    assert _map_mcp_server_name("SEARXNG") == "searxng"  # Case-insensitive
    assert _map_mcp_server_name("SearXNG") == "searxng"  # Case-insensitive
