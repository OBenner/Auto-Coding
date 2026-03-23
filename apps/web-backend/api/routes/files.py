"""
File System API routes

Provides endpoints for browsing and editing files in the project directory.
All operations are restricted to the project directory to prevent path traversal.
"""

import logging
import mimetypes
import shutil
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
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

# MIME types that match a binary prefix above but are actually text-readable
_TEXT_MIME_EXCEPTIONS = ("image/svg+xml",)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FileEntry(BaseModel):
    """Represents a single file or directory entry."""

    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Relative path from project root")
    type: str = Field(..., description="'file' or 'directory'")
    size: int | None = Field(
        None, description="File size in bytes (None for directories)"
    )
    extension: str | None = Field(
        None, description="File extension (e.g. '.py'), None for directories"
    )


class FileListResponse(BaseModel):
    """Response for listing files in a directory."""

    path: str = Field(
        ..., description="Requested directory path (relative to project root)"
    )
    entries: list[FileEntry] = Field(
        ..., description="Files and directories in the requested path"
    )


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
    encoding: str = Field(
        default="utf-8", description="Text encoding to use when writing"
    )


class FileWriteResponse(BaseModel):
    """Response after updating file content."""

    path: str = Field(..., description="File path relative to project root")
    size: int = Field(..., description="New file size in bytes")
    message: str = Field(..., description="Human-readable status message")


class MkdirRequest(BaseModel):
    """Request to create a directory."""

    path: str = Field(
        ..., description="Directory path relative to project root to create"
    )


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


def _sanitize_path_components(user_path: str) -> list[str]:
    """Extract and sanitise individual path components from user input.

    This is the taint-breaking boundary.  The function:

    1. Normalises separators so both ``/`` and ``\\`` are handled.
    2. Decomposes the string into individual components via ``PurePosixPath``.
    3. **Rejects** paths containing ``..`` with a 403 (path traversal attempt).
    4. Filters out ``.``, ``/``, and ``\\`` tokens.
    5. Validates each remaining component contains no embedded separators.

    Returns a **new** list of plain filename strings that are safe to pass to
    ``Path.joinpath``.  Returning validated component strings (rather than a
    ``Path`` derived from user input) ensures that CodeQL's taint tracker no
    longer considers the result as flowing from an untrusted source.

    Raises:
        HTTPException 403: If the path contains ``..`` traversal components.
    """
    clean = user_path.strip().lstrip("/\\")
    if not clean:
        return []

    # Replace backslashes so Windows-style paths are decomposed properly
    normalised = clean.replace("\\", "/")
    parts = PurePosixPath(normalised).parts

    # Reject any path that contains ".." -- this is always a traversal attempt
    if ".." in parts:
        logger.warning(
            "Path traversal attempt blocked: %s",
            sanitize_log(user_path),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: path is outside project directory",
        )

    safe: list[str] = []
    for part in parts:
        # Skip current-dir markers and root markers
        if part in (".", "/", "\\"):
            continue
        # Extra guard: reject components that somehow contain separators
        if "/" in part or "\\" in part:
            continue
        safe.append(part)

    return safe


def _build_safe_path(project_root: Path, components: list[str]) -> Path:
    """Construct and validate an absolute path from trusted components.

    ``components`` MUST come from ``_sanitize_path_components`` (i.e. they are
    individually validated plain filename strings, **not** raw user input).

    The function joins the components onto the *resolved* project root, then
    resolves the result and verifies containment.  Because the input list
    contains only audited filename tokens, CodeQL sees the resulting ``Path``
    as constructed from trusted data.

    The *non-resolved* joined path is returned so that symlinks within the
    project directory are preserved for callers.  The resolved path is used
    only for the containment check.

    Returns:
        Non-resolved absolute ``Path`` guaranteed to reside inside
        ``project_root`` (verified via resolved containment check).

    Raises:
        HTTPException 403: If the resolved path escapes the project directory.
    """
    if not components:
        return project_root

    safe_path = project_root.joinpath(*components)
    resolved = safe_path.resolve()

    # Primary containment check -- blocks any remaining traversal attempts
    if not resolved.is_relative_to(project_root):
        logger.warning(
            "Path traversal attempt blocked: %s",
            sanitize_log(str(safe_path)),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: path is outside project directory",
        )

    # Verify the parent is inside the project (catches edge cases where the
    # leaf doesn't exist yet but the parent is a symlink outside the root)
    if resolved != project_root and not resolved.parent.resolve().is_relative_to(
        project_root
    ):
        logger.warning(
            "Path traversal via parent blocked: %s",
            sanitize_log(str(safe_path)),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: path is outside project directory",
        )

    # Return the non-resolved path so symlinks inside the project are preserved
    return safe_path


def _safe_relative_path(absolute: Path) -> str:
    """Return the path relative to the project root as a forward-slash string.

    Uses only the validated *absolute* path -- never raw user input.
    """
    project_root = get_project_dir().resolve()
    if absolute.is_relative_to(project_root):
        return absolute.relative_to(project_root).as_posix()
    return absolute.as_posix()


