"""
Coder Agent Module
==================

Main autonomous agent loop that runs the coder agent to implement subtasks.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from context.constants import SKIP_DIRS
from core.file_utils import write_json_atomic
from core.model_fallback import MODEL_FALLBACK_CHAIN
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig
from core.providers.factory import create_engine_provider
from core.providers.task_router import TaskComplexityRouter
from linear_updater import (
    LinearTaskState,
    is_linear_enabled,
    linear_build_complete,
    linear_task_started,
    linear_task_stuck,
)
from notifications import notify_stuck_subtask
from phase_config import (
    get_phase_model,
    get_phase_thinking_budget,
    is_phase_model_locked,
    resolve_model_id,
)
from phase_event import ExecutionPhase, emit_phase
from progress import (
    count_subtasks,
    count_subtasks_detailed,
    get_current_phase,
    get_next_subtask,
    is_build_complete,
    print_build_complete_banner,
    print_progress_summary,
    print_session_header,
    reset_subtask_to_pending,
)
from prompts_pkg.prompt_generator import (
    format_context_for_prompt,
    generate_planner_prompt,
    generate_subtask_prompt,
    load_subtask_context,
)
from recovery import RecoveryAction, RecoveryManager
from security.constants import PROJECT_DIR_ENV_VAR
from task_logger import (
    LogPhase,
    get_task_logger,
)
from ui import (
    BuildState,
    Icons,
    StatusManager,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_key_value,
    print_status,
)

from .base import AUTO_CONTINUE_DELAY_SECONDS, HUMAN_INTERVENTION_FILE
from .memory_manager import (
    debug_memory_system_status,
    get_failure_patterns,
    get_graphiti_context,
    get_pattern_suggestions,
)
from .runtime import (
    RuntimeCapabilityError,
    create_runtime_session,
    get_runtime_mode,
    requirements_for_runtime_mode,
    resolve_runtime_mode_with_fallback,
    resolve_runtime_runner_route,
    run_runtime_session,
    runtime_fallback_enabled,
)
from .runtime.artifacts import (
    save_analysis_only_artifact,
    save_runtime_fallback_artifact,
    save_runtime_runner_route_artifact,
)
from .session import (
    post_session_processing,
    run_agent_session,
    run_agent_session_isolated,
    save_token_stats,
)
from .utils import (
    find_phase_for_subtask,
    find_subtask_in_plan,
    get_commit_count,
    get_latest_commit,
    load_implementation_plan,
    sync_spec_to_source,
)

# Import plugin system for agent lifecycle hooks
try:
    from plugins.base import PluginType
    from plugins.registry import PluginRegistry
    from plugins.sdk.agent import AgentContext

    PLUGINS_AVAILABLE = True
except ImportError:
    PLUGINS_AVAILABLE = False

# Import for context window usage display
try:
    from context.token_estimator import TokenEstimator

    TOKEN_ESTIMATOR_AVAILABLE = True
except ImportError:
    TOKEN_ESTIMATOR_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# FILE VALIDATION UTILITIES
# =============================================================================

# Directories to exclude from file path search — extends context.constants.SKIP_DIRS
_EXCLUDE_DIRS = frozenset(SKIP_DIRS | {".auto-claude", ".tox", "out"})


def _build_file_index(
    project_dir: Path, suffixes: set[str]
) -> dict[str, list[tuple[str, Path]]]:
    """Build an index of project files grouped by basename, scanning the tree once.

    Also indexes index.{ext} files under their parent directory name as a
    secondary key (e.g., api/index.ts is indexed under both "index.ts" and
    "api" as directory-stem).
    """
    index: dict[str, list[tuple[str, Path]]] = {}
    resolved_str = str(project_dir.resolve())

    for root, dirs, files in os.walk(project_dir.resolve()):
        dirs[:] = [d for d in dirs if d not in _EXCLUDE_DIRS]

        for filename in files:
            ext_idx = filename.rfind(".")
            if ext_idx == -1:
                continue
            file_suffix = filename[ext_idx:]
            if file_suffix not in suffixes:
                continue

            full_path = os.path.join(root, filename)
            rel_str = os.path.relpath(full_path, resolved_str).replace(os.sep, "/")
            rel_path = Path(rel_str)

            index.setdefault(filename, []).append((rel_str, rel_path))

            stem_part = filename[:ext_idx]
            if stem_part == "index":
                dir_name = os.path.basename(root)
                key = f"__dir_stem__:{dir_name}{file_suffix}"
                index.setdefault(key, []).append((rel_str, rel_path))

    return index


def _score_and_select(candidates: list[tuple[str, float]]) -> str | None:
    """Select the best candidate from a scored list.

    Requires a minimum score of 8.0 and a gap of at least 3.0 from the
    runner-up to avoid ambiguous matches.
    """
    if not candidates:
        return None

    candidates.sort(key=lambda x: x[1], reverse=True)
    best_path, best_score = candidates[0]

    if best_score < 8.0:
        return None

    if len(candidates) > 1:
        runner_up_score = candidates[1][1]
        if best_score - runner_up_score < 3.0:
            return None

    return best_path


def _find_correct_path_indexed(
    missing_path: str,
    parent_parts: tuple[str, ...],
    file_index: dict[str, list[tuple[str, Path]]],
) -> str | None:
    """Find the correct path using a pre-built file index (no tree walk needed)."""
    missing = Path(missing_path)
    basename = missing.name
    stem = missing.stem
    suffix = missing.suffix

    if not suffix:
        return None

    candidates: list[tuple[str, float]] = []

    # Strategy 1: Exact basename match
    for rel_str, rel_path in file_index.get(basename, []):
        score = 10.0
        candidate_parts = rel_path.parent.parts
        for i, part in enumerate(parent_parts):
            if i < len(candidate_parts) and candidate_parts[i] == part:
                score += 3.0
        depth_diff = abs(len(candidate_parts) - len(parent_parts))
        score -= 0.5 * depth_diff
        candidates.append((rel_str, score))

    # Strategy 2: index.{ext} in directory matching stem
    stem_key = f"__dir_stem__:{stem}{suffix}"
    for rel_str, rel_path in file_index.get(stem_key, []):
        score = 8.0
        candidate_parts = rel_path.parent.parts
        for i, part in enumerate(parent_parts):
            if i < len(candidate_parts) and candidate_parts[i] == part:
                score += 3.0
        depth_diff = abs(len(candidate_parts) - len(parent_parts))
        score -= 0.5 * depth_diff
        candidates.append((rel_str, score))

    return _score_and_select(candidates)


def _find_correct_path(missing_path: str, project_dir: Path) -> str | None:
    """Attempt to find the correct path for a missing file using fuzzy matching.

    Strategies:
    1. Same basename in nearby directory
    2. index.{ext} pattern (e.g., preload/api.ts -> preload/api/index.ts)
    """
    missing = Path(missing_path)
    basename = missing.name
    stem = missing.stem
    suffix = missing.suffix
    parent_parts = missing.parent.parts

    if not suffix:
        return None

    candidates: list[tuple[str, float]] = []
    resolved_project = project_dir.resolve()
    resolved_str = str(resolved_project)

    for root, dirs, files in os.walk(resolved_project):
        dirs[:] = [d for d in dirs if d not in _EXCLUDE_DIRS]

        for filename in files:
            if not filename.endswith(suffix):
                continue

            full_path = os.path.join(root, filename)
            rel_str = os.path.relpath(full_path, resolved_str).replace(os.sep, "/")
            rel = Path(rel_str)

            score = 0.0

            if filename == basename:
                score += 10.0
            elif filename == f"index{suffix}" and os.path.basename(root) == stem:
                score += 8.0
            else:
                continue

            candidate_parts = rel.parent.parts
            for i, part in enumerate(parent_parts):
                if i < len(candidate_parts) and candidate_parts[i] == part:
                    score += 3.0

            depth_diff = abs(len(candidate_parts) - len(parent_parts))
            score -= 0.5 * depth_diff

            candidates.append((rel_str, score))

    return _score_and_select(candidates)


def _auto_correct_subtask_files(
    subtask: dict,
    missing_files: list[str],
    project_dir: Path,
    spec_dir: Path,
) -> list[str]:
    """Attempt to auto-correct missing file paths in a subtask.

    Corrects paths in-memory AND persists changes to implementation_plan.json.

    Returns:
        List of file paths that could NOT be corrected
    """
    corrections: dict[str, str] = {}
    still_missing: list[str] = []

    suffixes_needed: set[str] = set()
    for missing_path in missing_files:
        suffix = Path(missing_path).suffix
        if suffix:
            suffixes_needed.add(suffix)
    file_index = (
        _build_file_index(project_dir, suffixes_needed) if suffixes_needed else {}
    )

    for missing_path in missing_files:
        missing = Path(missing_path)
        corrected = _find_correct_path_indexed(
            missing_path, missing.parent.parts, file_index
        )
        if corrected:
            corrections[missing_path] = corrected
            logger.info(f"Auto-corrected file path: {missing_path} -> {corrected}")
            print_status(f"Auto-corrected: {missing_path} -> {corrected}", "success")
        else:
            still_missing.append(missing_path)

    if not corrections:
        return still_missing

    # Update subtask in-memory
    files_to_modify = subtask.get("files_to_modify", [])
    subtask["files_to_modify"] = [corrections.get(f, f) for f in files_to_modify]

    # Persist corrections to implementation_plan.json
    plan_file = spec_dir / "implementation_plan.json"
    if plan_file.exists():
        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            subtask_id = subtask.get("id")
            if subtask_id is not None:
                plan_subtask = find_subtask_in_plan(plan, subtask_id)
                if plan_subtask:
                    plan_files = plan_subtask.get("files_to_modify", [])
                    plan_subtask["files_to_modify"] = [
                        corrections.get(f, f) for f in plan_files
                    ]

            write_json_atomic(plan_file, plan)
            logger.info(
                f"Persisted {len(corrections)} path correction(s) to implementation_plan.json"
            )
        except (OSError, TypeError, ValueError) as e:
            logger.warning(f"Failed to persist path corrections: {e}")

    return still_missing


def _validate_plan_file_paths(spec_dir: Path, project_dir: Path) -> str | None:
    """Validate all file paths in the implementation plan after planning.

    Returns a retry context string for the planner if uncorrectable paths remain,
    or None if all paths are valid.
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return None

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    resolved_project = project_dir.resolve()

    missing_entries: list[tuple[list[str], int, str]] = []
    suffixes_needed: set[str] = set()

    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            files = subtask.get("files_to_modify", [])
            for i, file_path in enumerate(files):
                full_path = (resolved_project / file_path).resolve()
                if not full_path.is_relative_to(resolved_project):
                    continue
                if full_path.exists():
                    continue

                missing = Path(file_path)
                if missing.suffix:
                    suffixes_needed.add(missing.suffix)
                    missing_entries.append((files, i, file_path))

    if not missing_entries:
        return None

    file_index = _build_file_index(project_dir, suffixes_needed)

    all_missing: list[str] = []
    corrections_made = 0

    for files_list, idx, file_path in missing_entries:
        missing = Path(file_path)
        corrected = _find_correct_path_indexed(
            file_path, missing.parent.parts, file_index
        )
        if corrected:
            files_list[idx] = corrected
            corrections_made += 1
            logger.info(f"Post-plan auto-corrected: {file_path} -> {corrected}")
            print_status(f"Auto-corrected: {file_path} -> {corrected}", "success")
        else:
            all_missing.append(file_path)

    if corrections_made > 0:
        try:
            write_json_atomic(plan_file, plan)
            logger.info(f"Persisted {corrections_made} post-plan path correction(s)")
        except (OSError, TypeError, ValueError) as e:
            logger.warning(f"Failed to persist post-plan corrections: {e}")

    if not all_missing:
        return None

    return (
        "## FILE PATH VALIDATION ERRORS\n\n"
        "The following files referenced in your implementation plan do NOT exist "
        "and could not be auto-corrected:\n"
        + "\n".join(f"- `{p}`" for p in all_missing)
        + "\n\nPlease fix these file paths in the `implementation_plan.json`.\n"
        "Use the project's actual file structure to find the correct paths.\n"
        "Common issues: wrong directory nesting, missing index files "
        "(e.g., `dir/file.ts` should be `dir/file/index.ts`)."
    )


