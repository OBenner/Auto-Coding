"""
Pair Programming Agent Module
==============================

Interactive AI pair programming agent that works alongside developers in real-time.

Provides:
- Real-time code suggestions as developer types
- Context-aware assistance
- Seamless transition between autonomous and pair modes
- Integration with suggestion engine for code analysis
"""

import asyncio
import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _import_backend_core():
    """
    Import backend.core modules, avoiding web-backend/core namespace collision.

    When imported from web-backend context, there's a naming conflict between
    apps/backend/core and apps/web-backend/core. This function ensures backend.core
    is accessible by adding backend to the front of sys.path and clearing conflicts.
    """
    # Get the backend directory
    # __file__ = apps/backend/agents/pair_programming.py
    # .parent = apps/backend/agents/
    # .parent.parent = apps/backend/
    backend_dir = Path(__file__).parent.parent
    backend_path = str(backend_dir)

    # Remove backend if already in path (to avoid duplicates)
    if backend_path in sys.path:
        sys.path.remove(backend_path)

    # Insert backend at the FRONT of sys.path so core.* imports find backend/core
    sys.path.insert(0, backend_path)

    # Remove any cached core modules from web-backend
    modules_to_remove = []
    for name in list(sys.modules.keys()):
        if name == "core" or name.startswith("core."):
            module = sys.modules[name]
            if hasattr(module, "__file__") and module.__file__:
                try:
                    module_path = Path(module.__file__).resolve()
                    # If it's not from backend, mark for removal
                    if not module_path.is_relative_to(backend_dir.resolve()):
                        modules_to_remove.append(name)
                except (OSError, RuntimeError):
                    # If we can't resolve the path, remove it to be safe
                    modules_to_remove.append(name)

    for name in modules_to_remove:
        del sys.modules[name]

    # Import core parent package first
    import importlib
    importlib.import_module("core")

    # Now import core.client and core.sentry
    client_module = importlib.import_module("core.client")
    sentry_module = importlib.import_module("core.sentry")

    return client_module, sentry_module


@dataclass
class PairSession:
    """
    Pair programming session state.

    Attributes:
        project_dir: Root project directory
        spec_dir: Spec directory
        mode: Current mode ("pair" or "autonomous")
        session_num: Session number counter
        verbose: Whether to show detailed output
    """

    project_dir: Path
    spec_dir: Path
    mode: str = "pair"  # "pair" or "autonomous"
    session_num: int = 0
    verbose: bool = False


