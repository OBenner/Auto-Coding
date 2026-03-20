"""
Model Lock Commands
===================

CLI commands for managing model locks in Auto-Claude specs.

Model locks prevent automatic model changes and ensure specific models are always
used for particular phases or agent types.
"""

import sys
from pathlib import Path

# Add apps/backend/ to sys.path so that sibling packages (phase_config/, etc.)
# can be imported when this module is loaded via relative imports from cli/.
# This is the established pattern across all CLI modules in this project.
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from phase_config import (
    AGENT_DEFAULT_MODELS,
    ModelLockConfig,
    is_agent_model_locked,
    is_phase_model_locked,
    load_model_locks,
    lock_agent_model,
    lock_phase_model,
    save_model_locks,
    unlock_agent_model,
    unlock_phase_model,
)
from ui import Icons, divider, icon, info, muted, print_header, success, warning

from .utils import find_spec, print_banner


# Valid phases for locking
VALID_PHASES = ["spec", "planning", "coding", "qa", "test_generation"]

# Derive valid agent types from phase_config (single source of truth)
VALID_AGENTS = sorted(AGENT_DEFAULT_MODELS.keys())


def _print_locks(locks: ModelLockConfig) -> None:
    """
    Print model locks in a human-readable format.

    Args:
        locks: Model lock configuration
    """
    if not locks:
        print(info("No model locks configured."))
        return

    print(f"\n{icon(Icons.LOCK)} Model Locks")
    print(divider())

    # Print phase locks
    if locks.get("phaseModels"):
        print_header("Phase Locks")
        for phase, model_id in locks["phaseModels"].items():
            print(f"  {phase:20} → {model_id}")
        print()
    else:
        print_header("Phase Locks")
        print(muted("  (none)"))
        print()

    # Print agent locks
    if locks.get("agentModels"):
        print_header("Agent Locks")
        for agent_type, model_id in locks["agentModels"].items():
            print(f"  {agent_type:30} → {model_id}")
        print()
    else:
        print_header("Agent Locks")
        print(muted("  (none)"))
        print()


def handle_model_lock_list_command(project_dir: Path, spec_identifier: str) -> None:
    """
    Handle the --model-lock-list command.

    Lists all model locks for a spec.

    Args:
        project_dir: Project directory path
        spec_identifier: Spec identifier (e.g., '001' or '001-feature-name')
    """
    print_banner()
    print(f"\n{icon(Icons.LOCK)} Model Locks\n")

    # Find the spec
    spec_dir = find_spec(project_dir, spec_identifier)
    if not spec_dir:
        print(warning(f"Spec '{spec_identifier}' not found"))
        print()
        return

    # Load and display locks
    locks = load_model_locks(spec_dir)
    _print_locks(locks)


def handle_model_lock_phase_command(
    project_dir: Path, spec_identifier: str, phase: str, model_id: str
) -> None:
    """
    Handle the --model-lock-phase command.

    Locks a phase to a specific model.

    Args:
        project_dir: Project directory path
        spec_identifier: Spec identifier (e.g., '001' or '001-feature-name')
        phase: Phase to lock (e.g., 'coding', 'planning')
        model_id: Model ID to lock to (e.g., 'claude-sonnet-4-5-20250929')
    """
    print_banner()
    print(f"\n{icon(Icons.LOCK)} Lock Phase Model\n")

    # Validate phase
    if phase not in VALID_PHASES:
        print(warning(f"Invalid phase '{phase}'"))
        print(info(f"Valid phases: {', '.join(VALID_PHASES)}"))
        print()
        return

    # Validate model_id
    if not model_id or not model_id.strip():
        print(warning("Model ID must not be empty"))
        print()
        return

    model_id = model_id.strip()

    # Find the spec
    spec_dir = find_spec(project_dir, spec_identifier)
    if not spec_dir:
        print(warning(f"Spec '{spec_identifier}' not found"))
        print()
        return

    try:
        # Lock the phase
        lock_phase_model(spec_dir, phase, model_id)
        print(success(f"✅ Locked phase '{phase}' to model '{model_id}'"))
        print()

        # Verify
        if is_phase_model_locked(spec_dir, phase):
            # Verify the persisted lock matches the normalized model_id
            locks = load_model_locks(spec_dir)
            saved_id = (locks.get("phaseModels") or {}).get(phase)
            if saved_id == model_id:
                _print_locks(locks)
                return
            else:
                print(
                    warning(
                        f"⚠️  Warning: Saved model ID '{saved_id}' does not match '{model_id}'"
                    )
                )
                print()
                return

        print(warning("⚠️  Warning: Lock was created but verification failed"))
        print()

    except Exception as e:
        print(warning(f"❌ Error locking phase: {e}"))
        print()


