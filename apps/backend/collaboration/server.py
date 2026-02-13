"""
WebSocket Server for Real-time Collaboration
============================================

Async WebSocket server for real-time collaborative spec editing.
Handles multiple clients, broadcasts CRDT operations, and manages presence.

Usage:
    python -m collaboration.server [--host HOST] [--port PORT]

Example:
    python -m collaboration.server --host localhost --port 8765
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import websockets.asyncio.server
from pydantic import BaseModel, Field

from collaboration.crdt_store import CRDTStore
from collaboration.models import (
    Comment,
    CommentStatus,
    Presence,
    PresenceType,
    Suggestion,
    SuggestionStatus,
    load_comments,
    load_suggestions,
    save_comments,
    save_suggestions,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import websockets
    from websockets.asyncio.server import WebSocketServerProtocol


class MessageType(str, Enum):
    """Type of WebSocket message."""

    # Client to server
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    OPERATION = "operation"
    PRESENCE_UPDATE = "presence_update"
    GET_CONTENT = "get_content"
    ADD_COMMENT = "add_comment"
    RESOLVE_COMMENT = "resolve_comment"
    ADD_SUGGESTION = "add_suggestion"
    REVIEW_SUGGESTION = "review_suggestion"

    # Server to client
    CONTENT_UPDATE = "content_update"
    OPERATION_BROADCAST = "operation_broadcast"
    PRESENCE_BROADCAST = "presence_broadcast"
    COMMENT_ADDED = "comment_added"
    COMMENT_RESOLVED = "comment_resolved"
    SUGGESTION_ADDED = "suggestion_added"
    SUGGESTION_REVIEWED = "suggestion_reviewed"
    ERROR = "error"
    INIT_STATE = "initial_state"


class WebSocketMessage(BaseModel):
    """A WebSocket message for client-server communication."""

    type: MessageType = Field(description="Message type")
    spec_id: str | None = Field(default=None, description="Spec identifier")
    data: dict = Field(default_factory=dict, description="Message payload")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Message timestamp",
    )

    def to_json(self) -> str:
        """Convert message to JSON string.

        Returns:
            JSON representation of the message
        """
        return self.model_dump_json()


class ConnectedClient:
    """Represents a connected WebSocket client."""

    def __init__(
        self,
        websocket: WebSocketServerProtocol,
        client_id: str,
        spec_id: str,
        user_id: str,
        user_name: str,
    ):
        """Initialize a connected client.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
            spec_id: Spec this client is editing
            user_id: User identifier
            user_name: Display name of user
        """
        self.websocket = websocket
        self.client_id = client_id
        self.spec_id = spec_id
        self.user_id = user_id
        self.user_name = user_name
        self.connected_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)

    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if client connection is stale.

        Args:
            timeout_seconds: Seconds before considering client stale

        Returns:
            True if client is stale
        """
        elapsed = (datetime.now(timezone.utc) - self.last_activity).total_seconds()
        return elapsed > timeout_seconds


