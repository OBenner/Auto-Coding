"""Completion-only runtime adapter."""

import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from ..capabilities import RuntimeCapabilities
from ..result import AgentRunResult

logger = logging.getLogger(__name__)


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
        try:
            if hasattr(self.agent_session, "complete"):
                async for chunk in self.agent_session.complete(message, stream=True):
                    yield str(chunk)
                return

            if hasattr(self.agent_session, "query") and hasattr(
                self.agent_session, "receive_response"
            ):
                client = getattr(self.agent_session, "client", None)
                if hasattr(client, "__aenter__") and hasattr(client, "__aexit__"):
                    async with client:
                        async for chunk in self._stream_query_response(message):
                            yield chunk
                else:
                    async for chunk in self._stream_query_response(message):
                        yield chunk
                return
        except Exception as e:
            logger.error(
                "Provider %s completion stream failed",
                self.provider_name,
                exc_info=True,
            )
            raise RuntimeError(
                f"Provider {self.provider_name} completion failed: {e}"
            ) from e

        raise AttributeError(
            f"Provider {self.provider_name} session does not expose a completion API"
        )

    async def _stream_query_response(self, message: str) -> AsyncIterator[str]:
        """Stream text from query/receive_response style sessions."""
        await self.agent_session.query(message)
        async for chunk in self.agent_session.receive_response():
            yield str(chunk)

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