def handle_model_lock_agent_command(
    project_dir: Path, spec_identifier: str, agent_type: str, model_id: str
) -> None:
    """
    Handle the --model-lock-agent command.

    Locks an agent type to a specific model.

    Args:
        project_dir: Project directory path
        spec_identifier: Spec identifier (e.g., '001' or '001-feature-name')
        agent_type: Agent type to lock (e.g., 'coder', 'planner')
        model_id: Model ID to lock to (e.g., 'claude-sonnet-4-5-20250929')
    """
    print_banner()
    print(f"\n{icon(Icons.LOCK)} Lock Agent Model\n")

    # Validate agent_type
    if agent_type not in VALID_AGENTS:
        print(warning(f"Invalid agent type '{agent_type}'"))
        # Show first 10 valid agents
        agents_str = ", ".join(VALID_AGENTS[:10])
        if len(VALID_AGENTS) > 10:
            agents_str += "..."
        print(info(f"Valid agent types: {agents_str}"))
        print()
        return

    # Validate model_id
    if not model_id or not model_id.strip():
        print(warning("Model ID must not be empty"))
        print()
        return

    model_id = model_id.strip()

    # Find the spec
    spec_dir = find_spec(project_dir, spec_identifier)
    if not spec_dir:
        print(warning(f"Spec '{spec_identifier}' not found"))
        print()
        return

    try:
        # Lock the agent
        lock_agent_model(spec_dir, agent_type, model_id)
        print(success(f"✅ Locked agent '{agent_type}' to model '{model_id}'"))
        print()

        # Verify
        if is_agent_model_locked(spec_dir, agent_type):
            # Verify the persisted lock matches the normalized model_id
            locks = load_model_locks(spec_dir)
            saved_id = (locks.get("agentModels") or {}).get(agent_type)
            if saved_id == model_id:
                _print_locks(locks)
                return
            else:
                print(
                    warning(
                        f"⚠️  Warning: Saved model ID '{saved_id}' does not match '{model_id}'"
                    )
                )
                print()
                return

        print(warning("⚠️  Warning: Lock was created but verification failed"))
        print()

    except Exception as e:
        print(warning(f"❌ Error locking agent: {e}"))
        print()


def handle_model_unlock_phase_command(
    project_dir: Path, spec_identifier: str, phase: str
) -> None:
    """
    Handle the --model-unlock-phase command.

    Unlocks a phase's model.

    Args:
        project_dir: Project directory path
        spec_identifier: Spec identifier (e.g., '001' or '001-feature-name')
        phase: Phase to unlock (e.g., 'coding', 'planning')
    """
    print_banner()
    print(f"\n{icon(Icons.LOCK)} Unlock Phase Model\n")

    # Validate phase
    if phase not in VALID_PHASES:
        print(warning(f"Invalid phase '{phase}'"))
        print(info(f"Valid phases: {', '.join(VALID_PHASES)}"))
        print()
        return

    # Find the spec
    spec_dir = find_spec(project_dir, spec_identifier)
    if not spec_dir:
        print(warning(f"Spec '{spec_identifier}' not found"))
        print()
        return

    try:
        # Unlock the phase
        unlock_phase_model(spec_dir, phase)
        print(success(f"✅ Unlocked phase '{phase}'"))
        print()

        # Display remaining locks
        locks = load_model_locks(spec_dir)
        _print_locks(locks)

    except Exception as e:
        print(warning(f"❌ Error unlocking phase: {e}"))
        print()


def handle_model_unlock_agent_command(
    project_dir: Path, spec_identifier: str, agent_type: str
) -> None:
    """
    Handle the --model-unlock-agent command.

    Unlocks an agent's model.

    Args:
        project_dir: Project directory path
        spec_identifier: Spec identifier (e.g., '001' or '001-feature-name')
        agent_type: Agent type to unlock (e.g., 'coder', 'planner')
    """
    print_banner()
    print(f"\n{icon(Icons.LOCK)} Unlock Agent Model\n")

    # Validate agent_type
    if agent_type not in VALID_AGENTS:
        print(warning(f"Invalid agent type '{agent_type}'"))
        # Show first 10 valid agents
        agents_str = ", ".join(VALID_AGENTS[:10])
        if len(VALID_AGENTS) > 10:
            agents_str += "..."
        print(info(f"Valid agent types: {agents_str}"))
        print()
        return

    # Find the spec
    spec_dir = find_spec(project_dir, spec_identifier)
    if not spec_dir:
        print(warning(f"Spec '{spec_identifier}' not found"))
        print()
        return

    try:
        # Unlock the agent
        unlock_agent_model(spec_dir, agent_type)
        print(success(f"✅ Unlocked agent '{agent_type}'"))
        print()

        # Display remaining locks
        locks = load_model_locks(spec_dir)
        _print_locks(locks)

    except Exception as e:
        print(warning(f"❌ Error unlocking agent: {e}"))
        print()


def handle_model_lock_clear_command(project_dir: Path, spec_identifier: str) -> None:
    """
    Handle the --model-lock-clear command.

    Clears all model locks for a spec.

    Args:
        project_dir: Project directory path
        spec_identifier: Spec identifier (e.g., '001' or '001-feature-name')
    """
    print_banner()
    print(f"\n{icon(Icons.LOCK)} Clear Model Locks\n")

    # Find the spec
    spec_dir = find_spec(project_dir, spec_identifier)
    if not spec_dir:
        print(warning(f"Spec '{spec_identifier}' not found"))
        print()
        return

    try:
        # Save empty locks config
        save_model_locks(spec_dir, {})
        print(success("✅ Cleared all model locks"))
        print()

        # Verify
        locks = load_model_locks(spec_dir)
        if not locks:
            print(success("✅ Verification: No locks remain"))
        else:
            print(
                warning(f"⚠️  Warning: Locks may remain: {locks}")
            )

        print()

    except Exception as e:
        print(warning(f"❌ Error clearing locks: {e}"))
        print()
