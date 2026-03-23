"""
Unit tests for Files API endpoints

Tests all /api/files endpoints including authentication, validation,
error handling, path traversal prevention, and response formats.
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Health endpoint (no auth required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_files_health(async_client: AsyncClient):
    """Test files health endpoint (no auth required)"""
    response = await async_client.get("/api/files/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["endpoint"] == "files"


# ---------------------------------------------------------------------------
# List endpoint – authentication tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_files_without_auth(async_client: AsyncClient):
    """Test that list_files requires authentication"""
    response = await async_client.get("/api/files/list")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_list_files_with_expired_token(
    async_client: AsyncClient, expired_token: str
):
    """Test that list_files rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get("/api/files/list", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_files_with_invalid_token(async_client: AsyncClient):
    """Test that list_files rejects invalid tokens"""
    headers = {"Authorization": "Bearer invalid-token-12345"}
    response = await async_client.get("/api/files/list", headers=headers)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List endpoint – success cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_files_root(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test listing files at project root"""
    # Create some files and directories in tmp_path
    (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "subdir").mkdir()

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get("/api/files/list", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "path" in data
    assert "entries" in data
    names = [e["name"] for e in data["entries"]]
    assert "readme.txt" in names
    assert "subdir" in names


@pytest.mark.asyncio
async def test_list_files_subdirectory(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test listing files in a subdirectory"""
    subdir = tmp_path / "mydir"
    subdir.mkdir()
    (subdir / "file_a.py").write_text("# code", encoding="utf-8")
    (subdir / "file_b.txt").write_text("text", encoding="utf-8")

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/list?path=mydir", headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["path"] == "mydir"
    names = [e["name"] for e in data["entries"]]
    assert "file_a.py" in names
    assert "file_b.txt" in names


@pytest.mark.asyncio
async def test_list_files_entry_fields(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test that file entries contain expected fields"""
    (tmp_path / "example.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / "somedir").mkdir()

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get("/api/files/list", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    file_entry = next(e for e in data["entries"] if e["name"] == "example.py")
    assert file_entry["type"] == "file"
    assert file_entry["size"] is not None
    assert file_entry["extension"] == ".py"
    assert "path" in file_entry

    dir_entry = next(e for e in data["entries"] if e["name"] == "somedir")
    assert dir_entry["type"] == "directory"
    assert dir_entry["size"] is None
    assert dir_entry["extension"] is None


# ---------------------------------------------------------------------------
# List endpoint – error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_files_path_not_found(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test list_files when path doesn't exist"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/list?path=nonexistent_dir", headers=auth_headers
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_list_files_path_is_file(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test list_files when path points to a file (not a directory)"""
    (tmp_path / "afile.txt").write_text("data", encoding="utf-8")

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/list?path=afile.txt", headers=auth_headers
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_list_files_path_traversal(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test that path traversal attempts are blocked for list"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/list?path=../../etc", headers=auth_headers
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "access denied" in data["detail"].lower()


# ---------------------------------------------------------------------------
# Content (read) endpoint – authentication tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_file_content_without_auth(async_client: AsyncClient):
    """Test that get_file_content requires authentication"""
    response = await async_client.get("/api/files/content?path=somefile.txt")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_file_content_with_expired_token(
    async_client: AsyncClient, expired_token: str
):
    """Test that get_file_content rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get(
        "/api/files/content?path=somefile.txt", headers=headers
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_file_content_with_invalid_token(async_client: AsyncClient):
    """Test that get_file_content rejects invalid tokens"""
    headers = {"Authorization": "Bearer bad-token"}
    response = await async_client.get(
        "/api/files/content?path=somefile.txt", headers=headers
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Content (read) endpoint – success cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_file_content_success(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test successfully reading a text file"""
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello, world!", encoding="utf-8")

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/content?path=hello.txt", headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["path"] == "hello.txt"
    assert data["content"] == "Hello, world!"
    assert data["size"] == len("Hello, world!".encode("utf-8"))
    assert data["encoding"] == "utf-8"


@pytest.mark.asyncio
async def test_get_file_content_python_file(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test reading a Python source file"""
    code = "def hello():\n    return 'world'\n"
    (tmp_path / "code.py").write_text(code, encoding="utf-8")

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/content?path=code.py", headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["content"] == code


# ---------------------------------------------------------------------------
# Content (read) endpoint – error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_file_content_not_found(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test get_file_content when file doesn't exist"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/content?path=missing.txt", headers=auth_headers
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "missing.txt" in data["detail"]


@pytest.mark.asyncio
async def test_get_file_content_path_is_directory(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test get_file_content when path points to a directory"""
    (tmp_path / "mydir").mkdir()

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/content?path=mydir", headers=auth_headers
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_get_file_content_path_traversal(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test that path traversal is blocked for content read"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.get(
        "/api/files/content?path=../../etc/passwd", headers=auth_headers
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "access denied" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_file_content_missing_path_param(
    async_client: AsyncClient, auth_headers: dict
):
    """Test get_file_content with missing required path param"""
    response = await async_client.get("/api/files/content", headers=auth_headers)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Write (PUT) endpoint – authentication tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_file_content_without_auth(async_client: AsyncClient):
    """Test that put_file_content requires authentication"""
    response = await async_client.put(
        "/api/files/content", json={"path": "test.txt", "content": "data"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_put_file_content_with_expired_token(
    async_client: AsyncClient, expired_token: str
):
    """Test that put_file_content rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.put(
        "/api/files/content",
        json={"path": "test.txt", "content": "data"},
        headers=headers,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_put_file_content_with_invalid_token(async_client: AsyncClient):
    """Test that put_file_content rejects invalid tokens"""
    headers = {"Authorization": "Bearer bad-token"}
    response = await async_client.put(
        "/api/files/content",
        json={"path": "test.txt", "content": "data"},
        headers=headers,
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Write (PUT) endpoint – success cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_file_content_create_new(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test creating a new file via PUT"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    content = "# new file\nprint('hello')\n"
    response = await async_client.put(
        "/api/files/content",
        json={"path": "newfile.py", "content": content},
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["path"] == "newfile.py"
    assert data["size"] == len(content.encode("utf-8"))
    assert "written" in data["message"].lower()

    # Verify the file was actually written
    assert (tmp_path / "newfile.py").read_text(encoding="utf-8") == content


@pytest.mark.asyncio
async def test_put_file_content_overwrite_existing(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test overwriting an existing file via PUT"""
    target = tmp_path / "existing.txt"
    target.write_text("old content", encoding="utf-8")

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    new_content = "new content"
    response = await async_client.put(
        "/api/files/content",
        json={"path": "existing.txt", "content": new_content},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert target.read_text(encoding="utf-8") == new_content


@pytest.mark.asyncio
async def test_put_file_content_creates_parent_dirs(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test that PUT creates missing parent directories"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.put(
        "/api/files/content",
        json={"path": "deep/nested/file.txt", "content": "nested content"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert (tmp_path / "deep" / "nested" / "file.txt").exists()


# ---------------------------------------------------------------------------
# Write (PUT) endpoint – error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_file_content_path_traversal(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test that path traversal is blocked for file write"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.put(
        "/api/files/content",
        json={"path": "../../evil.txt", "content": "pwned"},
        headers=auth_headers,
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "access denied" in data["detail"].lower()


@pytest.mark.asyncio
async def test_put_file_content_path_is_directory(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test PUT when target path already exists as a directory"""
    (tmp_path / "existingdir").mkdir()

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.put(
        "/api/files/content",
        json={"path": "existingdir", "content": "data"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_put_file_content_missing_fields(
    async_client: AsyncClient, auth_headers: dict
):
    """Test PUT with missing required request body fields"""
    # Missing content field
    response = await async_client.put(
        "/api/files/content",
        json={"path": "test.txt"},
        headers=auth_headers,
    )
    assert response.status_code == 422

    # Missing path field
    response = await async_client.put(
        "/api/files/content",
        json={"content": "data"},
        headers=auth_headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Delete endpoint – authentication tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_path_without_auth(async_client: AsyncClient):
    """Test that delete_path requires authentication"""
    response = await async_client.delete("/api/files?path=somefile.txt")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_delete_path_with_expired_token(
    async_client: AsyncClient, expired_token: str
):
    """Test that delete_path rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.delete("/api/files?path=somefile.txt", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_path_with_invalid_token(async_client: AsyncClient):
    """Test that delete_path rejects invalid tokens"""
    headers = {"Authorization": "Bearer bad-token"}
    response = await async_client.delete("/api/files?path=somefile.txt", headers=headers)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Delete endpoint – success cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_file_success(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test successfully deleting a file"""
    target = tmp_path / "todelete.txt"
    target.write_text("bye", encoding="utf-8")

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.delete(
        "/api/files?path=todelete.txt", headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["path"] == "todelete.txt"
    assert "deleted" in data["message"].lower()

    # Verify file is actually gone
    assert not target.exists()


@pytest.mark.asyncio
async def test_delete_directory_success(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test successfully deleting a directory (recursive)"""
    subdir = tmp_path / "rmdir"
    subdir.mkdir()
    (subdir / "child.txt").write_text("child", encoding="utf-8")

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.delete("/api/files?path=rmdir", headers=auth_headers)
    assert response.status_code == 200
    assert not subdir.exists()


# ---------------------------------------------------------------------------
# Delete endpoint – error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_path_not_found(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test delete when path doesn't exist"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.delete(
        "/api/files?path=ghost.txt", headers=auth_headers
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "ghost.txt" in data["detail"]


@pytest.mark.asyncio
async def test_delete_path_traversal(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test that path traversal is blocked for delete"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.delete(
        "/api/files?path=../../important", headers=auth_headers
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "access denied" in data["detail"].lower()


@pytest.mark.asyncio
async def test_delete_project_root_forbidden(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test that deleting the project root is not permitted"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    # Empty path resolves to project root
    response = await async_client.delete("/api/files?path=", headers=auth_headers)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_delete_missing_path_param(
    async_client: AsyncClient, auth_headers: dict
):
    """Test delete with missing required path query parameter"""
    response = await async_client.delete("/api/files", headers=auth_headers)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Mkdir endpoint – authentication tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mkdir_without_auth(async_client: AsyncClient):
    """Test that mkdir requires authentication"""
    response = await async_client.post(
        "/api/files/mkdir", json={"path": "newdir"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_mkdir_with_expired_token(
    async_client: AsyncClient, expired_token: str
):
    """Test that mkdir rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.post(
        "/api/files/mkdir", json={"path": "newdir"}, headers=headers
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Mkdir endpoint – success cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mkdir_success(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test successfully creating a directory"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.post(
        "/api/files/mkdir", json={"path": "brandnew"}, headers=auth_headers
    )
    assert response.status_code == 201

    data = response.json()
    assert data["path"] == "brandnew"
    assert "created" in data["message"].lower()
    assert (tmp_path / "brandnew").is_dir()


@pytest.mark.asyncio
async def test_mkdir_creates_nested_dirs(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test mkdir creates nested directories"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.post(
        "/api/files/mkdir",
        json={"path": "level1/level2/level3"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert (tmp_path / "level1" / "level2" / "level3").is_dir()


@pytest.mark.asyncio
async def test_mkdir_idempotent(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test mkdir is idempotent (existing directory returns 201)"""
    (tmp_path / "existing").mkdir()

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.post(
        "/api/files/mkdir", json={"path": "existing"}, headers=auth_headers
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# Mkdir endpoint – error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mkdir_path_is_file(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test mkdir when path already exists as a file"""
    (tmp_path / "afile.txt").write_text("data", encoding="utf-8")

    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.post(
        "/api/files/mkdir", json={"path": "afile.txt"}, headers=auth_headers
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_mkdir_path_traversal(
    async_client: AsyncClient, auth_headers: dict, tmp_path, monkeypatch
):
    """Test that path traversal is blocked for mkdir"""
    import api.routes.files as files_module

    monkeypatch.setattr(files_module, "get_project_dir", lambda: tmp_path)

    response = await async_client.post(
        "/api/files/mkdir",
        json={"path": "../../evildir"},
        headers=auth_headers,
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "access denied" in data["detail"].lower()
