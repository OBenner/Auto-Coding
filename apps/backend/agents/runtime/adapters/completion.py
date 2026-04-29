"""Completion-only runtime adapter."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from ..capabilities import RuntimeCapabilities
from ..result import AgentRunResult


class CompletionRuntimeSession:
    """Runtime for direct model SDKs and model gateways.

    This adapter intentionally exposes no filesystem, shell, MCP, or native tool
    loop capabilities. It is suitable for analysis and future patch proposal
    phases, not full autonomous coding.
    """

    name = "completion"
    capabilities = RuntimeCapabilities.completion_only()

    def __init__(self, *, provider_name: str, agent_session: Any):
        self.provider_name = provider_name
        self.agent_session = agent_session

    @property
    def context_client(self) -> Any:
        return None

    async def _stream_text(self, message: str) -> AsyncIterator[str]:
        if hasattr(self.agent_session, "complete"):
            async for chunk in self.agent_session.complete(message, stream=True):
                yield str(chunk)
            return

        if hasattr(self.agent_session, "query") and hasattr(
            self.agent_session, "receive_response"
        ):
            await self.agent_session.query(message)
            async for chunk in self.agent_session.receive_response():
                yield str(chunk)
            return

        raise AttributeError(
            f"Provider {self.provider_name} session does not expose a completion API"
        )

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        del spec_dir, verbose, phase, subtask_id

        chunks: list[str] = []
        async for chunk in self._stream_text(message):
            chunks.append(chunk)

        return AgentRunResult(
            status="complete",
            response_text="".join(chunks),
            usage_metadata=None,
            decision_tracker=None,
        )