class CollaborationServer:
    """WebSocket server for real-time collaborative editing."""

    def __init__(self, host: str = "localhost", port: int = 8765, spec_dir: Path | None = None):
        """Initialize the collaboration server.

        Args:
            host: Host to bind to
            port: Port to listen on
            spec_dir: Base directory for spec files (defaults to .auto-claude/specs or module-level _collaboration_dir)
        """
        self.host = host
        self.port = port
        # Check for module-level _collaboration_dir (used in tests)
        import collaboration
        if spec_dir is None and hasattr(collaboration, '_collaboration_dir'):
            spec_dir = collaboration._collaboration_dir
        self.spec_dir = spec_dir or Path.cwd() / ".auto-claude" / "specs"
        self.clients: dict[str, ConnectedClient] = {}
        # Maps spec_id -> list of client_ids
        self.spec_clients: dict[str, list[str]] = {}
        # Maps spec_id -> CRDTStore instance
        self.spec_stores: dict[str, CRDTStore] = {}
        # Maps spec_id -> presence data
        self.spec_presence: dict[str, dict[str, Presence]] = {}
        # Server task for lifecycle management
        self._server_task: asyncio.Task | None = None

    async def handle_client(self, websocket: WebSocketServerProtocol, client_id: str):
        """Handle a client connection.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        client: ConnectedClient | None = None

        try:
            # Wait for connect message
            init_message = await websocket.recv()
            init_data = json.loads(init_message)

            if init_data.get("type") != MessageType.CONNECT.value:
                await self.send_error(websocket, "First message must be CONNECT")
                return

            spec_id = init_data.get("spec_id")
            user_id = init_data.get("user_id") or client_id
            user_name = init_data.get("user_name", "Anonymous")

            if not spec_id:
                await self.send_error(websocket, "spec_id is required")
                return

            # Create client instance
            client = ConnectedClient(
                websocket=websocket,
                client_id=client_id,
                spec_id=spec_id,
                user_id=user_id,
                user_name=user_name,
            )

            # Register client
            await self._register_client(client)

            logger.info(
                "Client connected: %s (user=%s, spec=%s)",
                client_id,
                user_name,
                spec_id,
            )

            # Send initial state
            await self._send_initial_state(client)

            # Handle messages
            async for raw_message in websocket:
                try:
                    client.last_activity = datetime.now(timezone.utc)
                    message_data = json.loads(raw_message)

                    # Validate message structure
                    if "type" not in message_data:
                        logger.warning("Received message without type field")
                        continue

                    await self._handle_message(client, message_data)

                except json.JSONDecodeError as e:
                    logger.error("Failed to decode message: %s", e)
                    await self.send_error(websocket, f"Invalid JSON: {e}")
                except Exception as e:
                    logger.exception("Error handling message: %s")
                    await self.send_error(websocket, f"Internal error: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected: %s", client_id)
        except Exception as e:
            logger.exception("Error in client handler: %s")
        finally:
            if client:
                await self._unregister_client(client)

    async def _register_client(self, client: ConnectedClient):
        """Register a connected client.

        Args:
            client: Client to register
        """
        self.clients[client.client_id] = client

        # Add to spec client list
        if client.spec_id not in self.spec_clients:
            self.spec_clients[client.spec_id] = []
        self.spec_clients[client.spec_id].append(client.client_id)

        # Initialize CRDT store for spec if needed
        if client.spec_id not in self.spec_stores:
            store = CRDTStore(spec_id=client.spec_id)
            # Try to load from disk
            # For now, we'll initialize empty state
            # TODO: Load from spec directory when integrated with file system
            self.spec_stores[client.spec_id] = store

        # Add presence
        await self._update_presence(client, PresenceType.VIEWING, None)

        # Broadcast presence update to other clients
        await self._broadcast_presence(client.spec_id, exclude_client=client.client_id)

    async def _unregister_client(self, client: ConnectedClient):
        """Unregister a disconnected client.

        Args:
            client: Client to unregister
        """
        # Remove from clients dict
        if client.client_id in self.clients:
            del self.clients[client.client_id]

        # Remove from spec client list
        if client.spec_id in self.spec_clients:
            self.spec_clients[client.spec_id] = [
                cid for cid in self.spec_clients[client.spec_id] if cid != client.client_id
            ]

        # Remove presence
        if client.spec_id in self.spec_presence:
            if client.user_id in self.spec_presence[client.spec_id]:
                del self.spec_presence[client.spec_id][client.user_id]

        # Broadcast presence update
        await self._broadcast_presence(client.spec_id)

        logger.info(
            "Unregistered client %s from spec %s",
            client.client_id,
            client.spec_id,
        )

    async def _send_initial_state(self, client: ConnectedClient):
        """Send initial state to a newly connected client.

        Args:
            client: Client to send state to
        """
        store = self.spec_stores.get(client.spec_id)
        if not store:
            await self.send_error(
                client.websocket,
                f"No CRDT store found for spec {client.spec_id}",
            )
            return

        # Load comments and suggestions from storage
        comments_list = load_comments(self.spec_dir / client.spec_id)
        suggestions_list = load_suggestions(self.spec_dir / client.spec_id)

        # Send flattened initial state (no nested 'data' wrapper)
        initial_state = {
            "type": "initial_state",
            "spec_id": client.spec_id,
            "content": store.get_content(),
            "operations": store.get_operation_history(),
            "presence": [
                p.to_dict()
                for p in self.spec_presence.get(client.spec_id, {}).values()
            ],
            "comments": [c.to_dict() for c in comments_list],
            "suggestions": [s.to_dict() for s in suggestions_list],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await client.websocket.send(json.dumps(initial_state))

    async def _handle_message(self, client: ConnectedClient, message_data: dict):
        """Handle a message from a client.

        Args:
            client: Client that sent the message
            message_data: Parsed message data
        """
        message_type = message_data.get("type")
        data = message_data.get("data", {})

        if message_type == MessageType.OPERATION.value:
            await self._handle_operation(client, data)

        elif message_type == MessageType.PRESENCE_UPDATE.value:
            await self._handle_presence_update(client, data)

        elif message_type == MessageType.GET_CONTENT.value:
            await self._handle_get_content(client)

        elif message_type == MessageType.ADD_COMMENT.value:
            await self._handle_add_comment(client, data)

        elif message_type == MessageType.RESOLVE_COMMENT.value:
            await self._handle_resolve_comment(client, data)

        elif message_type == MessageType.ADD_SUGGESTION.value:
            await self._handle_add_suggestion(client, data)

        elif message_type == MessageType.REVIEW_SUGGESTION.value:
            await self._handle_review_suggestion(client, data)

        else:
            logger.warning("Unknown message type: %s", message_type)

    async def _handle_operation(self, client: ConnectedClient, data: dict):
        """Handle a CRDT operation from a client.

        Args:
            client: Client that sent the operation
            data: Operation data
        """
        store = self.spec_stores.get(client.spec_id)
        if not store:
            await self.send_error(
                client.websocket,
                f"No CRDT store found for spec {client.spec_id}",
            )
            return

        try:
            # Apply operation to store
            op_data = data.get("operation")
            if not op_data:
                await self.send_error(client.websocket, "Operation data is required")
                return

            # Apply the operation
            success = store.apply_remote_operation(op_data)

            if success:
                # Broadcast to all other clients in the same spec
                broadcast_message = WebSocketMessage(
                    type=MessageType.OPERATION_BROADCAST,
                    spec_id=client.spec_id,
                    data={
                        "operation": op_data,
                        "author_id": client.user_id,
                        "author_name": client.user_name,
                    },
                )

                await self._broadcast_to_spec(
                    client.spec_id,
                    broadcast_message.to_json(),
                    exclude_client=client.client_id,
                )

                logger.debug(
                    "Applied operation from %s for spec %s",
                    client.client_id,
                    client.spec_id,
                )

        except Exception as e:
            logger.exception("Failed to apply operation: %s")
            await self.send_error(client.websocket, f"Failed to apply operation: {e}")

    async def _handle_presence_update(self, client: ConnectedClient, data: dict):
        """Handle a presence update from a client.

        Args:
            client: Client that sent the update
            data: Presence update data
        """
        presence_type = data.get("presence_type")
        section_id = data.get("section_id")
        cursor_position = data.get("cursor_position")

        # Validate presence type
        try:
            if isinstance(presence_type, str):
                presence_type = PresenceType(presence_type)
        except ValueError:
            logger.warning("Invalid presence type: %s", presence_type)
            presence_type = PresenceType.VIEWING

        await self._update_presence(client, presence_type, section_id, cursor_position)

        # Broadcast to other clients
        await self._broadcast_presence(client.spec_id, exclude_client=client.client_id)

    async def _handle_get_content(self, client: ConnectedClient):
        """Handle a request for current content.

        Args:
            client: Client requesting content
        """
        store = self.spec_stores.get(client.spec_id)
        if not store:
            await self.send_error(
                client.websocket,
                f"No CRDT store found for spec {client.spec_id}",
            )
            return

        message = WebSocketMessage(
            type=MessageType.CONTENT_UPDATE,
            spec_id=client.spec_id,
            data={"content": store.get_content()},
        )

        await client.websocket.send(message.to_json())

    async def _handle_add_comment(self, client: ConnectedClient, data: dict):
        """Handle adding a new comment.

        Args:
            client: Client adding the comment
            data: Comment data
        """
        spec_id = client.spec_id
        section_id = data.get("section_id")
        content = data.get("content")
        parent_id = data.get("parent_id")

        if not content:
            await self.send_error(client.websocket, "Comment content is required")
            return

        # Create comment
        comment = Comment(
            id=str(uuid.uuid4()),
            spec_id=spec_id,
            section_id=section_id,
            author=client.user_id,
            author_name=client.user_name,
            content=content,
            parent_id=parent_id,
        )

        # Save to disk
        spec_dir = Path(f".auto-claude/specs/{spec_id}")
        comments = load_comments(spec_dir)
        comments.append(comment)
        save_comments(spec_dir, comments)

        # Broadcast to all clients in the spec
        message = WebSocketMessage(
            type=MessageType.COMMENT_ADDED,
            spec_id=spec_id,
            data={"comment": comment.to_dict()},
        )

        await self._broadcast_to_spec(spec_id, message.to_json())

        logger.info("Added comment %s to spec %s", comment.id, spec_id)

    async def _handle_resolve_comment(self, client: ConnectedClient, data: dict):
        """Handle resolving a comment.

        Args:
            client: Client resolving the comment
            data: Comment resolution data
        """
        comment_id = data.get("comment_id")
        if not comment_id:
            await self.send_error(client.websocket, "comment_id is required")
            return

        spec_dir = Path(f".auto-claude/specs/{client.spec_id}")
        comments = load_comments(spec_dir)

        # Find and update comment
        for comment in comments:
            if comment.id == comment_id:
                comment.status = CommentStatus.RESOLVED
                comment.resolved_by = client.user_id
                comment.resolved_at = datetime.now(timezone.utc)
                break

        save_comments(spec_dir, comments)

        # Broadcast resolution
        message = WebSocketMessage(
            type=MessageType.COMMENT_RESOLVED,
            spec_id=client.spec_id,
            data={
                "comment_id": comment_id,
                "resolved_by": client.user_id,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        await self._broadcast_to_spec(client.spec_id, message.to_json())

    async def _handle_add_suggestion(self, client: ConnectedClient, data: dict):
        """Handle adding a new suggestion.

        Args:
            client: Client adding the suggestion
            data: Suggestion data
        """
        spec_id = client.spec_id
        section_id = data.get("section_id")
        original_text = data.get("original_text")
        suggested_text = data.get("suggested_text")
        reason = data.get("reason")

        if not suggested_text:
            await self.send_error(client.websocket, "suggested_text is required")
            return

        # Create suggestion
        suggestion = Suggestion(
            id=str(uuid.uuid4()),
            spec_id=spec_id,
            section_id=section_id,
            author=client.user_id,
            author_name=client.user_name,
            original_text=original_text or "",
            suggested_text=suggested_text,
            reason=reason,
        )

        # Save to disk
        spec_dir = Path(f".auto-claude/specs/{spec_id}")
        suggestions = load_suggestions(spec_dir)
        suggestions.append(suggestion)
        save_suggestions(spec_dir, suggestions)

        # Broadcast to all clients
        message = WebSocketMessage(
            type=MessageType.SUGGESTION_ADDED,
            spec_id=spec_id,
            data={"suggestion": suggestion.to_dict()},
        )

        await self._broadcast_to_spec(spec_id, message.to_json())

        logger.info("Added suggestion %s to spec %s", suggestion.id, spec_id)

    async def _handle_review_suggestion(self, client: ConnectedClient, data: dict):
        """Handle reviewing a suggestion (accept/reject).

        Args:
            client: Client reviewing the suggestion
            data: Suggestion review data
        """
        suggestion_id = data.get("suggestion_id")
        status = data.get("status")
        review_comment = data.get("review_comment")

        if not suggestion_id or not status:
            await self.send_error(
                client.websocket,
                "suggestion_id and status are required",
            )
            return

        try:
            suggestion_status = SuggestionStatus(status)
        except ValueError:
            await self.send_error(client.websocket, f"Invalid status: {status}")
            return

        # Load and update suggestion
        spec_dir = Path(f".auto-claude/specs/{client.spec_id}")
        suggestions = load_suggestions(spec_dir)

        for suggestion in suggestions:
            if suggestion.id == suggestion_id:
                suggestion.status = suggestion_status
                suggestion.reviewed_by = client.user_id
                suggestion.reviewed_at = datetime.now(timezone.utc)
                suggestion.review_comment = review_comment
                break

        save_suggestions(spec_dir, suggestions)

        # Broadcast review
        message = WebSocketMessage(
            type=MessageType.SUGGESTION_REVIEWED,
            spec_id=client.spec_id,
            data={
                "suggestion_id": suggestion_id,
                "status": suggestion_status.value,
                "reviewed_by": client.user_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "review_comment": review_comment,
            },
        )

        await self._broadcast_to_spec(client.spec_id, message.to_json())

    async def _update_presence(
        self,
        client: ConnectedClient,
        presence_type: PresenceType,
        section_id: str | None,
        cursor_position: int | None = None,
    ):
        """Update presence for a client.

        Args:
            client: Client to update presence for
            presence_type: Type of presence
            section_id: Section being viewed/edited
            cursor_position: Optional cursor position
        """
        if client.spec_id not in self.spec_presence:
            self.spec_presence[client.spec_id] = {}

        self.spec_presence[client.spec_id][client.user_id] = Presence(
            spec_id=client.spec_id,
            user_id=client.user_id,
            user_name=client.user_name,
            presence_type=presence_type,
            section_id=section_id,
            cursor_position=cursor_position,
            last_seen=datetime.now(timezone.utc),
        )

    async def _broadcast_presence(self, spec_id: str, exclude_client: str | None = None):
        """Broadcast presence updates to all clients in a spec.

        Args:
            spec_id: Spec to broadcast to
            exclude_client: Optional client ID to exclude
        """
        presence_list = [
            p.to_dict()
            for p in self.spec_presence.get(spec_id, {}).values()
            if not p.is_stale(timeout_seconds=60)
        ]

        message = WebSocketMessage(
            type=MessageType.PRESENCE_BROADCAST,
            spec_id=spec_id,
            data={"presence": presence_list},
        )

        await self._broadcast_to_spec(
            spec_id,
            message.to_json(),
            exclude_client=exclude_client,
        )

    async def _broadcast_to_spec(
        self,
        spec_id: str,
        message: str,
        exclude_client: str | None = None,
    ):
        """Broadcast a message to all clients in a spec.

        Args:
            spec_id: Spec to broadcast to
            message: JSON message to broadcast
            exclude_client: Optional client ID to exclude
        """
        client_ids = self.spec_clients.get(spec_id, [])

        for client_id in client_ids:
            if exclude_client and client_id == exclude_client:
                continue

            client = self.clients.get(client_id)
            if client and not client.is_stale():
                try:
                    await client.websocket.send(message)
                except Exception as e:
                    logger.warning(
                        "Failed to send message to client %s: %s",
                        client_id,
                        e,
                    )

    async def send_error(self, websocket: WebSocketServerProtocol, message: str):
        """Send an error message to a client.

        Args:
            websocket: WebSocket connection
            message: Error message
        """
        error_message = WebSocketMessage(
            type=MessageType.ERROR,
            data={"error": message},
        )

        try:
            await websocket.send(error_message.to_json())
        except Exception as e:
            logger.warning("Failed to send error message: %s", e)

    async def start(self):
        """Start the WebSocket server."""
        logger.info("Starting collaboration server on %s:%d", self.host, self.port)

        async def handler(websocket: WebSocketServerProtocol):
            # Generate unique client ID
            client_id = str(uuid.uuid4())
            await self.handle_client(websocket, client_id)

        # Use websockets.asyncio.server.serve for websockets 12+
        async with websockets.asyncio.server.serve(
            handler,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ):
            logger.info("Server started on ws://%s:%d", self.host, self.port)
            # Keep server running
            await asyncio.Future()  # Run forever

    async def stop(self):
        """Stop the WebSocket server.

        Note: With context manager pattern, the server stops automatically
        when the context exits. This method is a placeholder for potential
        future explicit shutdown logic.
        """
        logger.info("Server shutdown requested")

    async def run(self):
        """Run server (alias for start, test compatibility)."""
        self._server_task = asyncio.create_task(self.start())
        await self._server_task

    def shutdown(self):
        """Shutdown server (test cleanup)."""
        if self._server_task:
            self._server_task.cancel()


def _setup_logging(level: str = "INFO"):
    """Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main():
    """Main entry point for the collaboration server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WebSocket server for real-time collaborative spec editing"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("COLLABORATION_HOST", "localhost"),
        help="Host to bind to (default: localhost from env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("COLLABORATION_PORT", "8765")),
        help="Port to listen on (default: 8765 from env var)",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    _setup_logging(args.log_level)

    server = CollaborationServer(host=args.host, port=args.port)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
