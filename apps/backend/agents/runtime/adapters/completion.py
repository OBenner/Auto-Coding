"""Completion-only runtime adapter."""

import inspect
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
        self._cancel_requested = False

    @property
    def context_client(self) -> Any:
        return None

    async def cancel(self) -> bool:
        """Request cancellation and forward it to the provider session if possible."""
        self._cancel_requested = True
        cancel_hook = getattr(self.agent_session, "cancel", None)
        if not callable(cancel_hook):
            return False
        result = cancel_hook()
        if inspect.isawaitable(result):
            result = await result
        return True if result is None else bool(result)

    async def _stream_text(self, message: str) -> AsyncIterator[str]:
        streamer = self._select_streamer()
        if streamer is None:
            raise AttributeError(
                f"Provider {self.provider_name} session does not expose a completion API"
            )
        if self._cancel_requested:
            return

        try:
            async for chunk in streamer(message):
                if self._cancel_requested:
                    return
                yield chunk
        except Exception as e:
            logger.error(
                "Provider %s completion stream failed",
                self.provider_name,
                exc_info=True,
            )
            raise RuntimeError(
                f"Provider {self.provider_name} completion failed: {e}"
            ) from e

    def _select_streamer(self):
        """Return the streaming method supported by this provider session."""
        if hasattr(self.agent_session, "complete"):
            return self._stream_complete_response
        if hasattr(self.agent_session, "query") and hasattr(
            self.agent_session,
            "receive_response",
        ):
            return self._stream_query_response_with_context
        return None

    async def _stream_complete_response(self, message: str) -> AsyncIterator[str]:
        """Stream text from complete(stream=True) style sessions."""
        async for chunk in self.agent_session.complete(message, stream=True):
            yield str(chunk)

    async def _stream_query_response_with_context(
        self,
        message: str,
    ) -> AsyncIterator[str]:
        """Stream text from query sessions, entering client context when present."""
        client = getattr(self.agent_session, "client", None)
        if not hasattr(client, "__aenter__") or not hasattr(client, "__aexit__"):
            async for chunk in self._stream_query_response(message):
                yield chunk
            return

        async with client:
            async for chunk in self._stream_query_response(message):
                yield chunk

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

        if self._cancel_requested:
            return AgentRunResult(
                status="cancelled",
                response_text="Completion runtime was cancelled before start.",
            )

        chunks: list[str] = []
        async for chunk in self._stream_text(message):
            if self._cancel_requested:
                return AgentRunResult(
                    status="cancelled",
                    response_text="Completion runtime was cancelled.",
                )
            chunks.append(chunk)

        if self._cancel_requested:
            return AgentRunResult(
                status="cancelled",
                response_text="Completion runtime was cancelled.",
            )

        return AgentRunResult(
            status="complete",
            response_text="".join(chunks),
            usage_metadata=None,
            decision_tracker=None,
        )
