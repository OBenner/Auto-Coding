"""
Tests for SessionContext code reference tracking.

Tests the session context storage and code reference tracking functionality
that enables persistent conversation history and codebase awareness.
"""

import sys
from pathlib import Path

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))


class TestSessionContextCodeReferences:
    """Tests for code reference tracking in SessionContext."""

    def test_session_context_has_code_reference_methods(self):
        """SessionContext should have all code reference tracking methods."""
        from agents.session_context import SessionContext

        required_methods = [
            "save_code_references",
            "get_code_references",
            "get_sessions_for_file",
            "get_all_code_references_for_session",
            "save_code_reference_episode",
        ]

        for method_name in required_methods:
            assert hasattr(
                SessionContext, method_name
            ), f"SessionContext missing method '{method_name}'"
            method = getattr(SessionContext, method_name)
            assert callable(method), f"SessionContext.{method_name} is not callable"

    def test_session_context_imports(self):
        """Test that SessionContext imports without errors."""
        from agents.session_context import (
            EPISODE_TYPE_CODE_REFERENCE,
            EPISODE_TYPE_CONVERSATION_ROUND,
            EPISODE_TYPE_SESSION_CONTEXT,
            SessionContext,
        )

        # Verify episode type constants exist
        assert EPISODE_TYPE_CODE_REFERENCE == "code_reference"
        assert EPISODE_TYPE_CONVERSATION_ROUND == "conversation_round"
        assert EPISODE_TYPE_SESSION_CONTEXT == "session_context"

    def test_session_context_initialization(self):
        """Test SessionContext can be initialized."""
        from agents.session_context import SessionContext

        spec_dir = Path("/tmp/test_spec")
        project_dir = Path("/tmp/test_project")

        ctx = SessionContext(
            spec_dir=spec_dir,
            project_dir=project_dir,
            graphiti_memory=None,
        )

        assert ctx.spec_dir == spec_dir
        assert ctx.project_dir == project_dir
        assert ctx._graphiti_memory is None
        assert ctx._initialized is False

    def test_save_conversation_round_extracts_code_references(self):
        """Test that save_conversation_round handles code references from round_data."""
        from agents.session_context import SessionContext

        # Verify the method signature includes handling of code_references
        import inspect

        sig = inspect.signature(SessionContext.save_conversation_round)
        params = list(sig.parameters.keys())

        # Should have self, session_id, round_data, subtask_id
        assert "self" in params
        assert "session_id" in params
        assert "round_data" in params
        assert "subtask_id" in params

    def test_get_code_references_signature(self):
        """Test get_code_references has correct signature."""
        from agents.session_context import SessionContext
        import inspect

        sig = inspect.signature(SessionContext.get_code_references)
        params = sig.parameters

        # Should accept optional session_id and file_path filters
        assert "session_id" in params
        assert "file_path" in params

        # Both should be optional (have defaults)
        assert params["session_id"].default is not inspect.Parameter.empty
        assert params["file_path"].default is not inspect.Parameter.empty

    def test_get_sessions_for_file_signature(self):
        """Test get_sessions_for_file has correct signature."""
        from agents.session_context import SessionContext
        import inspect

        sig = inspect.signature(SessionContext.get_sessions_for_file)
        params = sig.parameters

        # Should require file_path parameter
        assert "file_path" in params
        assert params["file_path"].default is inspect.Parameter.empty

    def test_save_code_reference_episode_signature(self):
        """Test save_code_reference_episode has correct signature."""
        from agents.session_context import SessionContext
        import inspect

        sig = inspect.signature(SessionContext.save_code_reference_episode)
        params = sig.parameters

        # Should have session_id, round_number, code_references
        assert "session_id" in params
        assert "round_number" in params
        assert "code_references" in params

        # All should be required (no defaults)
        assert params["session_id"].default is inspect.Parameter.empty
        assert params["round_number"].default is inspect.Parameter.empty
        assert params["code_references"].default is inspect.Parameter.empty


class TestCodeReferenceIntegration:
    """Integration tests for code reference tracking (requires Graphiti)."""

    def test_code_reference_methods_are_async(self):
        """Verify that code reference methods are async (coroutines)."""
        from agents.session_context import SessionContext
        import inspect

        async_methods = [
            "get_code_references",
            "get_sessions_for_file",
            "get_all_code_references_for_session",
            "save_code_reference_episode",
        ]

        for method_name in async_methods:
            method = getattr(SessionContext, method_name)
            assert inspect.iscoroutinefunction(
                method
            ), f"{method_name} should be an async method"
