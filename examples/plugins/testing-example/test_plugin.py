#!/usr/bin/env python3
"""
Tests for Testing Example Plugin
=================================

Comprehensive test suite demonstrating how to test Auto Code plugins.

This test file shows:
- Unit testing plugin methods
- Testing lifecycle hooks
- Using MockAgentContext for agent plugins
- Testing state management
- Testing error handling
- Integration testing patterns
- Best practices for plugin testing
"""

import pytest
from pathlib import Path

from apps.backend.plugins.base import PluginPermission, PluginType
from apps.backend.plugins.sdk.testing import MockAgentContext, PluginTestCase

# Import the plugin we're testing
from .agent import TestingExamplePlugin


class TestPluginMetadata:
    """Tests for plugin metadata and initialization."""

    def test_plugin_has_correct_type(self):
        """Plugin should be an agent type."""
        testcase = PluginTestCase()
        plugin = testcase.create_plugin(TestingExamplePlugin, "testing-example")

        assert plugin.plugin_type == PluginType.AGENT

    def test_plugin_has_required_permissions(self):
        """Plugin should require read_files permission."""
        testcase = PluginTestCase()
        plugin = testcase.create_plugin(
            TestingExamplePlugin,
            "testing-example",
            required_permissions=[PluginPermission.READ_FILES],
        )

        assert PluginPermission.READ_FILES in plugin.metadata.required_permissions

    def test_plugin_initialization(self):
        """Plugin should initialize with default state."""
        testcase = PluginTestCase()
        plugin = testcase.create_plugin(TestingExamplePlugin, "testing-example")

        # Verify initial state
        assert plugin.total_sessions == 0
        assert plugin.successful_sessions == 0
        assert plugin.failed_sessions == 0
        assert len(plugin.specs_processed) == 0
        assert len(plugin.enabled_features) == 0


class TestPluginLifecycle:
    """Tests for plugin lifecycle hooks."""

    def test_on_load_initializes_features(self):
        """on_load should initialize default features."""
        testcase = PluginTestCase()
        plugin = testcase.load_plugin(TestingExamplePlugin, "testing-example")

        # Verify features were initialized
        assert "session_tracking" in plugin.enabled_features
        assert "stats_logging" in plugin.enabled_features
        assert plugin.is_loaded

    def test_on_enable_resets_stats(self):
        """on_enable should reset all statistics."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        # Manually set some stats
        plugin.total_sessions = 10
        plugin.successful_sessions = 7
        plugin.failed_sessions = 3
        plugin.specs_processed.add("spec-001")

        # Call on_enable again
        plugin.on_enable()

        # Stats should be reset
        assert plugin.total_sessions == 0
        assert plugin.successful_sessions == 0
        assert plugin.failed_sessions == 0
        assert len(plugin.specs_processed) == 0

    def test_full_lifecycle(self):
        """Test complete plugin lifecycle."""
        testcase = PluginTestCase()
        plugin = testcase.create_plugin(TestingExamplePlugin, "testing-example")

        # Initial state
        assert not plugin.is_loaded
        assert not plugin.is_enabled

        # Load
        plugin.on_load()
        plugin._mark_loaded()
        assert plugin.is_loaded
        assert "session_tracking" in plugin.enabled_features

        # Enable
        plugin.on_enable()
        plugin._mark_enabled()
        assert plugin.is_enabled

        # Disable
        plugin.on_disable()
        plugin._mark_disabled()
        assert not plugin.is_enabled

        # Unload
        plugin.on_unload()
        plugin._mark_unloaded()
        assert not plugin.is_loaded


class TestSessionTracking:
    """Tests for session tracking functionality."""

    def test_before_session_increments_counter(self):
        """before_session should increment session counter."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        with MockAgentContext() as context:
            # Call before_session multiple times
            for i in range(3):
                plugin.before_session(context)

            assert plugin.total_sessions == 3

    def test_before_session_tracks_spec_names(self):
        """before_session should track unique spec names."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        # Create contexts with different spec names
        with MockAgentContext() as context1:
            # Override spec_dir name for testing
            context1._spec_dir = Path("/tmp/spec-001")
            plugin.before_session(context1)

        with MockAgentContext() as context2:
            context2._spec_dir = Path("/tmp/spec-002")
            plugin.before_session(context2)

        with MockAgentContext() as context3:
            context3._spec_dir = Path("/tmp/spec-001")  # Duplicate
            plugin.before_session(context3)

        # Should have 2 unique specs
        assert len(plugin.specs_processed) == 2
        assert "spec-001" in plugin.specs_processed
        assert "spec-002" in plugin.specs_processed

    def test_after_session_tracks_success(self):
        """after_session should track successful sessions."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        with MockAgentContext() as context:
            plugin.before_session(context)
            plugin.after_session(context, success=True)

        assert plugin.successful_sessions == 1
        assert plugin.failed_sessions == 0

    def test_after_session_tracks_failure(self):
        """after_session should track failed sessions."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        with MockAgentContext() as context:
            plugin.before_session(context)
            plugin.after_session(context, success=False)

        assert plugin.successful_sessions == 0
        assert plugin.failed_sessions == 1

    def test_after_session_calculates_success_rate(self):
        """after_session should calculate correct success rate."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        # Run multiple sessions
        for success in [True, True, False, True, False]:
            with MockAgentContext() as context:
                plugin.before_session(context)
                plugin.after_session(context, success=success)

        # Should have 60% success rate (3/5)
        stats = context.metadata.get("session_stats", {})
        assert stats["total"] == 5
        assert stats["successful"] == 3
        assert stats["failed"] == 2
        assert stats["success_rate"] == pytest.approx(60.0)


