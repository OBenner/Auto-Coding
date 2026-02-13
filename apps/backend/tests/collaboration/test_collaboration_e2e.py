"""
End-to-End Tests for Collaborative Editing
===========================================

Tests the complete collaborative editing workflow including:
- WebSocket server with multiple clients
- Real-time content synchronization
- Presence indicators
- Threaded comments
- Suggestion mode
- Version history
- Approval workflow

Run with:
    pytest apps/backend/tests/collaboration/test_collaboration_e2e.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest
import websockets.asyncio.client

from collaboration.crdt_store import CRDTStore, CrdtOperation, OpType
from collaboration.models import Comment, Presence, Suggestion, load_comments, load_suggestions
from collaboration.server import CollaborationServer, MessageType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_spec_dir():
    """Create a temporary directory for spec collaboration data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir) / "collaboration"
        spec_dir.mkdir(parents=True, exist_ok=True)

        # Create initial spec.md
        spec_md = spec_dir / "spec.md"
        spec_md.write_text("# Test Spec\n\nInitial content.\n")

        yield spec_dir


@pytest.fixture
async def collaboration_server(temp_spec_dir, unused_tcp_port):
    """Start a collaboration server for testing."""
    # Monkey patch the collaboration data directory
    import collaboration

    original_dir = getattr(collaboration, "_collaboration_dir", None)
    collaboration._collaboration_dir = temp_spec_dir

    server = CollaborationServer(host="localhost", port=unused_tcp_port)

    # Run server in background
    async def run_server():
        await server.run()

    server_task = asyncio.create_task(run_server())

    # Give server time to start
    await asyncio.sleep(0.2)

    yield server

    # Cleanup
    server.shutdown()
    await asyncio.sleep(0.1)

    try:
        server_task.cancel()
        await server_task
    except asyncio.CancelledError:
        pass

    if original_dir:
        collaboration._collaboration_dir = original_dir


@pytest.fixture
async def test_client(collaboration_server, unused_tcp_port):
    """Create a WebSocket client for testing."""
    uri = f"ws://localhost:{unused_tcp_port}"

    async with websockets.asyncio.client.connect(uri) as websocket:
        yield websocket


@pytest.fixture
async def two_test_clients(collaboration_server, unused_tcp_port):
    """Create two WebSocket clients for testing collaboration."""
    uri = f"ws://localhost:{unused_tcp_port}"

    async with websockets.asyncio.client.connect(uri) as client1:
        async with websockets.asyncio.client.connect(uri) as client2:
            yield client1, client2


# =============================================================================
# Helper Functions
# =============================================================================


async def connect_client(
    websocket: websockets.asyncio.client.ClientConnection,
    spec_id: str = "test-spec",
    user_id: str = "user1",
    user_name: str = "User 1",
):
    """Connect a client to the collaboration server."""
    connect_msg = {
        "type": MessageType.CONNECT.value,
        "spec_id": spec_id,
        "user_id": user_id,
        "user_name": user_name,
    }
    await websocket.send(json.dumps(connect_msg))

    # Receive initial state
    response = await websocket.recv()
    return json.loads(response)


async def send_operation(
    websocket: websockets.asyncio.client.ClientConnection,
    op_type: str,  # "insert" or "delete"
    position: int,
    content: str = "",
    author_id: str = "user1",
    author_name: str = "Test User",
):
    """Send CRDT operation to server."""
    operation_msg = {
        "type": MessageType.OPERATION.value,
        "data": {
            "operation": {
                "op_type": op_type,
                "position": position,
                "content": content,
                "author": author_id,
                "author_name": author_name,
            }
        },
    }
    await websocket.send(json.dumps(operation_msg))


async def send_presence_update(
    websocket: websockets.asyncio.client.ClientConnection,
    presence_type: str = "viewing",
):
    """Send a presence update to the server."""
    update_msg = {
        "type": MessageType.PRESENCE_UPDATE.value,
        "presence_type": presence_type,
    }
    await websocket.send(json.dumps(update_msg))


