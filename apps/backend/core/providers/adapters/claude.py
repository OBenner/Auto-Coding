"""
Claude Agent SDK Provider Adapter
=================================

Wraps the Claude Agent SDK client to implement the AIEngineProvider interface.
This is the default and recommended provider for Auto-Code.

The adapter delegates to the existing create_client() function from core.client
to preserve all existing functionality including:
- OAuth authentication
- MCP server configuration
- Security hooks and sandbox
- Tool permissions
- Extended thinking
"""

import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.providers.base import AgentSession, AIEngineProvider, SessionConfig
from core.providers.exceptions import ProviderConfigError, ProviderError

if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeSDKClient
    from core.providers.config import ProviderConfig

logger = logging.getLogger(__name__)


# Supported Claude models
CLAUDE_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-20250514",
]


class ClaudeAgentSession(AgentSession):
    """Agent session wrapping Claude SDK client.

    Provides a thin wrapper around ClaudeSDKClient for session management.
    The actual message handling is done through the SDK's query/receive_response
    pattern.

    Attributes:
        client: The underlying ClaudeSDKClient instance
    """

    def __init__(
        self,
        session_id: str,
        client: "ClaudeSDKClient",
        project_dir: Path,
        spec_dir: Path,
    ):
        """Initialize Claude session.

        Args:
            session_id: Unique identifier for this session
            client: ClaudeSDKClient instance
            project_dir: Project working directory
            spec_dir: Spec directory for this session
        """
        super().__init__(session_id, provider_name="claude")
        self._client = client
        self._project_dir = project_dir
        self._spec_dir = spec_dir

    @property
    def client(self) -> "ClaudeSDKClient":
        """Get the underlying Claude SDK client."""
        return self._client

    @property
    def project_dir(self) -> Path:
        """Get the project directory."""
        return self._project_dir

    @property
    def spec_dir(self) -> Path:
        """Get the spec directory."""
        return self._spec_dir

    async def query(self, message: str) -> None:
        """Send a query to the Claude agent.

        Args:
            message: The message/prompt to send
        """
        if not self._is_active:
            raise ProviderError("Session is closed")
        await self._client.query(message)

    async def receive_response(self) -> AsyncIterator[Any]:
        """Receive response messages from the Claude agent.

        Yields:
            Response message objects from the Claude SDK
        """
        if not self._is_active:
            raise ProviderError("Session is closed")
        async for msg in self._client.receive_response():
            yield msg

    def close(self) -> None:
        """Close the session."""
        super().close()
        # ClaudeSDKClient doesn't have explicit cleanup, but we mark session as inactive
        logger.debug(f"Claude session {self.session_id} closed")


