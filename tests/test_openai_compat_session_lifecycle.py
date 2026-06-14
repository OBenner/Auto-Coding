"""Async lifecycle of OpenAI-compatible sessions.

``OpenAICompatibleSession`` lazily creates one ``AsyncOpenAI`` client whose
``httpx`` transport is bound to the event loop it was built in. The synchronous
``close()`` only drops the reference, leaking the transport so it raises noisy
``TCPTransport closed`` errors when the garbage collector reclaims it after the
loop ends. ``aclose()`` tears the client down in-loop instead; the QA reviewer
runtime loop relies on this to avoid leaking a client per iteration.
"""

from __future__ import annotations

import pytest
from core.providers.adapters.openai import OpenAISession


class _FakeAsyncClient:
    """Stand-in for ``AsyncOpenAI`` with an awaitable ``close()``."""

    def __init__(self, *, raise_on_close: bool = False):
        self.closed = False
        self._raise_on_close = raise_on_close

    async def close(self) -> None:
        self.closed = True
        if self._raise_on_close:
            raise RuntimeError("transport already closed")


def _make_session() -> OpenAISession:
    # api_key is enough to construct the session; the real client is never built
    # because the tests inject a fake into ``_client`` directly.
    return OpenAISession(session_id="s1", model="gpt-4o", api_key="test-key")


@pytest.mark.asyncio
async def test_aclose_awaits_client_close_and_clears_state():
    session = _make_session()
    client = _FakeAsyncClient()
    session._client = client
    assert session.is_active is True

    await session.aclose()

    assert client.closed is True
    assert session._client is None
    assert session.is_active is False


@pytest.mark.asyncio
async def test_aclose_without_client_is_safe():
    session = _make_session()
    assert session._client is None

    await session.aclose()

    assert session.is_active is False


@pytest.mark.asyncio
async def test_aclose_swallows_client_close_errors():
    """A transport already torn down must not surface from cleanup."""
    session = _make_session()
    client = _FakeAsyncClient(raise_on_close=True)
    session._client = client

    await session.aclose()  # must not raise

    assert client.closed is True
    assert session._client is None
    assert session.is_active is False
