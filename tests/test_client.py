#!/usr/bin/env python3
"""
Tests for Client Creation and Token Validation
===============================================

Tests the client.py and simple_client.py module functionality including:
- Token validation before SDK initialization
- Encrypted token rejection
- Client creation with valid tokens
"""

import importlib
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Auth token env vars that need to be cleared between tests
AUTH_TOKEN_ENV_VARS = [
    "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_AUTH_TOKEN",
]


def _stub_project_context(monkeypatch):
    """Avoid importing heavyweight project-context dependencies in client tests."""
    fake_prompts_pkg = types.ModuleType("prompts_pkg")
    fake_project_context = types.ModuleType("prompts_pkg.project_context")
    fake_project_context.load_project_index = lambda _project_dir: {}
    fake_project_context.detect_project_capabilities = lambda _index: {}
    monkeypatch.setitem(sys.modules, "prompts_pkg", fake_prompts_pkg)
    monkeypatch.setitem(
        sys.modules,
        "prompts_pkg.project_context",
        fake_project_context,
    )


class TestClientTokenValidation:
    """Tests for client token validation."""

    @pytest.fixture(autouse=True)
    def clear_env(self, monkeypatch):
        """Clear auth environment variables before and after each test."""
        _stub_project_context(monkeypatch)
        for var in AUTH_TOKEN_ENV_VARS:
            os.environ.pop(var, None)
        yield
        for var in AUTH_TOKEN_ENV_VARS:
            os.environ.pop(var, None)

    def test_create_client_rejects_encrypted_tokens(self, tmp_path, monkeypatch):
        """Verify create_client() rejects encrypted tokens."""
        from core.client import create_client

        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "enc:test123456789012")
        # Mock keychain to ensure encrypted token is the only source
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)
        # Mock decrypt_token to raise ValueError (simulates decryption failure)
        # This ensures the encrypted token flows through to validate_token_not_encrypted
        monkeypatch.setattr(
            "core.auth.decrypt_token",
            lambda t: (_ for _ in ()).throw(ValueError("Decryption not supported")),
        )

        with pytest.raises(ValueError, match="encrypted format"):
            create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")

    def test_create_simple_client_rejects_encrypted_tokens(self, monkeypatch):
        """Verify create_simple_client() rejects encrypted tokens."""
        from core.simple_client import create_simple_client

        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "enc:test123456789012")
        # Mock keychain to ensure encrypted token is the only source
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)
        # Mock decrypt_token to raise ValueError (simulates decryption failure)
        monkeypatch.setattr(
            "core.auth.decrypt_token",
            lambda t: (_ for _ in ()).throw(ValueError("Decryption not supported")),
        )

        with pytest.raises(ValueError, match="encrypted format"):
            create_simple_client(agent_type="merge_resolver")

    def test_create_client_accepts_valid_plaintext_token(self, tmp_path, monkeypatch):
        """Verify create_client() accepts valid plaintext tokens and creates SDK client."""
        valid_token = "sk-ant-oat01-valid-plaintext-token"
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", valid_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        # Mock the SDK client to avoid actual initialization
        mock_sdk_client = MagicMock()
        with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.client import create_client

            client = create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")

            # Verify SDK client was created
            assert client is mock_sdk_client

    def test_create_simple_client_accepts_valid_plaintext_token(self, monkeypatch):
        """Verify create_simple_client() accepts valid plaintext tokens and creates SDK client."""
        valid_token = "sk-ant-oat01-valid-plaintext-token"
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", valid_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        # Mock the SDK client to avoid actual initialization
        mock_sdk_client = MagicMock()
        with patch("core.simple_client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.simple_client import create_simple_client

            client = create_simple_client(agent_type="merge_resolver")

            # Verify SDK client was created
            assert client is mock_sdk_client

    def test_create_client_validates_token_before_sdk_init(self, tmp_path, monkeypatch):
        """Verify create_client() validates token format before SDK initialization."""
        valid_token = "sk-ant-oat01-valid-token"
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", valid_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        # Mock validate_token_not_encrypted to verify it's called
        with (
            patch("core.client.validate_token_not_encrypted") as mock_validate,
            patch("core.client.ClaudeSDKClient"),
        ):
            from core.client import create_client

            create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")

            # Verify validation was called with the token
            mock_validate.assert_called_once_with(valid_token)

    def test_create_simple_client_validates_token_before_sdk_init(self, monkeypatch):
        """Verify create_simple_client() validates token format before SDK initialization."""
        valid_token = "sk-ant-oat01-valid-token"
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", valid_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        # Mock validate_token_not_encrypted to verify it's called
        with (
            patch("core.simple_client.validate_token_not_encrypted") as mock_validate,
            patch("core.simple_client.ClaudeSDKClient"),
        ):
            from core.simple_client import create_simple_client

            create_simple_client(agent_type="merge_resolver")

            # Verify validation was called with the token
            mock_validate.assert_called_once_with(valid_token)


class TestClientPluginMCPWiring:
    """Tests for wiring enabled integration plugin MCP tools into agent sessions."""

    def test_create_client_adds_enabled_integration_plugin_mcp_tools(
        self,
        tmp_path,
        monkeypatch,
    ):
        """Enabled integration plugins should be available to agent SDK sessions."""
        valid_token = "sk-ant-oat01-valid-token"
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", valid_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)
        _stub_project_context(monkeypatch)

        sdk_module = sys.modules["claude_agent_sdk"]
        monkeypatch.setattr(
            sdk_module,
            "create_sdk_mcp_server",
            lambda name, version, tools: {
                "name": name,
                "version": version,
                "tools": tools,
            },
            raising=False,
        )

        from plugins.registry import PluginRegistry

        PluginRegistry.reset_instance()
        PluginRegistry.get_instance(
            user_plugins_dir=tmp_path / ".auto-claude" / "plugins" / "user",
            system_plugins_dir=Path("apps/backend/plugins/system").resolve(),
            project_dir=tmp_path,
        )

        captured_options = {}

        def fake_options(**kwargs):
            captured_options.update(kwargs)
            return kwargs

        client_module = importlib.import_module("core.client")
        mock_sdk_client = MagicMock()
        with (
            patch.object(
                client_module,
                "ClaudeAgentOptions",
                side_effect=fake_options,
            ),
            patch.object(
                client_module,
                "ClaudeSDKClient",
                return_value=mock_sdk_client,
            ),
        ):
            client = client_module.create_client(
                tmp_path,
                tmp_path,
                "claude-sonnet-4",
                "coder",
            )

        assert client is mock_sdk_client
        mcp_servers = captured_options["mcp_servers"]
        allowed_tools = captured_options["allowed_tools"]

        assert "codebase-intelligence-integration" in mcp_servers
        assert (
            "mcp__codebase-intelligence-integration__build_codebase_index"
            in allowed_tools
        )
        assert (
            "mcp__codebase-intelligence-integration__trace_file_impact"
            in allowed_tools
        )

        PluginRegistry.reset_instance()
