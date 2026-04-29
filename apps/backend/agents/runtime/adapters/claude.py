"""Claude Agent SDK runtime adapter."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from ..capabilities import RuntimeCapabilities
from ..result import AgentRunResult


class ClaudeAgentRuntimeSession:
    """Runtime wrapper for the existing Claude Agent SDK session."""

    name = "claude_agent_sdk"
    provider_name = "claude"
    capabilities = RuntimeCapabilities.claude_agent_sdk()

    def __init__(
        self,
        *,
        agent_session: Any,
        session_runner: Callable[..., Awaitable[tuple]],
    ):
        self.agent_session = agent_session
        self._session_runner = session_runner

    @property
    def context_client(self) -> Any:
        """Client object used by existing plugin hooks."""
        return getattr(self.agent_session, "client", None)

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        del subtask_id

        client = self.context_client
        if client is None:
            raise AttributeError("Claude runtime session missing 'client' attribute")

        async with client:
            (
                status,
                response,
                usage_metadata,
                decision_tracker,
            ) = await self._session_runner(
                client, message, spec_dir, verbose, phase=phase
            )

        return AgentRunResult(
            status=status,
            response_text=response,
            usage_metadata=usage_metadata,
            decision_tracker=decision_tracker,
        )
