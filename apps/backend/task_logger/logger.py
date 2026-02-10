"""
Main TaskLogger class for logging task execution.
"""

from datetime import UTC, datetime
from pathlib import Path

from core.debug import debug, debug_error, debug_info, debug_success, is_debug_enabled

from .models import Bookmark, LogEntry, LogEntryType, LogPhase
from .storage import LogStorage
from .streaming import emit_marker


class TaskLogger:
    """
    Logger for a specific task/spec.

    Handles persistent storage of logs and emits streaming markers
    for real-time UI updates.

    Usage:
        logger = TaskLogger(spec_dir)
        logger.start_phase(LogPhase.CODING)
        logger.log("Starting implementation...")
        logger.tool_start("Read", "/path/to/file.py")
        logger.tool_end("Read")
        logger.log("File read complete")
        logger.end_phase(LogPhase.CODING, success=True)
    """

    LOG_FILE = "task_logs.json"

    def __init__(self, spec_dir: Path, emit_markers: bool = True):
        """
        Initialize the task logger.

        Args:
            spec_dir: Path to the spec directory
            emit_markers: Whether to emit streaming markers to stdout
        """
        self.spec_dir = Path(spec_dir)
        self.log_file = self.spec_dir / self.LOG_FILE
        self.emit_markers = emit_markers
        self.current_phase: LogPhase | None = None
        self.current_session: int | None = None
        self.current_subtask: str | None = None
        self.last_subtask: str | None = None  # Track last subtask for transition detection
        self.storage = LogStorage(spec_dir)

    @property
    def _data(self) -> dict:
        """Get the underlying storage data."""
        return self.storage.get_data()

    def _timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(UTC).isoformat()

    def _emit(self, marker_type: str, data: dict) -> None:
        """Emit a streaming marker to stdout for UI consumption."""
        emit_marker(marker_type, data, self.emit_markers)

    def _add_entry(self, entry: LogEntry) -> None:
        """Add an entry to the current phase."""
        self.storage.add_entry(entry)

    def _debug_log(
        self,
        content: str,
        entry_type: LogEntryType = LogEntryType.TEXT,
        phase: str | None = None,
        tool_name: str | None = None,
        **kwargs,
    ) -> None:
        """
        Output a log entry to the terminal via the debug logging system.

        Only outputs when DEBUG=true is set in the environment.

        Args:
            content: The message content
            entry_type: Type of entry for formatting
            phase: Current phase name
            tool_name: Tool name if this is a tool log
            **kwargs: Additional key-value pairs for debug output
        """
        if not is_debug_enabled():
            return

        module = "task_logger"
        prefix = f"[{phase or 'unknown'}]" if phase else ""

        if tool_name:
            prefix = f"{prefix}[{tool_name}]"

        message = f"{prefix} {content}" if prefix else content

        # Route to appropriate debug function based on entry type
        if entry_type == LogEntryType.ERROR:
            debug_error(module, message, **kwargs)
        elif entry_type == LogEntryType.SUCCESS:
            debug_success(module, message, **kwargs)
        elif entry_type in (
            LogEntryType.INFO,
            LogEntryType.PHASE_START,
            LogEntryType.PHASE_END,
        ):
            debug_info(module, message, **kwargs)
        elif entry_type in (LogEntryType.TOOL_START, LogEntryType.TOOL_END):
            debug(module, message, level=2, **kwargs)
        else:
            debug(module, message, **kwargs)

    def set_session(self, session: int) -> None:
        """Set the current session number."""
        self.current_session = session

    def start_session(self, session: int) -> None:
        """
        Start a new session.

        Args:
            session: Session number
        """
        self.current_session = session
        self.storage.start_session(session)

        # Debug log (when DEBUG=true)
        self._debug_log(f"Session {session} started", LogEntryType.INFO)

    def end_session(self) -> None:
        """End the current session and calculate duration."""
        if self.current_session is not None:
            self.storage.end_session(self.current_session)

            # Debug log (when DEBUG=true)
            self._debug_log(
                f"Session {self.current_session} ended", LogEntryType.INFO
            )

    def set_subtask(self, subtask_id: str | None) -> None:
        """
        Set the current subtask being processed.

        Automatically tracks subtask transitions.

        Args:
            subtask_id: New subtask ID (None to clear)
        """
        # Detect transition
        if subtask_id != self.current_subtask:
            # Record the transition
            self.storage.add_subtask_transition(
                from_subtask=self.current_subtask,
                to_subtask=subtask_id,
                session=self.current_session,
            )

            # Add subtask to session
            if subtask_id and self.current_session is not None:
                self.storage.add_subtask_to_session(self.current_session, subtask_id)

            # Debug log (when DEBUG=true)
            if subtask_id:
                self._debug_log(
                    f"Subtask transition: {self.current_subtask} -> {subtask_id}",
                    LogEntryType.INFO,
                )
            else:
                self._debug_log(
                    f"Subtask ended: {self.current_subtask}", LogEntryType.INFO
                )

            # Update current subtask
            self.last_subtask = self.current_subtask
            self.current_subtask = subtask_id

    def start_phase(self, phase: LogPhase, message: str | None = None) -> None:
        """
        Start a new phase, auto-closing any stale active phases.

        This handles restart/recovery scenarios where a previous run was interrupted
        before properly closing a phase. When starting a new phase, any other phases
        that are still marked as "active" will be auto-closed.

        Args:
            phase: The phase to start
            message: Optional message to log at phase start
        """
        self.current_phase = phase
        phase_key = phase.value

        # Auto-close any other active phases (handles restart/recovery scenarios)
        for other_phase_key, phase_data in self._data["phases"].items():
            if other_phase_key != phase_key and phase_data.get("status") == "active":
                # Auto-close stale phase from previous interrupted run
                self.storage.update_phase_status(
                    other_phase_key, "completed", self._timestamp()
                )
                # Add a log entry noting the auto-close
                auto_close_entry = LogEntry(
                    timestamp=self._timestamp(),
                    type=LogEntryType.PHASE_END.value,
                    content=f"{other_phase_key} phase auto-closed on resume",
                    phase=other_phase_key,
                    session=self.current_session,
                )
                self._add_entry(auto_close_entry)

        # Update phase status
        self.storage.update_phase_status(phase_key, "active")
        self.storage.set_phase_started(phase_key, self._timestamp())

        # Emit marker for UI
        self._emit("PHASE_START", {"phase": phase_key, "timestamp": self._timestamp()})

        # Add phase start entry
        phase_message = message or f"Starting {phase_key} phase"
        entry = LogEntry(
            timestamp=self._timestamp(),
            type=LogEntryType.PHASE_START.value,
            content=phase_message,
            phase=phase_key,
            session=self.current_session,
        )
        self._add_entry(entry)

        # Debug log (when DEBUG=true)
        self._debug_log(phase_message, LogEntryType.PHASE_START, phase_key)

        # Also print the message
        if message:
            print(message, flush=True)

    def end_phase(
        self, phase: LogPhase, success: bool = True, message: str | None = None
    ) -> None:
        """
        End a phase.

        Args:
            phase: The phase to end
            success: Whether the phase completed successfully
            message: Optional message to log at phase end
        """
        phase_key = phase.value

        # Update phase status
        status = "completed" if success else "failed"
        self.storage.update_phase_status(phase_key, status, self._timestamp())

        # Emit marker for UI
        self._emit(
            "PHASE_END",
            {"phase": phase_key, "success": success, "timestamp": self._timestamp()},
        )

        # Add phase end entry
        phase_message = (
            message or f"{'Completed' if success else 'Failed'} {phase_key} phase"
        )
        entry = LogEntry(
            timestamp=self._timestamp(),
            type=LogEntryType.PHASE_END.value,
            content=phase_message,
            phase=phase_key,
            session=self.current_session,
        )
        self._add_entry(entry)

        # Debug log (when DEBUG=true)
        entry_type = LogEntryType.SUCCESS if success else LogEntryType.ERROR
        self._debug_log(phase_message, entry_type, phase_key)

        if message:
            print(message, flush=True)

        if phase == self.current_phase:
            self.current_phase = None

        self.storage.save()

    def log(
        self,
        content: str,
        entry_type: LogEntryType = LogEntryType.TEXT,
        phase: LogPhase | None = None,
        print_to_console: bool = True,
    ) -> None:
        """
        Log a message.

        Args:
            content: The message to log
            entry_type: Type of entry (text, error, success, info)
            phase: Optional phase override (uses current_phase if not specified)
            print_to_console: Whether to also print to stdout (default True)
        """
        phase_key = (phase or self.current_phase or LogPhase.CODING).value

        entry = LogEntry(
            timestamp=self._timestamp(),
            type=entry_type.value,
            content=content,
            phase=phase_key,
            subtask_id=self.current_subtask,
            session=self.current_session,
        )
        self._add_entry(entry)

        # Emit streaming marker
        self._emit(
            "TEXT",
            {
                "content": content,
                "phase": phase_key,
                "type": entry_type.value,
                "subtask_id": self.current_subtask,
                "timestamp": self._timestamp(),
            },
        )

        # Debug log (when DEBUG=true)
        self._debug_log(content, entry_type, phase_key, subtask=self.current_subtask)

        # Also print to console (unless caller handles printing)
        if print_to_console:
            print(content, flush=True)

    def log_error(self, content: str, phase: LogPhase | None = None) -> None:
        """Log an error message."""
        self.log(content, LogEntryType.ERROR, phase)

    def log_success(self, content: str, phase: LogPhase | None = None) -> None:
        """Log a success message."""
        self.log(content, LogEntryType.SUCCESS, phase)

    def log_info(self, content: str, phase: LogPhase | None = None) -> None:
        """Log an info message."""
        self.log(content, LogEntryType.INFO, phase)

    def log_with_detail(
        self,
        content: str,
        detail: str,
        entry_type: LogEntryType = LogEntryType.TEXT,
        phase: LogPhase | None = None,
        subphase: str | None = None,
        collapsed: bool = True,
        print_to_console: bool = True,
    ) -> None:
        """
        Log a message with expandable detail content.

        Args:
            content: Brief summary shown by default
            detail: Full content shown when expanded (e.g., file contents, command output)
            entry_type: Type of entry (text, error, success, info)
            phase: Optional phase override
            subphase: Optional subphase grouping (e.g., "PROJECT DISCOVERY")
            collapsed: Whether detail should be collapsed by default (default True)
            print_to_console: Whether to print summary to stdout (default True)
        """
        phase_key = (phase or self.current_phase or LogPhase.CODING).value

        entry = LogEntry(
            timestamp=self._timestamp(),
            type=entry_type.value,
            content=content,
            phase=phase_key,
            subtask_id=self.current_subtask,
            session=self.current_session,
            detail=detail,
            subphase=subphase,
            collapsed=collapsed,
        )
        self._add_entry(entry)

        # Emit streaming marker with detail indicator
        self._emit(
            "TEXT",
            {
                "content": content,
                "phase": phase_key,
                "type": entry_type.value,
                "subtask_id": self.current_subtask,
                "timestamp": self._timestamp(),
                "has_detail": True,
                "subphase": subphase,
            },
        )

        # Debug log (when DEBUG=true) - include detail for verbose mode
        self._debug_log(
            content,
            entry_type,
            phase_key,
            subtask=self.current_subtask,
            subphase=subphase,
            detail=detail[:500] + "..." if len(detail) > 500 else detail,
        )

        if print_to_console:
            print(content, flush=True)

    def start_subphase(
        self,
        subphase: str,
        phase: LogPhase | None = None,
        print_to_console: bool = True,
    ) -> None:
        """
        Mark the start of a subphase within the current phase.

        Args:
            subphase: Name of the subphase (e.g., "PROJECT DISCOVERY", "CONTEXT GATHERING")
            phase: Optional phase override
            print_to_console: Whether to print to stdout
        """
        phase_key = (phase or self.current_phase or LogPhase.CODING).value

        entry = LogEntry(
            timestamp=self._timestamp(),
            type=LogEntryType.INFO.value,
            content=f"Starting {subphase}",
            phase=phase_key,
            subtask_id=self.current_subtask,
            session=self.current_session,
            subphase=subphase,
        )
        self._add_entry(entry)

        # Emit streaming marker
        self._emit(
            "SUBPHASE_START",
            {"subphase": subphase, "phase": phase_key, "timestamp": self._timestamp()},
        )

        # Debug log (when DEBUG=true)
        self._debug_log(
            f"Starting {subphase}", LogEntryType.INFO, phase_key, subphase=subphase
        )

        if print_to_console:
            print(f"\n--- {subphase} ---", flush=True)

    def tool_start(
        self,
        tool_name: str,
        tool_input: str | None = None,
        phase: LogPhase | None = None,
        print_to_console: bool = True,
    ) -> None:
        """
        Log the start of a tool execution.

        Args:
            tool_name: Name of the tool (e.g., "Read", "Write", "Bash")
            tool_input: Brief description of tool input
            phase: Optional phase override
            print_to_console: Whether to also print to stdout (default True)
        """
        phase_key = (phase or self.current_phase or LogPhase.CODING).value

        # Truncate long inputs for display (increased limit to avoid hiding critical info)
        display_input = tool_input
        if display_input and len(display_input) > 300:
            display_input = display_input[:297] + "..."

        entry = LogEntry(
            timestamp=self._timestamp(),
            type=LogEntryType.TOOL_START.value,
            content=f"[{tool_name}] {display_input or ''}".strip(),
            phase=phase_key,
            tool_name=tool_name,
            tool_input=display_input,
            subtask_id=self.current_subtask,
            session=self.current_session,
        )
        self._add_entry(entry)

        # Emit streaming marker (same format as insights_runner.py)
        self._emit(
            "TOOL_START",
            {"name": tool_name, "input": display_input, "phase": phase_key},
        )

        # Debug log (when DEBUG=true)
        self._debug_log(
            display_input or "started",
            LogEntryType.TOOL_START,
            phase_key,
            tool_name=tool_name,
        )

        if print_to_console:
            print(f"\n[Tool: {tool_name}]", flush=True)

    def tool_end(
        self,
        tool_name: str,
        success: bool = True,
        result: str | None = None,
        detail: str | None = None,
        phase: LogPhase | None = None,
        print_to_console: bool = False,
    ) -> None:
        """
        Log the end of a tool execution.

        Args:
            tool_name: Name of the tool
            success: Whether the tool succeeded
            result: Optional brief result description (shown in summary)
            detail: Optional full result content (expandable in UI, e.g., file contents, command output)
            phase: Optional phase override
            print_to_console: Whether to also print to stdout (default False for tool_end)
        """
        phase_key = (phase or self.current_phase or LogPhase.CODING).value

        # Truncate long results for display (increased limit to avoid hiding critical info)
        display_result = result
        if display_result and len(display_result) > 300:
            display_result = display_result[:297] + "..."

        status = "Done" if success else "Error"
        content = f"[{tool_name}] {status}"
        if display_result:
            content += f": {display_result}"

        # Truncate detail for storage (max 10KB to avoid bloating JSON)
        stored_detail = detail
        if stored_detail and len(stored_detail) > 10240:
            stored_detail = (
                stored_detail[:10240]
                + f"\n\n... [truncated - full output was {len(detail)} chars]"
            )

        entry = LogEntry(
            timestamp=self._timestamp(),
            type=LogEntryType.TOOL_END.value,
            content=content,
            phase=phase_key,
            tool_name=tool_name,
            subtask_id=self.current_subtask,
            session=self.current_session,
            detail=stored_detail,
            collapsed=True,
        )
        self._add_entry(entry)

        # Emit streaming marker
        self._emit(
            "TOOL_END",
            {
                "name": tool_name,
                "success": success,
                "phase": phase_key,
                "has_detail": detail is not None,
            },
        )

        # Debug log (when DEBUG=true)
        debug_kwargs = {"status": status}
        if display_result:
            debug_kwargs["result"] = display_result
        self._debug_log(
            content,
            LogEntryType.SUCCESS if success else LogEntryType.ERROR,
            phase_key,
            tool_name=tool_name,
            **debug_kwargs,
        )

        if print_to_console:
            if result:
                print(f"   [{status}] {display_result}", flush=True)
            else:
                print(f"   [{status}]", flush=True)

    def get_logs(self) -> dict:
        """Get all logs."""
        return self._data

    def get_phase_logs(self, phase: LogPhase) -> dict:
        """Get logs for a specific phase."""
        return self.storage.get_phase_data(phase.value)

    def create_bookmark(
        self,
        label: str,
        note: str | None = None,
        entry_timestamp: str | None = None,
    ) -> str:
        """
        Create a bookmark at the current moment or at a specific log entry.

        Args:
            label: User-provided label/title for the bookmark
            note: Optional note/comment
            entry_timestamp: Optional timestamp of specific log entry to bookmark.
                           If not provided, uses current timestamp.

        Returns:
            The bookmark ID
        """
        import uuid

        bookmark_id = str(uuid.uuid4())
        phase_key = (self.current_phase or LogPhase.CODING).value

        bookmark = Bookmark(
            id=bookmark_id,
            timestamp=self._timestamp(),
            entry_timestamp=entry_timestamp or self._timestamp(),
            phase=phase_key,
            label=label,
            note=note,
            session=self.current_session,
            subtask_id=self.current_subtask,
        )

        self.storage.add_bookmark(bookmark)

        # Emit streaming marker for real-time UI updates
        self._emit(
            "BOOKMARK_CREATED",
            {
                "id": bookmark_id,
                "label": label,
                "phase": phase_key,
                "session": self.current_session,
            },
        )

        # Debug log (when DEBUG=true)
        self._debug_log(f"Bookmark created: {label}", LogEntryType.INFO, phase_key)

        return bookmark_id

    def get_bookmarks(
        self,
        phase: str | None = None,
        session: int | None = None,
        subtask_id: str | None = None,
    ) -> list[dict]:
        """
        Get bookmarks, optionally filtered.

        Args:
            phase: Optional phase filter
            session: Optional session filter
            subtask_id: Optional subtask filter

        Returns:
            List of bookmark dictionaries
        """
        return self.storage.get_bookmarks(
            phase=phase, session=session, subtask_id=subtask_id
        )

    def remove_bookmark(self, bookmark_id: str) -> bool:
        """
        Remove a bookmark by its ID.

        Args:
            bookmark_id: The bookmark ID to remove

        Returns:
            True if bookmark was found and removed, False otherwise
        """
        success = self.storage.remove_bookmark(bookmark_id)

        if success:
            # Emit streaming marker for real-time UI updates
            self._emit("BOOKMARK_REMOVED", {"id": bookmark_id})

            # Debug log (when DEBUG=true)
            phase_key = (self.current_phase or LogPhase.CODING).value
            self._debug_log(
                f"Bookmark removed: {bookmark_id}", LogEntryType.INFO, phase_key
            )

        return success

    def clear(self) -> None:
        """Clear all logs (useful for testing)."""
        self.storage = LogStorage(self.spec_dir)
