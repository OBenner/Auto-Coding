"""
Integration tests for Specs API endpoints

Tests all /api/specs endpoints including authentication, validation,
error handling, and response formats.
Specs and tasks are synonymous in Auto Claude - this tests the alias endpoint.
"""

import json
import pytest
from pathlib import Path
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_specs_without_auth(async_client: AsyncClient):
    """Test that list_specs requires authentication"""
    response = await async_client.get("/api/specs")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_list_specs_with_expired_token(async_client: AsyncClient, expired_token: str):
    """Test that list_specs rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get("/api/specs", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_specs_with_invalid_token(async_client: AsyncClient):
    """Test that list_specs rejects invalid tokens"""
    headers = {"Authorization": "Bearer invalid-token-12345"}
    response = await async_client.get("/api/specs", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_specs_success(async_client: AsyncClient, auth_headers: dict):
    """Test successful spec listing with valid authentication"""
    response = await async_client.get("/api/specs", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "specs" in data
    assert "total" in data
    assert isinstance(data["specs"], list)
    assert isinstance(data["total"], int)

    # Verify response structure matches SpecListResponse
    if data["total"] > 0:
        spec = data["specs"][0]
        assert "number" in spec
        assert "name" in spec
        assert "folder" in spec
        assert "status" in spec
        assert "progress" in spec
        assert "has_build" in spec


@pytest.mark.asyncio
async def test_list_specs_empty_specs_dir(async_client: AsyncClient, auth_headers: dict, monkeypatch, tmp_path):
    """Test list_specs when specs directory doesn't exist"""
    # Patch the _get_specs_dir function to return a non-existent path
    def mock_get_specs_dir():
        return tmp_path / "nonexistent-specs"

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["specs"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_spec_detail_without_auth(async_client: AsyncClient):
    """Test that get_spec_detail requires authentication"""
    response = await async_client.get("/api/specs/001")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_spec_detail_with_expired_token(async_client: AsyncClient, expired_token: str):
    """Test that get_spec_detail rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get("/api/specs/001", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_spec_detail_not_found(async_client: AsyncClient, auth_headers: dict, monkeypatch, tmp_path):
    """Test get_spec_detail when spec doesn't exist"""
    # Patch to return non-existent specs dir
    def mock_get_specs_dir():
        return tmp_path / "nonexistent-specs"

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs/999", headers=auth_headers)
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "999" in data["detail"]
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_spec_detail_success(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test successful spec detail retrieval"""
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

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    # Test with spec number
    response = await async_client.get("/api/specs/001", headers=auth_headers)
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
async def test_get_spec_detail_with_full_folder_name(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_spec_detail using full folder name instead of just number"""
    # Create a mock spec directory structure
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "002-another-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Another Feature", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    # Test with full folder name
    response = await async_client.get("/api/specs/002-another-feature", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["number"] == "002"
    assert data["name"] == "another-feature"


@pytest.mark.asyncio
async def test_get_spec_detail_no_implementation_plan(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_spec_detail when implementation_plan.json doesn't exist"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "003-pending-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Pending Feature", encoding="utf-8")
    # No implementation_plan.json created

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs/003", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pending"
    assert data["has_build"] is False
    assert data["progress"]["total"] == 0
    assert data["progress"]["percentage"] == 0.0


@pytest.mark.asyncio
async def test_get_spec_detail_completed_spec(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_spec_detail for a fully completed spec"""
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

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs/004", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "complete"
    assert data["progress"]["completed"] == 2
    assert data["progress"]["total"] == 2
    assert data["progress"]["percentage"] == 100.0


@pytest.mark.asyncio
async def test_get_spec_detail_spec_read_error(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_spec_detail when spec.md exists but can't be read"""
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

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    response = await async_client.get("/api/specs/005", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    # Should still return spec info, just with None spec_content
    assert data["spec_content"] is None
    assert data["number"] == "005"


@pytest.mark.asyncio
async def test_specs_health(async_client: AsyncClient):
    """Test specs health endpoint (no auth required)"""
    response = await async_client.get("/api/specs/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["endpoint"] == "specs"
    assert "project_dir" in data
    assert "specs_dir_exists" in data
    assert isinstance(data["specs_dir_exists"], bool)


@pytest.mark.asyncio
async def test_list_specs_with_multiple_specs(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test list_specs with multiple specs in different states"""
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

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert len(data["specs"]) == 3

    # Verify each spec has expected fields and values
    specs = {spec["number"]: spec for spec in data["specs"]}

    assert specs["001"]["status"] == "pending"
    assert specs["001"]["has_build"] is False
    assert specs["001"]["progress"] == "-"

    assert "in_progress" in specs["002"]["status"]
    assert specs["002"]["has_build"] is True
    assert specs["002"]["progress"] == "1/2"

    assert "complete" in specs["003"]["status"]
    assert specs["003"]["has_build"] is True
    assert specs["003"]["progress"] == "2/2"


@pytest.mark.asyncio
async def test_get_spec_progress_without_auth(async_client: AsyncClient):
    """Test that get_spec_progress requires authentication"""
    response = await async_client.get("/api/specs/001/progress")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_spec_progress_not_found(async_client: AsyncClient, auth_headers: dict, monkeypatch, tmp_path):
    """Test get_spec_progress when spec doesn't exist"""
    def mock_get_specs_dir():
        return tmp_path / "nonexistent-specs"

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs/999/progress", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_spec_progress_success(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test successful spec progress retrieval"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "001-test-feature"
    spec_folder.mkdir(parents=True)

    # Create spec.md
    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Test Feature", encoding="utf-8")

    # Create implementation_plan.json
    plan_file = spec_folder / "implementation_plan.json"
    plan_data = {
        "phases": [
            {
                "subtasks": [
                    {"status": "completed"},
                    {"status": "completed"},
                    {"status": "in_progress"},
                    {"status": "pending"},
                    {"status": "failed"}
                ]
            }
        ]
    }
    plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs/001/progress", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["completed"] == 2
    assert data["in_progress"] == 1
    assert data["pending"] == 1
    assert data["failed"] == 1
    assert data["total"] == 5
    assert data["percentage"] == pytest.approx(40.0, rel=0.1)


@pytest.mark.asyncio
async def test_get_spec_progress_no_plan(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test get_spec_progress when implementation_plan.json doesn't exist"""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "002-pending"
    spec_folder.mkdir(parents=True)
    (spec_folder / "spec.md").write_text("# Pending", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs/002/progress", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["completed"] == 0
    assert data["in_progress"] == 0
    assert data["pending"] == 0
    assert data["failed"] == 0
    assert data["total"] == 0
    assert data["percentage"] == 0.0


@pytest.mark.asyncio
async def test_list_specs_ignores_invalid_folders(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test that list_specs ignores folders that don't match the spec naming pattern"""
    specs_dir = tmp_path / "specs"

    # Valid spec
    valid_spec = specs_dir / "001-valid-spec"
    valid_spec.mkdir(parents=True)
    (valid_spec / "spec.md").write_text("# Valid", encoding="utf-8")

    # Invalid folders (should be ignored)
    (specs_dir / "invalid-no-number").mkdir(parents=True)
    (specs_dir / "002").mkdir(parents=True)  # Missing name part
    (specs_dir / "random-folder").mkdir(parents=True)

    # File (not directory - should be ignored)
    (specs_dir / "file.txt").write_text("not a spec")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["specs"][0]["number"] == "001"


@pytest.mark.asyncio
async def test_list_specs_missing_spec_md(async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch):
    """Test that list_specs ignores spec folders without spec.md"""
    specs_dir = tmp_path / "specs"

    # Spec without spec.md (should be ignored)
    spec_no_md = specs_dir / "001-incomplete"
    spec_no_md.mkdir(parents=True)
    # No spec.md created

    # Valid spec
    valid_spec = specs_dir / "002-valid"
    valid_spec.mkdir(parents=True)
    (valid_spec / "spec.md").write_text("# Valid", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.specs as specs_module
    monkeypatch.setattr(specs_module, "_get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["specs"][0]["number"] == "002"
