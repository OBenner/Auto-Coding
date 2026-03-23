"""
Tests for the /api/specs/{spec_id}/progress endpoint.

The progress endpoint is specs-only (tasks have no equivalent endpoint).
"""

import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_spec_progress_without_auth(async_client: AsyncClient):
    """Test that get_spec_progress requires authentication."""
    response = await async_client.get("/api/specs/001/progress")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_spec_progress_not_found(
    async_client: AsyncClient, auth_headers: dict, monkeypatch, tmp_path
):
    """Test get_spec_progress when spec doesn't exist."""

    def mock_get_specs_dir():
        return tmp_path / "nonexistent-specs"

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs/999/progress", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_spec_progress_success(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test successful spec progress retrieval."""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "001-test-feature"
    spec_folder.mkdir(parents=True)

    spec_file = spec_folder / "spec.md"
    spec_file.write_text("# Test Feature", encoding="utf-8")

    plan_file = spec_folder / "implementation_plan.json"
    plan_data = {
        "phases": [
            {
                "subtasks": [
                    {"status": "completed"},
                    {"status": "completed"},
                    {"status": "in_progress"},
                    {"status": "pending"},
                    {"status": "failed"},
                ]
            }
        ]
    }
    plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

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
async def test_get_spec_progress_no_plan(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test get_spec_progress when implementation_plan.json doesn't exist."""
    specs_dir = tmp_path / "specs"
    spec_folder = specs_dir / "002-pending"
    spec_folder.mkdir(parents=True)
    (spec_folder / "spec.md").write_text("# Pending", encoding="utf-8")

    def mock_get_specs_dir():
        return specs_dir

    import api.routes.shared as shared_module

    monkeypatch.setattr(shared_module, "get_specs_dir", mock_get_specs_dir)

    response = await async_client.get("/api/specs/002/progress", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["completed"] == 0
    assert data["in_progress"] == 0
    assert data["pending"] == 0
    assert data["failed"] == 0
    assert data["total"] == 0
    assert data["percentage"] == pytest.approx(0.0)
