"""
File System API routes

Provides endpoints for browsing and editing files in the project directory.
All operations are restricted to the project directory to prevent path traversal.
"""

import logging
import mimetypes
from pathlib import Path
from typing import Annotated

from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.routes.shared import get_project_dir, sanitize_log

logger = logging.getLogger(__name__)

# Create router for file endpoints
router = APIRouter(prefix="/api/files", tags=["files"])

# File size limit for content reads (1 MB)
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024

# Binary/non-text MIME type prefixes that should not be returned as text
_BINARY_MIME_PREFIXES = ("image/", "audio/", "video/", "application/octet-stream")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FileEntry(BaseModel):
    """Represents a single file or directory entry."""

    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Relative path from project root")
    type: str = Field(..., description="'file' or 'directory'")
    size: int | None = Field(None, description="File size in bytes (None for directories)")
    extension: str | None = Field(None, description="File extension (e.g. '.py'), None for directories")


class FileListResponse(BaseModel):
    """Response for listing files in a directory."""

    path: str = Field(..., description="Requested directory path (relative to project root)")
    entries: list[FileEntry] = Field(..., description="Files and directories in the requested path")


class FileContentResponse(BaseModel):
    """Response for getting file content."""

    path: str = Field(..., description="File path relative to project root")
    content: str = Field(..., description="File content as text")
    size: int = Field(..., description="File size in bytes")
    encoding: str = Field(default="utf-8", description="Text encoding used")


class FileWriteRequest(BaseModel):
    """Request to update file content."""

    path: str = Field(..., description="File path relative to project root")
    content: str = Field(..., description="New file content")
    encoding: str = Field(default="utf-8", description="Text encoding to use when writing")


class FileWriteResponse(BaseModel):
    """Response after updating file content."""

    path: str = Field(..., description="File path relative to project root")
    size: int = Field(..., description="New file size in bytes")
    message: str = Field(..., description="Human-readable status message")


class MkdirRequest(BaseModel):
    """Request to create a directory."""

    path: str = Field(..., description="Directory path relative to project root to create")


class MkdirResponse(BaseModel):
    """Response after creating a directory."""

    path: str = Field(..., description="Directory path relative to project root")
    message: str = Field(..., description="Human-readable status message")


class DeleteResponse(BaseModel):
    """Response after deleting a file or directory."""

    path: str = Field(..., description="Path relative to project root that was deleted")
    message: str = Field(..., description="Human-readable status message")


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------


def _resolve_safe_path(relative_path: str) -> Path:
    """
    Resolve a relative path safely within the project directory.

    Args:
        relative_path: Path relative to project root (may start with '/')

    Returns:
        Resolved absolute Path guaranteed to be inside the project directory

    Raises:
        HTTPException: 400 if the path is empty, 403 if path traversal is detected
    """
    project_dir = get_project_dir().resolve()

    # Strip leading slashes so Path joining works as expected
    clean = relative_path.lstrip("/\\").strip()
    if not clean:
        # Empty path means the project root itself
        return project_dir

    target = (project_dir / clean).resolve()

    # Guard against path traversal
    try:
        target.relative_to(project_dir)
    except ValueError:
        logger.warning(
            "Path traversal attempt blocked: %s -> %s",
            sanitize_log(relative_path),
            sanitize_log(str(target)),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: path is outside project directory",
        )

    return target


def _relative_str(absolute: Path) -> str:
    """Return the path relative to the project root as a forward-slash string."""
    project_dir = get_project_dir().resolve()
    try:
        return absolute.relative_to(project_dir).as_posix()
    except ValueError:
        return absolute.as_posix()


def _is_binary(file_path: Path) -> bool:
    """Heuristic check: return True if the file is likely binary."""
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        for prefix in _BINARY_MIME_PREFIXES:
            if mime.startswith(prefix):
                return True
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/list", response_model=FileListResponse, status_code=status.HTTP_200_OK)
async def list_files(
    path: str = Query(default="", description="Directory path relative to project root"),
    auth: Annotated[dict, Depends(require_auth)] = None,
):
    """
    List files and directories at the given path within the project.

    Args:
        path: Directory path relative to the project root (default: project root)

    Returns:
        FileListResponse with a list of file and directory entries

    Raises:
        HTTPException: 403 for path traversal, 404 if path not found, 400 if not a directory

    Example:
        ```bash
        curl -X GET "http://localhost:8000/api/files/list?path=apps/web-backend" \\
             -H "Authorization: Bearer <token>"
        # Returns: {"path": "apps/web-backend", "entries": [...]}
        ```
    """
    try:
        logger.info("File list request: path=%s", sanitize_log(path))

        target = _resolve_safe_path(path)

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path not found: {path}",
            )

        if not target.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a directory: {path}",
            )

        entries: list[FileEntry] = []
        for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            entry_type = "file" if child.is_file() else "directory"
            size = child.stat().st_size if child.is_file() else None
            extension = child.suffix if child.is_file() else None
            entries.append(
                FileEntry(
                    name=child.name,
                    path=_relative_str(child),
                    type=entry_type,
                    size=size,
                    extension=extension if extension else None,
                )
            )

        return FileListResponse(
            path=_relative_str(target),
            entries=entries,
        )

    except HTTPException:
        raise
    except OSError as e:
        logger.error("OS error listing files: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list directory due to a filesystem error",
        )
    except Exception as e:
        logger.error("Unexpected error listing files: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list directory due to an internal error",
        )


