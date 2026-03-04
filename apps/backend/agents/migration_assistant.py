"""
Migration Assistant Agent Module
=================================

AI agent that guides framework, library, and language migrations through
incremental, validated steps with rollback capability at each checkpoint.
"""

import json
import logging
import platform
from pathlib import Path
from typing import Any

from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget
from prompts_pkg.prompt_loader import get_agent_prompt
from task_logger import LogEntryType, LogPhase, get_task_logger
from ui import (
    Icons,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_key_value,
    print_status,
)

logger = logging.getLogger(__name__)


def validate_migration_checkpoint(
    checkpoint_dir: Path, project_dir: Path
) -> dict[str, Any]:
    """
    Validate that a migration checkpoint is complete and valid.

    Checks for:
    - Checkpoint metadata file exists
    - Git commit was created
    - Rollback script exists and is executable

    Args:
        checkpoint_dir: Directory containing checkpoint files
        project_dir: Project root directory

    Returns:
        Dictionary with validation results:
        - valid: Boolean indicating if checkpoint is valid
        - issues: List of validation issues found
        - checkpoint_info: Metadata about the checkpoint
    """
    issues = []
    checkpoint_info = {}

    if not checkpoint_dir.exists():
        return {
            "valid": False,
            "issues": ["Checkpoint directory does not exist"],
            "checkpoint_info": {},
        }

    # Check for checkpoint metadata files
    # Support both checkpoints.json (CheckpointManager) and legacy commit files
    checkpoints_json = checkpoint_dir / "checkpoints.json"
    commit_files = list(checkpoint_dir.glob("checkpoint-*-commit.txt"))

    if checkpoints_json.exists():
        try:
            with open(checkpoints_json, encoding="utf-8") as f:
                data = json.load(f)
                checkpoints = data.get("checkpoints", [])
                if checkpoints:
                    latest = checkpoints[-1]
                    checkpoint_info["commit"] = latest.get("commit_hash", "")
                    checkpoint_info["checkpoint_file"] = "checkpoints.json"
                else:
                    issues.append("No checkpoints found in checkpoints.json")
        except (json.JSONDecodeError, OSError) as e:
            issues.append(f"Failed to read checkpoints.json: {e}")
    elif commit_files:
        # Legacy format: checkpoint-*-commit.txt
        latest_commit_file = sorted(commit_files)[-1]
        try:
            with open(latest_commit_file, encoding="utf-8") as f:
                commit_hash = f.read().strip()
                checkpoint_info["commit"] = commit_hash
                checkpoint_info["checkpoint_file"] = latest_commit_file.name
        except Exception as e:
            issues.append(f"Failed to read checkpoint commit file: {e}")
    else:
        issues.append("No checkpoint metadata found")

    # Check for rollback scripts
    rollback_dir = checkpoint_dir / "rollback"
    if not rollback_dir.exists():
        issues.append("Rollback directory does not exist")
    else:
        rollback_scripts = list(rollback_dir.glob("checkpoint-*.sh"))
        if not rollback_scripts:
            issues.append("No rollback scripts found")
        else:
            checkpoint_info["rollback_scripts"] = len(rollback_scripts)
            # Check if scripts are executable (Unix only)
            if platform.system() != "Windows":
                for script in rollback_scripts:
                    if not script.stat().st_mode & 0o100:
                        issues.append(f"Rollback script not executable: {script.name}")

    # Check for migration plan
    migration_plan = project_dir / "migration_plan.md"
    if migration_plan.exists():
        checkpoint_info["migration_plan"] = True
    else:
        logger.debug("No migration_plan.md found (optional)")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "checkpoint_info": checkpoint_info,
    }