class PairProgrammingAgent:
    """
    Interactive pair programming agent.

    Works alongside the developer in real-time, providing suggestions,
    explanations, and assistance as they code. Can seamlessly transition
    between autonomous and pair modes.
    """

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_thinking_tokens: int | None = None,
        verbose: bool = False,
    ):
        """
        Initialize the pair programming agent.

        Args:
            project_dir: Root directory for the project
            spec_dir: Directory containing the spec (optional)
            model: Claude model to use
            max_thinking_tokens: Max thinking tokens for AI responses
            verbose: Whether to show detailed output
        """
        self.project_dir = project_dir
        self.spec_dir = spec_dir
        self.model = model
        self.max_thinking_tokens = max_thinking_tokens
        self.verbose = verbose

        # Session state
        self.session_state = PairSession(
            project_dir=project_dir,
            spec_dir=spec_dir or project_dir,  # Default to project_dir if no spec
            mode="pair",
            session_num=0,
            verbose=verbose,
        )

        # Client will be created when session starts
        self._client = None

        logger.info(
            f"Initialized PairProgrammingAgent for {project_dir} with model {model}"
        )

    async def start_session(
        self,
        initial_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Start an interactive pair programming session.

        Args:
            initial_message: Optional initial message/task for the agent

        Returns:
            Session result dictionary with status and response
        """
        logger.info("Starting pair programming session")

        self.session_state.session_num += 1

        try:
            # Create Claude SDK client
            if not self._client:
                client_module, _ = _import_backend_core()
                create_client = client_module.create_client

                self._client = create_client(
                    project_dir=self.project_dir,
                    spec_dir=self.session_state.spec_dir,  # Use session state (has default fallback)
                    model=self.model,
                    agent_type="coder",  # Use coder tools for pair programming
                    max_thinking_tokens=self.max_thinking_tokens,
                )

            # Build prompt
            prompt = self._build_session_prompt(initial_message)

            # Run session
            result = await self._run_session(prompt)

            logger.info("Pair programming session completed")
            return result

        except Exception as e:
            logger.error(f"Error in pair programming session: {e}")
            _, sentry_module = _import_backend_core()
            capture_exception = sentry_module.capture_exception

            capture_exception(e)
            return {
                "status": "error",
                "error": str(e),
                "session_num": self.session_state.session_num,
            }

    async def switch_mode(self, mode: str) -> bool:
        """
        Switch between pair and autonomous modes.

        Args:
            mode: Target mode ("pair" or "autonomous")

        Returns:
            True if mode switch was successful
        """
        if mode not in ["pair", "autonomous"]:
            logger.warning(f"Invalid mode: {mode}")
            return False

        if mode == self.session_state.mode:
            logger.debug(f"Already in {mode} mode")
            return True

        logger.info(f"Switching mode: {self.session_state.mode} -> {mode}")
        self.session_state.mode = mode

        return True

    def get_mode(self) -> str:
        """
        Get current mode.

        Returns:
            Current mode ("pair" or "autonomous")
        """
        return self.session_state.mode

    def get_session_state(self) -> PairSession:
        """
        Get current session state.

        Returns:
            Current session state
        """
        return self.session_state

    def _build_session_prompt(
        self,
        initial_message: str | None,
    ) -> str:
        """
        Build the initial prompt for the pair programming session.

        Args:
            initial_message: Optional initial message from user

        Returns:
            Complete prompt string
        """
        # Load spec if available
        spec_content = ""
        if self.spec_dir:
            spec_path = self.spec_dir / "spec.md"
            if spec_path.exists():
                try:
                    spec_content = spec_path.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(f"Could not read spec: {e}")

        # Build prompt
        parts = [
            "# Pair Programming Session",
            "",
            "You are an AI pair programming assistant working alongside a developer.",
            "",
            "## Your Role",
            "- Provide real-time suggestions as the developer works",
            "- Answer questions and explain code",
            "- Suggest improvements and best practices",
            "- Help debug issues",
            "- Adapt your responses to the developer's pace and preferences",
            "",
        ]

        if spec_content:
            parts.extend([
                "## Current Feature Specification",
                "",
                spec_content,
                "",
            ])

        if initial_message:
            parts.extend([
                "## Initial Request",
                "",
                initial_message,
                "",
            ])

        parts.extend([
            "## Instructions",
            "- Be conversational and friendly",
            "- Ask clarifying questions when needed",
            "- Provide context for your suggestions",
            "- Respect the developer's autonomy - suggest, don't dictate",
            "",
            "Ready to start pair programming!",
        ])

        return "\n".join(parts)

    async def _run_session(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        """
        Run a single pair programming session.

        Args:
            prompt: The prompt to send to the agent

        Returns:
            Session result dictionary
        """
        try:
            # Send query to Claude SDK
            await self._client.query(prompt)

            # Collect response
            response_text = ""
            async for msg in self._client.receive_response():
                msg_type = type(msg).__name__

                # Handle AssistantMessage (text content)
                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__
                        if block_type == "TextBlock" and hasattr(block, "text"):
                            response_text += block.text
                            if self.verbose:
                                print(block.text, end="", flush=True)

            if self.verbose:
                print("\n" + "-" * 70 + "\n")

            return {
                "status": "success",
                "response": response_text,
                "mode": self.session_state.mode,
                "session_num": self.session_state.session_num,
            }

        except Exception as e:
            logger.error(f"Error running session: {e}")
            _, sentry_module = _import_backend_core()
            capture_exception = sentry_module.capture_exception

            capture_exception(e)
            return {
                "status": "error",
                "error": str(e),
                "session_num": self.session_state.session_num,
            }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cleanup resources
        self._client = None
        return False


async def create_pair_programming_agent(
    project_dir: Path,
    spec_dir: Path | None = None,
    model: str = "claude-sonnet-4-5-20250929",
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> PairProgrammingAgent:
    """
    Factory function to create a configured PairProgrammingAgent.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec (optional)
        model: Claude model to use
        max_thinking_tokens: Max thinking tokens
        verbose: Whether to show detailed output

    Returns:
        Configured PairProgrammingAgent instance
    """
    return PairProgrammingAgent(
        project_dir=project_dir,
        spec_dir=spec_dir,
        model=model,
        max_thinking_tokens=max_thinking_tokens,
        verbose=verbose,
    )


async def run_pair_programming_session(
    project_dir: Path,
    spec_dir: Path | None = None,
    model: str = "claude-sonnet-4-5-20250929",
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
    initial_message: str | None = None,
) -> dict[str, Any]:
    """
    Factory function to run a pair programming session.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec (optional)
        model: Claude model to use
        max_thinking_tokens: Max thinking tokens for AI responses
        verbose: Whether to show detailed output
        initial_message: Optional initial message/task

    Returns:
        Session result dictionary
    """
    async with PairProgrammingAgent(
        project_dir=project_dir,
        spec_dir=spec_dir,
        model=model,
        max_thinking_tokens=max_thinking_tokens,
        verbose=verbose,
    ) as agent:
        return await agent.start_session(initial_message=initial_message)
