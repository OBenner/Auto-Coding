"""
Parametrized API tests for /api/specs and /api/tasks endpoints.

Both endpoints are synonymous in Auto Code (specs and tasks share the same
underlying data and logic). This single parametrized file replaces the
previously duplicated test_api_specs.py and test_api_tasks.py files.
"""

import json

import pytest
from httpx import AsyncClient

# Parametrize all shared tests across both endpoints.
# Each tuple: (url_prefix, response_list_key, not_found_label)
_ENDPOINTS = [
    pytest.param("/api/specs", "specs", "Spec", id="specs"),
    pytest.param("/api/tasks", "tasks", "Task", id="tasks"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_list_without_auth(
    async_client: AsyncClient, url_prefix, list_key, label
):
    """Test that list endpoint requires authentication."""
    response = await async_client.get(url_prefix)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_list_with_expired_token(
    async_client: AsyncClient, expired_token: str, url_prefix, list_key, label
):
    """Test that list endpoint rejects expired tokens."""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get(url_prefix, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_list_with_invalid_token(
    async_client: AsyncClient, url_prefix, list_key, label
):
    """Test that list endpoint rejects invalid tokens."""
    headers = {"Authorization": "Bearer invalid-token-12345"}
    response = await async_client.get(url_prefix, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_list_success(
    async_client: AsyncClient, auth_headers: dict, url_prefix, list_key, label
):
    """Test successful listing with valid authentication."""
    response = await async_client.get(url_prefix, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert list_key in data
    assert "total" in data
    assert isinstance(data[list_key], list)
    assert isinstance(data["total"], int)

    if data["total"] > 0:
        item = data[list_key][0]
        assert "number" in item
        assert "name" in item
        assert "folder" in item
        assert "status" in item
        assert "progress" in item
        assert "has_build" in item


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_list_empty_specs_dir(
    async_client: AsyncClient,
    auth_headers: dict,
    monkeypatch,
    tmp_path,
    url_prefix,
    list_key,
    label,
):
    """Test list endpoint when specs directory doesn't exist."""

    def mock_get_specs_dir():
        return tmp_path / "nonexistent-specs"

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(url_prefix, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data[list_key] == []
    assert data["total"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_get_detail_without_auth(
    async_client: AsyncClient, url_prefix, list_key, label
):
    """Test that detail endpoint requires authentication."""
    response = await async_client.get(f"{url_prefix}/001")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_get_detail_with_expired_token(
    async_client: AsyncClient,
    expired_token: str,
    url_prefix,
    list_key,
    label,
):
    """Test that detail endpoint rejects expired tokens."""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get(f"{url_prefix}/001", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_get_detail_not_found(
    async_client: AsyncClient,
    auth_headers: dict,
    monkeypatch,
    tmp_path,
    url_prefix,
    list_key,
    label,
):
    """Test detail endpoint when item doesn't exist."""

    def mock_get_specs_dir():
        return tmp_path / "nonexistent-specs"

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(f"{url_prefix}/999", headers=auth_headers)
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "999" in data["detail"]
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_get_detail_success(
    async_client: AsyncClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
    url_prefix,
    list_key,
    label,
):
    """Test successful detail retrieval."""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "001-test-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_content = "# Test Feature\n\nThis is a test spec."
    spec_file.write_text(spec_content, encoding="utf-8")

    plan_file = spec_folder / "implementation_plan.json"
    plan_data = {
        "phases": [
            {
                "name": "Phase 1",
                "subtasks": [
                    {"id": "subtask-1", "status": "completed"},
                    {"id": "subtask-2", "status": "in_progress"},
                    {"id": "subtask-3", "status": "pending"},
                ],
            }
        ]
    }
    plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(f"{url_prefix}/001", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["number"] == "001"
    assert data["name"] == "test-feature"
    assert data["folder"] == "001-test-feature"
    assert data["status"] == "in_progress"
    assert data["has_build"] is True
    assert data["spec_content"] == spec_content

    progress = data["progress"]
    assert progress["completed"] == 1
    assert progress["in_progress"] == 1
    assert progress["pending"] == 1
    assert progress["failed"] == 0
    assert progress["total"] == 3
    assert progress["percentage"] == pytest.approx(33.33, rel=0.1)


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_get_detail_with_full_folder_name(
    async_client: AsyncClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
    url_prefix,
    list_key,
    label,
):
    """Test detail endpoint using full folder name instead of just number."""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "002-another-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Another Feature", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(
        f"{url_prefix}/002-another-feature", headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["number"] == "002"
    assert data["name"] == "another-feature"


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_get_detail_no_implementation_plan(
    async_client: AsyncClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
    url_prefix,
    list_key,
    label,
):
    """Test detail endpoint when implementation_plan.json doesn't exist."""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "003-pending-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Pending Feature", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(f"{url_prefix}/003", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pending"
    assert data["has_build"] is False
    assert data["progress"]["total"] == 0
    assert data["progress"]["percentage"] == pytest.approx(0.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_get_detail_completed(
    async_client: AsyncClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
    url_prefix,
    list_key,
    label,
):
    """Test detail endpoint for a fully completed item."""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "004-completed-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Completed Feature", encoding="utf-8")

    plan_file = spec_folder / "implementation_plan.json"
    plan_data = {
        "phases": [
            {
                "name": "Phase 1",
                "subtasks": [
                    {"id": "subtask-1", "status": "completed"},
                    {"id": "subtask-2", "status": "completed"},
                ],
            }
        ]
    }
    plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(f"{url_prefix}/004", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "complete"
    assert data["progress"]["completed"] == 2
    assert data["progress"]["total"] == 2
    assert data["progress"]["percentage"] == pytest.approx(100.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_get_detail_read_error(
    async_client: AsyncClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
    url_prefix,
    list_key,
    label,
):
    """Test detail endpoint when spec.md exists but can't be read."""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "005-unreadable-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Feature", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    # Replace spec.md with a directory of the same name to trigger a read error
    spec_file.unlink()
    spec_file.mkdir()

    response = await async_client.get(f"{url_prefix}/005", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["spec_content"] is None
    assert data["number"] == "005"


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_health(async_client: AsyncClient, url_prefix, list_key, label):
    """Test health endpoint (no auth required)."""
    endpoint_name = url_prefix.split("/")[-1]  # "specs" or "tasks"
    response = await async_client.get(f"{url_prefix}/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["endpoint"] == endpoint_name
    assert "project_dir" not in data, "Health endpoint must not expose filesystem paths"
    assert "specs_dir_exists" not in data, (
        "Health endpoint must not expose filesystem details"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_list_with_multiple_items(
    async_client: AsyncClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
    url_prefix,
    list_key,
    label,
):
    """Test list endpoint with multiple items in different states."""
    specs_dir = tmp_path / "specs"

    spec1 = specs_dir / "001-pending"
    spec1.mkdir(parents=True)
    (spec1 / "spec.md").write_text("# Pending", encoding="utf-8")

    spec2 = specs_dir / "002-in-progress"
    spec2.mkdir(parents=True)
    (spec2 / "spec.md").write_text("# In Progress", encoding="utf-8")
    plan2 = {
        "phases": [{"subtasks": [{"status": "completed"}, {"status": "in_progress"}]}]
    }
    (spec2 / "implementation_plan.json").write_text(json.dumps(plan2), encoding="utf-8")

    spec3 = specs_dir / "003-complete"
    spec3.mkdir(parents=True)
    (spec3 / "spec.md").write_text("# Complete", encoding="utf-8")
    plan3 = {
        "phases": [{"subtasks": [{"status": "completed"}, {"status": "completed"}]}]
    }
    (spec3 / "implementation_plan.json").write_text(json.dumps(plan3), encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(url_prefix, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert len(data[list_key]) == 3

    items = {item["number"]: item for item in data[list_key]}

    assert items["001"]["status"] == "pending"
    assert items["001"]["has_build"] is False
    assert items["001"]["progress"] == "-"

    assert "in_progress" in items["002"]["status"]
    assert items["002"]["has_build"] is True
    assert items["002"]["progress"] == "1/2"

    assert "complete" in items["003"]["status"]
    assert items["003"]["has_build"] is True
    assert items["003"]["progress"] == "2/2"


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_list_ignores_invalid_folders(
    async_client: AsyncClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
    url_prefix,
    list_key,
    label,
):
    """Test that list endpoint ignores folders that don't match the naming pattern."""
    specs_dir = tmp_path / "specs"

    valid_spec = specs_dir / "001-valid-spec"
    valid_spec.mkdir(parents=True)
    (valid_spec / "spec.md").write_text("# Valid", encoding="utf-8")

    (specs_dir / "invalid-no-number").mkdir(parents=True)
    (specs_dir / "002").mkdir(parents=True)
    (specs_dir / "random-folder").mkdir(parents=True)
    (specs_dir / "file.txt").write_text("not a spec")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(url_prefix, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data[list_key][0]["number"] == "001"


@pytest.mark.asyncio
@pytest.mark.parametrize("url_prefix,list_key,label", _ENDPOINTS)
async def test_list_missing_spec_md(
    async_client: AsyncClient,
    auth_headers: dict,
    tmp_path,
    monkeypatch,
    url_prefix,
    list_key,
    label,
):
    """Test that list endpoint ignores spec folders without spec.md."""
    specs_dir = tmp_path / "specs"

    spec_no_md = specs_dir / "001-incomplete"
    spec_no_md.mkdir(parents=True)

    valid_spec = specs_dir / "002-valid"
    valid_spec.mkdir(parents=True)
    (valid_spec / "spec.md").write_text("# Valid", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get(url_prefix, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data[list_key][0]["number"] == "002"