async def run_migration_assistant(
    project_dir: Path,
    spec_dir: Path,
    migration_context: dict[str, Any] | None = None,
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run Migration Assistant Agent session to guide code migrations.

    The agent will:
    1. Analyze the current codebase and migration target
    2. Create an incremental migration plan with checkpoints
    3. Implement changes in safe, validated steps
    4. Generate compatibility layers for gradual transition
    5. Adapt test suites during migration
    6. Provide rollback capability at each checkpoint

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        migration_context: Optional context about the migration (frameworks, versions, etc.)
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - checkpoints_created: Number of migration checkpoints created
        - success: Whether migration session succeeded
        - error: Error message if failed
        - migration_plan_path: Path to migration plan (if created)
    """
    # Initialize task logger
    task_logger = get_task_logger(spec_dir)

    # Print session header
    content = [
        bold(f"{icon(Icons.SPARKLES)} MIGRATION ASSISTANT SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Guiding incremental migration with validated checkpoints..."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Determine model and thinking budget
    if model is None:
        model = get_phase_model("migration")
    if max_thinking_tokens is None:
        max_thinking_tokens = get_phase_thinking_budget("migration")

    print_key_value("Model", model)
    print_key_value(
        "Thinking budget",
        str(max_thinking_tokens) if max_thinking_tokens else "Default",
    )
    print()

    # Log session start
    if task_logger:
        task_logger.start_phase(LogPhase.CODING, "Starting migration session...")
        if migration_context:
            task_logger.log(
                f"Migration context: {json.dumps(migration_context, indent=2)}",
                LogEntryType.INFO,
            )

    # Load the migration assistant prompt (validates it exists)
    try:
        _prompt = get_agent_prompt("migration_assistant")
    except Exception as e:
        error_msg = f"Failed to load migration_assistant prompt: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log(error_msg, LogEntryType.ERROR)
        return {
            "checkpoints_created": 0,
            "success": False,
            "error": error_msg,
        }

    # Create the starting message with migration context
    starting_message = """You are the Migration Assistant Agent. Your task is to guide a code migration through incremental, validated steps with rollback capability.

## Your Workflow

1. **Phase 0: Migration Context (MANDATORY)**
   - Read spec.md to understand the migration goal
   - Read implementation_plan.json to see planned migration steps
   - Read context.json to understand the codebase
   - Analyze current code to identify what needs migration

2. **Phase 1: Migration Analysis**
   - Assess current state (versions, patterns, dependencies)
   - Identify migration complexity and risks
   - Create migration_plan.md with phases, checkpoints, and rollback strategy

3. **Phase 2: Checkpoint System Setup**
   - Create .migration-checkpoints/ directory
   - Create rollback scripts directory
   - Save initial baseline checkpoint

4. **Phase 3: Incremental Implementation**
   - Work on one phase at a time
   - Create compatibility layers if needed
   - Update tests alongside code changes
   - Create checkpoint after each phase
   - Validate before proceeding

5. **Phase 4: Documentation**
   - Document migration decisions in MIGRATION_DECISIONS.md
   - Create user-facing MIGRATION_GUIDE.md
   - Update implementation_plan.json

Begin by loading context (Phase 0 in your prompt).
"""

    # Add migration context if provided
    if migration_context:
        starting_message += (
            f"\n\n## Migration Context\n\n{json.dumps(migration_context, indent=2)}\n"
        )

    # Create SDK client with migration_assistant agent type
    try:
        client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            agent_type="migration_assistant",
            max_thinking_tokens=max_thinking_tokens,
        )
    except Exception as e:
        error_msg = f"Failed to create Claude SDK client: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log(error_msg, LogEntryType.ERROR)
        return {
            "checkpoints_created": 0,
            "success": False,
            "error": error_msg,
        }

    # Run the migration assistant session
    print_status("Running migration assistant...", "progress")
    print()

    try:
        async with client:
            await client.create_agent_session(
                name="migration-assistant-session",
                starting_message=starting_message,
            )

        # Log completion
        if task_logger:
            task_logger.end_phase(
                LogPhase.CODING,
                success=True,
                message="Migration session completed",
            )

        # Check for created artifacts
        checkpoint_dir = project_dir / ".migration-checkpoints"
        migration_plan = project_dir / "migration_plan.md"

        checkpoints_created = 0
        if checkpoint_dir.exists():
            # Check checkpoints.json first, fall back to legacy commit files
            cj = checkpoint_dir / "checkpoints.json"
            if cj.exists():
                try:
                    with open(cj, encoding="utf-8") as f:
                        cj_data = json.load(f)
                    checkpoints_created = len(cj_data.get("checkpoints", []))
                except (json.JSONDecodeError, OSError):
                    pass
            if checkpoints_created == 0:
                commit_files = list(checkpoint_dir.glob("checkpoint-*-commit.txt"))
                checkpoints_created = len(commit_files)

            # Validate the checkpoint structure
            validation = validate_migration_checkpoint(checkpoint_dir, project_dir)
            if not validation["valid"]:
                logger.warning(f"Checkpoint validation issues: {validation['issues']}")
                if task_logger:
                    task_logger.log(
                        f"Checkpoint validation issues: {', '.join(validation['issues'])}",
                        LogEntryType.INFO,
                    )

        print()
        print_status("Migration session completed", "success")
        print_key_value("Checkpoints created", str(checkpoints_created))
        if migration_plan.exists():
            print_key_value(
                "Migration plan", str(migration_plan.relative_to(project_dir))
            )
        print()

        return {
            "checkpoints_created": checkpoints_created,
            "success": True,
            "migration_plan_path": str(migration_plan.relative_to(project_dir))
            if migration_plan.exists()
            else None,
        }

    except Exception as e:
        error_msg = f"Migration session failed: {e}"
        logger.error(error_msg, exc_info=True)
        if task_logger:
            task_logger.log(error_msg, LogEntryType.ERROR)
            task_logger.end_phase(
                LogPhase.CODING,
                success=False,
                message=error_msg,
            )

        print()
        print_status(f"Migration failed: {e}", "error")
        print()

        return {
            "checkpoints_created": 0,
            "success": False,
            "error": error_msg,
        }
