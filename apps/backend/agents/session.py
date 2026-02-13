"""
Agent Session Management
========================

Handles running agent sessions and post-session processing including
memory updates, recovery tracking, and Linear integration.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeSDKClient
from core.token_stats import PhaseTokenStats, PhaseType, TaskTokenStats
from debug import (
    debug,
    debug_detailed,
    debug_error,
    debug_section,
    debug_success,
    debug_warning,
)
from insight_extractor import extract_session_insights
from linear_updater import (
    linear_subtask_completed,
    linear_subtask_failed,
)
from progress import (
    count_subtasks_detailed,
    is_build_complete,
)
from recovery import RecoveryManager
from security.tool_input_validator import get_safe_tool_input
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)
from ui import (
    StatusManager,
    muted,
    print_key_value,
    print_status,
)

from .decision_tracker import DecisionTracker
from .memory_manager import save_session_memory
from .process_isolator import (
    AgentIsolationResult,
    AgentProcessError,
    AgentProcessIsolator,
    ResourceLimits,
)
from .utils import (
    find_subtask_in_plan,
    get_commit_count,
    get_latest_commit,
    load_implementation_plan,
    sync_spec_to_source,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Conversation History Tracking
# ============================================================================


class ConversationRound:
    """
    Represents a single round of conversation (user message + assistant response).

    Attributes:
        round_number: Sequential round number within session
        timestamp: When this round started
        user_message: The prompt/query sent to the agent
        assistant_response: The complete text response from the agent
        tool_calls: List of tools called during this round
        code_references: List of file paths referenced in this round
        phase: Execution phase (planning, coding, validation)
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
    """

    def __init__(
        self,
        round_number: int,
        user_message: str,
        timestamp: datetime | None = None,
        phase: str = "coding",
    ):
        self.round_number = round_number
        self.timestamp = timestamp or datetime.now()
        self.user_message = user_message
        self.assistant_response = ""
        self.tool_calls: list[dict[str, Any]] = []
        self.code_references: set[str] = set()
        self.phase = phase
        self.input_tokens = 0
        self.output_tokens = 0

    def add_text(self, text: str) -> None:
        """Add text to assistant response."""
        self.assistant_response += text

    def add_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        """Record a tool call."""
        self.tool_calls.append({"name": tool_name, "input": tool_input})

        # Extract file paths from common tool inputs
        if "file_path" in tool_input:
            self.code_references.add(tool_input["file_path"])
        elif "path" in tool_input:
            self.code_references.add(tool_input["path"])
        elif "pattern" in tool_input and "path" in tool_input:
            # Grep/Glob operations
            self.code_references.add(tool_input["path"])

    def set_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Set token usage for this round."""
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "round_number": self.round_number,
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase,
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "tool_calls": self.tool_calls,
            "code_references": list(self.code_references),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationRound":
        """Reconstruct from dictionary."""
        round_obj = cls(
            round_number=data["round_number"],
            user_message=data["user_message"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            phase=data.get("phase", "coding"),
        )
        round_obj.assistant_response = data["assistant_response"]
        round_obj.tool_calls = data.get("tool_calls", [])
        round_obj.code_references = set(data.get("code_references", []))
        round_obj.input_tokens = data.get("input_tokens", 0)
        round_obj.output_tokens = data.get("output_tokens", 0)
        return round_obj


class ConversationHistory:
    """
    Manages full conversation history for a session.

    This tracks all rounds of conversation, enabling:
    - Session resumption with full context
    - Context window optimization
    - Progress review and debugging
    """

    def __init__(self, spec_dir: Path, subtask_id: str | None = None):
        self.spec_dir = spec_dir
        self.subtask_id = subtask_id
        self.rounds: list[ConversationRound] = []
        self.session_start = datetime.now()
        self.session_id = f"{subtask_id}_{self.session_start.strftime('%Y%m%d_%H%M%S')}"

    def add_round(self, user_message: str, phase: str = "coding") -> ConversationRound:
        """Start a new conversation round."""
        round_number = len(self.rounds) + 1
        round_obj = ConversationRound(
            round_number=round_number, user_message=user_message, phase=phase
        )
        self.rounds.append(round_obj)
        return round_obj

    def get_current_round(self) -> ConversationRound | None:
        """Get the most recent conversation round."""
        return self.rounds[-1] if self.rounds else None

    def get_total_tokens(self) -> tuple[int, int]:
        """Get total input and output tokens across all rounds."""
        total_input = sum(r.input_tokens for r in self.rounds)
        total_output = sum(r.output_tokens for r in self.rounds)
        return total_input, total_output

    def get_all_code_references(self) -> set[str]:
        """Get all unique file paths referenced in the conversation."""
        all_refs = set()
        for round_obj in self.rounds:
            all_refs.update(round_obj.code_references)
        return all_refs

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "subtask_id": self.subtask_id,
            "session_start": self.session_start.isoformat(),
            "total_rounds": len(self.rounds),
            "rounds": [r.to_dict() for r in self.rounds],
        }

    @classmethod
    def from_dict(cls, spec_dir: Path, data: dict[str, Any]) -> "ConversationHistory":
        """Reconstruct from dictionary."""
        history = cls(spec_dir=spec_dir, subtask_id=data.get("subtask_id"))
        history.session_id = data["session_id"]
        history.session_start = datetime.fromisoformat(data["session_start"])
        history.rounds = [
            ConversationRound.from_dict(r) for r in data.get("rounds", [])
        ]
        return history

    def save(self) -> bool:
        """
        Save conversation history to JSON file.

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            history_dir = self.spec_dir / "conversation_history"
            history_dir.mkdir(parents=True, exist_ok=True)

            history_file = history_dir / f"{self.session_id}.json"

            with open(history_file, "w") as f:
                json.dump(self.to_dict(), f, indent=2)

            debug_success(
                "session",
                f"Saved conversation history: {len(self.rounds)} rounds",
                file=str(history_file),
            )
            return True

        except Exception as e:
            debug_error("session", f"Failed to save conversation history: {e}")
            logger.error(f"Failed to save conversation history: {e}")
            return False

    @classmethod
    def load_latest(
        cls, spec_dir: Path, subtask_id: str | None = None
    ) -> "ConversationHistory | None":
        """
        Load the most recent conversation history for a subtask.

        Args:
            spec_dir: Spec directory
            subtask_id: Optional subtask filter

        Returns:
            ConversationHistory object or None if no history exists
        """
        try:
            history_dir = spec_dir / "conversation_history"
            if not history_dir.exists():
                return None

            # Find all history files
            history_files = list(history_dir.glob("*.json"))
            if not history_files:
                return None

            # Filter by subtask_id if provided
            if subtask_id:
                history_files = [
                    f for f in history_files if f.stem.startswith(f"{subtask_id}_")
                ]
                if not history_files:
                    return None

            # Get most recent file
            latest_file = max(history_files, key=lambda f: f.stat().st_mtime)

            with open(latest_file) as f:
                data = json.load(f)

            debug_success(
                "session",
                f"Loaded conversation history: {data.get('total_rounds', 0)} rounds",
                file=str(latest_file),
            )
            return cls.from_dict(spec_dir, data)

        except Exception as e:
            debug_error("session", f"Failed to load conversation history: {e}")
            logger.warning(f"Failed to load conversation history: {e}")
            return None


def load_token_stats(spec_dir: Path) -> TaskTokenStats | None:
    """
    Load token statistics from token_stats.json in spec directory.

    Args:
        spec_dir: Path to spec directory

    Returns:
        TaskTokenStats object if file exists, None otherwise
    """
    stats_file = spec_dir / "token_stats.json"
    if not stats_file.exists():
        return None

    try:
        with open(stats_file) as f:
            data = json.load(f)

        # Reconstruct PhaseTokenStats objects
        phases: dict[PhaseType, PhaseTokenStats] = {}
        for phase_name, phase_data in data.get("phases", {}).items():
            phases[phase_name] = PhaseTokenStats(
                phase=phase_data["phase"],
                input_tokens=phase_data["input_tokens"],
                output_tokens=phase_data["output_tokens"],
                session_count=phase_data.get("session_count", 0),
                updated_at=datetime.fromisoformat(phase_data["updated_at"]),
            )

        return TaskTokenStats(
            phases=phases,
            total_input_tokens=data["total_input_tokens"],
            total_output_tokens=data["total_output_tokens"],
            total_tokens=data["total_tokens"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
    except Exception as e:
        logger.warning(f"Failed to load token stats from {stats_file}: {e}")
        return None


def save_token_stats(
    spec_dir: Path,
    phase: PhaseType,
    input_tokens: int,
    output_tokens: int,
) -> bool:
    """
    Update token statistics for a phase and persist to token_stats.json.

    This function loads existing stats, updates the specified phase, recalculates
    totals, and saves atomically.

    Args:
        spec_dir: Path to spec directory
        phase: Execution phase (planning, coding, validation)
        input_tokens: Number of input tokens used in this session
        output_tokens: Number of output tokens used in this session

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Load existing stats or create new
        existing_stats = load_token_stats(spec_dir)
        now = datetime.now()

        if existing_stats:
            phases = existing_stats.phases.copy()
            created_at = existing_stats.created_at
        else:
            phases = {}
            created_at = now

        # Update or create phase stats
        if phase in phases:
            phase_stats = phases[phase]
            phase_stats.input_tokens += input_tokens
            phase_stats.output_tokens += output_tokens
            phase_stats.session_count += 1
            phase_stats.updated_at = now
        else:
            phase_stats = PhaseTokenStats(
                phase=phase,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                session_count=1,
                updated_at=now,
            )
            phases[phase] = phase_stats

        # Recalculate totals
        total_input = sum(p.input_tokens for p in phases.values())
        total_output = sum(p.output_tokens for p in phases.values())

        # Create updated TaskTokenStats
        task_stats = TaskTokenStats(
            phases=phases,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_input + total_output,
            created_at=created_at,
            updated_at=now,
        )

        # Save to file (atomic write)
        stats_file = spec_dir / "token_stats.json"
        stats_file.parent.mkdir(parents=True, exist_ok=True)

        with open(stats_file, "w") as f:
            json.dump(task_stats.to_dict(), f, indent=2)

        logger.debug(
            f"Saved token stats for {phase} phase: {input_tokens} in, {output_tokens} out"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to save token stats to {spec_dir}: {e}")
        return False


async def post_session_processing(
    spec_dir: Path,
    project_dir: Path,
    subtask_id: str,
    session_num: int,
    commit_before: str | None,
    commit_count_before: int,
    recovery_manager: RecoveryManager,
    linear_enabled: bool = False,
    status_manager: StatusManager | None = None,
    source_spec_dir: Path | None = None,
) -> bool:
    """
    Process session results and update memory automatically.

    This runs in Python (100% reliable) instead of relying on agent compliance.

    Args:
        spec_dir: Spec directory containing memory/
        project_dir: Project root for git operations
        subtask_id: The subtask that was being worked on
        session_num: Current session number
        commit_before: Git commit hash before session
        commit_count_before: Number of commits before session
        recovery_manager: Recovery manager instance
        linear_enabled: Whether Linear integration is enabled
        status_manager: Optional status manager for ccstatusline
        source_spec_dir: Original spec directory (for syncing back from worktree)

    Returns:
        True if subtask was completed successfully
    """
    print()
    print(muted("--- Post-Session Processing ---"))

    # Sync implementation plan back to source (for worktree mode)
    if sync_spec_to_source(spec_dir, source_spec_dir):
        print_status("Implementation plan synced to main project", "success")

    # Check if implementation plan was updated
    plan = load_implementation_plan(spec_dir)
    if not plan:
        print("  Warning: Could not load implementation plan")
        return False

    subtask = find_subtask_in_plan(plan, subtask_id)
    if not subtask:
        print(f"  Warning: Subtask {subtask_id} not found in plan")
        return False

    subtask_status = subtask.get("status", "pending")

    # Check for new commits
    commit_after = get_latest_commit(project_dir)
    commit_count_after = get_commit_count(project_dir)
    new_commits = commit_count_after - commit_count_before

    print_key_value("Subtask status", subtask_status)
    print_key_value("New commits", str(new_commits))

    if subtask_status == "completed":
        # Success! Record the attempt and good commit
        print_status(f"Subtask {subtask_id} completed successfully", "success")

        # Update status file
        if status_manager:
            subtasks = count_subtasks_detailed(spec_dir)
            status_manager.update_subtasks(
                completed=subtasks["completed"],
                total=subtasks["total"],
                in_progress=0,
            )

        # Record successful attempt
        recovery_manager.record_attempt(
            subtask_id=subtask_id,
            session=session_num,
            success=True,
            approach=f"Implemented: {subtask.get('description', 'subtask')[:100]}",
        )

        # Get recovery hints for context (if this was a retry)
        attempt_count = recovery_manager.get_attempt_count(subtask_id)
        recovery_hints = (
            recovery_manager.get_recovery_hints(subtask_id)
            if attempt_count > 1
            else None
        )

        # Record good commit for rollback safety
        if commit_after and commit_after != commit_before:
            recovery_manager.record_good_commit(commit_after, subtask_id)
            print_status(f"Recorded good commit: {commit_after[:8]}", "success")

        # Record Linear session result (if enabled)
        if linear_enabled:
            # Get progress counts for the comment
            subtasks_detail = count_subtasks_detailed(spec_dir)
            await linear_subtask_completed(
                spec_dir=spec_dir,
                subtask_id=subtask_id,
                completed_count=subtasks_detail["completed"],
                total_count=subtasks_detail["total"],
            )
            print_status("Linear progress recorded", "success")

        # Extract rich insights from session (LLM-powered analysis)
        try:
            extracted_insights = await extract_session_insights(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                commit_before=commit_before,
                commit_after=commit_after,
                success=True,
                recovery_manager=recovery_manager,
            )
            insight_count = len(extracted_insights.get("file_insights", []))
            pattern_count = len(extracted_insights.get("patterns_discovered", []))
            if insight_count > 0 or pattern_count > 0:
                print_status(
                    f"Extracted {insight_count} file insights, {pattern_count} patterns",
                    "success",
                )
        except Exception as e:
            logger.warning(f"Insight extraction failed: {e}")
            extracted_insights = None

        # Save session memory (Graphiti=primary, file-based=fallback)
        try:
            save_success, storage_type = await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                success=True,
                subtasks_completed=[subtask_id],
                discoveries=extracted_insights,
            )
            if save_success:
                if storage_type == "graphiti":
                    print_status("Session saved to Graphiti memory", "success")
                else:
                    print_status(
                        "Session saved to file-based memory (fallback)", "info"
                    )
            else:
                print_status("Failed to save session memory", "warning")
        except Exception as e:
            logger.warning(f"Error saving session memory: {e}")
            print_status("Memory save failed", "warning")

        return True

    elif subtask_status == "in_progress":
        # Session ended without completion
        print_status(f"Subtask {subtask_id} still in progress", "warning")

        recovery_manager.record_attempt(
            subtask_id=subtask_id,
            session=session_num,
            success=False,
            approach="Session ended with subtask in_progress",
            error="Subtask not marked as completed",
        )

        # Get recovery hints to help next attempt
        attempt_count = recovery_manager.get_attempt_count(subtask_id)
        recovery_hints = recovery_manager.get_recovery_hints(subtask_id)
        if recovery_hints:
            print_status(
                f"Recovery hints available for next attempt ({attempt_count} attempts so far)",
                "info",
            )

        # Still record commit if one was made (partial progress)
        if commit_after and commit_after != commit_before:
            recovery_manager.record_good_commit(commit_after, subtask_id)
            print_status(
                f"Recorded partial progress commit: {commit_after[:8]}", "info"
            )

        # Record Linear session result (if enabled)
        if linear_enabled:
            attempt_count = recovery_manager.get_attempt_count(subtask_id)
            await linear_subtask_failed(
                spec_dir=spec_dir,
                subtask_id=subtask_id,
                attempt=attempt_count,
                error_summary="Session ended without completion",
            )

        # Extract insights even from failed sessions (valuable for future attempts)
        try:
            extracted_insights = await extract_session_insights(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                commit_before=commit_before,
                commit_after=commit_after,
                success=False,
                recovery_manager=recovery_manager,
            )
        except Exception as e:
            logger.debug(f"Insight extraction failed for incomplete session: {e}")
            extracted_insights = None

        # Save failed session memory (to track what didn't work)
        try:
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                success=False,
                subtasks_completed=[],
                discoveries=extracted_insights,
            )
        except Exception as e:
            logger.debug(f"Failed to save incomplete session memory: {e}")

        return False

    else:
        # Subtask still pending or failed
        print_status(
            f"Subtask {subtask_id} not completed (status: {subtask_status})", "error"
        )

        recovery_manager.record_attempt(
            subtask_id=subtask_id,
            session=session_num,
            success=False,
            approach="Session ended without progress",
            error=f"Subtask status is {subtask_status}",
        )

        # Get recovery hints to help diagnose and retry
        attempt_count = recovery_manager.get_attempt_count(subtask_id)
        recovery_hints = recovery_manager.get_recovery_hints(subtask_id)
        if recovery_hints and attempt_count > 0:
            print_status(f"Recovery hints available ({attempt_count} attempts)", "info")

        # Record Linear session result (if enabled)
        if linear_enabled:
            attempt_count = recovery_manager.get_attempt_count(subtask_id)
            await linear_subtask_failed(
                spec_dir=spec_dir,
                subtask_id=subtask_id,
                attempt=attempt_count,
                error_summary=f"Subtask status: {subtask_status}",
            )

        # Extract insights even from completely failed sessions
        try:
            extracted_insights = await extract_session_insights(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                commit_before=commit_before,
                commit_after=commit_after,
                success=False,
                recovery_manager=recovery_manager,
            )
        except Exception as e:
            logger.debug(f"Insight extraction failed for failed session: {e}")
            extracted_insights = None

        # Save failed session memory (to track what didn't work)
        try:
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                success=False,
                subtasks_completed=[],
                discoveries=extracted_insights,
            )
        except Exception as e:
            logger.debug(f"Failed to save failed session memory: {e}")

        return False


