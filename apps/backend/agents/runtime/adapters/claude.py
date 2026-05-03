"""Claude Agent SDK runtime adapter."""

import inspect
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
        client = getattr(self.agent_session, "client", None)
        if client is None:
            raise AttributeError(
                "Claude runtime requires an agent session with a 'client' attribute"
            )
        return client

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        client = self.context_client
        runner_kwargs = {"phase": phase}
        if "subtask_id" in inspect.signature(self._session_runner).parameters:
            runner_kwargs["subtask_id"] = subtask_id

        async with client:
            (
                status,
                response,
                usage_metadata,
                decision_tracker,
            ) = await self._session_runner(
                client,
                message,
                spec_dir,
                verbose,
                **runner_kwargs,
            )

        return AgentRunResult(
            status=status,
            response_text=response,
            usage_metadata=usage_metadata,
            decision_tracker=decision_tracker,
        )