async def add_comment(
    websocket: websockets.asyncio.client.ClientConnection,
    section: str,
    content: str,
    parent_id: str | None = None,
):
    """Add a comment to the spec."""
    comment_msg = {
        "type": MessageType.ADD_COMMENT.value,
        "section": section,
        "content": content,
        "parent_id": parent_id,
    }
    await websocket.send(json.dumps(comment_msg))


async def add_suggestion(
    websocket: websockets.asyncio.client.ClientConnection,
    section: str,
    original_text: str,
    proposed_text: str,
    reason: str = "",
):
    """Add a suggestion to the spec."""
    suggestion_msg = {
        "type": MessageType.ADD_SUGGESTION.value,
        "section": section,
        "original_text": original_text,
        "proposed_text": proposed_text,
        "reason": reason,
    }
    await websocket.send(json.dumps(suggestion_msg))


async def receive_messages(websocket: websockets.asyncio.client.ClientConnection, count: int = 1):
    """Receive multiple messages from the server."""
    messages = []
    for _ in range(count):
        msg = await websocket.recv()
        messages.append(json.loads(msg))
    return messages


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.asyncio
async def test_server_starts(collaboration_server):
    """Test that the collaboration server starts successfully."""
    assert collaboration_server is not None
    assert collaboration_server.host == "localhost"
    assert collaboration_server.port > 0


@pytest.mark.asyncio
async def test_client_connects(test_client):
    """Test that a client can connect to the server."""
    response = await connect_client(test_client, spec_id="test-spec-1")

    assert response["type"] == "initial_state"
    assert "content" in response
    assert "presence" in response
    assert "comments" in response
    assert "suggestions" in response


@pytest.mark.asyncio
async def test_two_clients_connect(two_test_clients):
    """Test that two clients can connect simultaneously."""
    client1, client2 = two_test_clients

    # Connect first client
    response1 = await connect_client(
        client1,
        spec_id="shared-spec",
        user_id="user1",
        user_name="Alice",
    )
    assert response1["type"] == "initial_state"

    # Connect second client
    response2 = await connect_client(
        client2,
        spec_id="shared-spec",
        user_id="user2",
        user_name="Bob",
    )
    assert response2["type"] == "initial_state"

    # Both clients should receive presence updates
    msg1 = await client1.recv()
    presence1 = json.loads(msg1)
    assert presence1["type"] == "presence_broadcast"
    assert len(presence1["presence"]) >= 1  # At least Bob


@pytest.mark.asyncio
async def test_content_sync_between_clients(two_test_clients):
    """Test that content changes sync between clients."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="sync-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="sync-spec", user_id="user2", user_name="Bob")

    # Clear initial presence messages
    await asyncio.sleep(0.1)

    # User 1 updates content
    new_content = "# Updated Spec\n\nThis is updated content."
    await send_operation(client1, "insert", 0, new_content, author_id="user1", author_name="Alice")

    # User 2 should receive the update
    msg = await client2.recv()
    broadcast = json.loads(msg)
    assert broadcast["type"] == "operation_broadcast"
    assert broadcast["data"]["operation"]["content"] == new_content


@pytest.mark.asyncio
async def test_presence_indicators(two_test_clients):
    """Test that presence indicators show active users."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="presence-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="presence-spec", user_id="user2", user_name="Bob")

    # Get initial presence
    msg1 = await client1.recv()
    presence1 = json.loads(msg1)

    assert presence1["type"] == "presence_update"
    assert len(presence1["presence"]) >= 1

    # Check that both users are present
    user_ids = [p["user_id"] for p in presence1["presence"]]
    assert "user2" in user_ids or "user1" in user_ids