@router.get("/content", response_model=FileContentResponse, status_code=status.HTTP_200_OK)
async def get_file_content(
    path: str = Query(..., description="File path relative to project root"),
    auth: Annotated[dict, Depends(require_auth)] = None,
):
    """
    Get the text content of a file.

    Args:
        path: File path relative to the project root

    Returns:
        FileContentResponse with file content as text

    Raises:
        HTTPException: 403 for path traversal, 404 if not found, 400 if binary or too large

    Example:
        ```bash
        curl -X GET "http://localhost:8000/api/files/content?path=apps/web-backend/main.py" \\
             -H "Authorization: Bearer <token>"
        # Returns: {"path": "...", "content": "...", "size": 1234}
        ```
    """
    try:
        logger.info("File content request: path=%s", sanitize_log(path))

        target = _resolve_safe_path(path)

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {path}",
            )

        if not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a file: {path}",
            )

        file_size = target.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large ({file_size} bytes). Maximum allowed size is {MAX_FILE_SIZE_BYTES} bytes.",
            )

        if _is_binary(target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File appears to be binary and cannot be returned as text: {path}",
            )

        content = target.read_text(encoding="utf-8")

        return FileContentResponse(
            path=_relative_str(target),
            content=content,
            size=file_size,
            encoding="utf-8",
        )

    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is not valid UTF-8 text: {path}",
        )
    except OSError as e:
        logger.error("OS error reading file: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file due to a filesystem error",
        )
    except Exception as e:
        logger.error("Unexpected error reading file: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file due to an internal error",
        )


@router.put("/content", response_model=FileWriteResponse, status_code=status.HTTP_200_OK)
async def put_file_content(
    request: FileWriteRequest,
    auth: Annotated[dict, Depends(require_auth)] = None,
):
    """
    Write (create or overwrite) a file with the given text content.

    Args:
        request: File write request with path and content

    Returns:
        FileWriteResponse confirming write with new file size

    Raises:
        HTTPException: 403 for path traversal, 400 for invalid path, 500 for write errors

    Example:
        ```bash
        curl -X PUT http://localhost:8000/api/files/content \\
             -H "Authorization: Bearer <token>" \\
             -H "Content-Type: application/json" \\
             -d '{"path": "apps/web-backend/test.py", "content": "# hello"}'
        # Returns: {"path": "...", "size": 7, "message": "File written successfully"}
        ```
    """
    try:
        logger.info("File write request: path=%s", sanitize_log(request.path))

        target = _resolve_safe_path(request.path)

        if target.exists() and target.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is a directory, cannot write file: {request.path}",
            )

        # Ensure parent directory exists
        target.parent.mkdir(parents=True, exist_ok=True)

        encoded = request.content.encode(request.encoding)
        target.write_bytes(encoded)

        return FileWriteResponse(
            path=_relative_str(target),
            size=len(encoded),
            message="File written successfully",
        )

    except HTTPException:
        raise
    except (LookupError, UnicodeEncodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Encoding error: {e}",
        )
    except OSError as e:
        logger.error("OS error writing file: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write file due to a filesystem error",
        )
    except Exception as e:
        logger.error("Unexpected error writing file: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write file due to an internal error",
        )


@router.post("/mkdir", response_model=MkdirResponse, status_code=status.HTTP_201_CREATED)
async def make_directory(
    request: MkdirRequest,
    auth: Annotated[dict, Depends(require_auth)] = None,
):
    """
    Create a directory (and any missing parent directories).

    Args:
        request: Mkdir request with directory path

    Returns:
        MkdirResponse confirming directory creation

    Raises:
        HTTPException: 403 for path traversal, 400 if path exists as a file

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/files/mkdir \\
             -H "Authorization: Bearer <token>" \\
             -H "Content-Type: application/json" \\
             -d '{"path": "apps/web-backend/new_module"}'
        # Returns: {"path": "...", "message": "Directory created successfully"}
        ```
    """
    try:
        logger.info("Mkdir request: path=%s", sanitize_log(request.path))

        target = _resolve_safe_path(request.path)

        if target.exists() and target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path already exists as a file: {request.path}",
            )

        target.mkdir(parents=True, exist_ok=True)

        return MkdirResponse(
            path=_relative_str(target),
            message="Directory created successfully",
        )

    except HTTPException:
        raise
    except OSError as e:
        logger.error("OS error creating directory: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create directory due to a filesystem error",
        )
    except Exception as e:
        logger.error("Unexpected error creating directory: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create directory due to an internal error",
        )


@router.delete("", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_path(
    path: str = Query(..., description="File or directory path relative to project root"),
    auth: Annotated[dict, Depends(require_auth)] = None,
):
    """
    Delete a file or directory.

    Directories are deleted recursively. Deletion of the project root is not permitted.

    Args:
        path: File or directory path relative to project root

    Returns:
        DeleteResponse confirming deletion

    Raises:
        HTTPException: 403 for path traversal or project root, 404 if not found

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/api/files?path=apps/web-backend/temp.py" \\
             -H "Authorization: Bearer <token>"
        # Returns: {"path": "...", "message": "Deleted successfully"}
        ```
    """
    try:
        logger.info("Delete request: path=%s", sanitize_log(path))

        target = _resolve_safe_path(path)
        project_dir = get_project_dir().resolve()

        # Prevent deleting the project root
        if target == project_dir:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Deletion of the project root directory is not permitted",
            )

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path not found: {path}",
            )

        if target.is_file():
            target.unlink()
        else:
            import shutil
            shutil.rmtree(target)

        return DeleteResponse(
            path=_relative_str(target),
            message="Deleted successfully",
        )

    except HTTPException:
        raise
    except OSError as e:
        logger.error("OS error deleting path: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete path due to a filesystem error",
        )
    except Exception as e:
        logger.error("Unexpected error deleting path: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete path due to an internal error",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def files_health():
    """
    Health check for files API.

    Returns:
        Dictionary with status information
    """
    return {
        "status": "ok",
        "endpoint": "files",
    }