class TestContextMetadata:
    """Tests for context metadata manipulation."""

    def test_debug_mode_adds_debug_info(self):
        """Debug mode should add debug info to context."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        with MockAgentContext() as context:
            # Enable debug mode via metadata
            context.metadata["enable_debug_mode"] = True
            plugin.before_session(context)

            # Should have debug info
            assert "debug_info" in context.metadata
            debug_info = context.metadata["debug_info"]
            assert "project_name" in debug_info
            assert "spec_name" in debug_info
            assert "phase" in debug_info

    def test_spec_dir_validation(self):
        """Plugin should validate spec directory existence."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        with MockAgentContext() as context:
            plugin.before_session(context)

            # Should mark spec_dir as existing (MockAgentContext creates it)
            assert context.metadata.get("spec_dir_exists") is True

    def test_spec_files_counting(self):
        """Plugin should count files in spec directory."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        with MockAgentContext() as context:
            # Create some test files
            (context.spec_dir / "test1.txt").write_text("test")
            (context.spec_dir / "test2.txt").write_text("test")
            (context.spec_dir / "subdir").mkdir()

            plugin.before_session(context)

            # Should count only files, not directories
            assert context.metadata.get("spec_files") == 2


class TestFeatureToggles:
    """Tests for feature toggle functionality."""

    def test_enable_feature(self):
        """Should be able to enable features."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        plugin.enable_feature("test_feature")
        assert "test_feature" in plugin.enabled_features

    def test_disable_feature(self):
        """Should be able to disable features."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        plugin.disable_feature("session_tracking")
        assert "session_tracking" not in plugin.enabled_features

    def test_disabled_session_tracking_stops_counting(self):
        """Disabling session_tracking should stop session counting."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        # Disable session tracking
        plugin.disable_feature("session_tracking")

        with MockAgentContext() as context:
            plugin.before_session(context)
            plugin.after_session(context, success=True)

        # Should not have incremented
        assert plugin.total_sessions == 0
        assert plugin.successful_sessions == 0


class TestStatisticsAPI:
    """Tests for statistics API methods."""

    def test_get_stats_returns_correct_data(self):
        """get_stats should return current statistics."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        # Run some sessions
        for success in [True, True, False]:
            with MockAgentContext() as context:
                plugin.before_session(context)
                plugin.after_session(context, success=success)

        stats = plugin.get_stats()
        assert stats["total_sessions"] == 3
        assert stats["successful_sessions"] == 2
        assert stats["failed_sessions"] == 1
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.01)

    def test_reset_stats_clears_all_data(self):
        """reset_stats should clear all statistics."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        # Set some stats
        plugin.total_sessions = 10
        plugin.successful_sessions = 7
        plugin.failed_sessions = 3
        plugin.specs_processed.add("spec-001")

        # Reset
        plugin.reset_stats()

        # Should be cleared
        assert plugin.total_sessions == 0
        assert plugin.successful_sessions == 0
        assert plugin.failed_sessions == 0
        assert len(plugin.specs_processed) == 0


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_handles_missing_spec_dir(self):
        """Plugin should handle missing spec directory gracefully."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        with MockAgentContext() as context:
            # Delete spec dir
            import shutil
            shutil.rmtree(context.spec_dir)

            # Should not raise exception
            plugin.before_session(context)

            # Should mark as not existing
            assert context.metadata.get("spec_dir_exists") is False

    def test_handles_zero_sessions(self):
        """Statistics should handle zero sessions correctly."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        stats = plugin.get_stats()
        assert stats["success_rate"] == 0  # No division by zero


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_complete_session_workflow(self):
        """Test complete workflow of multiple sessions."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(
            TestingExamplePlugin,
            "testing-example",
            required_permissions=[PluginPermission.READ_FILES],
        )

        # Verify plugin state
        assert plugin.is_loaded
        assert plugin.is_enabled

        # Run multiple sessions with different outcomes
        session_results = [
            ("spec-001", True),
            ("spec-002", True),
            ("spec-001", False),  # Same spec again
            ("spec-003", True),
        ]

        for spec_name, success in session_results:
            with MockAgentContext() as context:
                # Override spec name
                context._spec_dir = Path(f"/tmp/{spec_name}")

                # Run session
                plugin.before_session(context)
                plugin.after_session(context, success=success)

        # Verify final state
        stats = plugin.get_stats()
        assert stats["total_sessions"] == 4
        assert stats["successful_sessions"] == 3
        assert stats["failed_sessions"] == 1
        assert stats["specs_processed"] == 3  # 3 unique specs

    def test_plugin_with_debug_mode_and_file_operations(self):
        """Test plugin with debug mode and file operations."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(TestingExamplePlugin, "testing-example")

        with MockAgentContext() as context:
            # Enable debug mode
            context.metadata["enable_debug_mode"] = True

            # Create test files
            (context.spec_dir / "spec.md").write_text("# Spec")
            (context.spec_dir / "plan.json").write_text("{}")

            # Run session
            plugin.before_session(context)

            # Verify debug info
            assert "debug_info" in context.metadata
            assert context.metadata["spec_dir_exists"] is True
            assert context.metadata["spec_files"] == 2

            # Verify session counting
            assert plugin.total_sessions == 1


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