def _is_binary(file_path: Path) -> bool:
    """Heuristic check: return True if the file is likely binary."""
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        if mime in _TEXT_MIME_EXCEPTIONS:
            return False
        for prefix in _BINARY_MIME_PREFIXES:
            if mime.startswith(prefix):
                return True
    return False


@contextmanager
def _handle_file_errors(operation: str):
    """Context manager that catches common filesystem exceptions and converts
    them into appropriate ``HTTPException`` responses.

    ``HTTPException`` instances raised inside the block propagate unchanged.

    Args:
        operation: Human-readable operation name used in generic error messages
                   (e.g. ``"list directory"``, ``"read file"``).
    """
    try:
        yield
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not valid UTF-8 text",
        )
    except (LookupError, UnicodeEncodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Encoding error: {exc}",
        )
    except OSError as exc:
        logger.error("OS error during %s: %s", operation, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {operation} due to a filesystem error",
        )
    except Exception as exc:
        logger.error("Unexpected error during %s: %s", operation, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {operation} due to an internal error",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/list", response_model=FileListResponse, status_code=status.HTTP_200_OK)
async def list_files(
    path: str = Query(
        default="", description="Directory path relative to project root"
    ),
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
    with _handle_file_errors("list directory"):
        logger.info("File list request: path=%s", sanitize_log(path))

        project_root = get_project_dir().resolve()
        components = _sanitize_path_components(path)
        target = _build_safe_path(project_root, components)
        safe_path = _safe_relative_path(target)

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path not found: {safe_path}",
            )

        if not target.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a directory: {safe_path}",
            )

        entries: list[FileEntry] = []
        for child in sorted(
            target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())
        ):
            entry_type = "file" if child.is_file() else "directory"
            size = child.stat().st_size if child.is_file() else None
            extension = child.suffix if child.is_file() else None
            entries.append(
                FileEntry(
                    name=child.name,
                    path=_safe_relative_path(child),
                    type=entry_type,
                    size=size,
                    extension=extension if extension else None,
                )
            )

        return FileListResponse(path=safe_path, entries=entries)


@router.get(
    "/content", response_model=FileContentResponse, status_code=status.HTTP_200_OK
)
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
    with _handle_file_errors("read file"):
        logger.info("File content request: path=%s", sanitize_log(path))

        project_root = get_project_dir().resolve()
        components = _sanitize_path_components(path)
        target = _build_safe_path(project_root, components)
        safe_path = _safe_relative_path(target)

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {safe_path}",
            )

        if not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a file: {safe_path}",
            )

        file_size = target.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File too large ({file_size} bytes). "
                    f"Maximum allowed size is {MAX_FILE_SIZE_BYTES} bytes."
                ),
            )

        if _is_binary(target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File appears to be binary and cannot be returned as text: {safe_path}",
            )

        content = target.read_text(encoding="utf-8")

        return FileContentResponse(
            path=safe_path,
            content=content,
            size=file_size,
            encoding="utf-8",
        )


@router.put(
    "/content", response_model=FileWriteResponse, status_code=status.HTTP_200_OK
)
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
    with _handle_file_errors("write file"):
        logger.info("File write request: path=%s", sanitize_log(request.path))

        project_root = get_project_dir().resolve()
        components = _sanitize_path_components(request.path)
        target = _build_safe_path(project_root, components)
        safe_path = _safe_relative_path(target)

        if target.exists() and target.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is a directory, cannot write file: {safe_path}",
            )

        target.parent.mkdir(parents=True, exist_ok=True)

        encoded = request.content.encode(request.encoding)
        target.write_bytes(encoded)

        return FileWriteResponse(
            path=safe_path,
            size=len(encoded),
            message="File written successfully",
        )


@router.post(
    "/mkdir", response_model=MkdirResponse, status_code=status.HTTP_201_CREATED
)
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
    with _handle_file_errors("create directory"):
        logger.info("Mkdir request: path=%s", sanitize_log(request.path))

        project_root = get_project_dir().resolve()
        components = _sanitize_path_components(request.path)
        target = _build_safe_path(project_root, components)
        safe_path = _safe_relative_path(target)

        if target.exists() and target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path already exists as a file: {safe_path}",
            )

        target.mkdir(parents=True, exist_ok=True)

        return MkdirResponse(
            path=safe_path,
            message="Directory created successfully",
        )


@router.delete("", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_path(
    path: str = Query(
        ..., description="File or directory path relative to project root"
    ),
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
    with _handle_file_errors("delete path"):
        logger.info("Delete request: path=%s", sanitize_log(path))

        project_root = get_project_dir().resolve()
        components = _sanitize_path_components(path)
        target = _build_safe_path(project_root, components)
        safe_path = _safe_relative_path(target)

        # Prevent deleting the project root
        if target == project_root:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Deletion of the project root directory is not permitted",
            )

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path not found: {safe_path}",
            )

        if target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)

        return DeleteResponse(
            path=safe_path,
            message="Deleted successfully",
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
