"""
Agent Plugin SDK
=================

SDK for creating custom agent plugins.

Agent plugins can:
- Hook into agent lifecycle (before/after sessions)
- Monitor agent messages and tool use
- Add custom tools and behaviors
- Access agent context (project, spec, session)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from ..base import PluginBase, PluginMetadata, PluginType

if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeSDKClient

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """
    Context information provided to agent plugins.

    This context is passed to plugin lifecycle hooks to provide information
    about the current agent session, project, and spec.

    Attributes:
        project_dir: Root directory of the project being worked on
        spec_dir: Directory containing the current spec
        session_id: Optional unique identifier for the current agent session
        client: Optional Claude SDK client for the current session (available during session)
        phase: Optional phase name (planning, coding, qa_review, qa_fix)
        metadata: Optional additional metadata as key-value pairs
    """

    project_dir: Path
    spec_dir: Path
    session_id: Optional[str] = None
    client: Optional["ClaudeSDKClient"] = None
    phase: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}

    @property
    def spec_name(self) -> str:
        """Get the spec directory name."""
        return self.spec_dir.name

    @property
    def project_name(self) -> str:
        """Get the project directory name."""
        return self.project_dir.name


class AgentPlugin(PluginBase):
    """
    Base class for agent plugins.

    Agent plugins extend Auto Claude's agent capabilities by hooking into the
    agent lifecycle and providing custom behaviors, tools, or monitoring.

    Lifecycle hooks:
    - before_session: Called before an agent session starts
    - after_session: Called after an agent session completes
    - on_message: Called when agent receives a message (for monitoring)

    Example:
        ```python
        class MyAgentPlugin(AgentPlugin):
            def on_load(self):
                logger.info("MyAgentPlugin loaded")

            def on_enable(self):
                logger.info("MyAgentPlugin enabled")

            def before_session(self, context: AgentContext) -> None:
                logger.info(f"Session starting for spec: {context.spec_name}")

            def after_session(self, context: AgentContext, success: bool) -> None:
                status = "succeeded" if success else "failed"
                logger.info(f"Session {status} for spec: {context.spec_name}")

            def on_message(self, context: AgentContext, message: Any) -> None:
                # Monitor agent messages
                pass

            def on_disable(self):
                logger.info("MyAgentPlugin disabled")

            def on_unload(self):
                logger.info("MyAgentPlugin unloaded")
        ```
    """

    def __init__(self, metadata: PluginMetadata):
        """
        Initialize agent plugin.

        Args:
            metadata: Plugin metadata from plugin.json

        Raises:
            ValueError: If plugin_type is not AGENT
        """
        if metadata.plugin_type != PluginType.AGENT:
            raise ValueError(
                f"AgentPlugin requires plugin_type=AGENT, got {metadata.plugin_type}"
            )
        super().__init__(metadata)
        logger.debug(f"AgentPlugin initialized: {metadata.name}")

    def before_session(self, context: AgentContext) -> None:
        """
        Called before an agent session starts.

        Use this hook to:
        - Set up session-specific resources
        - Log session start
        - Validate context
        - Initialize monitoring

        Args:
            context: Information about the current agent session

        Raises:
            Exception: If plugin cannot prepare for session (will abort session)
        """
        pass

    def after_session(self, context: AgentContext, success: bool) -> None:
        """
        Called after an agent session completes.

        Use this hook to:
        - Clean up session resources
        - Log session results
        - Save analytics/metrics
        - Send notifications

        Args:
            context: Information about the completed agent session
            success: True if session completed successfully, False if error occurred
        """
        pass

    def on_message(self, context: AgentContext, message: Any) -> None:
        """
        Called when agent receives a message during a session.

        This is a monitoring/logging hook. DO NOT modify the message or block.
        Use this for:
        - Analytics and metrics
        - Debug logging
        - Real-time monitoring
        - Message filtering/analysis

        Args:
            context: Information about the current agent session
            message: The message received from the Claude SDK (AssistantMessage, etc.)

        Note:
            This method should be lightweight and fast. Heavy processing should be
            done asynchronously or in a background thread.
        """
        pass