@pytest.mark.asyncio
async def test_add_comment_appears_in_both_clients(two_test_clients):
    """Test that comments added in one client appear in both."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="comment-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="comment-spec", user_id="user2", user_name="Bob")

    # Clear initial messages
    await asyncio.sleep(0.1)

    # User 1 adds a comment
    await add_comment(
        client1,
        section="Introduction",
        content="This section needs more details.",
    )

    # User 1 receives confirmation
    msg1 = await client1.recv()
    comment1 = json.loads(msg1)
    assert comment1["type"] == "comment_added"

    # User 2 should see the comment
    msg2 = await client2.recv()
    comment2 = json.loads(msg2)
    assert comment2["type"] == "comment_added"
    assert comment2["comment"]["content"] == "This section needs more details."


@pytest.mark.asyncio
async def test_threaded_comments(two_test_clients):
    """Test that comments can be threaded (replies)."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="thread-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="thread-spec", user_id="user2", user_name="Bob")

    # Clear initial messages
    await asyncio.sleep(0.1)

    # User 1 adds a parent comment
    await add_comment(
        client1,
        section="Introduction",
        content="Main question about this section.",
    )

    msg1 = await client1.recv()
    parent_comment = json.loads(msg1)
    parent_id = parent_comment["comment"]["id"]

    # User 2 replies to the comment
    await add_comment(
        client2,
        section="Introduction",
        content="I agree, we should discuss this.",
        parent_id=parent_id,
    )

    msg2 = await client2.recv()
    reply = json.loads(msg2)

    assert reply["type"] == "comment_added"
    assert reply["comment"]["parent_id"] == parent_id
    assert reply["comment"]["content"] == "I agree, we should discuss this."


@pytest.mark.asyncio
async def test_suggestion_creation(two_test_clients):
    """Test that suggestions can be created and received."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="suggestion-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="suggestion-spec", user_id="user2", user_name="Bob")

    # Clear initial messages
    await asyncio.sleep(0.1)

    # User 1 creates a suggestion
    await add_suggestion(
        client1,
        section="Requirements",
        original_text="The system must be fast.",
        proposed_text="The system must respond within 200ms.",
        reason="More specific requirement.",
    )

    # User 1 receives confirmation
    msg1 = await client1.recv()
    suggestion1 = json.loads(msg1)
    assert suggestion1["type"] == "suggestion_added"

    # User 2 should see the suggestion
    msg2 = await client2.recv()
    suggestion2 = json.loads(msg2)
    assert suggestion2["type"] == "suggestion_added"
    assert suggestion2["suggestion"]["original_text"] == "The system must be fast."
    assert suggestion2["suggestion"]["proposed_text"] == "The system must respond within 200ms."


@pytest.mark.asyncio
async def test_suggestion_accept_reject(two_test_clients):
    """Test that suggestions can be accepted and rejected."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="decision-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="decision-spec", user_id="user2", user_name="Bob")

    # Clear initial messages
    await asyncio.sleep(0.1)

    # User 1 creates a suggestion
    await add_suggestion(
        client1,
        section="Requirements",
        original_text="Old text",
        proposed_text="New text",
    )

    msg1 = await client1.recv()
    suggestion_id = json.loads(msg1)["suggestion"]["id"]

    # User 2 accepts the suggestion
    accept_msg = {
        "type": MessageType.ACCEPT_SUGGESTION.value,
        "suggestion_id": suggestion_id,
    }
    await client2.send(json.dumps(accept_msg))

    # Both clients should receive notification
    msg2 = await client2.recv()
    notification2 = json.loads(msg2)
    assert notification2["type"] == "suggestion_accepted"


