"""
Integration tests for Tasks API endpoints

Tests all /api/tasks endpoints including authentication, validation,
error handling, and response formats.
"""

import json
import pytest
from pathlib import Path
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_tasks_without_auth(async_client: AsyncClient):
    """Test that list_tasks requires authentication"""
    response = await async_client.get("/api/tasks")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_list_tasks_with_expired_token(async_client: AsyncClient, expired_token: str):
    """Test that list_tasks rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get("/api/tasks", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_tasks_with_invalid_token(async_client: AsyncClient):
    """Test that list_tasks rejects invalid tokens"""
    headers = {"Authorization": "Bearer invalid-token-12345"}
    response = await async_client.get("/api/tasks", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_tasks_success(async_client: AsyncClient, auth_headers: dict):
    """Test successful task listing with valid authentication"""
    response = await async_client.get("/api/tasks", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "tasks" in data
    assert "total" in data
    assert isinstance(data["tasks"], list)
    assert isinstance(data["total"], int)

    # Verify response structure matches TaskListResponse
    if data["total"] > 0:
        task = data["tasks"][0]
        assert "number" in task
        assert "name" in task
        assert "folder" in task
        assert "status" in task
        assert "progress" in task
        assert "has_build" in task


@pytest.mark.asyncio
async def test_list_tasks_empty_specs_dir(async_client: AsyncClient, auth_headers: dict, monkeypatch, tmp_path):
    """Test list_tasks when specs directory doesn't exist"""
    # Patch the _get_specs_dir function to return a non-existent path
    def mock_get_specs_dir():
        return tmp_path / "nonexistent-specs"

    import api.routes.tasks as tasks_module
    monkeypatch.setattr(tasks_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/tasks", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tasks"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_task_detail_without_auth(async_client: AsyncClient):
    """Test that get_task_detail requires authentication"""
    response = await async_client.get("/api/tasks/001")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_task_detail_with_expired_token(async_client: AsyncClient, expired_token: str):
    """Test that get_task_detail rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get("/api/tasks/001", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_task_detail_not_found(async_client: AsyncClient, auth_headers: dict, monkeypatch, tmp_path):
    """Test get_task_detail when task doesn't exist"""
    # Patch to return non-existent specs dir
    def mock_get_specs_dir():
        return tmp_path / "nonexistent-specs"

    import api.routes.tasks as tasks_module
    monkeypatch.setattr(tasks_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/tasks/999", headers=auth_headers)
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "999" in data["detail"]
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_task_detail_success(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test successful task detail retrieval"""
    # Create a mock spec directory structure
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "001-test-feature"
    spec_folder.mkdir(parents=True)

    # Create spec.md
    spec_file = spec_folder / "spec.md"
    spec_content = "# Test Feature\n\nThis is a test spec."
    spec_file.write_text(spec_content, encoding="utf-8")

    # Create implementation_plan.json
    plan_file = spec_folder / "implementation_plan.json"
    plan_data = {
        "phases": [
            {
                "name": "Phase 1",
                "subtasks": [
                    {"id": "subtask-1", "status": "completed"},
                    {"id": "subtask-2", "status": "in_progress"},
                    {"id": "subtask-3", "status": "pending"}
                ]
            }
        ]
    }
    plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

    # Patch _get_specs_dir to return our tmp_path
    def mock_get_specs_dir():
        return specs_dir

    import api.routes.tasks as tasks_module
    monkeypatch.setattr(tasks_module, "_get_specs_dir", mock_get_specs_dir)

    # Test with task number
    response = await async_client.get("/api/tasks/001", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["number"] == "001"
    assert data["name"] == "test-feature"
    assert data["folder"] == "001-test-feature"
    assert data["status"] == "in_progress"
    assert data["has_build"] is True
    assert data["spec_content"] == spec_content

    # Verify progress detail
    progress = data["progress"]
    assert progress["completed"] == 1
    assert progress["in_progress"] == 1
    assert progress["pending"] == 1
    assert progress["failed"] == 0
    assert progress["total"] == 3
    assert progress["percentage"] == pytest.approx(33.33, rel=0.1)


@pytest.mark.asyncio
async def test_get_task_detail_with_full_folder_name(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_task_detail using full folder name instead of just number"""
    # Create a mock spec directory structure
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "002-another-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Another Feature", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.tasks as tasks_module
    monkeypatch.setattr(tasks_module, "_get_specs_dir", mock_get_specs_dir)

    # Test with full folder name
    response = await async_client.get("/api/tasks/002-another-feature", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["number"] == "002"
    assert data["name"] == "another-feature"


@pytest.mark.asyncio
async def test_get_task_detail_no_implementation_plan(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_task_detail when implementation_plan.json doesn't exist"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "003-pending-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Pending Feature", encoding="utf-8")
    # No implementation_plan.json created

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.tasks as tasks_module
    monkeypatch.setattr(tasks_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/tasks/003", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pending"
    assert data["has_build"] is False
    assert data["progress"]["total"] == 0
    assert data["progress"]["percentage"] == 0.0


@pytest.mark.asyncio
async def test_get_task_detail_completed_task(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_task_detail for a fully completed task"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "004-completed-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Completed Feature", encoding="utf-8")

    # All subtasks completed
    plan_file = spec_folder / "implementation_plan.json"
    plan_data = {
        "phases": [
            {
                "name": "Phase 1",
                "subtasks": [
                    {"id": "subtask-1", "status": "completed"},
                    {"id": "subtask-2", "status": "completed"}
                ]
            }
        ]
    }
    plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.tasks as tasks_module
    monkeypatch.setattr(tasks_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/tasks/004", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "complete"
    assert data["progress"]["completed"] == 2
    assert data["progress"]["total"] == 2
    assert data["progress"]["percentage"] == 100.0


@pytest.mark.asyncio
async def test_get_task_detail_spec_read_error(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_task_detail when spec.md exists but can't be read"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "005-unreadable-feature"
    spec_folder.mkdir(parents=True)

    # Create spec.md but make it unreadable (we'll simulate this with monkeypatch)
    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Feature", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    # Mock read_text to raise an exception
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self.name == "spec.md":
            raise OSError("Permission denied")
        return original_read_text(self, *args, **kwargs)

    import api.routes.tasks as tasks_module
    monkeypatch.setattr(tasks_module, "_get_specs_dir", mock_get_specs_dir)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    response = await async_client.get("/api/tasks/005", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    # Should still return task info, just with None spec_content
    assert data["spec_content"] is None
    assert data["number"] == "005"


@pytest.mark.asyncio
async def test_tasks_health(async_client: AsyncClient):
    """Test tasks health endpoint (no auth required)"""
    response = await async_client.get("/api/tasks/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["endpoint"] == "tasks"
    assert "project_dir" in data
    assert "specs_dir_exists" in data
    assert isinstance(data["specs_dir_exists"], bool)


@pytest.mark.asyncio
async def test_list_tasks_with_multiple_specs(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test list_tasks with multiple specs in different states"""
    specs_dir = tmp_path / "specs"

    # Spec 1: pending (no plan)
    spec1 = specs_dir / "001-pending"
    spec1.mkdir(parents=True)
    (spec1 / "spec.md").write_text("# Pending", encoding="utf-8")

    # Spec 2: in progress
    spec2 = specs_dir / "002-in-progress"
    spec2.mkdir(parents=True)
    (spec2 / "spec.md").write_text("# In Progress", encoding="utf-8")
    plan2 = {
        "phases": [
            {
                "subtasks": [
                    {"status": "completed"},
                    {"status": "in_progress"}
                ]
            }
        ]
    }
    (spec2 / "implementation_plan.json").write_text(json.dumps(plan2), encoding="utf-8")

    # Spec 3: complete
    spec3 = specs_dir / "003-complete"
    spec3.mkdir(parents=True)
    (spec3 / "spec.md").write_text("# Complete", encoding="utf-8")
    plan3 = {
        "phases": [
            {
                "subtasks": [
                    {"status": "completed"},
                    {"status": "completed"}
                ]
            }
        ]
    }
    (spec3 / "implementation_plan.json").write_text(json.dumps(plan3), encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.tasks as tasks_module
    monkeypatch.setattr(tasks_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/tasks", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert len(data["tasks"]) == 3

    # Verify each task has expected fields and values
    tasks = {task["number"]: task for task in data["tasks"]}

    assert tasks["001"]["status"] == "pending"
    assert tasks["001"]["has_build"] is False
    assert tasks["001"]["progress"] == "-"

    assert "in_progress" in tasks["002"]["status"]
    assert tasks["002"]["has_build"] is True
    assert tasks["002"]["progress"] == "1/2"

    assert "complete" in tasks["003"]["status"]
    assert tasks["003"]["has_build"] is True
    assert tasks["003"]["progress"] == "2/2"