def format_context_for_resume(history: ConversationHistory) -> str:
    """
    Format conversation history into a context summary for session resumption.

    Args:
        history: ConversationHistory object to format

    Returns:
        Formatted context string for resuming the session
    """
    if not history or not history.rounds:
        return ""

    context_parts = [
        "# Session Resume Context",
        "",
        f"Session ID: {history.session_id}",
        f"Total rounds: {len(history.rounds)}",
        f"Session started: {history.session_start.isoformat()}",
        "",
        "## Previous Conversation Summary",
        "",
    ]

    # Include last 5 rounds for immediate context
    recent_rounds = history.rounds[-5:] if len(history.rounds) > 5 else history.rounds

    for round_obj in recent_rounds:
        context_parts.append(f"### Round {round_obj.round_number}")
        context_parts.append(f"**User:** {round_obj.user_message[:200]}...")
        if round_obj.assistant_response:
            response_preview = round_obj.assistant_response[:300]
            context_parts.append(f"**Assistant:** {response_preview}...")
        if round_obj.tool_calls:
            tools_used = [tc["name"] for tc in round_obj.tool_calls[:3]]
            context_parts.append(f"**Tools used:** {', '.join(tools_used)}")
        context_parts.append("")

    # Include code references
    code_refs = history.get_all_code_references()
    if code_refs:
        context_parts.append("## Code References from Session")
        for ref in sorted(code_refs)[:10]:  # Limit to 10 most recent
            context_parts.append(f"- {ref}")
        context_parts.append("")

    # Token usage summary
    total_input, total_output = history.get_total_tokens()
    if total_input > 0 or total_output > 0:
        context_parts.append("## Token Usage")
        context_parts.append(f"- Input tokens: {total_input:,}")
        context_parts.append(f"- Output tokens: {total_output:,}")
        context_parts.append("")

    return "\n".join(context_parts)