def validate_subtask_files(
    subtask: dict, project_dir: Path, spec_dir: Path | None = None
) -> dict:
    """Validate all files_to_modify exist before subtask execution.

    Returns dict with success status, missing_files, and invalid_paths.
    If spec_dir is provided, attempts auto-correction of wrong paths.
    """
    files_to_modify = subtask.get("files_to_modify", [])
    if not files_to_modify:
        return {"success": True, "missing_files": [], "invalid_paths": []}

    resolved_project = project_dir.resolve()
    missing_files = []
    invalid_paths = []

    for file_path in files_to_modify:
        full_path = (resolved_project / file_path).resolve()
        if not full_path.is_relative_to(resolved_project):
            invalid_paths.append(file_path)
            continue
        if not full_path.exists():
            missing_files.append(file_path)

    if invalid_paths:
        return {
            "success": False,
            "error": f"Path traversal detected: {', '.join(invalid_paths)}",
            "missing_files": missing_files,
            "invalid_paths": invalid_paths,
        }

    if missing_files:
        # Attempt auto-correction if spec_dir is provided
        if spec_dir:
            still_missing = _auto_correct_subtask_files(
                subtask, missing_files, project_dir, spec_dir
            )
            if not still_missing:
                return {"success": True, "missing_files": [], "invalid_paths": []}
            missing_files = still_missing

        return {
            "success": False,
            "error": f"Planned files do not exist: {', '.join(missing_files)}",
            "missing_files": missing_files,
            "invalid_paths": [],
        }

    return {"success": True, "missing_files": [], "invalid_paths": []}


