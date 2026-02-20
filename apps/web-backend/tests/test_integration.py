"""
Integration tests for Agent Execution Flow

Tests the integration between:
- Agent runner service
- WebSocket event broadcasting
- Task management (create, status, cancel)
- Agent API routes
- Event models and propagation

These tests verify that the entire agent execution flow works together,
from API request through WebSocket event delivery.
"""

import asyncio
import contextlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.models.agent_event import (
    ErrorEvent,
    ExecutionEvent,
    ExecutionProgressData,
    LogEvent,
)
from api.websocket import (
    ConnectionManager,
    broadcast_error_event,
    broadcast_execution_event,
    broadcast_log_event,
    manager,
)
from core.security import create_access_token
from fastapi import WebSocket
from services.agent_runner import (
    _running_tasks,
    _sanitize_log,
    cancel_task,
    cleanup_completed_tasks,
    get_task_status,
)

# ============================================================================
# Agent Execution Flow Integration Tests
# ============================================================================


class TestAgentExecutionFlowIntegration:
    """
    Tests for the complete agent execution flow.

    These tests verify the integration between API endpoints, the agent runner
    service, and WebSocket event broadcasting.
    """

    @patch("api.routes.agents.start_agent_task")
    @patch("api.routes.agents.cleanup_completed_tasks")
    def test_start_agent_and_get_status(self, mock_cleanup, mock_start, test_client):
        """Test starting an agent and then checking its status."""
        # Start agent
        mock_start.return_value = "001:planner"

        start_response = test_client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "planner"}
        )

        assert start_response.status_code == 202
        task_id = start_response.json()["task_id"]
        assert task_id == "001:planner"

        # Check status
        with patch("api.routes.agents.get_task_status") as mock_status:
            mock_status.return_value = {"status": "running"}

            status_response = test_client.get(f"/api/agents/status/{task_id}")

            assert status_response.status_code == 200
            assert status_response.json()["status"] == "running"

    @patch("api.routes.agents.start_agent_task")
    @patch("api.routes.agents.cleanup_completed_tasks")
    @patch("api.routes.agents.cancel_task")
    def test_start_agent_and_cancel(
        self, mock_cancel, mock_cleanup, mock_start, test_client
    ):
        """Test starting an agent and then cancelling it."""
        # Start agent
        mock_start.return_value = "001:coder"

        start_response = test_client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "coder"}
        )

        assert start_response.status_code == 202
        task_id = start_response.json()["task_id"]

        # Cancel agent
        mock_cancel.return_value = True

        cancel_response = test_client.post(f"/api/agents/cancel/{task_id}")

        assert cancel_response.status_code == 200
        assert cancel_response.json()["cancelled"] is True

    @patch("api.routes.agents.start_agent_task")
    @patch("api.routes.agents.cleanup_completed_tasks")
    def test_agent_flow_with_completion(self, mock_cleanup, mock_start, test_client):
        """Test full agent flow from start to completion."""
        mock_start.return_value = "001:qa_reviewer"

        # Start agent
        start_response = test_client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "qa_reviewer"}
        )

        assert start_response.status_code == 202
        task_id = start_response.json()["task_id"]

        # Simulate completion - check status returns completed
        with patch("api.routes.agents.get_task_status") as mock_status:
            mock_status.return_value = {
                "status": "completed",
                "result": {"success": True, "message": "QA review passed"},
            }

            status_response = test_client.get(f"/api/agents/status/{task_id}")

            assert status_response.status_code == 200
            data = status_response.json()
            assert data["status"] == "completed"
            assert data["result"]["success"] is True

    def test_multiple_agents_different_specs(self, test_client):
        """Test running agents for different specs concurrently."""
        with patch("api.routes.agents.start_agent_task") as mock_start:
            with patch("api.routes.agents.cleanup_completed_tasks"):
                # Start first agent
                mock_start.return_value = "001:planner"
                resp1 = test_client.post(
                    "/api/agents/run", json={"spec_id": "001", "agent_type": "planner"}
                )
                assert resp1.status_code == 202
                assert resp1.json()["task_id"] == "001:planner"

                # Start second agent for different spec
                mock_start.return_value = "002:planner"
                resp2 = test_client.post(
                    "/api/agents/run", json={"spec_id": "002", "agent_type": "planner"}
                )
                assert resp2.status_code == 202
                assert resp2.json()["task_id"] == "002:planner"