async def resume_session(
    spec_dir: Path,
    subtask_id: str,
    new_message: str,
) -> tuple[str, ConversationHistory | None]:
    """
    Resume a previous session with full context restore.

    Loads the most recent conversation history for the given subtask
    and formats it for continuing the session.

    Args:
        spec_dir: Spec directory path
        subtask_id: ID of the subtask to resume
        new_message: New message to send after resuming

    Returns:
        Tuple of (formatted_message, conversation_history) where:
        - formatted_message: Message with resume context prepended
        - conversation_history: Loaded ConversationHistory or None if not found
    """
    debug_section("session", f"Resuming session for subtask: {subtask_id}")

    # Load latest conversation history for this subtask
    history = ConversationHistory.load_latest(spec_dir, subtask_id)

    if not history:
        debug_warning(
            "session",
            f"No previous session history found for subtask {subtask_id}",
        )
        # Return as-is if no history exists
        return new_message, None

    debug_success(
        "session",
        f"Loaded session history: {len(history.rounds)} rounds",
        session_id=history.session_id,
        total_rounds=len(history.rounds),
    )

    # Format context for resume
    context_summary = format_context_for_resume(history)

    # Prepend context to new message
    resume_message = (
        f"{context_summary}\n\n"
        f"---\n\n"
        f"## Resuming Session\n\n"
        f"You are resuming the above session. Continue from where you left off.\n\n"
        f"{new_message}"
    )

    debug(
        "session",
        "Formatted resume message",
        context_length=len(context_summary),
        total_length=len(resume_message),
    )

    return resume_message, history


