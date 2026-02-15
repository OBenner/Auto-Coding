"""
Unit tests for Agent API routes

Tests the agent execution API endpoints including:
- POST /api/agents/run - Start agent execution
- GET /api/agents/status/{task_id} - Check agent status
- POST /api/agents/cancel/{task_id} - Cancel running agent
- GET /api/agents/health - Agent API health check
"""

from unittest.mock import MagicMock, patch

# Import agent route models
from api.routes.agents import (
    AgentCancelResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentStatusResponse,
)

# ============================================================================
# Agent Request/Response Model Tests
# ============================================================================


class TestAgentModels:
    """Tests for Pydantic models used by agent routes."""

    def test_agent_run_request_valid(self):
        """Test valid agent run request."""
        request = AgentRunRequest(
            spec_id="001",
            agent_type="planner",
            model="claude-sonnet-4-5-20250929",
            verbose=False,
        )
        assert request.spec_id == "001"
        assert request.agent_type == "planner"

    def test_agent_run_request_with_name_suffix(self):
        """Test agent run request with spec ID including name suffix."""
        request = AgentRunRequest(spec_id="001-feature-auth", agent_type="coder")
        assert request.spec_id == "001-feature-auth"

    def test_agent_run_request_all_agent_types(self):
        """Test all valid agent types."""
        for agent_type in ["planner", "coder", "qa_reviewer", "qa_fixer"]:
            request = AgentRunRequest(spec_id="001", agent_type=agent_type)
            assert request.agent_type == agent_type

    def test_agent_run_request_default_values(self):
        """Test default values for agent run request."""
        request = AgentRunRequest(spec_id="001", agent_type="planner")
        assert request.model == "claude-sonnet-4-5-20250929"
        assert request.verbose is False

    def test_agent_run_response(self):
        """Test agent run response model."""
        response = AgentRunResponse(
            task_id="001:planner",
            spec_id="001",
            agent_type="planner",
            status="started",
            message="Agent task started",
        )
        assert response.task_id == "001:planner"
        assert response.status == "started"

    def test_agent_status_response_running(self):
        """Test agent status response for running task."""
        response = AgentStatusResponse(
            task_id="001:planner", status="running", result=None, error=None
        )
        assert response.status == "running"

    def test_agent_status_response_completed(self):
        """Test agent status response for completed task."""
        response = AgentStatusResponse(
            task_id="001:planner",
            status="completed",
            result={"success": True},
            error=None,
        )
        assert response.status == "completed"
        assert response.result["success"] is True

    def test_agent_status_response_failed(self):
        """Test agent status response for failed task."""
        response = AgentStatusResponse(
            task_id="001:planner",
            status="failed",
            result=None,
            error="Task failed due to timeout",
        )
        assert response.status == "failed"
        assert "timeout" in response.error.lower()

    def test_agent_cancel_response(self):
        """Test agent cancel response model."""
        response = AgentCancelResponse(
            task_id="001:planner", cancelled=True, message="Task cancelled"
        )
        assert response.cancelled is True


# ============================================================================
# Agent Route Endpoint Tests
# ============================================================================


