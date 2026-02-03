"""
File Watcher Service

Service layer for monitoring file system changes in real-time.
Uses watchdog library to detect file modifications, creations, and deletions.
Supports callback-based notification for pair programming mode.
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from threading import Thread

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    # Create dummy base classes for type hints when watchdog not available
    class FileSystemEventHandler:
        pass
    class FileSystemEvent:
        pass

logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """
    Handler for file system events.

    Filters events and invokes registered callbacks for relevant file changes.
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        file_patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize file change handler.

        Args:
            callback: Function to call when file changes (receives event_type, file_path)
            file_patterns: List of file patterns to watch (e.g., ["*.py", "*.ts"])
            ignore_patterns: List of patterns to ignore (e.g., ["*.pyc", "node_modules/*"])
        """
        super().__init__()
        self.callback = callback
        self.file_patterns = file_patterns or []
        self.ignore_patterns = ignore_patterns or [
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "__pycache__/*",
            ".git/*",
            ".venv/*",
            "node_modules/*",
            "*.log",
            ".auto-claude/*",
        ]

    def _should_process(self, path: str) -> bool:
        """
        Check if file should be processed based on patterns.

        Args:
            path: File path to check

        Returns:
            True if file should be processed
        """
        from fnmatch import fnmatch

        # Check ignore patterns first
        for pattern in self.ignore_patterns:
            if fnmatch(path, pattern) or pattern in path:
                return False

        # If no file patterns specified, accept all (except ignored)
        if not self.file_patterns:
            return True

        # Check if matches any allowed pattern
        for pattern in self.file_patterns:
            if fnmatch(path, pattern):
                return True

        return False

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if not event.is_directory and self._should_process(event.src_path):
            try:
                self.callback("modified", event.src_path)
            except Exception as e:
                logger.error(f"Error in file change callback: {e}", exc_info=True)

    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if not event.is_directory and self._should_process(event.src_path):
            try:
                self.callback("created", event.src_path)
            except Exception as e:
                logger.error(f"Error in file change callback: {e}", exc_info=True)

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        if not event.is_directory and self._should_process(event.src_path):
            try:
                self.callback("deleted", event.src_path)
            except Exception as e:
                logger.error(f"Error in file change callback: {e}", exc_info=True)


class FileWatcher:
    """
    File watcher service for real-time file system monitoring.

    Uses watchdog library to monitor directories and trigger callbacks
    when files are modified, created, or deleted.
    """

    def __init__(
        self,
        watch_path: Path,
        callback: Callable[[str, str], None],
        file_patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        recursive: bool = True,
    ):
        """
        Initialize file watcher.

        Args:
            watch_path: Directory path to watch
            callback: Function to call when file changes (receives event_type, file_path)
            file_patterns: List of file patterns to watch (e.g., ["*.py", "*.ts"])
            ignore_patterns: List of patterns to ignore
            recursive: Whether to watch subdirectories recursively

        Raises:
            ImportError: If watchdog library is not installed
            ValueError: If watch_path does not exist
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "watchdog library is required for file watching. "
                "Install it with: pip install watchdog"
            )

        if not watch_path.exists():
            raise ValueError(f"Watch path does not exist: {watch_path}")

        if not watch_path.is_dir():
            raise ValueError(f"Watch path must be a directory: {watch_path}")

        self.watch_path = watch_path
        self.callback = callback
        self.file_patterns = file_patterns
        self.ignore_patterns = ignore_patterns
        self.recursive = recursive

        self.observer: Optional[Observer] = None
        self.event_handler: Optional[FileChangeHandler] = None
        self._is_running = False

    def start(self):
        """
        Start watching for file changes.

        Raises:
            RuntimeError: If watcher is already running
        """
        if self._is_running:
            raise RuntimeError("File watcher is already running")

        logger.info(
            f"Starting file watcher: path={self.watch_path}, "
            f"recursive={self.recursive}, patterns={self.file_patterns}"
        )

        # Create event handler
        self.event_handler = FileChangeHandler(
            callback=self.callback,
            file_patterns=self.file_patterns,
            ignore_patterns=self.ignore_patterns,
        )

        # Create and start observer
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.watch_path),
            recursive=self.recursive,
        )
        self.observer.start()

        self._is_running = True
        logger.info("File watcher started successfully")

    def stop(self):
        """
        Stop watching for file changes.
        """
        if not self._is_running:
            return

        logger.info("Stopping file watcher")

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)
            self.observer = None

        self.event_handler = None
        self._is_running = False

        logger.info("File watcher stopped")

    def is_running(self) -> bool:
        """
        Check if watcher is currently running.

        Returns:
            True if watcher is running
        """
        return self._is_running

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


