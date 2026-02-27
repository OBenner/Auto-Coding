"""
Integration tests for Agents API endpoints

Tests all /api/agents endpoints including authentication, validation,
error handling, and response formats.
"""

import pytest
from pathlib import Path
from httpx import AsyncClient
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_run_agent_without_auth(async_client: AsyncClient):
    """Test that run_agent requires authentication"""
    request_data = {
        "spec_id": "001",
        "agent_type": "planner"
    }
    response = await async_client.post("/api/agents/run", json=request_data)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_run_agent_with_expired_token(async_client: AsyncClient, expired_token: str):
    """Test that run_agent rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    request_data = {
        "spec_id": "001",
        "agent_type": "planner"
    }
    response = await async_client.post("/api/agents/run", json=request_data, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_run_agent_with_invalid_token(async_client: AsyncClient):
    """Test that run_agent rejects invalid tokens"""
    headers = {"Authorization": "Bearer invalid-token-12345"}
    request_data = {
        "spec_id": "001",
        "agent_type": "planner"
    }
    response = await async_client.post("/api/agents/run", json=request_data, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_run_agent_success(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test successful agent execution request"""
    # Create mock spec directory
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "001-test-feature"
    spec_folder.mkdir(parents=True)
    (spec_folder / "spec.md").write_text("# Test Feature", encoding="utf-8")

    # Mock _get_project_dir to return our tmp_path
    def mock_get_project_dir():
        return tmp_path

    # Mock start_agent_task to return task_id without actually starting
    def mock_start_agent_task(spec_id, agent_type, project_dir, model, verbose):
        return f"{spec_id}:{agent_type}"

    # Mock cleanup
    def mock_cleanup():
        pass

    import api.routes.agents as agents_module
    import services.agent_runner as runner_module

    monkeypatch.setattr(agents_module, "_get_project_dir", mock_get_project_dir)
    monkeypatch.setattr(runner_module, "start_agent_task", mock_start_agent_task)
    monkeypatch.setattr(runner_module, "cleanup_completed_tasks", mock_cleanup)

    request_data = {
        "spec_id": "001",
        "agent_type": "planner",
        "model": "claude-sonnet-4-5-20250929",
        "verbose": False
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 202

    data = response.json()
    assert data["task_id"] == "001:planner"
    assert data["spec_id"] == "001"
    assert data["agent_type"] == "planner"
    assert data["status"] == "started"
    assert "started" in data["message"].lower()


@pytest.mark.asyncio
async def test_run_agent_spec_not_found(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test run_agent when spec doesn't exist"""
    # Mock to return non-existent specs dir
    def mock_get_project_dir():
        return tmp_path / "nonexistent"

    # Mock start_agent_task to raise FileNotFoundError
    def mock_start_agent_task(spec_id, agent_type, project_dir, model, verbose):
        raise FileNotFoundError(f"Spec not found: {spec_id}")

    import api.routes.agents as agents_module
    import services.agent_runner as runner_module

    monkeypatch.setattr(agents_module, "_get_project_dir", mock_get_project_dir)
    monkeypatch.setattr(runner_module, "start_agent_task", mock_start_agent_task)

    request_data = {
        "spec_id": "999",
        "agent_type": "planner"
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "999" in data["detail"]


@pytest.mark.asyncio
async def test_run_agent_already_running(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test run_agent when task is already running"""
    def mock_get_project_dir():
        return tmp_path

    # Mock start_agent_task to raise RuntimeError
    def mock_start_agent_task(spec_id, agent_type, project_dir, model, verbose):
        raise RuntimeError(f"Agent task already running for spec {spec_id}")

    import api.routes.agents as agents_module
    import services.agent_runner as runner_module

    monkeypatch.setattr(agents_module, "_get_project_dir", mock_get_project_dir)
    monkeypatch.setattr(runner_module, "start_agent_task", mock_start_agent_task)

    request_data = {
        "spec_id": "001",
        "agent_type": "coder"
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 409

    data = response.json()
    assert "detail" in data
    assert "running" in data["detail"].lower()


@pytest.mark.asyncio
async def test_run_agent_invalid_agent_type(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test run_agent with invalid agent type"""
    def mock_get_project_dir():
        return tmp_path

    # Mock start_agent_task to raise ValueError
    def mock_start_agent_task(spec_id, agent_type, project_dir, model, verbose):
        raise ValueError(f"Invalid agent_type: {agent_type}")

    import api.routes.agents as agents_module
    import services.agent_runner as runner_module

    monkeypatch.setattr(agents_module, "_get_project_dir", mock_get_project_dir)
    monkeypatch.setattr(runner_module, "start_agent_task", mock_start_agent_task)

    request_data = {
        "spec_id": "001",
        "agent_type": "invalid_agent"
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    # FastAPI returns 422 for invalid Literal enum values (Pydantic validation error)
    assert response.status_code == 422

    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_run_agent_all_agent_types(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test run_agent with all valid agent types"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "001-test"
    spec_folder.mkdir(parents=True)
    (spec_folder / "spec.md").write_text("# Test", encoding="utf-8")

    def mock_get_project_dir():
        return tmp_path

    def mock_start_agent_task(spec_id, agent_type, project_dir, model, verbose):
        return f"{spec_id}:{agent_type}"

    def mock_cleanup():
        pass

    import api.routes.agents as agents_module
    import services.agent_runner as runner_module

    monkeypatch.setattr(agents_module, "_get_project_dir", mock_get_project_dir)
    monkeypatch.setattr(runner_module, "start_agent_task", mock_start_agent_task)
    monkeypatch.setattr(runner_module, "cleanup_completed_tasks", mock_cleanup)

    # Test all valid agent types
    valid_types = ["planner", "coder", "qa_reviewer", "qa_fixer"]

    for agent_type in valid_types:
        request_data = {
            "spec_id": "001",
            "agent_type": agent_type
        }

        response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
        assert response.status_code == 202

        data = response.json()
        assert data["agent_type"] == agent_type
        assert data["task_id"] == f"001:{agent_type}"


@pytest.mark.asyncio
async def test_run_agent_with_custom_model(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test run_agent with custom model parameter"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "001-test"
    spec_folder.mkdir(parents=True)
    (spec_folder / "spec.md").write_text("# Test", encoding="utf-8")

    def mock_get_project_dir():
        return tmp_path

    captured_model = None

    def mock_start_agent_task(spec_id, agent_type, project_dir, model, verbose):
        nonlocal captured_model
        captured_model = model
        return f"{spec_id}:{agent_type}"

    def mock_cleanup():
        pass

    import api.routes.agents as agents_module
    import services.agent_runner as runner_module

    monkeypatch.setattr(agents_module, "_get_project_dir", mock_get_project_dir)
    monkeypatch.setattr(runner_module, "start_agent_task", mock_start_agent_task)
    monkeypatch.setattr(runner_module, "cleanup_completed_tasks", mock_cleanup)

    request_data = {
        "spec_id": "001",
        "agent_type": "planner",
        "model": "claude-opus-4-20250514",
        "verbose": True
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 202
    assert captured_model == "claude-opus-4-20250514"


@pytest.mark.asyncio
async def test_get_agent_status_without_auth(async_client: AsyncClient):
    """Test that get_agent_status requires authentication"""
    response = await async_client.get("/api/agents/status/001:planner")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_agent_status_with_expired_token(async_client: AsyncClient, expired_token: str):
    """Test that get_agent_status rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get("/api/agents/status/001:planner", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_agent_status_not_found(async_client: AsyncClient, auth_headers: dict, monkeypatch):
    """Test get_agent_status when task doesn't exist"""
    def mock_get_task_status(task_id):
        return None

    import services.agent_runner as runner_module
    monkeypatch.setattr(runner_module, "get_task_status", mock_get_task_status)

    response = await async_client.get("/api/agents/status/999:planner", headers=auth_headers)
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "999:planner" in data["detail"]


@pytest.mark.asyncio
async def test_get_agent_status_running(async_client: AsyncClient, auth_headers: dict, monkeypatch):
    """Test get_agent_status for a running task"""
    def mock_get_task_status(task_id):
        return {
            "status": "running"
        }

    import services.agent_runner as runner_module
    monkeypatch.setattr(runner_module, "get_task_status", mock_get_task_status)

    response = await async_client.get("/api/agents/status/001:planner", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == "001:planner"
    assert data["status"] == "running"
    assert data["result"] is None
    assert data["error"] is None


@pytest.mark.asyncio
async def test_get_agent_status_completed(async_client: AsyncClient, auth_headers: dict, monkeypatch):
    """Test get_agent_status for a completed task"""
    def mock_get_task_status(task_id):
        return {
            "status": "completed",
            "result": {
                "success": True,
                "agent_type": "planner",
                "message": "Planner execution completed"
            }
        }

    import services.agent_runner as runner_module
    monkeypatch.setattr(runner_module, "get_task_status", mock_get_task_status)

    response = await async_client.get("/api/agents/status/001:planner", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == "001:planner"
    assert data["status"] == "completed"
    assert data["result"]["success"] is True
    assert data["result"]["agent_type"] == "planner"
    assert data["error"] is None


@pytest.mark.asyncio
async def test_get_agent_status_failed(async_client: AsyncClient, auth_headers: dict, monkeypatch):
    """Test get_agent_status for a failed task"""
    def mock_get_task_status(task_id):
        return {
            "status": "failed",
            "error": "Agent execution error: Something went wrong"
        }

    import services.agent_runner as runner_module
    monkeypatch.setattr(runner_module, "get_task_status", mock_get_task_status)

    response = await async_client.get("/api/agents/status/001:coder", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == "001:coder"
    assert data["status"] == "failed"
    assert data["result"] is None
    assert "error" in data["error"].lower()


@pytest.mark.asyncio
async def test_cancel_agent_without_auth(async_client: AsyncClient):
    """Test that cancel_agent requires authentication"""
    response = await async_client.post("/api/agents/cancel/001:planner")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_agent_with_expired_token(async_client: AsyncClient, expired_token: str):
    """Test that cancel_agent rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.post("/api/agents/cancel/001:planner", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cancel_agent_success(async_client: AsyncClient, auth_headers: dict, monkeypatch):
    """Test successful agent cancellation"""
    def mock_cancel_task(task_id):
        return True

    import services.agent_runner as runner_module
    monkeypatch.setattr(runner_module, "cancel_task", mock_cancel_task)

    response = await async_client.post("/api/agents/cancel/001:coder", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == "001:coder"
    assert data["cancelled"] is True
    assert "cancelled" in data["message"].lower()


@pytest.mark.asyncio
async def test_cancel_agent_not_found(async_client: AsyncClient, auth_headers: dict, monkeypatch):
    """Test cancel_agent when task doesn't exist"""
    def mock_cancel_task(task_id):
        return False

    import services.agent_runner as runner_module
    monkeypatch.setattr(runner_module, "cancel_task", mock_cancel_task)

    response = await async_client.post("/api/agents/cancel/999:planner", headers=auth_headers)
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "999:planner" in data["detail"]


@pytest.mark.asyncio
async def test_cancel_agent_already_completed(async_client: AsyncClient, auth_headers: dict, monkeypatch):
    """Test cancel_agent for an already completed task"""
    def mock_cancel_task(task_id):
        return False

    import services.agent_runner as runner_module
    monkeypatch.setattr(runner_module, "cancel_task", mock_cancel_task)

    response = await async_client.post("/api/agents/cancel/001:planner", headers=auth_headers)
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_agents_health(async_client: AsyncClient):
    """Test agents health endpoint (no auth required)"""
    response = await async_client.get("/api/agents/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["endpoint"] == "agents"


@pytest.mark.asyncio
async def test_run_agent_missing_spec_id(async_client: AsyncClient, auth_headers: dict):
    """Test run_agent with missing spec_id (validation error)"""
    request_data = {
        "agent_type": "planner"
        # Missing spec_id
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 422  # Validation error

    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_run_agent_missing_agent_type(async_client: AsyncClient, auth_headers: dict):
    """Test run_agent with missing agent_type (validation error)"""
    request_data = {
        "spec_id": "001"
        # Missing agent_type
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 422  # Validation error

    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_run_agent_invalid_model_type(async_client: AsyncClient, auth_headers: dict):
    """Test run_agent with invalid model type (non-string)"""
    request_data = {
        "spec_id": "001",
        "agent_type": "planner",
        "model": 12345  # Should be string
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_run_agent_invalid_verbose_type(async_client: AsyncClient, auth_headers: dict):
    """Test run_agent with invalid verbose type (non-boolean, non-coercible)"""
    request_data = {
        "spec_id": "001",
        "agent_type": "planner",
        "verbose": []  # Empty list cannot be coerced to bool by Pydantic
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_run_agent_server_error(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test run_agent handles unexpected server errors"""
    def mock_get_project_dir():
        return tmp_path

    # Mock start_agent_task to raise unexpected error
    def mock_start_agent_task(spec_id, agent_type, project_dir, model, verbose):
        raise Exception("Unexpected server error")

    import api.routes.agents as agents_module
    import services.agent_runner as runner_module

    monkeypatch.setattr(agents_module, "_get_project_dir", mock_get_project_dir)
    monkeypatch.setattr(runner_module, "start_agent_task", mock_start_agent_task)

    request_data = {
        "spec_id": "001",
        "agent_type": "planner"
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 500

    data = response.json()
    assert "detail" in data
    # API must return a generic error message, not leak the raw exception
    assert "failed" in data["detail"].lower()
    assert "Unexpected server error" not in data["detail"]


@pytest.mark.asyncio
async def test_run_agent_with_spec_folder_name(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test run_agent with full spec folder name instead of just number"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "002-my-feature"
    spec_folder.mkdir(parents=True)
    (spec_folder / "spec.md").write_text("# My Feature", encoding="utf-8")

    def mock_get_project_dir():
        return tmp_path

    def mock_start_agent_task(spec_id, agent_type, project_dir, model, verbose):
        return f"{spec_id}:{agent_type}"

    def mock_cleanup():
        pass

    import api.routes.agents as agents_module
    import services.agent_runner as runner_module

    monkeypatch.setattr(agents_module, "_get_project_dir", mock_get_project_dir)
    monkeypatch.setattr(runner_module, "start_agent_task", mock_start_agent_task)
    monkeypatch.setattr(runner_module, "cleanup_completed_tasks", mock_cleanup)

    request_data = {
        "spec_id": "002-my-feature",
        "agent_type": "coder"
    }

    response = await async_client.post("/api/agents/run", json=request_data, headers=auth_headers)
    assert response.status_code == 202

    data = response.json()
    assert data["spec_id"] == "002-my-feature"
    assert data["task_id"] == "002-my-feature:coder"
