"""
File System Service

Service layer for sandboxed file system operations for the web-based IDE.
Provides methods to list, read, write, create, delete, and rename files/directories,
all constrained within a configured sandbox root directory.

Security:
    All path operations are validated against the sandbox root to prevent
    directory traversal attacks. Symlinks are resolved before validation.
"""

import logging
import mimetypes
import shutil
from pathlib import Path
from typing import Any

from core import sanitize_log as _sanitize_log

logger = logging.getLogger(__name__)


class FileSystemError(Exception):
    """Base exception for file system service errors."""

    pass


class PathTraversalError(FileSystemError):
    """Raised when a path would escape the sandbox root."""

    pass


class FileNotFoundError(FileSystemError):
    """Raised when a requested file or directory does not exist."""

    pass


class FileAlreadyExistsError(FileSystemError):
    """Raised when attempting to create a file that already exists."""

    pass


class PermissionError(FileSystemError):
    """Raised when an operation is not permitted."""

    pass


class FileSystemService:
    """
    Service for sandboxed file system operations.

    All operations are restricted to the configured sandbox root directory.
    Paths outside the sandbox are rejected with a PathTraversalError.
    """

    # File size limit for read operations (10 MB)
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

    # Binary file detection chunk size
    BINARY_CHECK_BYTES = 8192

    def __init__(self, sandbox_root: str):
        """
        Initialize the file system service.

        Args:
            sandbox_root: Absolute path to the sandbox root directory.
                All file operations are restricted to this directory.

        Raises:
            ValueError: If sandbox_root does not exist or is not a directory.
        """
        root_path = Path(sandbox_root).resolve()

        if not root_path.exists():
            raise ValueError(
                f"Sandbox root does not exist: {_sanitize_log(sandbox_root)}"
            )

        if not root_path.is_dir():
            raise ValueError(
                f"Sandbox root is not a directory: {_sanitize_log(sandbox_root)}"
            )

        self.sandbox_root = root_path
        logger.info(
            f"FileSystemService initialized with sandbox root: {_sanitize_log(str(root_path))}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, relative_path: str) -> Path:
        """
        Resolve a relative path to an absolute path within the sandbox.

        Resolves symlinks and validates that the resulting path is contained
        within the sandbox root.

        Args:
            relative_path: Path relative to the sandbox root (or absolute).

        Returns:
            Resolved absolute Path within the sandbox.

        Raises:
            PathTraversalError: If the resolved path is outside the sandbox root.
        """
        # Normalise separators and strip leading slashes so the path
        # is always treated as relative to the sandbox root.
        clean = relative_path.replace("\\", "/").lstrip("/")

        candidate = (self.sandbox_root / clean).resolve()

        # Check containment – resolve() expands symlinks so a symlink
        # pointing outside the sandbox is caught here.
        try:
            candidate.relative_to(self.sandbox_root)
        except ValueError:
            raise PathTraversalError(
                f"Path '{_sanitize_log(relative_path)}' escapes the sandbox root"
            )

        return candidate

    def _is_binary(self, path: Path) -> bool:
        """
        Detect whether a file is binary by inspecting its leading bytes.

        Args:
            path: Absolute path to the file.

        Returns:
            True if the file appears to be binary, False otherwise.
        """
        try:
            with open(path, "rb") as fh:
                chunk = fh.read(self.BINARY_CHECK_BYTES)
            return b"\x00" in chunk
        except OSError:
            return False

    def _entry_info(self, path: Path) -> dict[str, Any]:
        """
        Build a metadata dictionary for a file or directory entry.

        Args:
            path: Absolute path to the entry.

        Returns:
            Dictionary with entry metadata.
        """
        stat = path.stat()
        is_dir = path.is_dir()
        rel = path.relative_to(self.sandbox_root)

        entry: dict[str, Any] = {
            "name": path.name,
            "path": rel.as_posix(),
            "is_directory": is_dir,
            "size": stat.st_size if not is_dir else None,
            "modified": stat.st_mtime,
        }

        if not is_dir:
            mime_type, _ = mimetypes.guess_type(path.name)
            entry["mime_type"] = mime_type or "application/octet-stream"
            entry["is_binary"] = self._is_binary(path)

        return entry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_directory(self, path: str = "") -> dict[str, Any]:
        """
        List the contents of a directory within the sandbox.

        Args:
            path: Path relative to the sandbox root. Defaults to root.

        Returns:
            Dictionary with:
                - ``path``: Normalised relative path of the listed directory.
                - ``entries``: Sorted list of entry metadata dicts
                  (directories first, then files, both alphabetically).

        Raises:
            FileNotFoundError: If the path does not exist.
            FileSystemError: If the path is not a directory.
            PathTraversalError: If the path escapes the sandbox.
        """
        abs_path = self._resolve_path(path)

        if not abs_path.exists():
            raise FileNotFoundError(f"Directory not found: {_sanitize_log(path)}")

        if not abs_path.is_dir():
            raise FileSystemError(f"Path is not a directory: {_sanitize_log(path)}")

        try:
            raw_entries = list(abs_path.iterdir())
        except OSError as exc:
            raise FileSystemError(f"Cannot list directory: {exc}") from exc

        # Directories first, then files, both sorted case-insensitively
        dirs = sorted(
            [e for e in raw_entries if e.is_dir()],
            key=lambda p: p.name.lower(),
        )
        files = sorted(
            [e for e in raw_entries if e.is_file()],
            key=lambda p: p.name.lower(),
        )

        entries = [self._entry_info(e) for e in dirs + files]
        rel = abs_path.relative_to(self.sandbox_root)

        logger.debug(
            "Listed directory '%s': %d entries",
            _sanitize_log(path),
            len(entries),
        )

        return {
            "path": rel.as_posix(),
            "entries": entries,
        }

    def read_file(self, path: str) -> dict[str, Any]:
        """
        Read the contents of a file within the sandbox.

        Args:
            path: Path to the file relative to the sandbox root.

        Returns:
            Dictionary with:
                - ``path``: Normalised relative path.
                - ``content``: File content as a string (text files only).
                - ``is_binary``: True if the file is binary.
                - ``size``: File size in bytes.
                - ``mime_type``: Detected MIME type.

        Raises:
            FileNotFoundError: If the file does not exist.
            FileSystemError: If the path is a directory or file is too large.
            PathTraversalError: If the path escapes the sandbox.
        """
        abs_path = self._resolve_path(path)

        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {_sanitize_log(path)}")

        if abs_path.is_dir():
            raise FileSystemError(
                f"Path is a directory, not a file: {_sanitize_log(path)}"
            )

        size = abs_path.stat().st_size
        if size > self.MAX_FILE_SIZE_BYTES:
            raise FileSystemError(
                f"File exceeds maximum readable size "
                f"({size} > {self.MAX_FILE_SIZE_BYTES} bytes): {_sanitize_log(path)}"
            )

        is_binary = self._is_binary(abs_path)
        mime_type, _ = mimetypes.guess_type(abs_path.name)
        rel = abs_path.relative_to(self.sandbox_root)

        if is_binary:
            logger.debug(
                "Skipping content read for binary file '%s'", _sanitize_log(path)
            )
            return {
                "path": rel.as_posix(),
                "content": None,
                "is_binary": True,
                "size": size,
                "mime_type": mime_type or "application/octet-stream",
            }

        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise FileSystemError(f"Cannot read file: {exc}") from exc

        logger.debug("Read file '%s' (%d bytes)", _sanitize_log(path), size)

        return {
            "path": rel.as_posix(),
            "content": content,
            "is_binary": False,
            "size": size,
            "mime_type": mime_type or "text/plain",
        }

    def write_file(
        self, path: str, content: str, create_parents: bool = True
    ) -> dict[str, Any]:
        """
        Write content to a file within the sandbox.

        Creates the file if it does not exist; overwrites it if it does.

        Args:
            path: Path to the file relative to the sandbox root.
            content: Text content to write.
            create_parents: If True, create any missing parent directories.

        Returns:
            Dictionary with ``path`` and ``size`` of the written file.

        Raises:
            FileSystemError: If a directory exists at the given path, or on I/O error.
            PathTraversalError: If the path escapes the sandbox.
        """
        abs_path = self._resolve_path(path)

        if abs_path.is_dir():
            raise FileSystemError(
                f"Cannot write file: path is an existing directory: {_sanitize_log(path)}"
            )

        if create_parents:
            abs_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            abs_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise FileSystemError(f"Cannot write file: {exc}") from exc

        size = abs_path.stat().st_size
        rel = abs_path.relative_to(self.sandbox_root)

        logger.info("Wrote file '%s' (%d bytes)", _sanitize_log(path), size)

        return {
            "path": rel.as_posix(),
            "size": size,
        }

    def create_file(self, path: str, content: str = "") -> dict[str, Any]:
        """
        Create a new file within the sandbox (fails if it already exists).

        Args:
            path: Path to the new file relative to the sandbox root.
            content: Optional initial content (default: empty string).

        Returns:
            Dictionary with ``path`` and ``size`` of the created file.

        Raises:
            FileAlreadyExistsError: If a file or directory already exists at path.
            PathTraversalError: If the path escapes the sandbox.
        """
        abs_path = self._resolve_path(path)

        if abs_path.exists():
            raise FileAlreadyExistsError(f"File already exists: {_sanitize_log(path)}")

        abs_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            abs_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise FileSystemError(f"Cannot create file: {exc}") from exc

        size = abs_path.stat().st_size
        rel = abs_path.relative_to(self.sandbox_root)

        logger.info("Created file '%s'", _sanitize_log(path))

        return {
            "path": rel.as_posix(),
            "size": size,
        }

    def create_directory(self, path: str) -> dict[str, Any]:
        """
        Create a new directory (and any required parents) within the sandbox.

        Args:
            path: Path to the directory relative to the sandbox root.

        Returns:
            Dictionary with ``path`` of the created directory.

        Raises:
            FileAlreadyExistsError: If a file (not a directory) already exists at path.
            PathTraversalError: If the path escapes the sandbox.
        """
        abs_path = self._resolve_path(path)

        if abs_path.is_file():
            raise FileAlreadyExistsError(
                f"A file already exists at path: {_sanitize_log(path)}"
            )

        try:
            abs_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FileSystemError(f"Cannot create directory: {exc}") from exc

        rel = abs_path.relative_to(self.sandbox_root)

        logger.info("Created directory '%s'", _sanitize_log(path))

        return {"path": rel.as_posix()}

    def delete(self, path: str, recursive: bool = False) -> dict[str, Any]:
        """
        Delete a file or directory within the sandbox.

        Args:
            path: Path relative to the sandbox root.
            recursive: If True, delete directories recursively.
                If False, non-empty directories raise FileSystemError.

        Returns:
            Dictionary with ``path`` of the deleted entry and ``deleted`` True.

        Raises:
            FileNotFoundError: If the path does not exist.
            FileSystemError: If the path is a non-empty directory and recursive=False.
            PathTraversalError: If the path escapes the sandbox.
        """
        abs_path = self._resolve_path(path)

        if not abs_path.exists():
            raise FileNotFoundError(f"Path not found: {_sanitize_log(path)}")

        # Prevent deletion of the sandbox root itself
        if abs_path == self.sandbox_root:
            raise PermissionError("Cannot delete the sandbox root directory")

        rel = abs_path.relative_to(self.sandbox_root)

        try:
            if abs_path.is_dir():
                if recursive:
                    shutil.rmtree(abs_path)
                else:
                    abs_path.rmdir()  # Raises OSError if non-empty
            else:
                abs_path.unlink()
        except OSError as exc:
            raise FileSystemError(f"Cannot delete path: {exc}") from exc

        logger.info("Deleted '%s' (recursive=%s)", _sanitize_log(path), recursive)

        return {"path": rel.as_posix(), "deleted": True}

    def rename(self, source: str, destination: str) -> dict[str, Any]:
        """
        Rename or move a file or directory within the sandbox.

        Args:
            source: Current path relative to the sandbox root.
            destination: New path relative to the sandbox root.

        Returns:
            Dictionary with ``source`` and ``destination`` relative paths.

        Raises:
            FileNotFoundError: If the source path does not exist.
            FileAlreadyExistsError: If the destination already exists.
            PathTraversalError: If either path escapes the sandbox.
        """
        abs_src = self._resolve_path(source)
        abs_dst = self._resolve_path(destination)

        if not abs_src.exists():
            raise FileNotFoundError(f"Source not found: {_sanitize_log(source)}")

        if abs_dst.exists():
            raise FileAlreadyExistsError(
                f"Destination already exists: {_sanitize_log(destination)}"
            )

        # Ensure parent of destination exists
        abs_dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            abs_src.rename(abs_dst)
        except OSError as exc:
            raise FileSystemError(f"Cannot rename: {exc}") from exc

        rel_src = abs_src.relative_to(self.sandbox_root)
        rel_dst = abs_dst.relative_to(self.sandbox_root)

        logger.info(
            "Renamed '%s' -> '%s'",
            _sanitize_log(source),
            _sanitize_log(destination),
        )

        return {
            "source": rel_src.as_posix(),
            "destination": rel_dst.as_posix(),
        }

    def get_file_info(self, path: str) -> dict[str, Any]:
        """
        Get metadata for a file or directory without reading its content.

        Args:
            path: Path relative to the sandbox root.

        Returns:
            Entry metadata dictionary (see :meth:`_entry_info`).

        Raises:
            FileNotFoundError: If the path does not exist.
            PathTraversalError: If the path escapes the sandbox.
        """
        abs_path = self._resolve_path(path)

        if not abs_path.exists():
            raise FileNotFoundError(f"Path not found: {_sanitize_log(path)}")

        return self._entry_info(abs_path)