def _mark_runtime_subtask_completed(
    spec_dir: Path,
    subtask_id: str,
    completed_by: str,
) -> bool:
    """Mark a subtask completed after a limited local runtime applies changes."""
    plan_file = spec_dir / "implementation_plan.json"
    plan = load_implementation_plan(spec_dir)
    if not plan:
        return False

    subtask = find_subtask_in_plan(plan, subtask_id)
    if not subtask:
        return False

    subtask["status"] = "completed"
    subtask["completed_by"] = completed_by

    try:
        from datetime import UTC, datetime

        subtask["completed_at"] = datetime.now(UTC).isoformat()
    except (OSError, OverflowError, ValueError):
        logger.debug(
            "Unable to timestamp runtime completion for subtask %s",
            subtask_id,
            exc_info=True,
        )

    for phase in plan.get("phases", []):
        subtasks = phase.get("subtasks", [])
        if subtasks and all(item.get("status") == "completed" for item in subtasks):
            phase["status"] = "completed"

    try:
        write_json_atomic(plan_file, plan, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to persist runtime subtask completion: %s", e)
        return False
    return True


def _mark_patch_subtask_completed(spec_dir: Path, subtask_id: str) -> bool:
    """Mark a subtask completed after Auto Code applies a patch proposal."""
    return _mark_runtime_subtask_completed(
        spec_dir,
        subtask_id,
        completed_by="patch_proposal",
    )


def _display_context_window_usage(
    context: dict,
    subtask_id: str | None = None,
) -> None:
    """
    Display context window usage information to the user.

    This provides transparency about what files are included in the context
    and the estimated token usage, helping users understand the scope of
    information being provided to the AI agent.

    Args:
        context: Context dict from load_subtask_context
        subtask_id: Optional subtask ID for more detailed display
    """
    if not TOKEN_ESTIMATOR_AVAILABLE:
        return

    pattern_files = list(context.get("patterns", {}).keys())
    files_to_modify = list(context.get("files_to_modify", {}).keys())
    total_files = len(pattern_files) + len(files_to_modify)

    if total_files == 0:
        return

    token_estimator = TokenEstimator()

    pattern_tokens = sum(
        token_estimator.count_tokens(context["patterns"][f]) for f in pattern_files
    )
    modify_tokens = sum(
        token_estimator.count_tokens(context["files_to_modify"][f])
        for f in files_to_modify
    )
    total_tokens = pattern_tokens + modify_tokens

    status_level = _get_context_status_level(total_tokens)

    print()
    print_status("Context Window Usage", status_level)
    print_key_value("Total Files", str(total_files))
    print_key_value("Estimated Tokens", f"{total_tokens:,}")
    print_key_value(
        "Pattern Files", f"{len(pattern_files)} ({pattern_tokens:,} tokens)"
    )
    print_key_value(
        "Files to Modify", f"{len(files_to_modify)} ({modify_tokens:,} tokens)"
    )

    _print_context_warnings(total_tokens)

    max_context = 200_000
    percentage = (total_tokens / max_context) * 100
    print_key_value("Context Usage", f"{percentage:.1f}%")

    if subtask_id:
        _print_context_file_list(pattern_files, files_to_modify)

    print()


def _get_context_status_level(total_tokens: int) -> str:
    """Return status level string based on token count."""
    if total_tokens > 150_000:
        return "error"
    if total_tokens > 100_000:
        return "warning"
    return "success"


def _print_context_warnings(total_tokens: int) -> None:
    """Print warning messages if context is too large."""
    if total_tokens > 150_000:
        print()
        print_status(
            f"⚠️ Context window is critically large ({total_tokens:,} tokens). "
            f"This may impact performance or exceed model limits.",
            "error",
        )
    elif total_tokens > 100_000:
        print()
        print_status(
            f"⚠️ Context window is large ({total_tokens:,} tokens). "
            f"Consider reducing file count or using summaries.",
            "warning",
        )


def _print_context_file_list(
    pattern_files: list[str], files_to_modify: list[str]
) -> None:
    """Print the list of files included in context."""
    print()
    print(muted("Files included in context:"))
    for label, files in [
        ("Pattern files", pattern_files),
        ("Files to modify", files_to_modify),
    ]:
        if not files:
            continue
        print(muted(f"  {label}:"))
        for f in files[:5]:
            print(muted(f"    - {f}"))
        if len(files) > 5:
            print(muted(f"    ... and {len(files) - 5} more"))


async def run_autonomous_agent(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    max_iterations: int | None = None,
    verbose: bool = False,
    source_spec_dir: Path | None = None,
    restart_from: str | None = None,
) -> None:
    """
    Run the autonomous agent loop with automatic memory management.

    The agent can use subagents (via Task tool) for parallel execution if needed.
    This is decided by the agent itself based on the task complexity.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec (auto-claude/specs/001-name/)
        model: Claude model to use
        max_iterations: Maximum number of iterations (None for unlimited)
        verbose: Whether to show detailed output
        source_spec_dir: Original spec directory in main project (for syncing from worktree)
        restart_from: Subtask ID to restart from (None for normal execution)
    """
    # Set environment variable for security hooks to find the correct project directory
    # This is needed because os.getcwd() may return the wrong directory in worktree mode
    os.environ[PROJECT_DIR_ENV_VAR] = str(project_dir.resolve())

    # Initialize recovery manager (handles memory persistence)
    recovery_manager = RecoveryManager(spec_dir, project_dir)

    # Initialize status manager for ccstatusline
    status_manager = StatusManager(project_dir)
    status_manager.set_active(spec_dir.name, BuildState.BUILDING)

    # Initialize task logger for persistent logging
    task_logger = get_task_logger(spec_dir)

    # Debug: Print memory system status at startup
    debug_memory_system_status()

    # Update initial subtask counts
    subtasks = count_subtasks_detailed(spec_dir)
    status_manager.update_subtasks(
        completed=subtasks["completed"],
        total=subtasks["total"],
        in_progress=subtasks["in_progress"],
    )

    # Check Linear integration status
    linear_task = None
    if is_linear_enabled():
        linear_task = LinearTaskState.load(spec_dir)
        if linear_task and linear_task.task_id:
            print_status("Linear integration: ENABLED", "success")
            print_key_value("Task", linear_task.task_id)
            print_key_value("Status", linear_task.status)
            print()
        else:
            print_status("Linear enabled but no task created for this spec", "warning")
            print()

    # Check if this is a fresh start or continuation
    # Lazy import to avoid circular import: prompts_pkg → agents → coder → prompts_pkg
    from prompts_pkg.prompts import is_first_run

    first_run = is_first_run(spec_dir)

    # Restore provider config if restarting
    if restart_from:
        try:
            from core.providers.config import get_provider_config
            from implementation_plan import ImplementationPlan

            plan_file = spec_dir / "implementation_plan.json"
            if plan_file.exists():
                plan = ImplementationPlan.load(plan_file)
                if plan.provider_config:
                    # Restore provider and model from saved config
                    provider_config = get_provider_config()
                    saved_provider = plan.provider_config.get("provider")
                    saved_model = plan.provider_config.get("model")

                    if saved_provider:
                        os.environ["AI_ENGINE_PROVIDER"] = saved_provider
                        logger.info(f"Restored provider from config: {saved_provider}")
                    if saved_model:
                        # Restore model via provider-specific env var
                        model_env_map = {
                            "claude": "CLAUDE_MODEL",
                            "litellm": "LITELLM_MODEL",
                            "openrouter": "OPENROUTER_MODEL",
                            "zhipuai": "ZHIPUAI_MODEL",
                        }
                        env_key = model_env_map.get(
                            saved_provider or provider_config.provider
                        )
                        if env_key:
                            os.environ[env_key] = saved_model
                        logger.info(f"Restored model from config: {saved_model}")
        except Exception as e:
            logger.warning(f"Failed to restore provider config: {e}")

    # Track which phase we're in for logging
    current_log_phase = LogPhase.CODING
    is_planning_phase = False
    planning_retry_context: str | None = None
    planning_validation_failures = 0
    max_planning_validation_retries = 3

    # Track recovery state for enhanced recovery
    pending_recovery_action: RecoveryAction | None = None
    override_model: str | None = None  # For model fallback
    recovery_guidance: str | None = None  # Strategy guidance for next attempt

    def _validate_and_fix_implementation_plan() -> tuple[bool, list[str]]:
        from spec.validate_pkg import SpecValidator, auto_fix_plan

        spec_validator = SpecValidator(spec_dir)
        result = spec_validator.validate_implementation_plan()
        if result.valid:
            return True, []

        fixed = auto_fix_plan(spec_dir)
        if fixed:
            result = spec_validator.validate_implementation_plan()
            if result.valid:
                return True, []

        return False, result.errors

    if first_run:
        print_status(
            "Fresh start - will use Planner Agent to create implementation plan", "info"
        )
        content = [
            bold(f"{icon(Icons.GEAR)} PLANNER SESSION"),
            "",
            f"Spec: {highlight(spec_dir.name)}",
            muted("The agent will analyze your spec and create a subtask-based plan."),
        ]
        print()
        print(box(content, width=70, style="heavy"))
        print()

        # Update status for planning phase
        status_manager.update(state=BuildState.PLANNING)
        emit_phase(ExecutionPhase.PLANNING, "Creating implementation plan")
        is_planning_phase = True
        current_log_phase = LogPhase.PLANNING

        # Start planning phase in task logger
        if task_logger:
            task_logger.start_phase(
                LogPhase.PLANNING, "Starting implementation planning..."
            )

        # Update Linear to "In Progress" when build starts
        if linear_task and linear_task.task_id:
            print_status("Updating Linear task to In Progress...", "progress")
            await linear_task_started(spec_dir)
    else:
        print(f"Continuing build: {highlight(spec_dir.name)}")
        print_progress_summary(spec_dir)

        # Check if already complete
        if is_build_complete(spec_dir):
            print_build_complete_banner(spec_dir)
            status_manager.update(state=BuildState.COMPLETE)
            return

        # Start/continue coding phase in task logger
        if task_logger:
            task_logger.start_phase(LogPhase.CODING, "Continuing implementation...")

        # Emit phase event when continuing build
        emit_phase(ExecutionPhase.CODING, "Continuing implementation")

    # Show human intervention hint
    content = [
        bold("INTERACTIVE CONTROLS"),
        "",
        f"Press {highlight('Ctrl+C')} once  {icon(Icons.ARROW_RIGHT)} Pause and optionally add instructions",
        f"Press {highlight('Ctrl+C')} twice {icon(Icons.ARROW_RIGHT)} Exit immediately",
    ]
    print(box(content, width=70, style="light"))
    print()

    # Main loop
    iteration = 0

    while True:
        iteration += 1

        # Clear restart_from after first iteration to continue normally
        if iteration > 1 and restart_from:
            restart_from = None

        # Check for human intervention (PAUSE file)
        pause_file = spec_dir / HUMAN_INTERVENTION_FILE
        if pause_file.exists():
            print("\n" + "=" * 70)
            print("  PAUSED BY HUMAN")
            print("=" * 70)

            pause_content = pause_file.read_text(encoding="utf-8").strip()
            if pause_content:
                print(f"\nMessage: {pause_content}")

            print("\nTo resume, delete the PAUSE file:")
            print(f"  rm {pause_file}")
            print("\nThen run again:")
            print(f"  python auto-claude/run.py --spec {spec_dir.name}")
            return

        # Check max iterations
        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            print("To continue, run the script again without --max-iterations")
            break

        # Get the next subtask to work on (planner sessions shouldn't bind to a subtask)
        next_subtask = None if first_run else get_next_subtask(spec_dir, restart_from)
        subtask_id = next_subtask.get("id") if next_subtask else None

        # Update status for this session
        status_manager.update_session(iteration)
        if next_subtask and next_subtask.get("phase_name"):
            current_phase = get_current_phase(spec_dir)
            if current_phase:
                status_manager.update_phase(
                    current_phase.get("name", ""),
                    current_phase.get("phase", 0),
                    current_phase.get("total", 0),
                )
        status_manager.update_subtasks(in_progress=1)

        # Print session header
        print_session_header(
            session_num=iteration,
            is_planner=first_run,
            subtask_id=subtask_id,
            subtask_desc=next_subtask.get("description") if next_subtask else None,
            phase_name=next_subtask.get("phase_name") if next_subtask else None,
            attempt=recovery_manager.get_attempt_count(subtask_id) + 1
            if subtask_id
            else 1,
        )

        # Capture state before session for post-processing
        commit_before = get_latest_commit(project_dir)
        commit_count_before = get_commit_count(project_dir)

        # === ENHANCED RECOVERY: Handle pending recovery action ===
        if pending_recovery_action:
            # Apply exponential backoff delay if specified
            if pending_recovery_action.wait_seconds > 0:
                print_status(
                    f"Recovery backoff: waiting {pending_recovery_action.wait_seconds:.1f}s before retry...",
                    "progress",
                )
                await asyncio.sleep(pending_recovery_action.wait_seconds)

            # Handle rollback action
            if pending_recovery_action.action == "rollback":
                print_status(
                    f"Rolling back to commit {pending_recovery_action.target[:8]}...",
                    "warning",
                )
                rollback_success = recovery_manager.rollback_to_commit(
                    pending_recovery_action.target
                )
                if rollback_success:
                    print_status("Rollback successful", "success")
                else:
                    print_status("Rollback failed", "error")

            # Display recovery notification if needed
            if pending_recovery_action.should_notify:
                print()
                print_status(pending_recovery_action.notification_message, "warning")
                print()

            # Clear the pending action
            pending_recovery_action = None

        # Get the phase-specific model and thinking level (respects task_metadata.json configuration)
        # first_run means we're in planning phase, otherwise coding phase
        current_phase = "planning" if first_run else "coding"

        # Use override model if set (for model fallback), otherwise use phase model
        if override_model:
            phase_model = resolve_model_id(override_model)
            print_status(f"Using fallback model: {override_model}", "progress")
        else:
            phase_model = get_phase_model(spec_dir, current_phase, model)

        phase_thinking_budget = get_phase_thinking_budget(spec_dir, current_phase)

        # Use appropriate agent_type for correct tool permissions and thinking budget
        agent_type_for_session = "planner" if first_run else "coder"
        provider_config = ProviderConfig.from_env(agent_type=agent_type_for_session)
        requested_runtime_mode = get_runtime_mode(agent_type_for_session)
        route_allowed_providers = None
        if (
            requested_runtime_mode == "full_autonomous"
            and not runtime_fallback_enabled()
        ):
            route_allowed_providers = {"claude", "codex"}

        if (
            next_subtask
            and current_phase == "coding"
            and not override_model
            and model is None
            and not is_phase_model_locked(spec_dir, current_phase)
        ):
            route = TaskComplexityRouter().route(
                next_subtask,
                agent_type=agent_type_for_session,
                provider_config=provider_config,
                allowed_providers=route_allowed_providers,
            )
            provider_config = provider_config.with_provider_model(
                route.provider,
                route.model,
            )
            phase_model = route.model
            print_status(
                f"Smart routing: {route.complexity} -> {route.provider}/{route.model}",
                "info",
            )
            logger.info("Smart routing selected: %s", route)

        runner_route = resolve_runtime_runner_route(
            provider_config=provider_config,
            provider_name=provider_config.provider,
            requested_mode=requested_runtime_mode,
            phase=current_phase,
        )
        if runner_route.route_applied:
            routed_model = provider_config.get_model_for(runner_route.selected_provider)
            if routed_model:
                provider_config = provider_config.with_provider_model(
                    runner_route.selected_provider,
                    routed_model,
                )
                phase_model = routed_model
            print_status(
                f"Runner routing: {runner_route.requested_provider}/"
                f"{runner_route.requested_mode} -> "
                f"{runner_route.selected_provider}/{runner_route.runner_id}",
                "warning",
            )
            logger.info("Runtime runner route selected: %s", runner_route.to_dict())
            route_artifact = save_runtime_runner_route_artifact(
                spec_dir=spec_dir,
                route=runner_route,
                phase=current_phase,
                session_num=iteration,
                subtask_id=subtask_id,
            )
            print_status(f"Runner route details: {route_artifact}", "info")

        # Filled after provider/runtime resolution so plugin hooks can see the
        # runtime context client before the session starts.
        client = None
        runtime_metadata: dict[str, object] = {
            "task": "Create implementation plan from the current spec"
            if first_run
            else "",
            "phase_name": current_phase,
        }

        # Generate appropriate prompt
        if first_run:
            prompt = generate_planner_prompt(spec_dir, project_dir)
            if planning_retry_context:
                prompt += "\n\n" + planning_retry_context

            # Retrieve Graphiti memory context for planning phase
            # This gives the planner knowledge of previous patterns, gotchas, and insights
            planner_context = await get_graphiti_context(
                spec_dir,
                project_dir,
                {
                    "description": "Planning implementation for new feature",
                    "id": "planner",
                },
            )
            if planner_context:
                prompt += "\n\n" + planner_context
                print_status("Graphiti memory context loaded for planner", "success")

            first_run = False
            current_log_phase = LogPhase.PLANNING

            # Set session info in logger
            if task_logger:
                task_logger.set_session(iteration)
        else:
            # Switch to coding phase after planning
            just_transitioned_from_planning = False
            if is_planning_phase:
                just_transitioned_from_planning = True
                is_planning_phase = False
                current_log_phase = LogPhase.CODING
                emit_phase(ExecutionPhase.CODING, "Starting implementation")
                if task_logger:
                    task_logger.end_phase(
                        LogPhase.PLANNING,
                        success=True,
                        message="Implementation plan created",
                    )
                    task_logger.start_phase(
                        LogPhase.CODING, "Starting implementation..."
                    )
                # In worktree mode, the UI prefers planning logs from the main spec dir.
                # Ensure the planning->coding transition is immediately reflected there.
                if sync_spec_to_source(spec_dir, source_spec_dir):
                    print_status("Phase transition synced to main project", "success")

            if not next_subtask:
                # FIX for Issue #495: Race condition after planning phase
                # The implementation_plan.json may not be fully flushed to disk yet,
                # or there may be a brief delay before subtasks become available.
                # Retry with exponential backoff before giving up.
                if just_transitioned_from_planning:
                    print_status(
                        "Waiting for implementation plan to be ready...", "progress"
                    )
                    for retry_attempt in range(3):
                        delay = (retry_attempt + 1) * 2  # 2s, 4s, 6s
                        await asyncio.sleep(delay)
                        next_subtask = get_next_subtask(spec_dir, restart_from)
                        if next_subtask:
                            # Update subtask_id after successful retry
                            subtask_id = next_subtask.get("id")
                            print_status(
                                f"Found subtask {subtask_id} after {delay}s delay",
                                "success",
                            )
                            break
                        print_status(
                            f"Retry {retry_attempt + 1}/3: No subtask found yet...",
                            "warning",
                        )

                if not next_subtask:
                    print("No pending subtasks found - build may be complete!")
                    break

            # Validate that all files_to_modify exist before attempting execution
            # This prevents infinite retry loops when implementation plan references non-existent files
            # Pass spec_dir to enable auto-correction of wrong paths
            validation_result = validate_subtask_files(
                next_subtask, project_dir, spec_dir
            )
            if not validation_result["success"]:
                # File validation failed - record error and skip session
                error_msg = validation_result["error"]
                attempt_count = recovery_manager.get_attempt_count(subtask_id)
                recovery_manager.record_attempt(
                    subtask_id, iteration, False, "file_validation", error_msg
                )
                print_status(f"File validation failed: {error_msg}", "error")

                if attempt_count >= 2:
                    recovery_manager.mark_subtask_stuck(
                        subtask_id,
                        f"File validation failed after {attempt_count} attempts: {error_msg}",
                    )
                    emit_phase(
                        ExecutionPhase.FAILED,
                        f"Subtask {subtask_id} stuck: file validation failed",
                        subtask=subtask_id,
                    )
                    print_status(
                        f"Subtask {subtask_id} marked as STUCK after {attempt_count} failed validation attempts",
                        "error",
                    )

                first_run = False
                continue

            # Get attempt count for recovery context
            attempt_count = recovery_manager.get_attempt_count(subtask_id)
            recovery_hints = (
                recovery_manager.get_recovery_hints(subtask_id)
                if attempt_count > 0
                else None
            )

            # Find the phase for this subtask
            plan = load_implementation_plan(spec_dir)
            phase = find_phase_for_subtask(plan, subtask_id) if plan else {}

            # Retrieve pattern suggestions for this subtask
            subtask_description = next_subtask.get("description", "")
            pattern_suggestions = await get_pattern_suggestions(
                spec_dir=spec_dir,
                project_dir=project_dir,
                query=subtask_description,
            )

            # Retrieve failure patterns for retries (learn from past failures)
            failure_patterns = None
            if attempt_count > 0:
                failure_patterns = await get_failure_patterns(
                    spec_dir=spec_dir,
                    project_dir=project_dir,
                    query=subtask_description,
                    num_results=3,  # Get top 3 most relevant failure patterns
                )
                if failure_patterns:
                    print_status(
                        "Failure pattern context loaded for recovery", "success"
                    )

            # Generate focused, minimal prompt for this subtask
            prompt = generate_subtask_prompt(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask=next_subtask,
                phase=phase or {},
                attempt_count=attempt_count,
                recovery_hints=recovery_hints,
                pattern_suggestions=pattern_suggestions,
            )
            runtime_metadata = {
                "task": subtask_description,
                "files": [
                    str(file_path)
                    for file_path in next_subtask.get("files_to_modify", [])
                    if file_path
                ],
                "subtask_id": subtask_id,
                "phase_name": phase.get("name") or next_subtask.get("phase_name"),
                "attempt": attempt_count,
            }

            # Add recovery strategy guidance if available
            if recovery_guidance:
                prompt += f"\n\n## RECOVERY STRATEGY\n\n{recovery_guidance}\n"
                # Clear the guidance after using it
                recovery_guidance = None

            # Add failure patterns for retries (learn from past similar failures)
            if failure_patterns:
                prompt += f"\n\n{failure_patterns}\n"

            # Load and append relevant file context
            context = load_subtask_context(spec_dir, project_dir, next_subtask)
            if context.get("patterns") or context.get("files_to_modify"):
                prompt += "\n\n" + format_context_for_prompt(context)

                # Display context window usage for transparency
                _display_context_window_usage(context, subtask_id)

            # Retrieve and append Graphiti memory context (if enabled)
            graphiti_context = await get_graphiti_context(
                spec_dir, project_dir, next_subtask
            )
            if graphiti_context:
                prompt += "\n\n" + graphiti_context
                print_status("Graphiti memory context loaded", "success")

            # Show what we're working on
            print(f"Working on: {highlight(subtask_id)}")
            print(f"Description: {next_subtask.get('description', 'No description')}")
            if attempt_count > 0:
                print_status(f"Previous attempts: {attempt_count}", "warning")
            print()

        # Set subtask info in logger
        if task_logger and subtask_id:
            task_logger.set_subtask(subtask_id)
            task_logger.set_session(iteration)

        # Check if process isolation is enabled. Provider/runtime resolution
        # happens before plugin hooks so hooks see the active runtime client in
        # non-isolated mode.
        use_process_isolation = (
            os.getenv("AGENT_PROCESS_ISOLATION", "").lower() == "true"
        )
        analysis_only_terminal_message: str | None = None

        provider = create_engine_provider(provider_config)
        runtime_phase = (
            "planning" if current_log_phase == LogPhase.PLANNING else "coding"
        )
        runtime_decision = resolve_runtime_mode_with_fallback(
            provider_name=provider.name,
            requested_mode=requested_runtime_mode,
            phase=runtime_phase,
        )
        runtime_mode = runtime_decision.selected_mode
        if runtime_decision.fallback_applied:
            logger.warning("[RUNTIME FALLBACK] %s", runtime_decision.reason)
            fallback_artifact = save_runtime_fallback_artifact(
                spec_dir=spec_dir,
                decision=runtime_decision,
                phase=runtime_phase,
                session_num=iteration,
                subtask_id=subtask_id,
            )
            print_status(
                f"Runtime fallback: {runtime_decision.requested_mode} -> "
                f"{runtime_mode} ({provider.name}); details: {fallback_artifact}",
                "warning",
            )

        if use_process_isolation and (
            provider.name != "claude" or runtime_mode != "full_autonomous"
        ):
            logger.warning(
                "Process isolation disabled for provider=%s runtime=%s",
                provider.name,
                runtime_mode,
            )
            print_status(
                "Process isolation disabled because the selected provider/runtime "
                "must use the in-process runtime engine",
                "warning",
            )
            use_process_isolation = False

        runtime_session = None
        if not use_process_isolation or provider.name == "claude":
            session_config = SessionConfig(
                name=f"{agent_type_for_session}-session-{iteration}",
                model=phase_model,
                extra={
                    "agent_type": agent_type_for_session,
                    "max_thinking_tokens": phase_thinking_budget,
                    "runtime_metadata": runtime_metadata,
                },
            )

            if provider.name == "claude":
                session = provider.create_session(
                    session_config,
                    project_dir=project_dir,
                    spec_dir=spec_dir,
                    agent_type=agent_type_for_session,
                    max_thinking_tokens=phase_thinking_budget,
                )
            else:
                session = provider.create_session(session_config)

            subagent_session_factory = None
            if runtime_mode == "generic_edit":

                def subagent_session_factory(
                    task,
                    *,
                    child_agent_type=agent_type_for_session,
                    child_model=phase_model,
                    child_provider=provider,
                    child_subtask_id=subtask_id,
                    child_thinking_budget=phase_thinking_budget,
                ):
                    child_session_config = SessionConfig(
                        name=f"{child_agent_type}-subagent-{task.id}",
                        model=child_model,
                        extra={
                            "agent_type": child_agent_type,
                            "parent_subtask_id": child_subtask_id,
                            "runtime_subagent_id": task.id,
                            "runtime_metadata": {
                                "task": getattr(task, "description", str(task.id)),
                                "subtask_id": child_subtask_id,
                            },
                        },
                    )
                    if child_provider.name == "claude":
                        child_session = child_provider.create_session(
                            child_session_config,
                            project_dir=project_dir,
                            spec_dir=spec_dir,
                            agent_type=child_agent_type,
                            max_thinking_tokens=child_thinking_budget,
                        )
                    else:
                        child_session = child_provider.create_session(
                            child_session_config
                        )
                    return create_runtime_session(
                        provider_name=child_provider.name,
                        agent_session=child_session,
                        claude_session_runner=run_agent_session,
                        runtime_mode="analysis_only",
                        project_dir=project_dir,
                        agent_type=child_agent_type,
                    )

            runtime_session = create_runtime_session(
                provider_name=provider.name,
                agent_session=session,
                claude_session_runner=run_agent_session,
                runtime_mode=runtime_mode,
                project_dir=project_dir,
                agent_type=agent_type_for_session,
                subagent_session_factory=subagent_session_factory,
            )
            client = runtime_session.context_client

        # Call before_session hook for enabled agent plugins
        if PLUGINS_AVAILABLE:
            try:
                registry = PluginRegistry.get_instance()
                agent_plugins = registry.list_plugins(
                    plugin_type=PluginType.AGENT, enabled_only=True
                )

                if agent_plugins:
                    # Create agent context for plugins
                    agent_context = AgentContext(
                        project_dir=project_dir,
                        spec_dir=spec_dir,
                        session_id=f"session-{iteration}",
                        client=client,
                        phase="planning" if is_planning_phase else "coding",
                        metadata={
                            "subtask_id": subtask_id,
                            "iteration": iteration,
                            "provider": provider.name,
                            "runtime_mode": runtime_mode,
                            "process_isolation": use_process_isolation,
                            "attempt": recovery_manager.get_attempt_count(subtask_id)
                            + 1
                            if subtask_id
                            else 1,
                        },
                    )

                    # Call before_session for each enabled agent plugin
                    for plugin in agent_plugins:
                        try:
                            plugin.before_session(agent_context)
                            logger.debug(
                                f"Called before_session for plugin: {plugin.name}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Plugin {plugin.name} before_session hook failed: {e}"
                            )
            except Exception as e:
                logger.warning(f"Failed to call before_session hooks: {e}")

        if use_process_isolation:
            # Run in isolated subprocess for crash resistance
            if verbose or iteration == 1:
                print_status(
                    "Process isolation: ENABLED (crash-resistant mode)", "info"
                )
            status, response, usage_metadata = await run_agent_session_isolated(
                project_dir=project_dir,
                spec_dir=spec_dir,
                agent_type=agent_type_for_session,
                model=phase_model,
                starting_message=prompt,
                system_prompt=None,
                max_thinking_tokens=phase_thinking_budget,
                session_name=f"{agent_type_for_session}-session-{iteration}",
                limits=None,  # Use default ResourceLimits
            )
        else:
            # Run in current process (legacy mode)
            if runtime_session is None:
                raise RuntimeError("Runtime session was not initialized")
            requirements = requirements_for_runtime_mode(
                runtime_mode,
                phase=runtime_phase,
            )
            try:
                result = await run_runtime_session(
                    runtime_session,
                    prompt,
                    spec_dir,
                    verbose,
                    phase=current_log_phase,
                    requirements=requirements,
                    subtask_id=subtask_id,
                )
            except RuntimeCapabilityError as e:
                logger.error(str(e))
                print_status(str(e), "error")
                if task_logger:
                    task_logger.log_error(str(e), current_log_phase)
                status_manager.update(state=BuildState.ERROR)
                return

            status = result.status
            usage_metadata = result.usage_metadata

            if runtime_mode == "analysis_only" and current_log_phase == LogPhase.CODING:
                artifact_path = save_analysis_only_artifact(
                    spec_dir=spec_dir,
                    response_text=result.response_text,
                    provider_name=provider.name,
                    phase="coding",
                    session_num=iteration,
                    subtask_id=subtask_id,
                )
                analysis_only_terminal_message = (
                    "Analysis-only runtime completed text analysis but cannot "
                    "complete coding subtasks because it has no workspace edit "
                    "or tool capabilities. Saved model output to "
                    f"{artifact_path}. Use patch_proposal for validated diffs "
                    "or Claude/full_autonomous for autonomous coding."
                )
                status = "error"
                status_manager.update(state=BuildState.ERROR)

            if (
                runtime_mode in {"patch_proposal", "generic_edit"}
                and current_log_phase == LogPhase.CODING
                and subtask_id
                and status != "error"
            ):
                if _mark_runtime_subtask_completed(
                    spec_dir,
                    subtask_id,
                    completed_by=runtime_mode,
                ):
                    print_status(
                        f"Marked subtask {subtask_id} completed from {runtime_mode}",
                        "success",
                    )
                    if is_build_complete(spec_dir):
                        status = "complete"
                else:
                    message = (
                        f"{runtime_mode} completed but subtask status could not be "
                        f"updated for {subtask_id}"
                    )
                    logger.error(message)
                    print_status(message, "error")
                    if task_logger:
                        task_logger.log_error(message, current_log_phase)
                    status = "error"
                    status_manager.update(state=BuildState.ERROR)

        # Call after_session hook for enabled agent plugins
        if PLUGINS_AVAILABLE:
            try:
                registry = PluginRegistry.get_instance()
                agent_plugins = registry.list_plugins(
                    plugin_type=PluginType.AGENT, enabled_only=True
                )

                if agent_plugins:
                    # Create agent context for plugins
                    agent_context = AgentContext(
                        project_dir=project_dir,
                        spec_dir=spec_dir,
                        session_id=f"session-{iteration}",
                        client=client,
                        phase="planning" if is_planning_phase else "coding",
                        metadata={
                            "subtask_id": subtask_id,
                            "session": iteration,
                            "status": status,
                        },
                    )

                    # Call after_session for each enabled agent plugin
                    session_success = status != "error"
                    for plugin in agent_plugins:
                        try:
                            plugin.after_session(agent_context, success=session_success)
                            logger.debug(
                                f"Called after_session for plugin: {plugin.name}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Plugin {plugin.name} after_session hook failed: {e}"
                            )
            except Exception as e:
                logger.warning(f"Failed to call after_session hooks: {e}")

        if analysis_only_terminal_message:
            logger.error(analysis_only_terminal_message)
            print_status(analysis_only_terminal_message, "error")
            if task_logger:
                task_logger.log_error(
                    analysis_only_terminal_message,
                    current_log_phase,
                )
            if subtask_id:
                if not reset_subtask_to_pending(spec_dir, subtask_id):
                    logger.error(
                        "Could not reset analysis-only subtask %s to pending in %s",
                        subtask_id,
                        spec_dir,
                    )
                    print_status(
                        f"Could not reset subtask {subtask_id} to pending",
                        "error",
                    )
                recovery_manager.record_attempt(
                    subtask_id=subtask_id,
                    session=iteration,
                    success=False,
                    approach="Analysis-only runtime produced a text artifact",
                    error=analysis_only_terminal_message,
                )
                subtasks = count_subtasks_detailed(spec_dir)
                status_manager.update_subtasks(
                    completed=subtasks["completed"],
                    total=subtasks["total"],
                    in_progress=0,
                )
            if sync_spec_to_source(spec_dir, source_spec_dir):
                print_status("Analysis artifact synced to main project", "success")
            emit_phase(
                ExecutionPhase.FAILED,
                "Analysis-only runtime cannot complete coding subtasks",
                subtask=subtask_id,
            )
            return

        # Save token statistics for coding phase
        if usage_metadata and current_log_phase == LogPhase.CODING:
            try:
                saved = save_token_stats(
                    spec_dir,
                    "coding",
                    usage_metadata["input_tokens"],
                    usage_metadata["output_tokens"],
                )
                if saved:
                    logger.debug(
                        f"Coding phase token stats saved: {usage_metadata['input_tokens']} in, "
                        f"{usage_metadata['output_tokens']} out"
                    )
            except Exception as e:
                logger.warning(f"Failed to save coding phase token stats: {e}")

        plan_validated = False
        if is_planning_phase and status != "error":
            valid, errors = _validate_and_fix_implementation_plan()
            if valid:
                # Persist provider configuration to implementation plan
                try:
                    from core.providers.config import get_provider_config
                    from implementation_plan import ImplementationPlan

                    plan_file = spec_dir / "implementation_plan.json"
                    if plan_file.exists():
                        plan = ImplementationPlan.load(plan_file)
                        provider_config = get_provider_config()
                        if provider_config and not plan.provider_config:
                            plan.provider_config = {
                                "provider": provider_config.provider,
                                "model": provider_config.get_model_for_provider(),
                            }
                            await plan.async_save(plan_file)
                            logger.debug(
                                "Provider config persisted to implementation_plan.json"
                            )
                except Exception as e:
                    logger.warning(f"Failed to persist provider config to plan: {e}")

                # Validate file paths in the newly created plan
                path_issues = _validate_plan_file_paths(spec_dir, project_dir)
                if (
                    path_issues
                    and planning_validation_failures < max_planning_validation_retries
                ):
                    planning_validation_failures += 1
                    planning_retry_context = path_issues
                    print_status(
                        "Plan has invalid file paths - retrying planner",
                        "warning",
                    )
                    first_run = True
                    status = "continue"
                else:
                    if path_issues:
                        logger.warning(
                            f"Plan has uncorrectable file paths after "
                            f"{planning_validation_failures} retries - proceeding anyway"
                        )
                    plan_validated = True
                    planning_retry_context = None
            else:
                planning_validation_failures += 1
                if planning_validation_failures >= max_planning_validation_retries:
                    print_status(
                        "implementation_plan.json validation failed too many times",
                        "error",
                    )
                    for err in errors:
                        print(f"  - {err}")
                    status_manager.update(state=BuildState.ERROR)
                    return

                print_status(
                    "implementation_plan.json invalid - retrying planner", "warning"
                )
                for err in errors:
                    print(f"  - {err}")

                planning_retry_context = (
                    "## IMPLEMENTATION PLAN VALIDATION ERRORS\n\n"
                    "The previous `implementation_plan.json` is INVALID.\n"
                    "You MUST rewrite it to match the required schema:\n"
                    "- Top-level: `feature`, `workflow_type`, `phases`\n"
                    "- Each phase: `id` (or `phase`) and `name`, and `subtasks`\n"
                    "- Each subtask: `id`, `description`, `status` (use `pending` for not started)\n\n"
                    "Validation errors:\n" + "\n".join(f"- {e}" for e in errors)
                )
                # Stay in planning mode for the next iteration
                first_run = True
                status = "continue"

        # === POST-SESSION PROCESSING (100% reliable) ===
        # Only run post-session processing for coding sessions.
        if subtask_id and current_log_phase == LogPhase.CODING:
            linear_is_enabled = (
                linear_task is not None and linear_task.task_id is not None
            )
            success = await post_session_processing(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=iteration,
                commit_before=commit_before,
                commit_count_before=commit_count_before,
                recovery_manager=recovery_manager,
                linear_enabled=linear_is_enabled,
                status_manager=status_manager,
                source_spec_dir=source_spec_dir,
            )

            # === ENHANCED RECOVERY: Handle failures with smart recovery ===
            if not success:
                attempt_count = recovery_manager.get_attempt_count(subtask_id)

                # Classify the failure type
                # We use a generic "verification failed" error since we don't have the actual error message
                # The recovery system will use attempt history to determine if it's circular
                error_message = (
                    f"Subtask {subtask_id} verification failed or incomplete"
                )
                failure_type = recovery_manager.classify_failure(
                    error_message, subtask_id
                )

                # Determine recovery action (handles exponential backoff, model fallback, DLQ, notifications)
                recovery_action = recovery_manager.determine_recovery_action(
                    failure_type, subtask_id
                )

                # Record the notification or silent failure
                recovery_manager.record_recovery_notification(
                    subtask_id, failure_type, recovery_action
                )

                print()
                print_status(f"Recovery action: {recovery_action.action}", "warning")
                print_key_value("Reason", recovery_action.reason)

                # Handle different recovery actions
                if recovery_action.action == "retry":
                    # CRITICAL: Reset subtask status to 'pending' so get_next_subtask() can find it.
                    # Without this, the subtask stays 'in_progress' and the retry loop
                    # exits with "No pending subtasks found - build may be complete!"
                    if subtask_id:
                        if reset_subtask_to_pending(spec_dir, subtask_id):
                            print_status(
                                f"Reset subtask {subtask_id} to pending for retry",
                                "info",
                            )
                        else:
                            print_status(
                                f"Warning: Could not reset subtask {subtask_id} status",
                                "warning",
                            )

                    # Set up for retry with exponential backoff and optional model fallback
                    pending_recovery_action = recovery_action

                    # Set model fallback if recommended
                    if recovery_action.use_model_fallback:
                        # Extract current model shorthand and get fallback
                        current_model_shorthand = "sonnet"  # Default
                        if "opus" in phase_model.lower():
                            current_model_shorthand = "opus"
                        elif "sonnet" in phase_model.lower():
                            current_model_shorthand = "sonnet"
                        elif "haiku" in phase_model.lower():
                            current_model_shorthand = "haiku"

                        # Get fallback model from chain
                        fallback_chain = MODEL_FALLBACK_CHAIN.get(
                            current_model_shorthand, []
                        )
                        if fallback_chain:
                            override_model = fallback_chain[0]  # Use first fallback
                            print_status(
                                f"Will try fallback model: {override_model}", "info"
                            )
                        else:
                            override_model = None

                    # Set recovery guidance from strategy
                    if recovery_action.strategy:
                        recovery_guidance = recovery_action.strategy.guidance
                        print_key_value(
                            "Strategy", recovery_action.strategy.description
                        )

                    print_status(
                        f"Will retry after {recovery_action.wait_seconds:.1f}s backoff",
                        "progress",
                    )

                elif recovery_action.action == "skip":
                    # Mark subtask as stuck and skip
                    recovery_manager.mark_subtask_stuck(
                        subtask_id, recovery_action.reason
                    )
                    print_status(f"Subtask {subtask_id} marked as STUCK", "error")
                    print(muted("Recovery exhausted - consider manual intervention"))

                    # Notify user about stuck subtask
                    notify_stuck_subtask(
                        subtask_id=subtask_id,
                        reason=recovery_action.reason,
                        attempt_count=attempt_count,
                        spec_dir=spec_dir,
                    )

                    # Record stuck subtask in Linear (if enabled)
                    if linear_is_enabled:
                        await linear_task_stuck(
                            spec_dir=spec_dir,
                            subtask_id=subtask_id,
                            attempt_count=attempt_count,
                        )
                        print_status("Linear notified of stuck subtask", "info")

                elif recovery_action.action == "escalate":
                    # Critical failure - escalate to human
                    recovery_manager.mark_subtask_stuck(
                        subtask_id, recovery_action.reason
                    )
                    print()
                    print_status("ESCALATION REQUIRED", "error")
                    print_status(recovery_action.reason, "error")
                    print(
                        muted(
                            "This failure has been added to the dead-letter queue for manual review"
                        )
                    )
                    print()

                    # Notify user about escalation
                    notify_stuck_subtask(
                        subtask_id=subtask_id,
                        reason=recovery_action.reason,
                        attempt_count=attempt_count,
                        spec_dir=spec_dir,
                    )

                    # Record stuck subtask in Linear (if enabled)
                    if linear_is_enabled:
                        await linear_task_stuck(
                            spec_dir=spec_dir,
                            subtask_id=subtask_id,
                            attempt_count=attempt_count,
                        )
                        print_status("Linear notified of escalation", "info")

                elif recovery_action.action == "rollback":
                    # Rollback will be handled at the start of next iteration
                    # Reset subtask to pending so it's retried after rollback
                    if subtask_id:
                        reset_subtask_to_pending(spec_dir, subtask_id)
                    pending_recovery_action = recovery_action
                    print_status(
                        f"Will rollback to {recovery_action.target[:8]} on next iteration",
                        "warning",
                    )

                elif recovery_action.action == "continue":
                    # Context exhausted - will continue in next session
                    # Reset subtask to pending so it's picked up in the next session
                    if subtask_id:
                        reset_subtask_to_pending(spec_dir, subtask_id)
                    print_status(
                        "Context exhausted - will continue in next session", "info"
                    )

                # Sync recovery status changes back to main project (worktree mode)
                if source_spec_dir:
                    sync_spec_to_source(spec_dir, source_spec_dir)

                print()
        elif plan_validated and source_spec_dir:
            # After planning phase, sync the newly created implementation plan back to source
            if sync_spec_to_source(spec_dir, source_spec_dir):
                print_status("Implementation plan synced to main project", "success")

        # Handle session status
        if status == "complete":
            # Don't emit COMPLETE here - subtasks are done but QA hasn't run yet
            # QA loop will emit COMPLETE after actual approval
            print_build_complete_banner(spec_dir)
            status_manager.update(state=BuildState.COMPLETE)

            if task_logger:
                task_logger.end_phase(
                    LogPhase.CODING,
                    success=True,
                    message="All subtasks completed successfully",
                )

            if linear_task and linear_task.task_id:
                await linear_build_complete(spec_dir)
                print_status("Linear notified: build complete, ready for QA", "success")

            break

        elif status == "continue":
            print(
                muted(
                    f"\nAgent will auto-continue in {AUTO_CONTINUE_DELAY_SECONDS}s..."
                )
            )
            print_progress_summary(spec_dir)

            # Update state back to building
            status_manager.update(
                state=BuildState.PLANNING if is_planning_phase else BuildState.BUILDING
            )

            # Show next subtask info
            next_subtask = get_next_subtask(spec_dir, restart_from)
            if next_subtask:
                subtask_id = next_subtask.get("id")
                print(
                    f"\nNext: {highlight(subtask_id)} - {next_subtask.get('description')}"
                )

                attempt_count = recovery_manager.get_attempt_count(subtask_id)
                if attempt_count > 0:
                    print_status(
                        f"WARNING: {attempt_count} previous attempt(s)", "warning"
                    )

            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        elif status == "error":
            emit_phase(ExecutionPhase.FAILED, "Session encountered an error")
            print_status("Session encountered an error", "error")
            print(muted("Will retry with a fresh session..."))
            status_manager.update(state=BuildState.ERROR)
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        # Small delay between sessions
        if max_iterations is None or iteration < max_iterations:
            print("\nPreparing next session...\n")
            await asyncio.sleep(1)

    # Final summary
    content = [
        bold(f"{icon(Icons.SESSION)} SESSION SUMMARY"),
        "",
        f"Project: {project_dir}",
        f"Spec: {highlight(spec_dir.name)}",
        f"Sessions completed: {iteration}",
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print_progress_summary(spec_dir)

    # Show stuck subtasks if any
    stuck_subtasks = recovery_manager.get_stuck_subtasks()
    if stuck_subtasks:
        print()
        print_status("STUCK SUBTASKS (need manual intervention):", "error")
        for stuck in stuck_subtasks:
            print(f"  {icon(Icons.ERROR)} {stuck['subtask_id']}: {stuck['reason']}")

    # Instructions
    completed, total = count_subtasks(spec_dir)
    if completed < total:
        content = [
            bold(f"{icon(Icons.PLAY)} NEXT STEPS"),
            "",
            f"{total - completed} subtasks remaining.",
            f"Run again: {highlight(f'python auto-claude/run.py --spec {spec_dir.name}')}",
        ]
    else:
        content = [
            bold(f"{icon(Icons.SUCCESS)} NEXT STEPS"),
            "",
            "All subtasks completed!",
            "  1. Review the auto-claude/* branch",
            "  2. Run manual tests",
            "  3. Merge to main",
        ]

    print()
    print(box(content, width=70, style="light"))
    print()

    # Set final status
    if completed == total:
        status_manager.update(state=BuildState.COMPLETE)
    else:
        status_manager.update(state=BuildState.PAUSED)