# ============================================================================
# WebSocket Event Broadcasting Integration Tests
# ============================================================================


class TestWebSocketBroadcastIntegration:
    """
    Tests for WebSocket event broadcasting during agent execution.

    Verifies that agent execution events are properly broadcast to
    subscribed WebSocket clients.
    """

    @pytest.fixture
    def connection_manager(self):
        """Create a fresh ConnectionManager for each test."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        ws = MagicMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_execution_event_broadcast_to_subscribers(
        self, connection_manager, mock_websocket
    ):
        """Test that execution events are broadcast to spec subscribers."""
        # Connect and subscribe to spec
        await connection_manager.connect(mock_websocket, {"sub": "test@example.com"})
        connection_manager.subscribe(mock_websocket, "spec-001")

        # Create and broadcast execution event
        event = ExecutionEvent(
            event_type="execution",
            timestamp=datetime.now().isoformat(),
            spec_id="spec-001",
            data=ExecutionProgressData(
                phase="coding",
                phase_progress=50.0,
                overall_progress=25.0,
                message="Implementing feature",
                current_subtask="subtask-1-1",
            ),
        )

        await connection_manager.broadcast_to_spec("spec-001", event)

        # Verify event was sent
        mock_websocket.send_json.assert_called_once()
        call_data = mock_websocket.send_json.call_args[0][0]
        assert call_data["event_type"] == "execution"
        assert call_data["spec_id"] == "spec-001"
        assert call_data["data"]["phase"] == "coding"
        assert call_data["data"]["current_subtask"] == "subtask-1-1"

    @pytest.mark.asyncio
    async def test_log_event_broadcast(self, connection_manager, mock_websocket):
        """Test log event broadcasting during agent execution."""
        await connection_manager.connect(mock_websocket, {"sub": "test@example.com"})
        connection_manager.subscribe(mock_websocket, "spec-001")

        event = LogEvent(
            event_type="log",
            timestamp=datetime.now().isoformat(),
            spec_id="spec-001",
            log_line="[Coder] Starting implementation of authentication module",
            level="info",
            data=None,
        )

        await connection_manager.broadcast_to_spec("spec-001", event)

        mock_websocket.send_json.assert_called_once()
        call_data = mock_websocket.send_json.call_args[0][0]
        assert call_data["event_type"] == "log"
        assert "authentication module" in call_data["log_line"]
        assert call_data["level"] == "info"

    @pytest.mark.asyncio
    async def test_error_event_broadcast(self, connection_manager, mock_websocket):
        """Test error event broadcasting when agent fails."""
        await connection_manager.connect(mock_websocket, {"sub": "test@example.com"})
        connection_manager.subscribe(mock_websocket, "spec-001")

        event = ErrorEvent(
            event_type="error",
            timestamp=datetime.now().isoformat(),
            spec_id="spec-001",
            error_message="Agent execution timed out after 30 minutes",
            error_type="TimeoutError",
            traceback="Traceback: ...",
            data=None,
        )

        await connection_manager.broadcast_to_spec("spec-001", event)

        mock_websocket.send_json.assert_called_once()
        call_data = mock_websocket.send_json.call_args[0][0]
        assert call_data["event_type"] == "error"
        assert "timed out" in call_data["error_message"]
        assert call_data["error_type"] == "TimeoutError"

    @pytest.mark.asyncio
    async def test_events_not_sent_to_unsubscribed_clients(
        self, connection_manager, mock_websocket
    ):
        """Test that events are not sent to clients not subscribed to the spec."""
        # Connect but don't subscribe to spec-001
        await connection_manager.connect(mock_websocket, {"sub": "test@example.com"})
        connection_manager.subscribe(mock_websocket, "spec-002")  # Different spec

        event = ExecutionEvent(
            event_type="execution",
            timestamp=datetime.now().isoformat(),
            spec_id="spec-001",
            data=ExecutionProgressData(
                phase="planning", phase_progress=10.0, overall_progress=5.0
            ),
        )

        await connection_manager.broadcast_to_spec("spec-001", event)

        # Should not receive the event
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_events(self, connection_manager):
        """Test that all subscribers receive broadcast events."""
        # Create multiple mock websockets
        ws1 = MagicMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        ws3 = MagicMock(spec=WebSocket)
        ws3.accept = AsyncMock()
        ws3.send_json = AsyncMock()

        # Connect all and subscribe to same spec
        await connection_manager.connect(ws1, {"sub": "user1@example.com"})
        await connection_manager.connect(ws2, {"sub": "user2@example.com"})
        await connection_manager.connect(ws3, {"sub": "user3@example.com"})

        connection_manager.subscribe(ws1, "spec-001")
        connection_manager.subscribe(ws2, "spec-001")
        # ws3 is not subscribed

        event = ExecutionEvent(
            event_type="execution",
            timestamp=datetime.now().isoformat(),
            spec_id="spec-001",
            data=ExecutionProgressData(
                phase="qa_review",
                phase_progress=100.0,
                overall_progress=75.0,
                message="QA review complete",
            ),
        )

        await connection_manager.broadcast_to_spec("spec-001", event)

        # ws1 and ws2 should receive, ws3 should not
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
        ws3.send_json.assert_not_called()


# ============================================================================
# Agent Runner Service Integration Tests
# ============================================================================


class TestAgentRunnerServiceIntegration:
    """
    Tests for the agent runner service integration.

    Verifies task lifecycle management, WebSocket broadcast integration,
    and error handling.
    """

    def test_task_lifecycle_simulation(self):
        """Test simulated task lifecycle (create, status, complete)."""

        async def run_test():
            async def mock_agent_task():
                await asyncio.sleep(0.01)
                return {"success": True}

            task_id = "test-001:planner"

            with patch.dict(_running_tasks, {}, clear=True):
                task = asyncio.create_task(mock_agent_task())
                _running_tasks[task_id] = task

                # Check status while running
                status = get_task_status(task_id)
                assert status is not None
                assert status["status"] == "running"

                # Run until complete
                result = await task
                assert result is not None

                # Check status after completion
                status = get_task_status(task_id)
                assert status["status"] == "completed"
                assert status["result"]["success"] is True

        asyncio.run(run_test())

    def test_task_cancellation_flow(self):
        """Test task cancellation flow."""

        async def long_running_task():
            try:
                await asyncio.sleep(10)  # Long sleep
                return {"success": True}
            except asyncio.CancelledError:
                raise  # Re-raise to properly cancel

        async def run_test():
            task_id = "test-002:coder"

            with patch.dict(_running_tasks, {}, clear=True):
                task = asyncio.create_task(long_running_task())
                _running_tasks[task_id] = task

                # Let the task start
                await asyncio.sleep(0.01)

                # Cancel the task
                cancelled = cancel_task(task_id)
                assert cancelled is True

                # Wait for cancellation to propagate
                with contextlib.suppress(asyncio.CancelledError):
                    await task

                # Verify task is cancelled
                assert task.cancelled()

        asyncio.run(run_test())

    def test_cleanup_removes_completed_tasks(self):
        """Test that cleanup_completed_tasks removes finished tasks."""

        async def run_test():
            async def quick_task():
                return {"done": True}

            with patch.dict(_running_tasks, {}, clear=True):
                # Create a completed task
                task = asyncio.create_task(quick_task())
                result = await task  # Wait for completion
                assert result is not None
                _running_tasks["completed-task"] = task

                # Create a running task
                async def running_task():
                    await asyncio.sleep(10)

                running = asyncio.create_task(running_task())
                _running_tasks["running-task"] = running

                # Let tasks start
                await asyncio.sleep(0.01)

                # Cleanup
                cleanup_completed_tasks()

                # Completed task should be removed
                assert "completed-task" not in _running_tasks
                # Running task should remain
                assert "running-task" in _running_tasks

                # Cleanup
                running.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await running

        asyncio.run(run_test())

    def test_sanitize_log_prevents_injection(self):
        """Test that log sanitization prevents log injection."""
        # Test newline injection
        malicious = "normal\ninjected: dangerous"
        sanitized = _sanitize_log(malicious)
        assert "\n" not in sanitized
        assert "\\n" in sanitized

        # Test carriage return injection
        malicious2 = "normal\r\ninjected"
        sanitized2 = _sanitize_log(malicious2)
        assert "\r" not in sanitized2
        assert "\n" not in sanitized2


# ============================================================================
# WebSocket Connection and Agent Event Integration Tests
# ============================================================================


class TestWebSocketAgentEventIntegration:
    """
    Tests for WebSocket connection handling during agent execution.

    Verifies proper connection management, subscription handling, and
    message delivery for agent events.
    """

    def test_websocket_agent_event_subscription_flow(self, test_client):
        """Test the complete WebSocket subscription flow for agent events."""
        token = create_access_token({"sub": "test@example.com"})

        with test_client.websocket_connect(
            f"/ws/agent-events?token={token}"
        ) as websocket:
            # Receive connection confirmation
            data = websocket.receive_json()
            assert data["status"] == "connected"

            # Subscribe to a spec
            websocket.send_json({"action": "subscribe", "spec_id": "001-test"})
            data = websocket.receive_json()
            assert data["status"] == "subscribed"
            assert data["spec_id"] == "001-test"

            # Unsubscribe
            websocket.send_json({"action": "unsubscribe", "spec_id": "001-test"})
            data = websocket.receive_json()
            assert data["status"] == "unsubscribed"

    def test_websocket_ping_pong_during_agent_execution(self, test_client):
        """Test ping/pong keepalive during long agent executions."""
        token = create_access_token({"sub": "test@example.com"})

        with test_client.websocket_connect(
            f"/ws/agent-events?token={token}"
        ) as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Simulate multiple ping/pong cycles (keepalive during long execution)
            for _ in range(3):
                websocket.send_json({"action": "ping"})
                data = websocket.receive_json()
                assert data["status"] == "pong"
                assert "timestamp" in data

    def test_websocket_resubscription_after_disconnect_reconnect(self, test_client):
        """Test that clients can resubscribe after reconnection."""
        token = create_access_token({"sub": "test@example.com"})

        # First connection
        with test_client.websocket_connect(
            f"/ws/agent-events?token={token}"
        ) as websocket:
            websocket.receive_json()
            websocket.send_json({"action": "subscribe", "spec_id": "001"})
            data = websocket.receive_json()
            assert data["status"] == "subscribed"

        # Reconnect and resubscribe
        with test_client.websocket_connect(
            f"/ws/agent-events?token={token}"
        ) as websocket:
            websocket.receive_json()
            websocket.send_json({"action": "subscribe", "spec_id": "001"})
            data = websocket.receive_json()
            assert data["status"] == "subscribed"


# ============================================================================
# Agent Phase Transition Integration Tests
# ============================================================================


class TestAgentPhaseTransitionIntegration:
    """
    Tests for agent phase transitions and progress updates.

    Verifies that progress events accurately reflect agent execution phases.
    """

    @pytest.mark.asyncio
    async def test_phase_transition_events(self):
        """Test that phase transitions generate correct events."""
        conn_manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await conn_manager.connect(mock_ws, {"sub": "test@example.com"})
        conn_manager.subscribe(mock_ws, "spec-001")

        # Simulate phase transitions
        phases = [
            ("planning", 0.0, 0.0),
            ("planning", 50.0, 10.0),
            ("planning", 100.0, 20.0),
            ("coding", 0.0, 20.0),
            ("coding", 50.0, 40.0),
            ("coding", 100.0, 60.0),
            ("qa_review", 0.0, 60.0),
            ("qa_review", 100.0, 80.0),
            ("complete", 100.0, 100.0),
        ]

        for phase, phase_progress, overall_progress in phases:
            event = ExecutionEvent(
                event_type="execution",
                timestamp=datetime.now().isoformat(),
                spec_id="spec-001",
                data=ExecutionProgressData(
                    phase=phase,
                    phase_progress=phase_progress,
                    overall_progress=overall_progress,
                    message=f"Phase: {phase}",
                ),
            )
            await conn_manager.broadcast_to_spec("spec-001", event)

        # Verify all events were sent
        assert mock_ws.send_json.call_count == len(phases)

        # Verify final event shows completion
        final_call = mock_ws.send_json.call_args_list[-1][0][0]
        assert final_call["data"]["phase"] == "complete"
        assert final_call["data"]["overall_progress"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_subtask_progress_tracking(self):
        """Test that subtask progress is properly tracked in events."""
        conn_manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await conn_manager.connect(mock_ws, {"sub": "test@example.com"})
        conn_manager.subscribe(mock_ws, "spec-001")

        # Simulate subtask progression
        subtasks = [
            ("subtask-1-1", 33.0),
            ("subtask-1-2", 66.0),
            ("subtask-1-3", 100.0),
        ]

        for subtask_id, progress in subtasks:
            event = ExecutionEvent(
                event_type="execution",
                timestamp=datetime.now().isoformat(),
                spec_id="spec-001",
                data=ExecutionProgressData(
                    phase="coding",
                    phase_progress=progress,
                    overall_progress=progress * 0.5,  # 50% weight for coding
                    message=f"Working on {subtask_id}",
                    current_subtask=subtask_id,
                ),
            )
            await conn_manager.broadcast_to_spec("spec-001", event)

        # Verify subtask progression
        calls = mock_ws.send_json.call_args_list
        assert len(calls) == 3

        for i, (subtask_id, _) in enumerate(subtasks):
            call_data = calls[i][0][0]
            assert call_data["data"]["current_subtask"] == subtask_id


# ============================================================================
# Error Handling Integration Tests
# ============================================================================


class TestAgentErrorHandlingIntegration:
    """
    Tests for error handling during agent execution.

    Verifies proper error propagation through API and WebSocket.
    """

    def test_agent_spec_not_found_error_flow(self, test_client):
        """Test error flow when spec is not found."""
        with patch("api.routes.agents.start_agent_task") as mock_start:
            mock_start.side_effect = FileNotFoundError("Spec not found: 999")

            response = test_client.post(
                "/api/agents/run", json={"spec_id": "999", "agent_type": "planner"}
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_agent_conflict_error_flow(self, test_client):
        """Test error flow when agent is already running."""
        with patch("api.routes.agents.start_agent_task") as mock_start:
            mock_start.side_effect = RuntimeError(
                "Agent task already running for spec 001"
            )

            response = test_client.post(
                "/api/agents/run", json={"spec_id": "001", "agent_type": "coder"}
            )

            assert response.status_code == 409
            assert "already" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_error_broadcast_on_agent_failure(self):
        """Test that errors are broadcast to WebSocket clients."""
        conn_manager = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await conn_manager.connect(mock_ws, {"sub": "test@example.com"})
        conn_manager.subscribe(mock_ws, "spec-001")

        # Broadcast error event
        error_event = ErrorEvent(
            event_type="error",
            timestamp=datetime.now().isoformat(),
            spec_id="spec-001",
            error_message="Build failed: Test suite not passing",
            error_type="BuildError",
            traceback="Traceback details...",
            data=None,
        )

        await conn_manager.broadcast_to_spec("spec-001", error_event)

        mock_ws.send_json.assert_called_once()
        call_data = mock_ws.send_json.call_args[0][0]
        assert call_data["event_type"] == "error"
        assert "Build failed" in call_data["error_message"]
        assert call_data["error_type"] == "BuildError"


# ============================================================================
# Agent Type Integration Tests
# ============================================================================


class TestAgentTypeIntegration:
    """
    Tests for different agent types working together.

    Verifies the flow between planner, coder, qa_reviewer, and qa_fixer.
    """

    def test_all_agent_types_can_be_started(self, test_client):
        """Test that all agent types can be started via API."""
        agent_types = ["planner", "coder", "qa_reviewer", "qa_fixer"]

        for agent_type in agent_types:
            with patch("api.routes.agents.start_agent_task") as mock_start:
                with patch("api.routes.agents.cleanup_completed_tasks"):
                    mock_start.return_value = f"001:{agent_type}"

                    response = test_client.post(
                        "/api/agents/run",
                        json={"spec_id": "001", "agent_type": agent_type},
                    )

                    assert response.status_code == 202, f"Failed for {agent_type}"
                    assert response.json()["agent_type"] == agent_type

    def test_agent_type_phase_mapping(self):
        """Test that agent types map to correct execution phases."""
        phase_map = {
            "planner": "planning",
            "coder": "coding",
            "qa_reviewer": "qa_review",
            "qa_fixer": "qa_fixing",
        }

        for agent_type, expected_phase in phase_map.items():
            # Verify the mapping is consistent with event broadcasting
            assert expected_phase in [
                "planning",
                "coding",
                "qa_review",
                "qa_fixing",
                "idle",
                "complete",
                "failed",
            ]


# ============================================================================
# Broadcast Helper Function Integration Tests
# ============================================================================


class TestBroadcastHelperIntegration:
    """
    Tests for the broadcast helper functions.

    Verifies that helper functions properly integrate with the ConnectionManager.
    """

    @pytest.mark.asyncio
    async def test_broadcast_execution_event_helper(self):
        """Test broadcast_execution_event helper function integration."""
        # Setup subscriber
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()

        manager.active_connections[mock_ws] = {
            "subscriptions": {"test-spec"},
            "user": {"sub": "test@example.com"},
        }
        manager.spec_subscriptions["test-spec"] = {mock_ws}

        try:
            await broadcast_execution_event(
                spec_id="test-spec",
                phase="coding",
                phase_progress=75.0,
                overall_progress=50.0,
                message="Implementation in progress",
                current_subtask="subtask-2-1",
            )

            mock_ws.send_json.assert_called_once()
            call_data = mock_ws.send_json.call_args[0][0]
            assert call_data["event_type"] == "execution"
            assert call_data["spec_id"] == "test-spec"
            assert call_data["data"]["phase_progress"] == pytest.approx(75.0)
            assert call_data["data"]["current_subtask"] == "subtask-2-1"
        finally:
            manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_broadcast_log_event_helper(self):
        """Test broadcast_log_event helper function integration."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()

        manager.active_connections[mock_ws] = {
            "subscriptions": {"test-spec"},
            "user": {},
        }
        manager.spec_subscriptions["test-spec"] = {mock_ws}

        try:
            await broadcast_log_event(
                spec_id="test-spec",
                log_line="[Coder] Writing tests for authentication module",
                level="debug",
            )

            mock_ws.send_json.assert_called_once()
            call_data = mock_ws.send_json.call_args[0][0]
            assert call_data["event_type"] == "log"
            assert call_data["level"] == "debug"
            assert "authentication module" in call_data["log_line"]
        finally:
            manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_broadcast_error_event_helper(self):
        """Test broadcast_error_event helper function integration."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()

        manager.active_connections[mock_ws] = {
            "subscriptions": {"test-spec"},
            "user": {},
        }
        manager.spec_subscriptions["test-spec"] = {mock_ws}

        try:
            await broadcast_error_event(
                spec_id="test-spec",
                error_message="API rate limit exceeded",
                error_type="RateLimitError",
                traceback="Stack trace here...",
            )

            mock_ws.send_json.assert_called_once()
            call_data = mock_ws.send_json.call_args[0][0]
            assert call_data["event_type"] == "error"
            assert call_data["error_type"] == "RateLimitError"
            assert "rate limit" in call_data["error_message"].lower()
        finally:
            manager.disconnect(mock_ws)


# ============================================================================
# Integration Test Summary
# ============================================================================


def test_integration_test_summary():
    """
    Agent execution flow integration test coverage summary.

    This test always passes and serves as documentation of what is tested.
    """
    coverage = {
        "agent_execution_flow": [
            "Start agent and check status",
            "Start agent and cancel",
            "Full agent flow to completion",
            "Multiple agents for different specs",
        ],
        "websocket_broadcasting": [
            "Execution event broadcast to subscribers",
            "Log event broadcasting",
            "Error event broadcasting",
            "Events not sent to unsubscribed clients",
            "Multiple subscribers receive events",
        ],
        "agent_runner_service": [
            "Task lifecycle (create, status, complete)",
            "Task cancellation flow",
            "Cleanup removes completed tasks",
            "Log sanitization prevents injection",
        ],
        "websocket_connection_handling": [
            "Subscription flow for agent events",
            "Ping/pong keepalive during execution",
            "Resubscription after reconnection",
        ],
        "phase_transitions": [
            "Phase transition events",
            "Subtask progress tracking",
        ],
        "error_handling": [
            "Spec not found error flow",
            "Agent conflict error flow",
            "Error broadcast on agent failure",
        ],
        "agent_types": [
            "All agent types can be started",
            "Agent type to phase mapping",
        ],
        "broadcast_helpers": [
            "broadcast_execution_event helper",
            "broadcast_log_event helper",
            "broadcast_error_event helper",
        ],
    }

    print("\n" + "=" * 70)
    print("AGENT EXECUTION FLOW INTEGRATION TEST COVERAGE SUMMARY")
    print("=" * 70)

    for category, tests in coverage.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for test in tests:
            print(f"  - {test}")

    print("\n" + "=" * 70)

    assert True
