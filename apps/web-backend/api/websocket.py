"""
WebSocket Endpoint for Real-Time Agent Progress

Provides WebSocket connections for clients to receive real-time agent progress updates.
Clients can subscribe to specific spec IDs and receive execution, ideation, and roadmap events.
"""

import asyncio
import json
import logging
import os
from datetime import datetime

from core.security import verify_websocket_token
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from api.models.agent_event import (
    AgentEvent,
    ErrorEvent,
    LogEvent,
)

logger = logging.getLogger(__name__)


def _sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")


router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Handles client subscriptions to specific spec IDs and broadcasts
    events to all subscribed clients.
    """

    def __init__(self):
        # Active connections: {websocket: {"subscriptions": set of spec_ids, "user": user_claims}}
        self.active_connections: dict[WebSocket, dict] = {}
        # Reverse index: {spec_id: set of subscribed websockets}
        self.spec_subscriptions: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_claims: dict | None = None):
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_claims: Optional dictionary of authenticated user claims
        """
        await websocket.accept()
        self.active_connections[websocket] = {
            "subscriptions": set(),
            "user": user_claims or {},
        }
        user_id = user_claims.get("sub", "anonymous") if user_claims else "anonymous"
        logger.info(
            f"WebSocket connected: {id(websocket)} (user: {_sanitize_log(user_id)})"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection and clean up subscriptions"""
        if websocket in self.active_connections:
            # Remove from spec subscriptions
            for spec_id in self.active_connections[websocket]["subscriptions"]:
                if spec_id in self.spec_subscriptions:
                    self.spec_subscriptions[spec_id].discard(websocket)
                    if not self.spec_subscriptions[spec_id]:
                        del self.spec_subscriptions[spec_id]

            # Remove connection
            user_id = (
                self.active_connections[websocket].get("user", {}).get("sub", "unknown")
            )
            del self.active_connections[websocket]
            logger.info(
                f"WebSocket disconnected: {id(websocket)} (user: {_sanitize_log(user_id)})"
            )

    def subscribe(self, websocket: WebSocket, spec_id: str):
        """Subscribe a WebSocket to a specific spec ID"""
        if websocket in self.active_connections:
            self.active_connections[websocket]["subscriptions"].add(spec_id)
            if spec_id not in self.spec_subscriptions:
                self.spec_subscriptions[spec_id] = set()
            self.spec_subscriptions[spec_id].add(websocket)
            logger.info(
                f"WebSocket {id(websocket)} subscribed to spec {_sanitize_log(spec_id)}"
            )

    def unsubscribe(self, websocket: WebSocket, spec_id: str):
        """Unsubscribe a WebSocket from a specific spec ID"""
        if websocket in self.active_connections:
            self.active_connections[websocket]["subscriptions"].discard(spec_id)
            if spec_id in self.spec_subscriptions:
                self.spec_subscriptions[spec_id].discard(websocket)
                if not self.spec_subscriptions[spec_id]:
                    del self.spec_subscriptions[spec_id]
            logger.info(
                f"WebSocket {id(websocket)} unsubscribed from spec {_sanitize_log(spec_id)}"
            )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to {id(websocket)}: {e}")

    async def broadcast_to_spec(self, spec_id: str, event: AgentEvent):
        """
        Broadcast an event to all clients subscribed to a specific spec ID.

        Args:
            spec_id: The spec ID to broadcast to
            event: The event to broadcast (must be a subclass of AgentEvent)
        """
        if spec_id not in self.spec_subscriptions:
            logger.debug(f"No subscribers for spec {_sanitize_log(spec_id)}")
            return

        subscribers = list(self.spec_subscriptions[spec_id])
        if not subscribers:
            return

        message = event.model_dump(mode="json")
        logger.debug(
            f"Broadcasting to {len(subscribers)} subscribers of spec {_sanitize_log(spec_id)}: {event.event_type}"
        )

        disconnected = []
        for websocket in subscribers:
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to {id(websocket)}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)

    async def broadcast_to_all(self, event: AgentEvent):
        """
        Broadcast an event to all connected clients (regardless of subscription).

        Args:
            event: The event to broadcast
        """
        if not self.active_connections:
            return

        message = event.model_dump(mode="json")
        logger.debug(
            f"Broadcasting to all {len(self.active_connections)} clients: {event.event_type}"
        )

        disconnected = []
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to {id(websocket)}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/agent-events")
async def agent_events_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent events.

    Authentication:
        Clients must provide a valid JWT token via query parameter.
        Example: ws://localhost:8000/ws/agent-events?token=<your-jwt-token>

    Protocol:
        Client -> Server:
            {"action": "subscribe", "spec_id": "001"}
            {"action": "unsubscribe", "spec_id": "001"}
            {"action": "ping"}

        Server -> Client:
            {"event_type": "execution", "spec_id": "001", "timestamp": "...", "data": {...}}
            {"event_type": "log", "spec_id": "001", "timestamp": "...", "log_line": "..."}
            {"event_type": "error", "spec_id": "001", "timestamp": "...", "error_message": "..."}
            {"status": "error", "message": "Authentication failed"} (on auth failure)

    Example:
        // With authentication
        const token = localStorage.getItem('auth_token');
        const ws = new WebSocket(`ws://localhost:8000/ws/agent-events?token=${token}`);
        ws.send(JSON.stringify({action: "subscribe", spec_id: "001"}));
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Received event:", data);
        };
    """
    # Extract and validate token from query parameters
    token = websocket.query_params.get("token")
    user_claims = None

    try:
        user_claims = verify_websocket_token(token)
    except Exception as e:
        # Accept the connection first (required by FastAPI), then close with error
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(f"WebSocket authentication failed: {e}")
        return

    # Connect with authenticated user claims
    await manager.connect(websocket, user_claims)

    # Send connection confirmation
    user_id = user_claims.get("sub", "unknown")
    await manager.send_personal_message(
        {
            "status": "connected",
            "user": user_id,
            "timestamp": datetime.now().isoformat(),
        },
        websocket,
    )

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    spec_id = message.get("spec_id")
                    if spec_id:
                        manager.subscribe(websocket, spec_id)
                        await manager.send_personal_message(
                            {
                                "status": "subscribed",
                                "spec_id": spec_id,
                                "timestamp": datetime.now().isoformat(),
                            },
                            websocket,
                        )
                    else:
                        await manager.send_personal_message(
                            {
                                "status": "error",
                                "message": "spec_id is required for subscribe action",
                            },
                            websocket,
                        )

                elif action == "unsubscribe":
                    spec_id = message.get("spec_id")
                    if spec_id:
                        manager.unsubscribe(websocket, spec_id)
                        await manager.send_personal_message(
                            {
                                "status": "unsubscribed",
                                "spec_id": spec_id,
                                "timestamp": datetime.now().isoformat(),
                            },
                            websocket,
                        )

                elif action == "ping":
                    await manager.send_personal_message(
                        {"status": "pong", "timestamp": datetime.now().isoformat()},
                        websocket,
                    )

                else:
                    await manager.send_personal_message(
                        {"status": "error", "message": f"Unknown action: {action}"},
                        websocket,
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"status": "error", "message": "Invalid JSON"}, websocket
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await manager.send_personal_message(
                    {"status": "error", "message": str(e)}, websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Client disconnected: {id(websocket)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Helper functions for broadcasting events from other parts of the application


async def broadcast_execution_event(
    spec_id: str,
    phase: str,
    phase_progress: float = 0.0,
    overall_progress: float = 0.0,
    message: str = None,
    current_subtask: str = None,
):
    """
    Helper function to broadcast execution progress events.

    Can be called from agent execution code to push real-time updates.
    """
    from api.models.agent_event import ExecutionEvent, ExecutionProgressData

    event = ExecutionEvent(
        event_type="execution",
        timestamp=datetime.now().isoformat(),
        spec_id=spec_id,
        data=ExecutionProgressData(
            phase=phase,
            phase_progress=phase_progress,
            overall_progress=overall_progress,
            message=message,
            current_subtask=current_subtask,
        ),
    )
    await manager.broadcast_to_spec(spec_id, event)


async def broadcast_log_event(spec_id: str, log_line: str, level: str = "info"):
    """
    Helper function to broadcast log events.

    Can be called to stream agent logs to connected clients.
    """
    event = LogEvent(
        event_type="log",
        timestamp=datetime.now().isoformat(),
        spec_id=spec_id,
        log_line=log_line,
        level=level,
        data=None,
    )
    await manager.broadcast_to_spec(spec_id, event)


async def broadcast_error_event(
    spec_id: str, error_message: str, error_type: str = None, traceback: str = None
):
    """
    Helper function to broadcast error events.

    Can be called when agent execution encounters errors.
    """
    event = ErrorEvent(
        event_type="error",
        timestamp=datetime.now().isoformat(),
        spec_id=spec_id,
        error_message=error_message,
        error_type=error_type,
        traceback=traceback,
        data=None,
    )
    await manager.broadcast_to_spec(spec_id, event)


@router.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for interactive PTY terminal sessions.

    Authentication:
        Clients must provide a valid JWT token via query parameter.
        Example: ws://localhost:8000/ws/terminal?token=<your-jwt-token>&session_id=<session-id>

    Protocol:
        Client -> Server:
            {"type": "input", "data": "<keystrokes>"}
            {"type": "resize", "rows": 24, "cols": 80}
            {"type": "ping"}

        Server -> Client:
            {"type": "output", "data": "<terminal output>"}
            {"type": "error", "message": "<error message>"}
            {"type": "status", "status": "connected|closed"}
            {"type": "pong"}

    Terminal Features:
        - Full shell access with PTY (supports colors, formatting, interactive apps)
        - ANSI escape sequence support (xterm-256color)
        - Dynamic terminal resize
        - Automatic cleanup on disconnect
        - Session isolation per connection

    Example:
        // Connect to terminal with authentication
        const token = localStorage.getItem('auth_token');
        const sessionId = 'my-terminal-session';
        const ws = new WebSocket(
            `ws://localhost:8000/ws/terminal?token=${token}&session_id=${sessionId}`
        );

        // Send input
        ws.send(JSON.stringify({type: "input", data: "ls -la\\n"}));

        // Receive output and write to xterm.js
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === "output") {
                term.write(data.data);
            }
        };

        // Resize terminal
        const resize = {type: "resize", rows: 40, cols: 120};
        ws.send(JSON.stringify(resize));
    """
    # Extract and validate token from query parameters
    token = websocket.query_params.get("token")
    session_id = websocket.query_params.get("session_id", "default")

    try:
        user_claims = verify_websocket_token(token)
    except Exception as e:
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(f"Terminal WebSocket authentication failed: {e}")
        return

    # Import terminal manager here to avoid circular imports
    from services.terminal_manager import terminal_manager

    # Accept the WebSocket connection
    await websocket.accept()

    # Get or create terminal session
    session = terminal_manager.get_session(session_id)
    if not session:
        # Create new session with user's home directory or default project directory
        working_dir = user_claims.get("working_dir", os.getcwd())
        session = terminal_manager.create_session(
            session_id=session_id,
            working_dir=working_dir,
            shell=os.environ.get("SHELL", "/bin/bash"),  # nosec B604 - Intentional: terminal feature requires shell
            rows=24,
            cols=80,
        )

        if not session:
            await websocket.send_json(
                {"type": "error", "message": "Failed to create terminal session"}
            )
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

    # Send connection confirmation
    user_id = user_claims.get("sub", "unknown")
    await websocket.send_json(
        {
            "type": "status",
            "status": "connected",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }
    )
    logger.info(
        f"Terminal WebSocket connected: session={_sanitize_log(session_id)} user={_sanitize_log(user_id)}"
    )

    # Start output reader task
    read_task = asyncio.create_task(_read_terminal_output(session, websocket))

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "input":
                    # Write input to terminal
                    input_data = message.get("data", "")
                    session.write_input(input_data)

                elif msg_type == "resize":
                    # Resize terminal
                    rows = message.get("rows", 24)
                    cols = message.get("cols", 80)
                    session.resize(rows, cols)
                    logger.debug(
                        "Terminal resized: session=%s size=%dx%d",
                        _sanitize_log(session_id),
                        int(rows),
                        int(cols),
                    )

                elif msg_type == "ping":
                    await websocket.send_json(
                        {"type": "pong", "timestamp": datetime.now().isoformat()}
                    )

                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {msg_type}",
                        }
                    )

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Error processing terminal message: {e}")
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        logger.info(
            f"Terminal WebSocket disconnected: session={_sanitize_log(session_id)}"
        )
    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
    finally:
        # Cancel read task
        read_task.cancel()
        try:
            await read_task
        except asyncio.CancelledError:
            pass  # Expected: read_task was intentionally cancelled

        # Send close status
        try:
            await websocket.send_json(
                {
                    "type": "status",
                    "status": "closed",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception:  # nosec B110 - Cleanup handler: ignore send errors on disconnect
            pass

        # Clean up session
        terminal_manager.close_session(session_id)


async def _read_terminal_output(session, websocket: WebSocket):
    """
    Continuously read output from terminal PTY and send to WebSocket.

    Args:
        session: TerminalSession object
        websocket: WebSocket connection to send output to
    """
    try:
        while session.is_alive():
            output = await session.read_output()
            if output:
                await websocket.send_json({"type": "output", "data": output})
            else:
                # Small delay to avoid busy waiting
                await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        logger.debug(
            f"Terminal output reader cancelled for session {_sanitize_log(session.session_id)}"
        )
    except Exception as e:
        logger.error(f"Error reading terminal output: {e}")


# Export the manager for use in other modules
__all__ = [
    "router",
    "manager",
    "broadcast_execution_event",
    "broadcast_log_event",
    "broadcast_error_event",
]
