"""
Unit tests for agents/tools_pkg/models.py — SearXNG integration
"""

import os
from unittest.mock import patch


class TestIsSearxngEnabled:
    """Tests for is_searxng_enabled() with proper env isolation."""

    def test_enabled_when_true(self):
        """Returns True when SEARXNG_ENABLED=true."""
        with patch.dict(os.environ, {"SEARXNG_ENABLED": "true"}):
            from agents.tools_pkg.models import is_searxng_enabled

            assert is_searxng_enabled() is True

    def test_disabled_when_false(self):
        """Returns False when SEARXNG_ENABLED=false."""
        with patch.dict(os.environ, {"SEARXNG_ENABLED": "false"}):
            from agents.tools_pkg.models import is_searxng_enabled

            assert is_searxng_enabled() is False

    def test_disabled_when_unset(self):
        """Returns False when SEARXNG_ENABLED is not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SEARXNG_ENABLED", None)
            from agents.tools_pkg.models import is_searxng_enabled

            assert is_searxng_enabled() is False

    def test_case_insensitive(self):
        """Handles case-insensitive values."""
        with patch.dict(os.environ, {"SEARXNG_ENABLED": "True"}):
            from agents.tools_pkg.models import is_searxng_enabled

            assert is_searxng_enabled() is True


class TestSearxngConstants:
    """Tests for SearXNG-related constants."""

    def test_searxng_tools_constant(self):
        """SEARXNG_TOOLS contains expected tool names."""
        from agents.tools_pkg.models import SEARXNG_TOOLS

        assert SEARXNG_TOOLS == [
            "mcp__searxng__web_search",
            "mcp__searxng__read_url",
        ]

    def test_map_mcp_server_name_searxng(self):
        """_map_mcp_server_name maps searxng correctly (case-insensitive)."""
        from agents.tools_pkg.models import _map_mcp_server_name

        assert _map_mcp_server_name("searxng") == "searxng"
        assert _map_mcp_server_name("SEARXNG") == "searxng"
        assert _map_mcp_server_name("SearXNG") == "searxng"


class TestSearxngServerActivation:
    """Integration tests verifying SearXNG is wired into server selection."""

    def test_searxng_added_to_servers_when_enabled(self):
        """get_required_mcp_servers includes 'searxng' when SEARXNG_ENABLED=true."""
        with patch.dict(os.environ, {"SEARXNG_ENABLED": "true"}):
            from agents.tools_pkg.models import get_required_mcp_servers

            servers = get_required_mcp_servers("coder")
            assert "searxng" in servers

    def test_searxng_absent_when_disabled(self):
        """get_required_mcp_servers excludes 'searxng' when SEARXNG_ENABLED is not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SEARXNG_ENABLED", None)
            from agents.tools_pkg.models import get_required_mcp_servers

            servers = get_required_mcp_servers("coder")
            assert "searxng" not in servers