async def run_agent_session(
    client: ClaudeSDKClient,
    message: str,
    spec_dir: Path,
    verbose: bool = False,
    phase: LogPhase = LogPhase.CODING,
    conversation_history: ConversationHistory | None = None,
    subtask_id: str | None = None,
) -> tuple[str, str, dict[str, int] | None, "DecisionTracker"]:
    """
    Run a single agent session using Claude Agent SDK.

    Supports session resumption by passing an existing conversation_history.

    Args:
        client: Claude SDK client
        message: The prompt to send
        spec_dir: Spec directory path
        verbose: Whether to show detailed output
        phase: Current execution phase for logging
        conversation_history: Optional existing history for resuming sessions
        subtask_id: Optional subtask ID for session tracking

    Returns:
        (status, response_text, usage_metadata, decision_tracker) where:
        - status: "continue", "complete", or "error"
        - response_text: The agent's response
        - usage_metadata: Dict with "input_tokens" and "output_tokens" keys (or None if unavailable)
        - decision_tracker: DecisionTracker instance for tracking AI decisions
    """
    debug_section("session", f"Agent Session - {phase.value}")
    debug(
        "session",
        "Starting agent session",
        spec_dir=str(spec_dir),
        phase=phase.value,
        prompt_length=len(message),
        prompt_preview=message[:200] + "..." if len(message) > 200 else message,
    )
    print("Sending prompt to Claude Agent SDK...\n")

    # Get task logger for this spec
    task_logger = get_task_logger(spec_dir)

    # Initialize decision tracker for this session
    decision_tracker = DecisionTracker(
        spec_dir=spec_dir,
        task_logger=task_logger,
        current_phase=phase,
    )
    if subtask_id:
        decision_tracker.set_subtask(subtask_id)

    current_tool = None
    message_count = 0
    tool_count = 0

    # Initialize or reuse conversation history tracking
    if conversation_history is None:
        conversation_history = ConversationHistory(
            spec_dir=spec_dir, subtask_id=subtask_id
        )
        debug("session", "Created new conversation history", subtask_id=subtask_id)
    else:
        debug(
            "session",
            "Resuming with existing conversation history",
            session_id=conversation_history.session_id,
            previous_rounds=len(conversation_history.rounds),
        )

    current_round = conversation_history.add_round(
        user_message=message, phase=phase.value
    )
    debug(
        "session", "Created conversation round", round_number=current_round.round_number
    )

    try:
        # Send the query
        debug("session", "Sending query to Claude SDK...")
        await client.query(message)
        debug_success("session", "Query sent successfully")

        # Collect response text and show tool use
        response_text = ""
        debug("session", "Starting to receive response stream...")
        async for msg in client.receive_response():
            msg_type = type(msg).__name__
            message_count += 1
            debug_detailed(
                "session",
                f"Received message #{message_count}",
                msg_type=msg_type,
            )

            # Handle AssistantMessage (text and tool use)
            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "TextBlock" and hasattr(block, "text"):
                        response_text += block.text
                        print(block.text, end="", flush=True)
                        # Track text in conversation history
                        current_round.add_text(block.text)
                        # Log text to task logger (persist without double-printing)
                        if task_logger and block.text.strip():
                            task_logger.log(
                                block.text,
                                LogEntryType.TEXT,
                                phase,
                                print_to_console=False,
                            )
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input_display = None
                        tool_count += 1

                        # Safely extract tool input (handles None, non-dict, etc.)
                        inp = get_safe_tool_input(block)

                        # Extract meaningful tool input for display
                        if inp:
                            if "pattern" in inp:
                                tool_input_display = f"pattern: {inp['pattern']}"
                            elif "file_path" in inp:
                                fp = inp["file_path"]
                                if len(fp) > 50:
                                    fp = "..." + fp[-47:]
                                tool_input_display = fp
                            elif "command" in inp:
                                cmd = inp["command"]
                                if len(cmd) > 50:
                                    cmd = cmd[:47] + "..."
                                tool_input_display = cmd
                            elif "path" in inp:
                                tool_input_display = inp["path"]

                        debug(
                            "session",
                            f"Tool call #{tool_count}: {tool_name}",
                            tool_input=tool_input_display,
                            full_input=str(inp)[:500] if inp else None,
                        )

                        # Track tool call in conversation history
                        if inp:
                            current_round.add_tool_call(tool_name, inp)

                        # Log tool start (handles printing too)
                        if task_logger:
                            task_logger.tool_start(
                                tool_name,
                                tool_input_display,
                                phase,
                                print_to_console=True,
                            )
                        else:
                            print(f"\n[Tool: {tool_name}]", flush=True)

                        if verbose and hasattr(block, "input"):
                            input_str = str(block.input)
                            if len(input_str) > 300:
                                print(f"   Input: {input_str[:300]}...", flush=True)
                            else:
                                print(f"   Input: {input_str}", flush=True)
                        current_tool = tool_name

            # Handle UserMessage (tool results)
            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "ToolResultBlock":
                        result_content = getattr(block, "content", "")
                        is_error = getattr(block, "is_error", False)

                        # Check if this is an error (not just content containing "blocked")
                        if is_error and "blocked" in str(result_content).lower():
                            # Actual blocked command by security hook
                            debug_error(
                                "session",
                                f"Tool BLOCKED: {current_tool}",
                                result=str(result_content)[:300],
                            )
                            print(f"   [BLOCKED] {result_content}", flush=True)
                            if task_logger and current_tool:
                                task_logger.tool_end(
                                    current_tool,
                                    success=False,
                                    result="BLOCKED",
                                    detail=str(result_content),
                                    phase=phase,
                                )
                        elif is_error:
                            # Show errors (truncated)
                            error_str = str(result_content)[:500]
                            debug_error(
                                "session",
                                f"Tool error: {current_tool}",
                                error=error_str[:200],
                            )
                            print(f"   [Error] {error_str}", flush=True)
                            if task_logger and current_tool:
                                # Store full error in detail for expandable view
                                task_logger.tool_end(
                                    current_tool,
                                    success=False,
                                    result=error_str[:100],
                                    detail=str(result_content),
                                    phase=phase,
                                )
                        else:
                            # Tool succeeded
                            debug_detailed(
                                "session",
                                f"Tool success: {current_tool}",
                                result_length=len(str(result_content)),
                            )
                            if verbose:
                                result_str = str(result_content)[:200]
                                print(f"   [Done] {result_str}", flush=True)
                            else:
                                print("   [Done]", flush=True)
                            if task_logger and current_tool:
                                # Store full result in detail for expandable view (only for certain tools)
                                # Skip storing for very large outputs like Glob results
                                detail_content = None
                                if current_tool in (
                                    "Read",
                                    "Grep",
                                    "Bash",
                                    "Edit",
                                    "Write",
                                ):
                                    result_str = str(result_content)
                                    # Only store if not too large (detail truncation happens in logger)
                                    if (
                                        len(result_str) < 50000
                                    ):  # 50KB max before truncation
                                        detail_content = result_str
                                task_logger.tool_end(
                                    current_tool,
                                    success=True,
                                    detail=detail_content,
                                    phase=phase,
                                )

                        current_tool = None

        print("\n" + "-" * 70 + "\n")

        # Extract usage metadata from Claude SDK client
        usage_metadata = None
        try:
            # Try to get usage metadata from the client
            # The Claude SDK client may expose usage metadata after the session completes
            if hasattr(client, "usage_metadata"):
                metadata = client.usage_metadata
                if (
                    metadata
                    and hasattr(metadata, "input_tokens")
                    and hasattr(metadata, "output_tokens")
                ):
                    usage_metadata = {
                        "input_tokens": metadata.input_tokens,
                        "output_tokens": metadata.output_tokens,
                    }
                    debug_success(
                        "session",
                        "Extracted usage metadata",
                        input_tokens=metadata.input_tokens,
                        output_tokens=metadata.output_tokens,
                    )
            elif hasattr(client, "_usage"):
                # Alternative: some SDKs store usage in a _usage attribute
                usage = client._usage
                if (
                    isinstance(usage, dict)
                    and "input_tokens" in usage
                    and "output_tokens" in usage
                ):
                    usage_metadata = {
                        "input_tokens": usage["input_tokens"],
                        "output_tokens": usage["output_tokens"],
                    }
                    debug_success(
                        "session",
                        "Extracted usage metadata from _usage",
                        input_tokens=usage["input_tokens"],
                        output_tokens=usage["output_tokens"],
                    )
        except Exception as e:
            logger.debug(f"Could not extract usage metadata from client: {e}")

        # Persist usage metadata to token_stats.json if available
        if usage_metadata:
            # Map LogPhase to PhaseType
            phase_type_map = {
                LogPhase.PLANNING: "planning",
                LogPhase.CODING: "coding",
                LogPhase.VALIDATION: "validation",
            }
            phase_type = phase_type_map.get(
                phase, "coding"
            )  # Default to coding if unknown

            try:
                saved = save_token_stats(
                    spec_dir,
                    phase_type,
                    usage_metadata["input_tokens"],
                    usage_metadata["output_tokens"],
                )
                if saved:
                    print_status(
                        f"Token usage recorded: {usage_metadata['input_tokens']} in, {usage_metadata['output_tokens']} out",
                        "info",
                    )
            except Exception as e:
                logger.warning(f"Failed to persist token stats: {e}")

        # Update conversation history with usage metadata and save
        if usage_metadata:
            current_round.set_usage(
                usage_metadata["input_tokens"], usage_metadata["output_tokens"]
            )
        conversation_history.save()

        # Check if build is complete
        if is_build_complete(spec_dir):
            debug_success(
                "session",
                "Session completed - build is complete",
                message_count=message_count,
                tool_count=tool_count,
                response_length=len(response_text),
            )
            return "complete", response_text, usage_metadata, decision_tracker

        debug_success(
            "session",
            "Session completed - continuing",
            message_count=message_count,
            tool_count=tool_count,
            response_length=len(response_text),
        )
        return "continue", response_text, usage_metadata, decision_tracker

    except Exception as e:
        debug_error(
            "session",
            f"Session error: {e}",
            exception_type=type(e).__name__,
            message_count=message_count,
            tool_count=tool_count,
        )
        print(f"Error during agent session: {e}")
        if task_logger:
            task_logger.log_error(f"Session error: {e}", phase)
        # Save conversation history even on error for debugging
        try:
            conversation_history.save()
        except Exception as save_err:
            logger.debug(f"Failed to save conversation history after error: {save_err}")
        return "error", str(e), None, decision_tracker


