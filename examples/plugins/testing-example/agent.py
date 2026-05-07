"""
Testing Example Agent Plugin
=============================

An example agent plugin demonstrating testable plugin patterns and best practices.

This plugin shows:
- How to structure plugins for testability
- State management and tracking
- Configurable behavior through metadata
- Error handling and validation
- Different testing scenarios

Perfect for learning how to write well-tested plugins.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from apps.backend.plugins.sdk.agent import AgentContext, AgentPlugin

logger = logging.getLogger(__name__)


class TestingExamplePlugin(AgentPlugin):
    """
    Example agent plugin demonstrating testable patterns.

    This plugin demonstrates:
    - Session statistics tracking
    - Configurable behavior through context metadata
    - File operations (reading spec files)
    - Error handling and validation
    - State persistence patterns
    - Multiple testing scenarios

    State tracked:
    - total_sessions: Count of all sessions handled
    - successful_sessions: Count of successful sessions
    - failed_sessions: Count of failed sessions
    - specs_processed: Set of unique spec names
    """

    def __init__(self, metadata):
        """Initialize the testing example plugin."""
        super().__init__(metadata)
        self.total_sessions = 0
        self.successful_sessions = 0
        self.failed_sessions = 0
        self.specs_processed = set()
        self.enabled_features = set()
        logger.debug(f"{self.name}: Plugin instance created")

    def on_load(self) -> None:
        """
        Called when plugin is first loaded.

        Validates configuration and initializes default features.
        """
        logger.info(f"{self.name}: Plugin loaded (version {self.version})")

        # Initialize default features
        self.enabled_features = {"session_tracking", "stats_logging"}
        logger.debug(f"{self.name}: Enabled features: {self.enabled_features}")

    def on_unload(self) -> None:
        """
        Called when plugin is being unloaded.

        Logs final statistics before cleanup.
        """
        logger.info(f"{self.name}: Plugin unloading...")
        logger.info(
            f"{self.name}: Final stats - "
            f"Total: {self.total_sessions}, "
            f"Success: {self.successful_sessions}, "
            f"Failed: {self.failed_sessions}, "
            f"Specs: {len(self.specs_processed)}"
        )

    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Resets statistics to start fresh.
        """
        logger.info(f"{self.name}: Plugin enabled")
        self.total_sessions = 0
        self.successful_sessions = 0
        self.failed_sessions = 0
        self.specs_processed.clear()

    def on_disable(self) -> None:
        """
        Called when plugin is disabled.

        Logs statistics before disabling.
        """
        logger.info(
            f"{self.name}: Plugin disabled after {self.total_sessions} sessions "
            f"({self.successful_sessions} successful, {self.failed_sessions} failed)"
        )

    def before_session(self, context: AgentContext) -> None:
        """
        Called before an agent session starts.

        Tracks session and can modify context based on configuration.

        Args:
            context: Information about the current agent session
        """
        if "session_tracking" not in self.enabled_features:
            return

        self.total_sessions += 1
        self.specs_processed.add(context.spec_name)

        logger.info(
            f"{self.name}: Starting session #{self.total_sessions} "
            f"for spec '{context.spec_name}'"
        )

        # Check for feature flags in context metadata
        if context.metadata.get("enable_debug_mode"):
            logger.debug(f"{self.name}: Debug mode enabled for this session")
            context.metadata["debug_info"] = self._gather_debug_info(context)

        # Validate spec directory exists (demonstrates testable file operations)
        if not context.spec_dir.exists():
            logger.warning(f"{self.name}: Spec directory does not exist: {context.spec_dir}")
            context.metadata["spec_dir_exists"] = False
        else:
            context.metadata["spec_dir_exists"] = True
            context.metadata["spec_files"] = self._count_spec_files(context.spec_dir)

    def after_session(self, context: AgentContext, success: bool) -> None:
        """
        Called after an agent session completes.

        Updates success/failure statistics.

        Args:
            context: Information about the completed agent session
            success: True if session completed successfully
        """
        if "session_tracking" not in self.enabled_features:
            return

        if success:
            self.successful_sessions += 1
            status_msg = "succeeded"
        else:
            self.failed_sessions += 1
            status_msg = "failed"

        # Calculate success rate
        success_rate = (
            (self.successful_sessions / self.total_sessions * 100)
            if self.total_sessions > 0
            else 0
        )

        logger.info(
            f"{self.name}: Session {status_msg} for spec '{context.spec_name}' "
            f"(success rate: {success_rate:.1f}%)"
        )

        # Store stats in context for testing
        context.metadata["session_stats"] = {
            "total": self.total_sessions,
            "successful": self.successful_sessions,
            "failed": self.failed_sessions,
            "success_rate": success_rate,
        }

    def on_message(self, context: AgentContext, message: Any) -> None:
        """
        Called when agent receives a message during a session.

        This is a monitoring/logging hook for analytics.

        Args:
            context: Information about the current agent session
            message: The message received from the Claude SDK
        """
        if "message_logging" in self.enabled_features:
            message_type = type(message).__name__
            logger.debug(f"{self.name}: Received message of type {message_type}")

    # Helper methods (private, but still testable)

    def _gather_debug_info(self, context: AgentContext) -> Dict[str, Any]:
        """
        Gather debug information about the current context.

        Args:
            context: The agent context

        Returns:
            Dictionary with debug information
        """
        return {
            "project_name": context.project_name,
            "spec_name": context.spec_name,
            "phase": context.phase,
            "session_id": context.session_id,
            "total_sessions": self.total_sessions,
        }

    def _count_spec_files(self, spec_dir: Path) -> int:
        """
        Count files in the spec directory.

        Args:
            spec_dir: Path to the spec directory

        Returns:
            Number of files in the directory
        """
        try:
            return len([f for f in spec_dir.iterdir() if f.is_file()])
        except Exception as e:
            logger.warning(f"{self.name}: Error counting spec files: {e}")
            return 0

    def enable_feature(self, feature: str) -> None:
        """
        Enable a plugin feature.

        Args:
            feature: Name of the feature to enable
        """
        self.enabled_features.add(feature)
        logger.debug(f"{self.name}: Enabled feature: {feature}")

    def disable_feature(self, feature: str) -> None:
        """
        Disable a plugin feature.

        Args:
            feature: Name of the feature to disable
        """
        self.enabled_features.discard(feature)
        logger.debug(f"{self.name}: Disabled feature: {feature}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current plugin statistics.

        Returns:
            Dictionary with current stats
        """
        return {
            "total_sessions": self.total_sessions,
            "successful_sessions": self.successful_sessions,
            "failed_sessions": self.failed_sessions,
            "specs_processed": len(self.specs_processed),
            "success_rate": (
                (self.successful_sessions / self.total_sessions * 100)
                if self.total_sessions > 0
                else 0
            ),
        }

    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        self.total_sessions = 0
        self.successful_sessions = 0
        self.failed_sessions = 0
        self.specs_processed.clear()
        logger.debug(f"{self.name}: Statistics reset")
