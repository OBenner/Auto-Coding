"""
WebSocket Endpoint for Real-Time Agent Progress

Provides WebSocket connections for clients to receive real-time agent progress updates.
Clients can subscribe to specific spec IDs and receive execution, ideation, and roadmap events.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from api.models.agent_event import (
    AgentEvent,
    ExecutionEvent,
    IdeationEvent,
    RoadmapEvent,
    LogEvent,
    ErrorEvent,
    WebSocketMessage,
    PhaseEvent,
)
from api.models.pair_programming import SuggestionEvent

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Handles client subscriptions to specific spec IDs and broadcasts
    events to all subscribed clients.
    """

    def __init__(self):
        # Active connections: {websocket: set of subscribed spec_ids}
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        # Reverse index: {spec_id: set of subscribed websockets}
        self.spec_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[websocket] = set()
        logger.info(f"WebSocket connected: {id(websocket)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection and clean up subscriptions"""
        if websocket in self.active_connections:
            # Remove from spec subscriptions
            for spec_id in self.active_connections[websocket]:
                if spec_id in self.spec_subscriptions:
                    self.spec_subscriptions[spec_id].discard(websocket)
                    if not self.spec_subscriptions[spec_id]:
                        del self.spec_subscriptions[spec_id]

            # Remove connection
            del self.active_connections[websocket]
            logger.info(f"WebSocket disconnected: {id(websocket)}")

    def subscribe(self, websocket: WebSocket, spec_id: str):
        """Subscribe a WebSocket to a specific spec ID"""
        if websocket in self.active_connections:
            self.active_connections[websocket].add(spec_id)
            if spec_id not in self.spec_subscriptions:
                self.spec_subscriptions[spec_id] = set()
            self.spec_subscriptions[spec_id].add(websocket)
            logger.info(f"WebSocket {id(websocket)} subscribed to spec {spec_id}")

    def unsubscribe(self, websocket: WebSocket, spec_id: str):
        """Unsubscribe a WebSocket from a specific spec ID"""
        if websocket in self.active_connections:
            self.active_connections[websocket].discard(spec_id)
            if spec_id in self.spec_subscriptions:
                self.spec_subscriptions[spec_id].discard(websocket)
                if not self.spec_subscriptions[spec_id]:
                    del self.spec_subscriptions[spec_id]
            logger.info(f"WebSocket {id(websocket)} unsubscribed from spec {spec_id}")

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
            logger.debug(f"No subscribers for spec {spec_id}")
            return

        subscribers = list(self.spec_subscriptions[spec_id])
        if not subscribers:
            return

        message = event.model_dump(mode="json")
        logger.debug(f"Broadcasting to {len(subscribers)} subscribers of spec {spec_id}: {event.event_type}")

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
        logger.debug(f"Broadcasting to all {len(self.active_connections)} clients: {event.event_type}")

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

    async def broadcast_suggestion(self, suggestion_event: SuggestionEvent):
        """
        Broadcast a suggestion event to clients subscribed to the spec ID.

        If the suggestion has no spec_id, broadcasts to all connected clients.
        This supports both spec-specific suggestions and general pair programming suggestions.

        Args:
            suggestion_event: The SuggestionEvent to broadcast
        """
        spec_id = suggestion_event.spec_id

        # If no spec_id, broadcast to all clients
        if not spec_id:
            if not self.active_connections:
                logger.debug("No active connections for suggestion broadcast")
                return

            message = suggestion_event.model_dump(mode="json")
            logger.debug(f"Broadcasting suggestion to all {len(self.active_connections)} clients")

            disconnected = []
            for websocket in list(self.active_connections.keys()):
                try:
                    await websocket.send_json(message)
                except WebSocketDisconnect:
                    disconnected.append(websocket)
                except Exception as e:
                    logger.error(f"Error broadcasting suggestion to {id(websocket)}: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected clients
            for websocket in disconnected:
                self.disconnect(websocket)
            return

        # Broadcast to spec-specific subscribers
        if spec_id not in self.spec_subscriptions:
            logger.debug(f"No subscribers for spec {spec_id} suggestion")
            return

        subscribers = list(self.spec_subscriptions[spec_id])
        if not subscribers:
            return

        message = suggestion_event.model_dump(mode="json")
        logger.debug(f"Broadcasting suggestion to {len(subscribers)} subscribers of spec {spec_id}")

        disconnected = []
        for websocket in subscribers:
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting suggestion to {id(websocket)}: {e}")
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

    Protocol:
        Client -> Server:
            {"action": "subscribe", "spec_id": "001"}
            {"action": "unsubscribe", "spec_id": "001"}
            {"action": "ping"}

        Server -> Client:
            {"event_type": "execution", "spec_id": "001", "timestamp": "...", "data": {...}}
            {"event_type": "log", "spec_id": "001", "timestamp": "...", "log_line": "..."}
            {"event_type": "error", "spec_id": "001", "timestamp": "...", "error_message": "..."}

    Example:
        const ws = new WebSocket("ws://localhost:8000/ws/agent-events");
        ws.send(JSON.stringify({action: "subscribe", spec_id: "001"}));
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Received event:", data);
        };
    """
    await manager.connect(websocket)

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
                                "timestamp": datetime.now().isoformat()
                            },
                            websocket
                        )
                    else:
                        await manager.send_personal_message(
                            {
                                "status": "error",
                                "message": "spec_id is required for subscribe action"
                            },
                            websocket
                        )

                elif action == "unsubscribe":
                    spec_id = message.get("spec_id")
                    if spec_id:
                        manager.unsubscribe(websocket, spec_id)
                        await manager.send_personal_message(
                            {
                                "status": "unsubscribed",
                                "spec_id": spec_id,
                                "timestamp": datetime.now().isoformat()
                            },
                            websocket
                        )

                elif action == "ping":
                    await manager.send_personal_message(
                        {
                            "status": "pong",
                            "timestamp": datetime.now().isoformat()
                        },
                        websocket
                    )

                else:
                    await manager.send_personal_message(
                        {
                            "status": "error",
                            "message": f"Unknown action: {action}"
                        },
                        websocket
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "status": "error",
                        "message": "Invalid JSON"
                    },
                    websocket
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await manager.send_personal_message(
                    {
                        "status": "error",
                        "message": str(e)
                    },
                    websocket
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
    current_subtask: str = None
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
            current_subtask=current_subtask
        )
    )
    await manager.broadcast_to_spec(spec_id, event)


async def broadcast_log_event(
    spec_id: str,
    log_line: str,
    level: str = "info"
):
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
        data=None
    )
    await manager.broadcast_to_spec(spec_id, event)


async def broadcast_error_event(
    spec_id: str,
    error_message: str,
    error_type: str = None,
    traceback: str = None
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
        data=None
    )
    await manager.broadcast_to_spec(spec_id, event)


async def broadcast_suggestion_event(
    suggestion_id: str,
    suggestion_type: str,
    content: str,
    confidence: float,
    description: str,
    spec_id: str = None,
    range_data: dict = None,
    reasoning: str = None,
    file_path: str = None
):
    """
    Helper function to broadcast AI pair programming suggestions.

    Can be called from suggestion engine or pair programming agent to stream
    real-time code suggestions to connected clients.

    Args:
        suggestion_id: Unique identifier for the suggestion
        suggestion_type: Type of suggestion (completion, refactor, fix, explanation)
        content: Suggested code or explanation text
        confidence: Confidence score (0.0-1.0)
        description: Human-readable description
        spec_id: Optional spec/task ID (broadcasts to all if None)
        range_data: Optional code range dict with start_line, start_column, end_line, end_column
        reasoning: Optional reasoning for the suggestion
        file_path: Optional file path the suggestion applies to
    """
    from api.models.pair_programming import SuggestionEvent, SuggestionData, CodeRange

    # Build suggestion data
    suggestion_data = SuggestionData(
        suggestion_id=suggestion_id,
        type=suggestion_type,
        content=content,
        confidence=confidence,
        description=description,
        reasoning=reasoning,
        file_path=file_path,
        range=CodeRange(**range_data) if range_data else None
    )

    event = SuggestionEvent(
        event_type="pair_suggestion",
        timestamp=datetime.now().isoformat(),
        spec_id=spec_id,
        data=suggestion_data
    )

    await manager.broadcast_suggestion(event)


# Export the manager for use in other modules
__all__ = [
    "router",
    "manager",
    "broadcast_execution_event",
    "broadcast_log_event",
    "broadcast_error_event",
    "broadcast_suggestion_event",
]