class TestAgentRoutes:
    """Tests for agent API endpoints."""

    def test_agents_health_endpoint(self, test_client):
        """Test agents API health endpoint."""
        response = test_client.get("/api/agents/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["endpoint"] == "agents"
        assert "project_dir" in data

    @patch("api.routes.agents.start_agent_task")
    @patch("api.routes.agents.cleanup_completed_tasks")
    def test_run_agent_success(self, mock_cleanup, mock_start, test_client):
        """Test starting an agent successfully."""
        mock_start.return_value = "001:planner"

        response = test_client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "planner"}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "001:planner"
        assert data["spec_id"] == "001"
        assert data["agent_type"] == "planner"
        assert data["status"] == "started"
        mock_cleanup.assert_called_once()

    @patch("api.routes.agents.start_agent_task")
    def test_run_agent_spec_not_found(self, mock_start, test_client):
        """Test running agent with non-existent spec."""
        mock_start.side_effect = FileNotFoundError("Spec not found: 999")

        response = test_client.post(
            "/api/agents/run", json={"spec_id": "999", "agent_type": "planner"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("api.routes.agents.start_agent_task")
    def test_run_agent_already_running(self, mock_start, test_client):
        """Test running agent when one is already running for the spec."""
        mock_start.side_effect = RuntimeError("Task already running")

        response = test_client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "planner"}
        )

        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()

    @patch("api.routes.agents.start_agent_task")
    def test_run_agent_invalid_request(self, mock_start, test_client):
        """Test running agent with invalid parameters."""
        mock_start.side_effect = ValueError("Invalid agent_type")

        response = test_client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "invalid_type"}
        )

        # Pydantic validation catches invalid agent_type before reaching route
        assert response.status_code == 422

    @patch("api.routes.agents.start_agent_task")
    def test_run_agent_server_error(self, mock_start, test_client):
        """Test running agent with unexpected server error."""
        mock_start.side_effect = Exception("Unexpected error")

        response = test_client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "planner"}
        )

        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()

    @patch("api.routes.agents.get_task_status")
    def test_get_agent_status_running(self, mock_status, test_client):
        """Test getting status of a running task."""
        mock_status.return_value = {"status": "running"}

        response = test_client.get("/api/agents/status/001:planner")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "001:planner"
        assert data["status"] == "running"

    @patch("api.routes.agents.get_task_status")
    def test_get_agent_status_completed(self, mock_status, test_client):
        """Test getting status of a completed task."""
        mock_status.return_value = {
            "status": "completed",
            "result": {"success": True, "message": "Task completed"},
        }

        response = test_client.get("/api/agents/status/001:planner")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"]["success"] is True

    @patch("api.routes.agents.get_task_status")
    def test_get_agent_status_failed(self, mock_status, test_client):
        """Test getting status of a failed task."""
        mock_status.return_value = {
            "status": "failed",
            "error": "Agent execution timed out",
        }

        response = test_client.get("/api/agents/status/001:planner")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "timed out" in data["error"]

    @patch("api.routes.agents.get_task_status")
    def test_get_agent_status_not_found(self, mock_status, test_client):
        """Test getting status of non-existent task."""
        mock_status.return_value = None

        response = test_client.get("/api/agents/status/nonexistent:task")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("api.routes.agents.cancel_task")
    def test_cancel_agent_success(self, mock_cancel, test_client):
        """Test cancelling a running task successfully."""
        mock_cancel.return_value = True

        response = test_client.post("/api/agents/cancel/001:planner")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "001:planner"
        assert data["cancelled"] is True

    @patch("api.routes.agents.cancel_task")
    def test_cancel_agent_not_found(self, mock_cancel, test_client):
        """Test cancelling a task that doesn't exist or is already done."""
        mock_cancel.return_value = False

        response = test_client.post("/api/agents/cancel/nonexistent:task")

        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is False
        assert (
            "not found" in data["message"].lower()
            or "completed" in data["message"].lower()
        )

    @patch("api.routes.agents.cancel_task")
    def test_cancel_agent_server_error(self, mock_cancel, test_client):
        """Test cancelling with unexpected server error."""
        mock_cancel.side_effect = Exception("Cancel failed")

        response = test_client.post("/api/agents/cancel/001:planner")

        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()


# ============================================================================
# Agent Runner Service Tests
# ============================================================================


class TestAgentRunnerService:
    """Tests for the agent runner service functions."""

    def test_sanitize_log_newlines(self):
        """Test that log sanitization handles newlines."""
        from services.agent_runner import _sanitize_log

        result = _sanitize_log("test\nline\r\nvalue")
        assert "\\n" in result
        assert "\\r" in result
        assert "\n" not in result
        assert "\r" not in result

    def test_sanitize_log_normal_string(self):
        """Test that log sanitization preserves normal strings."""
        from services.agent_runner import _sanitize_log

        result = _sanitize_log("normal string")
        assert result == "normal string"

    @patch("services.agent_runner._running_tasks", {})
    def test_get_task_status_not_found(self):
        """Test get_task_status returns None for unknown task."""
        from services.agent_runner import get_task_status

        result = get_task_status("unknown:task")
        assert result is None

    @patch("services.agent_runner._running_tasks", {})
    def test_cancel_task_not_found(self):
        """Test cancel_task returns False for unknown task."""
        from services.agent_runner import cancel_task

        result = cancel_task("unknown:task")
        assert result is False

    @patch("services.agent_runner._running_tasks", {})
    def test_cleanup_completed_tasks_empty(self):
        """Test cleanup_completed_tasks with no tasks."""
        from services.agent_runner import cleanup_completed_tasks

        # Should not raise
        cleanup_completed_tasks()

    @patch("services.agent_runner._running_tasks")
    def test_cleanup_completed_tasks_removes_done(self, mock_tasks):
        """Test cleanup_completed_tasks removes completed tasks."""
        from services.agent_runner import cleanup_completed_tasks

        # Create mock tasks
        done_task = MagicMock()
        done_task.done.return_value = True

        running_task = MagicMock()
        running_task.done.return_value = False

        mock_tasks.__iter__ = lambda self: iter(["001:done", "002:running"])
        mock_tasks.items.return_value = [
            ("001:done", done_task),
            ("002:running", running_task),
        ]
        mock_tasks.__delitem__ = MagicMock()
        mock_tasks.__contains__ = lambda self, key: key in ["001:done", "002:running"]

        cleanup_completed_tasks()

        # Verify done task was deleted
        mock_tasks.__delitem__.assert_called_once_with("001:done")


