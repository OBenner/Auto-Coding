"""
Hello World Agent Plugin
=========================

A simple example agent plugin that demonstrates the AgentPlugin interface
and basic lifecycle hooks.

This plugin:
- Logs messages at each lifecycle stage
- Tracks session count
- Demonstrates context access
- Shows how to implement all required hooks
"""

import logging

from apps.backend.plugins.sdk.agent import AgentContext, AgentPlugin

logger = logging.getLogger(__name__)


class HelloWorldAgentPlugin(AgentPlugin):
    """
    Example agent plugin that logs lifecycle events.

    This plugin demonstrates:
    - Implementing all required lifecycle hooks (on_load, on_unload, on_enable, on_disable)
    - Using before_session and after_session hooks
    - Accessing context information (project_dir, spec_dir, etc.)
    - Maintaining plugin state across sessions
    """

    def __init__(self, metadata):
        """Initialize the hello world agent plugin."""
        super().__init__(metadata)
        self.session_count = 0
        logger.debug(f"{self.name}: Plugin instance created")

    def on_load(self) -> None:
        """
        Called when plugin is first loaded.

        Use this to validate configuration and initialize resources.
        """
        logger.info(f"{self.name}: Plugin loaded")
        logger.debug(f"{self.name}: Version {self.version}")
        logger.debug(f"{self.name}: Author {self.metadata.author}")

    def on_unload(self) -> None:
        """
        Called when plugin is being unloaded.

        Use this to clean up resources and save state.
        """
        logger.info(f"{self.name}: Plugin unloaded after {self.session_count} sessions")

    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Use this to register tools/services and start background tasks.
        """
        logger.info(f"{self.name}: Plugin enabled")
        self.session_count = 0

    def on_disable(self) -> None:
        """
        Called when plugin is disabled.

        Use this to unregister tools/services and stop background tasks.
        """
        logger.info(f"{self.name}: Plugin disabled")

    def before_session(self, context: AgentContext) -> None:
        """
        Called before an agent session starts.

        Args:
            context: Information about the current agent session
        """
        self.session_count += 1
        logger.info(
            f"{self.name}: Starting session #{self.session_count} "
            f"for spec '{context.spec_name}' in project '{context.project_name}'"
        )

        if context.phase:
            logger.debug(f"{self.name}: Session phase: {context.phase}")

        if context.session_id:
            logger.debug(f"{self.name}: Session ID: {context.session_id}")

    def after_session(self, context: AgentContext, success: bool) -> None:
        """
        Called after an agent session completes.

        Args:
            context: Information about the completed agent session
            success: True if session completed successfully
        """
        status = "succeeded" if success else "failed"
        logger.info(f"{self.name}: Session {status} for spec '{context.spec_name}'")

        if not success:
            logger.warning(f"{self.name}: Session failed - you may want to investigate")

    def on_message(self, context: AgentContext, message: any) -> None:
        """
        Called when agent receives a message during a session.

        This is a monitoring/logging hook for analytics and debugging.

        Args:
            context: Information about the current agent session
            message: The message received from the Claude SDK
        """
        # Example: Log message type for debugging
        message_type = type(message).__name__
        logger.debug(f"{self.name}: Received message of type {message_type}")
