"""
Migration Commands
==================

CLI commands for running the migration assistant agent.
"""

import asyncio
import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from agents.migration_assistant import (
    run_migration_assistant,
    validate_migration_checkpoint,
)
from ui import (
    Icons,
    bold,
    icon,
    info,
    muted,
    print_key_value,
    success,
    warning,
)

from .utils import print_banner, validate_environment


def handle_migration_status_command(project_dir: Path, spec_dir: Path) -> None:
    """
    Handle the --migration-status command.

    Shows migration checkpoint status and validation results.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory path
    """
    print_banner()
    print(f"\nSpec: {spec_dir.name}")
    print(f"Project: {project_dir}\n")

    # Check for checkpoint directory
    checkpoint_dir = project_dir / ".migration-checkpoints"
    migration_plan = project_dir / "migration_plan.md"

    if not checkpoint_dir.exists():
        print(info(f"{icon(Icons.INFO)} No migration checkpoints found."))
        print(muted("Run migration assistant to create checkpoints."))
        print()
        return

    # Validate checkpoints
    validation = validate_migration_checkpoint(checkpoint_dir, project_dir)

    print(bold("Migration Status:"))
    print()

    # Show checkpoint info
    if validation["checkpoint_info"]:
        info_dict = validation["checkpoint_info"]
        if "commit" in info_dict:
            print_key_value("Latest checkpoint", info_dict["checkpoint_file"])
            print_key_value("Commit", info_dict["commit"][:12])
        if "rollback_scripts" in info_dict:
            print_key_value("Rollback scripts", str(info_dict["rollback_scripts"]))
        if info_dict.get("migration_plan"):
            print_key_value("Migration plan", str(migration_plan.relative_to(project_dir)))

    print()

    # Show validation status
    if validation["valid"]:
        print(success(f"{icon(Icons.SUCCESS)} Checkpoints are valid."))
    else:
        print(warning(f"{icon(Icons.WARNING)} Checkpoint validation issues:"))
        for issue in validation["issues"]:
            print(f"  • {issue}")

    print()


def handle_migration_command(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    verbose: bool = False,
) -> None:
    """
    Handle the --migrate command (run migration assistant).

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory path
        model: Model to use for migration
        verbose: Enable verbose output
    """
    print_banner()
    print(f"\nRunning migration assistant for: {spec_dir.name}")
    if not validate_environment(spec_dir):
        sys.exit(1)

    try:
        result = asyncio.run(
            run_migration_assistant(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model=model,
                verbose=verbose,
            )
        )

        if result["success"]:
            print(
                success(
                    f"\n{icon(Icons.SUCCESS)} Migration session completed successfully."
                )
            )
            if result.get("checkpoints_created", 0) > 0:
                print(
                    info(
                        f"{icon(Icons.INFO)} Created {result['checkpoints_created']} checkpoint(s)."
                    )
                )
            if result.get("migration_plan_path"):
                print(
                    info(
                        f"{icon(Icons.INFO)} Migration plan: {result['migration_plan_path']}"
                    )
                )
            print()
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"\n❌ Migration failed: {error_msg}\n")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nMigration assistant paused.")
        print(
            f"Resume with: python auto-claude/run.py --spec {spec_dir.name} --migrate"
        )
    except Exception as e:
        print(f"\n❌ Migration failed: {e}\n")
        sys.exit(1)