async def run_agent_session_isolated(
    project_dir: Path,
    spec_dir: Path,
    agent_type: str,
    model: str,
    starting_message: str,
    system_prompt: str | None = None,
    max_thinking_tokens: int | None = None,
    session_name: str = "agent-session",
    limits: ResourceLimits | None = None,
) -> tuple[str, str, dict[str, int] | None]:
    """
    Run an agent session in an isolated subprocess with resource limits.

    This provides crash-resistant execution by running the agent in a separate
    process with controlled resource usage. If the agent crashes, the main
    process remains unaffected.

    Args:
        project_dir: Root directory of the project
        spec_dir: Spec directory path
        agent_type: Type of agent to run (coder, planner, qa_reviewer, qa_fixer)
        model: Claude model to use
        starting_message: The prompt to send to the agent
        system_prompt: Optional custom system prompt
        max_thinking_tokens: Optional thinking token limit
        session_name: Name for the agent session
        limits: Optional resource limits (defaults to ResourceLimits())

    Returns:
        (status, response_text, usage_metadata) where:
        - status: "continue", "complete", or "error"
        - response_text: The agent's response or error message
        - usage_metadata: Dict with "input_tokens" and "output_tokens" keys (or None)

    Raises:
        AgentProcessError: If subprocess execution fails critically
    """
    debug_section(
        "session", f"Isolated Agent Session - {agent_type} (process isolation)"
    )
    debug(
        "session",
        "Starting isolated agent session",
        project_dir=str(project_dir),
        spec_dir=str(spec_dir),
        agent_type=agent_type,
        model=model,
        session_name=session_name,
    )

    # Initialize process isolator with resource limits
    isolator = AgentProcessIsolator(project_dir=project_dir, limits=limits)

    # Build command-line arguments for subprocess
    import sys

    agent_script = Path(__file__).parent / "agent_subprocess.py"

    if not agent_script.exists():
        error_msg = f"Agent subprocess script not found: {agent_script}"
        debug_error("session", error_msg)
        return "error", error_msg, None

    args = [
        "--project-dir",
        str(project_dir),
        "--spec-dir",
        str(spec_dir),
        "--agent-type",
        agent_type,
        "--model",
        model,
        "--message",
        starting_message,
        "--session-name",
        session_name,
    ]

    if system_prompt:
        args.extend(["--system-prompt", system_prompt])

    if max_thinking_tokens:
        args.extend(["--max-thinking-tokens", str(max_thinking_tokens)])

    debug_verbose(
        "session",
        "Executing agent in isolated subprocess",
        script=agent_script.name,
        args=args,
    )

    # Execute agent in isolated subprocess
    print(
        f"Running {agent_type} agent in isolated subprocess (resource-limited)...\n"
    )

    try:
        result: AgentIsolationResult = isolator.execute_agent(
            agent_script=str(agent_script),
            agent_args=args,
            working_dir=project_dir,
        )

        debug(
            "session",
            "Subprocess execution completed",
            success=result.success,
            return_code=result.return_code,
            execution_time=result.execution_time,
            violated_limits=result.violated_limits,
        )

        # Handle execution results
        if not result.success:
            error_details = []

            if result.crashed:
                error_details.append(f"Agent process crashed (exit code: {result.return_code})")

            if result.violated_limits:
                limits_str = ", ".join(result.violated_limits)
                error_details.append(f"Resource limits exceeded: {limits_str}")

            if result.error:
                error_details.append(f"Error: {result.error}")

            if result.stderr:
                error_details.append(f"stderr: {result.stderr[:500]}")

            error_msg = "\n".join(error_details)
            debug_error("session", "Isolated agent session failed", error=error_msg)
            print(f"\n[ERROR] Agent subprocess failed:\n{error_msg}\n")

            return "error", error_msg, None

        # Parse agent output from JSON
        if result.agent_output:
            debug_success(
                "session",
                "Agent subprocess completed successfully",
                execution_time=result.execution_time,
            )

            agent_success = result.agent_output.get("success", False)
            agent_output = result.agent_output.get("output", {})
            agent_error = result.agent_output.get("error")

            if not agent_success:
                error_msg = agent_error or "Agent session failed (no error message)"
                debug_error("session", "Agent reported failure", error=error_msg)
                print(f"\n[ERROR] Agent session failed: {error_msg}\n")
                return "error", error_msg, None

            # Extract response from agent output
            response_text = ""
            if isinstance(agent_output, dict):
                response_text = agent_output.get("response", "")
            elif isinstance(agent_output, str):
                response_text = agent_output
            else:
                response_text = str(agent_output)

            # Note: Usage metadata not currently available from subprocess
            # This would require extending agent_subprocess.py to capture and return it
            usage_metadata = None

            print(
                f"\n✓ Agent subprocess completed successfully "
                f"(execution time: {result.execution_time:.1f}s)\n"
            )

            # For subprocess execution, we consider it "complete" since it ran to completion
            return "complete", response_text, usage_metadata

        else:
            # No JSON output but success - treat stdout as response
            debug_warning(
                "session",
                "Agent subprocess succeeded but produced no JSON output",
                stdout_length=len(result.stdout),
            )
            return "complete", result.stdout, None

    except AgentProcessError as e:
        error_msg = f"Process isolation error: {e}"
        debug_error("session", error_msg, exception_type=type(e).__name__)
        print(f"\n[ERROR] {error_msg}\n")
        return "error", error_msg, None

    except Exception as e:
        error_msg = f"Unexpected error in isolated session: {e}"
        debug_error(
            "session",
            error_msg,
            exception_type=type(e).__name__,
            traceback=str(e),
        )
        print(f"\n[ERROR] {error_msg}\n")
        return "error", error_msg, None
