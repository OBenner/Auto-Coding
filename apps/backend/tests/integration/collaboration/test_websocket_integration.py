"""Integration tests for WebSocket collaboration features."""

import pytest
import asyncio
import json
from pathlib import Path
import tempfile
import websockets

from collaboration.server import CollaborationServer


def test_collaboration_modules_import():
    """Test collaboration modules can be imported together."""
    from collaboration.server import CollaborationServer
    from collaboration.crdt_store import CRDTStore
    from collaboration.comments import CommentManager
    from collaboration.suggestions import SuggestionManager

    assert CollaborationServer is not None
    assert CRDTStore is not None
    assert CommentManager is not None
    assert SuggestionManager is not None


@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection between client and server."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir)
        server = CollaborationServer(host="localhost", port=9999, spec_dir=spec_dir)

        # Start server in background
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.2)  # Give server time to start

        try:
            async with websockets.connect("ws://localhost:9999") as ws:
                # Send connect message
                await ws.send(json.dumps({"type": "connect", "spec_id": "test"}))

                # Receive initial_state
                response = json.loads(await ws.recv())
                assert response["type"] == "initial_state"
                assert "content" in response
                assert "comments" in response
        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_multi_client_presence():
    """Test presence updates with multiple clients."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir)
        server = CollaborationServer(host="localhost", port=9998, spec_dir=spec_dir)

        # Start server in background
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.2)

        try:
            async with websockets.connect("ws://localhost:9998") as ws1:
                async with websockets.connect("ws://localhost:9998") as ws2:
                    # Connect both clients
                    await ws1.send(json.dumps({"type": "connect", "spec_id": "test", "user_id": "user1"}))
                    await ws2.send(json.dumps({"type": "connect", "spec_id": "test", "user_id": "user2"}))

                    # Get initial states
                    response1 = json.loads(await ws1.recv())
                    response2 = json.loads(await ws2.recv())

                    # Verify both clients connected
                    assert response1["type"] == "initial_state"
                    assert response2["type"] == "initial_state"
        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