# ============================================================================
# Agent Model Validation Tests
# ============================================================================


class TestAgentValidation:
    """Tests for input validation on agent routes."""

    def test_run_agent_missing_spec_id(self, test_client):
        """Test running agent without spec_id."""
        response = test_client.post("/api/agents/run", json={"agent_type": "planner"})

        assert response.status_code == 422

    def test_run_agent_missing_agent_type(self, test_client):
        """Test running agent without agent_type."""
        response = test_client.post("/api/agents/run", json={"spec_id": "001"})

        assert response.status_code == 422

    def test_run_agent_invalid_agent_type(self, test_client):
        """Test running agent with invalid agent_type."""
        response = test_client.post(
            "/api/agents/run", json={"spec_id": "001", "agent_type": "invalid"}
        )

        assert response.status_code == 422

    def test_run_agent_with_all_options(self, test_client):
        """Test running agent with all optional fields."""
        with patch("api.routes.agents.start_agent_task") as mock_start:
            with patch("api.routes.agents.cleanup_completed_tasks"):
                mock_start.return_value = "001:coder"

                response = test_client.post(
                    "/api/agents/run",
                    json={
                        "spec_id": "001",
                        "agent_type": "coder",
                        "model": "claude-sonnet-4-5-20250929",
                        "verbose": True,
                    },
                )

                assert response.status_code == 202
                mock_start.assert_called_once()
                call_kwargs = mock_start.call_args
                # Verify all parameters were passed
                assert call_kwargs[1]["spec_id"] == "001"
                assert call_kwargs[1]["agent_type"] == "coder"
                assert call_kwargs[1]["verbose"] is True


# ============================================================================
# Agent Endpoint URL Encoding Tests
# ============================================================================


class TestAgentURLEncoding:
    """Tests for proper handling of URL-encoded task IDs."""

    @patch("api.routes.agents.get_task_status")
    def test_status_with_colon_in_task_id(self, mock_status, test_client):
        """Test getting status with task ID containing colon."""
        mock_status.return_value = {"status": "running"}

        response = test_client.get("/api/agents/status/001-feature:planner")

        assert response.status_code == 200
        mock_status.assert_called_once_with("001-feature:planner")

    @patch("api.routes.agents.cancel_task")
    def test_cancel_with_colon_in_task_id(self, mock_cancel, test_client):
        """Test cancelling with task ID containing colon."""
        mock_cancel.return_value = True

        response = test_client.post("/api/agents/cancel/001-feature:qa_reviewer")

        assert response.status_code == 200
        mock_cancel.assert_called_once_with("001-feature:qa_reviewer")


# ============================================================================
# Test Summary
# ============================================================================


def test_agent_test_summary():
    """
    Agent API test coverage summary.

    This test always passes and serves as documentation of what is tested.
    """
    coverage = {
        "request_response_models": [
            "Valid agent run request",
            "Spec ID with name suffix",
            "All agent types (planner, coder, qa_reviewer, qa_fixer)",
            "Default values",
            "Run response model",
            "Status response (running/completed/failed)",
            "Cancel response model",
        ],
        "run_endpoint": [
            "Successful agent start",
            "Spec not found (404)",
            "Already running (409)",
            "Invalid request (422)",
            "Server error (500)",
        ],
        "status_endpoint": [
            "Running task status",
            "Completed task status",
            "Failed task status",
            "Task not found (404)",
        ],
        "cancel_endpoint": [
            "Successful cancellation",
            "Task not found/already done",
            "Server error",
        ],
        "health_endpoint": [
            "Health check response",
        ],
        "agent_runner_service": [
            "Log sanitization",
            "Get non-existent task status",
            "Cancel non-existent task",
            "Cleanup completed tasks",
        ],
        "validation": [
            "Missing spec_id",
            "Missing agent_type",
            "Invalid agent_type",
            "All optional fields",
        ],
        "url_encoding": [
            "Task ID with colon",
        ],
    }

    print("\n" + "=" * 70)
    print("AGENT API TEST COVERAGE SUMMARY")
    print("=" * 70)

    for category, tests in coverage.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for test in tests:
            print(f"  - {test}")

    print("\n" + "=" * 70)

    assert True
