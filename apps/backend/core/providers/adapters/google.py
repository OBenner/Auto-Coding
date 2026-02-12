"""
Google Gemini Provider Adapter
===============================

Wraps the Google Generative AI SDK to implement the AIEngineProvider interface.
Provides access to Google's Gemini models for AI-powered development.

Supported Models:
- gemini-2.0-flash (default): Fast, efficient model for most tasks
- gemini-2.0-flash-thinking: Advanced reasoning with extended thinking
- gemini-1.5-pro: High-performance model for complex tasks
- gemini-1.5-flash: Balanced performance and speed

Environment Variables:
    GOOGLE_API_KEY: Required for Google Gemini provider

Example:
    from core.providers.adapters.google import GoogleProvider
    from core.providers.config import ProviderConfig

    config = ProviderConfig.from_env()
    provider = GoogleProvider(config)

    session_config = SessionConfig(
        name="coder-session",
        system_prompt="You are an expert developer.",
        model="gemini-2.0-flash",
        working_directory="/path/to/project"
    )
    session = provider.create_session(session_config)
"""

import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.providers.base import AgentSession, AIEngineProvider, SessionConfig
from core.providers.exceptions import ProviderConfigError, ProviderError, ProviderNotInstalled

if TYPE_CHECKING:
    from core.providers.config import ProviderConfig

logger = logging.getLogger(__name__)


# Supported Google Gemini models
GOOGLE_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-thinking",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

# Default model
DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"


class GoogleAgentSession(AgentSession):
    """Agent session wrapping Google Generative AI client.

    Provides session management for Google Gemini models.
    Handles message formatting, conversation history, and streaming responses.

    Attributes:
        model: The Google GenerativeModel instance
        chat: Active chat session for conversation continuity
        system_instruction: System prompt for the model
    """

    def __init__(
        self,
        session_id: str,
        model: Any,
        genai: Any,
        system_instruction: str = "",
        project_dir: Path | None = None,
        spec_dir: Path | None = None,
    ):
        """Initialize Google session.

        Args:
            session_id: Unique identifier for this session
            model: Google GenerativeModel instance
            genai: Google generativeai module
            system_instruction: System prompt for the model
            project_dir: Project working directory
            spec_dir: Spec directory for this session
        """
        super().__init__(session_id, provider_name="google")
        self._model = model
        self._genai = genai
        self._system_instruction = system_instruction
        self._project_dir = project_dir
        self._spec_dir = spec_dir
        self._chat = None
        self._message_history: list[dict[str, str]] = []

    @property
    def model(self) -> Any:
        """Get the Google GenerativeModel instance."""
        return self._model

    @property
    def project_dir(self) -> Path | None:
        """Get the project directory."""
        return self._project_dir

    @property
    def spec_dir(self) -> Path | None:
        """Get the spec directory."""
        return self._spec_dir

    async def query(self, message: str) -> None:
        """Send a query to the Google Gemini model.

        Args:
            message: The message/prompt to send

        Raises:
            ProviderError: If session is closed or query fails
        """
        if not self._is_active:
            raise ProviderError("Session is closed")

        # Add to message history
        self._message_history.append({"role": "user", "content": message})

        # Initialize chat if needed
        if self._chat is None:
            self._chat = self._model.start_chat(history=[])

    async def receive_response(self) -> AsyncIterator[Any]:
        """Receive response from the Google Gemini model.

        Yields:
            Response text chunks as they are received

        Raises:
            ProviderError: If session is closed or no query was sent
        """
        if not self._is_active:
            raise ProviderError("Session is closed")

        if self._chat is None:
            raise ProviderError("No query sent. Call query() first.")

        try:
            # Get the last user message
            last_message = self._message_history[-1]["content"]

            # Send message and stream response
            response = self._chat.send_message(last_message, stream=True)

            # Stream text chunks
            for chunk in response:
                if hasattr(chunk, "text"):
                    yield chunk.text

            # Add assistant response to history
            if hasattr(response, "text"):
                self._message_history.append(
                    {"role": "assistant", "content": response.text}
                )

        except Exception as e:
            logger.error(f"Error receiving response from Google: {e}")
            raise ProviderError(f"Error receiving response: {e}") from e

    def close(self) -> None:
        """Close the session."""
        super().close()
        self._chat = None
        self._message_history.clear()
        logger.debug(f"Google session {self.session_id} closed")