class ClaudeAgentProvider(AIEngineProvider):
    """Claude Agent SDK provider implementation.

    Wraps the existing create_client() function from core.client to implement
    the AIEngineProvider interface. This preserves all existing functionality
    while enabling the provider abstraction layer.

    Usage:
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig.from_env()
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(
            name="coder-session",
            system_prompt="You are an expert developer.",
            model="claude-sonnet-4-5-20250929",
            working_directory="/path/to/project"
        )
        session = provider.create_session(session_config)

    Attributes:
        config: Provider configuration
    """

    def __init__(self, config: "ProviderConfig"):
        """Initialize Claude provider.

        Args:
            config: Provider configuration with credentials
        """
        self._config = config
        self._active_session: ClaudeAgentSession | None = None
        self._validation_errors: list[str] = []

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "claude"

    @property
    def config(self) -> "ProviderConfig":
        """Get the provider configuration."""
        return self._config

    def create_session(
        self,
        config: SessionConfig,
        project_dir: Path | None = None,
        spec_dir: Path | None = None,
        agent_type: str = "coder",
        max_thinking_tokens: int | None = None,
        output_format: dict | None = None,
        agents: dict | None = None,
        runtime_metadata: dict | None = None,
    ) -> ClaudeAgentSession:
        """Create a new Claude agent session.

        Creates a ClaudeSDKClient using the existing create_client() function
        and wraps it in a ClaudeAgentSession for the provider abstraction.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)
            project_dir: Working directory for the agent (required)
            spec_dir: Spec directory for this session (required)
            agent_type: Agent type identifier from AGENT_CONFIGS
                       (e.g., 'coder', 'planner', 'qa_reviewer')
            max_thinking_tokens: Token budget for extended thinking
            output_format: Optional structured output format for JSON responses
            agents: Optional dict of subagent definitions for parallel execution
            runtime_metadata: Optional task/file metadata for plugin runtime hooks

        Returns:
            ClaudeAgentSession wrapping the SDK client

        Raises:
            ProviderConfigError: If project_dir or spec_dir not provided
            ProviderError: If session creation fails
        """
        # Validate required directories
        if project_dir is None:
            # Try to get from extra config
            if config.extra and "project_dir" in config.extra:
                project_dir = Path(config.extra["project_dir"])
            else:
                raise ProviderConfigError(
                    "project_dir is required for Claude session creation. "
                    "Pass it directly or in config.extra['project_dir']."
                )

        if spec_dir is None:
            # Try to get from extra config
            if config.extra and "spec_dir" in config.extra:
                spec_dir = Path(config.extra["spec_dir"])
            else:
                raise ProviderConfigError(
                    "spec_dir is required for Claude session creation. "
                    "Pass it directly or in config.extra['spec_dir']."
                )

        # Convert to Path objects if needed
        if isinstance(project_dir, str):
            project_dir = Path(project_dir)
        if isinstance(spec_dir, str):
            spec_dir = Path(spec_dir)

        # Get model from config or provider config
        model = config.model or self._config.claude_model

        # Get max_thinking_tokens from extra if not provided
        if max_thinking_tokens is None and config.extra:
            max_thinking_tokens = config.extra.get("max_thinking_tokens")

        # Get agent_type from extra if provided
        if config.extra and "agent_type" in config.extra:
            agent_type = config.extra["agent_type"]

        if runtime_metadata is None and config.extra:
            runtime_metadata = config.extra.get("runtime_metadata")

        try:
            # Import here to avoid circular imports
            from core.client import create_client

            # Create the SDK client using existing factory
            client = create_client(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model=model,
                agent_type=agent_type,
                max_thinking_tokens=max_thinking_tokens,
                output_format=output_format,
                agents=agents,
                runtime_metadata=runtime_metadata,
            )

            # Generate session ID
            session_id = f"claude-{uuid.uuid4().hex[:12]}"

            # Create and store session
            session = ClaudeAgentSession(
                session_id=session_id,
                client=client,
                project_dir=project_dir,
                spec_dir=spec_dir,
            )
            self._active_session = session

            logger.info(
                f"Created Claude session {session_id} "
                f"(model={model}, agent_type={agent_type})"
            )

            return session

        except Exception as e:
            logger.error(f"Failed to create Claude session: {e}")
            raise ProviderError(f"Failed to create Claude session: {e}") from e

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Uses the active session to send a message and stream back text responses.
        This is a convenience method for simple message/response patterns.
        For full control, use the session's query() and receive_response() methods.

        Args:
            message: The message to send

        Yields:
            Text response chunks as they are received

        Raises:
            ProviderError: If no active session or sending fails
        """
        if not self._active_session:
            raise ProviderError("No active session. Call create_session() first.")

        if not self._active_session.is_active:
            raise ProviderError("Session is closed. Create a new session.")

        try:
            # Send the query
            await self._active_session.query(message)

            # Stream response text
            async for msg in self._active_session.receive_response():
                msg_type = type(msg).__name__

                # Extract text from AssistantMessage
                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__
                        if block_type == "TextBlock" and hasattr(block, "text"):
                            yield block.text

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise ProviderError(f"Error sending message: {e}") from e

    def get_supported_models(self) -> list[str]:
        """Return list of supported Claude models.

        Returns:
            List of Claude model identifiers
        """
        return CLAUDE_MODELS.copy()

    def validate_config(self) -> bool:
        """Validate provider configuration.

        Claude SDK uses OAuth authentication, so API key is not strictly required.
        The SDK handles token lifecycle internally via require_auth_token().

        Returns:
            True (Claude SDK auth is handled at session creation time)
        """
        self._validation_errors = []

        # Claude SDK uses OAuth, validation happens at session creation
        # We could check for ANTHROPIC_API_KEY but it's optional with OAuth
        return True

    def get_validation_errors(self) -> list[str]:
        """Get detailed validation error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        return self._validation_errors.copy()

    def health_check(self) -> bool:
        """Check if provider is healthy.

        For Claude, this validates config and checks if auth is available.

        Returns:
            True if provider can create sessions
        """
        if not self.validate_config():
            return False

        # Try to import auth module and check token availability
        try:
            from core.auth import get_oauth_token

            token = get_oauth_token()
            return bool(token)
        except Exception:
            # If auth check fails, we might still work with API key
            return bool(self._config.anthropic_api_key)

    def get_active_session(self) -> ClaudeAgentSession | None:
        """Get the currently active session, if any.

        Returns:
            Active ClaudeAgentSession or None
        """
        if self._active_session and self._active_session.is_active:
            return self._active_session
        return None

    def close(self) -> None:
        """Clean up provider resources.

        Closes any active session.
        """
        if self._active_session:
            self._active_session.close()
            self._active_session = None
        logger.debug("Claude provider closed")

    def __repr__(self) -> str:
        """Return string representation of provider."""
        return (
            f"ClaudeAgentProvider(name={self.name!r}, "
            f"model={self._config.claude_model!r})"
        )