class AsyncFileWatcher:
    """
    Async wrapper for FileWatcher to integrate with async/await code.

    Bridges the synchronous watchdog library with async event handling.
    """

    def __init__(
        self,
        watch_path: Path,
        file_patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        recursive: bool = True,
    ):
        """
        Initialize async file watcher.

        Args:
            watch_path: Directory path to watch
            file_patterns: List of file patterns to watch
            ignore_patterns: List of patterns to ignore
            recursive: Whether to watch subdirectories recursively
        """
        self.watch_path = watch_path
        self.file_patterns = file_patterns
        self.ignore_patterns = ignore_patterns
        self.recursive = recursive

        self.watcher: Optional[FileWatcher] = None
        self._callbacks: List[Callable[[str, str], None]] = []
        self._event_queue: Optional[asyncio.Queue] = None
        self._processing_task: Optional[asyncio.Task] = None

    def add_callback(self, callback: Callable[[str, str], None]):
        """
        Add a callback to be invoked on file changes.

        Args:
            callback: Async function to call (receives event_type, file_path)
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str, str], None]):
        """
        Remove a callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _on_file_change(self, event_type: str, file_path: str):
        """
        Internal callback that queues events for async processing.

        Args:
            event_type: Type of event ("modified", "created", "deleted")
            file_path: Path to the changed file
        """
        if self._event_queue:
            # Use thread-safe put_nowait since this runs in watchdog thread
            try:
                self._event_queue.put_nowait((event_type, file_path))
            except asyncio.QueueFull:
                logger.warning(f"Event queue full, dropping event: {event_type} {file_path}")

    async def _process_events(self):
        """Process file change events from the queue."""
        while True:
            try:
                event_type, file_path = await self._event_queue.get()

                # Invoke all registered callbacks
                for callback in self._callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event_type, file_path)
                        else:
                            callback(event_type, file_path)
                    except Exception as e:
                        logger.error(
                            f"Error in async callback for {event_type} {file_path}: {e}",
                            exc_info=True,
                        )

                self._event_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing file events: {e}", exc_info=True)

    async def start(self):
        """
        Start watching for file changes.

        Raises:
            RuntimeError: If watcher is already running
        """
        if self.watcher and self.watcher.is_running():
            raise RuntimeError("Async file watcher is already running")

        # Create event queue
        self._event_queue = asyncio.Queue(maxsize=1000)

        # Start event processing task
        self._processing_task = asyncio.create_task(self._process_events())

        # Create and start file watcher
        self.watcher = FileWatcher(
            watch_path=self.watch_path,
            callback=self._on_file_change,
            file_patterns=self.file_patterns,
            ignore_patterns=self.ignore_patterns,
            recursive=self.recursive,
        )
        self.watcher.start()

        logger.info(f"Async file watcher started for {self.watch_path}")

    async def stop(self):
        """Stop watching for file changes."""
        if self.watcher:
            self.watcher.stop()
            self.watcher = None

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

        self._event_queue = None

        logger.info("Async file watcher stopped")

    def is_running(self) -> bool:
        """
        Check if watcher is currently running.

        Returns:
            True if watcher is running
        """
        return self.watcher is not None and self.watcher.is_running()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