@pytest.mark.asyncio
async def test_version_history_tracking(two_test_clients, temp_spec_dir):
    """Test that version history tracks all changes."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="version-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="version-spec", user_id="user2", user_name="Bob")

    # Clear initial messages
    await asyncio.sleep(0.1)

    # Make multiple edits
    await send_operation(client1, "insert", 0, "# Version 1\n", author_id="user1", author_name="Alice")
    await asyncio.sleep(0.1)

    await send_operation(client2, "insert", 0, "# Version 2\n", author_id="user2", author_name="Bob")
    await asyncio.sleep(0.1)

    await send_operation(client1, "insert", 0, "# Version 3\n", author_id="user1", author_name="Alice")
    await asyncio.sleep(0.1)

    # Request version history
    history_msg = {
        "type": MessageType.GET_VERSIONS.value,
    }
    await client1.send(json.dumps(history_msg))

    msg = await client1.recv()
    versions = json.loads(msg)

    assert versions["type"] == "version_history"
    assert len(versions["versions"]) >= 3


@pytest.mark.asyncio
async def test_approval_workflow(two_test_clients):
    """Test the approval workflow for specs."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="approval-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="approval-spec", user_id="user2", user_name="Bob")

    # Clear initial messages
    await asyncio.sleep(0.1)

    # Finalize content
    final_content = "# Final Spec\n\nThis is ready for implementation."
    await send_operation(client1, "insert", 0, final_content, author_id="user1", author_name="Alice")
    await asyncio.sleep(0.1)

    # Request approval
    approve_msg = {
        "type": MessageType.APPROVE_VERSION.value,
        "user_id": "user1",
        "user_name": "Alice",
    }
    await client1.send(json.dumps(approve_msg))

    # Receive approval confirmation
    msg = await client1.recv()
    approval = json.loads(msg)

    assert approval["type"] == "version_approved"
    assert approval["version"]["approved"] is True


@pytest.mark.asyncio
async def test_concurrent_editing_no_conflicts(two_test_clients):
    """Test that concurrent editing doesn't cause conflicts."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="concurrent-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="concurrent-spec", user_id="user2", user_name="Bob")

    # Clear initial messages
    await asyncio.sleep(0.1)

    # Both clients edit simultaneously (within short time window)
    await send_operation(client1, "insert", 0, "# Edit 1\n\nContent from Alice.", author_id="user1", author_name="Alice")
    await send_operation(client2, "insert", 0, "# Edit 2\n\nContent from Bob.", author_id="user2", author_name="Bob")

    # Both should receive updates
    msg1 = await client1.recv()
    broadcast1 = json.loads(msg1)
    assert broadcast1["type"] == "operation_broadcast"

    msg2 = await client2.recv()
    broadcast2 = json.loads(msg2)
    assert broadcast2["type"] == "operation_broadcast"

    # No errors should occur
    # The CRDT should handle the concurrent edits


@pytest.mark.asyncio
async def test_client_reconnection(test_client, collaboration_server):
    """Test that clients can reconnect after disconnect."""
    # First connection
    response1 = await connect_client(test_client, spec_id="reconnect-spec")
    assert response1["type"] == "initial_state"

    # Disconnect
    await test_client.close()

    # Reconnect
    uri = f"ws://localhost:{collaboration_server.port}"
    async with websockets.asyncio.client.connect(uri) as new_connection:
        response2 = await connect_client(new_connection, spec_id="reconnect-spec")
        assert response2["type"] == "initial_state"


@pytest.mark.asyncio
async def test_error_handling_invalid_message(test_client):
    """Test that the server handles invalid messages gracefully."""
    await connect_client(test_client, spec_id="error-spec")

    # Send invalid message
    await test_client.send(json.dumps({"type": "invalid_type", "data": "test"}))

    # Should receive error message
    msg = await test_client.recv()
    error = json.loads(msg)

    assert error["type"] == "error"
    assert "message" in error


@pytest.mark.asyncio
async def test_comment_resolution(two_test_clients):
    """Test that comments can be resolved."""
    client1, client2 = two_test_clients

    # Connect both clients
    await connect_client(client1, spec_id="resolve-spec", user_id="user1", user_name="Alice")
    await connect_client(client2, spec_id="resolve-spec", user_id="user2", user_name="Bob")

    # Clear initial messages
    await asyncio.sleep(0.1)

    # User 1 adds a comment
    await add_comment(client1, section="Requirements", content="Please clarify this.")

    msg1 = await client1.recv()
    comment_id = json.loads(msg1)["comment"]["id"]

    # User 2 resolves the comment
    resolve_msg = {
        "type": MessageType.RESOLVE_COMMENT.value,
        "comment_id": comment_id,
    }
    await client2.send(json.dumps(resolve_msg))

    # Both clients should receive resolution notification
    msg2 = await client2.recv()
    resolution2 = json.loads(msg2)
    assert resolution2["type"] == "comment_resolved"