class GoogleProvider(AIEngineProvider):
    """Google Gemini provider implementation.

    Implements the AIEngineProvider interface using the Google Generative AI SDK.
    Provides access to Google's Gemini models with streaming support.

    Usage:
        from core.providers.adapters.google import GoogleProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig.from_env()
        provider = GoogleProvider(config)

        session_config = SessionConfig(
            name="coder-session",
            system_prompt="You are an expert developer.",
            model="gemini-2.0-flash"
        )
        session = provider.create_session(session_config)

    Attributes:
        config: Provider configuration
    """

    def __init__(self, config: "ProviderConfig"):
        """Initialize Google provider.

        Args:
            config: Provider configuration with Google API key

        Raises:
            ProviderNotInstalled: If google-generativeai is not installed
        """
        self._config = config
        self._active_session: GoogleAgentSession | None = None
        self._validation_errors: list[str] = []

        # Try to import and configure Google AI
        try:
            import google.generativeai as genai
            self._genai = genai

            # Configure with API key if available
            if config.google_api_key:
                genai.configure(api_key=config.google_api_key)

        except ImportError as e:
            raise ProviderNotInstalled(
                "Google provider requires google-generativeai. "
                "Install with: pip install google-generativeai"
            ) from e

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "google"

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
    ) -> GoogleAgentSession:
        """Create a new Google Gemini agent session.

        Args:
            config: Session configuration (name, system_prompt, model, etc.)
            project_dir: Working directory for the agent (optional)
            spec_dir: Spec directory for this session (optional)
            agent_type: Agent type identifier (informational)
            max_thinking_tokens: Token budget for extended thinking (not used)
            output_format: Optional structured output format (not implemented)
            agents: Optional subagent definitions (not implemented)

        Returns:
            GoogleAgentSession for interacting with Gemini

        Raises:
            ProviderConfigError: If API key is missing
            ProviderError: If session creation fails
        """
        # Validate API key
        if not self._config.google_api_key:
            raise ProviderConfigError(
                "Google API key is required. Set GOOGLE_API_KEY environment variable."
            )

        # Get model from config or use default
        model_name = config.model or self._config.google_model or DEFAULT_GOOGLE_MODEL

        # Get system instruction from config
        system_instruction = config.system_prompt or ""

        try:
            # Create GenerativeModel with system instruction
            if system_instruction:
                model = self._genai.GenerativeModel(
                    model_name, system_instruction=system_instruction
                )
            else:
                model = self._genai.GenerativeModel(model_name)

            # Generate session ID
            session_id = f"google-{uuid.uuid4().hex[:12]}"

            # Create and store session
            session = GoogleAgentSession(
                session_id=session_id,
                model=model,
                genai=self._genai,
                system_instruction=system_instruction,
                project_dir=project_dir,
                spec_dir=spec_dir,
            )
            self._active_session = session

            logger.info(
                f"Created Google session {session_id} "
                f"(model={model_name}, agent_type={agent_type})"
            )

            return session

        except Exception as e:
            logger.error(f"Failed to create Google session: {e}")
            raise ProviderError(f"Failed to create Google session: {e}") from e

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Uses the active session to send a message and stream back text responses.

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
            async for text_chunk in self._active_session.receive_response():
                yield text_chunk

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise ProviderError(f"Error sending message: {e}") from e

    def get_supported_models(self) -> list[str]:
        """Return list of supported Google Gemini models.

        Returns:
            List of Gemini model identifiers
        """
        return GOOGLE_MODELS.copy()

    def validate_config(self) -> bool:
        """Validate provider configuration.

        Checks that Google API key is present.

        Returns:
            True if configuration is valid
        """
        self._validation_errors = []

        if not self._config.google_api_key:
            self._validation_errors.append(
                "Google API key is required. Set GOOGLE_API_KEY environment variable."
            )
            return False

        return True

    def get_validation_errors(self) -> list[str]:
        """Get detailed validation error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        return self._validation_errors.copy()

    def health_check(self) -> bool:
        """Check if provider is healthy.

        For Google, this validates the API key is present.

        Returns:
            True if provider can create sessions
        """
        return self.validate_config()

    def get_active_session(self) -> GoogleAgentSession | None:
        """Get the currently active session, if any.

        Returns:
            Active GoogleAgentSession or None
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
        logger.debug("Google provider closed")

    def __repr__(self) -> str:
        """Return string representation of provider."""
        model = self._config.google_model or DEFAULT_GOOGLE_MODEL
        return f"GoogleProvider(name={self.name!r}, model={model!r})"
