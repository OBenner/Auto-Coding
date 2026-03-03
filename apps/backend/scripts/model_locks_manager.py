#!/usr/bin/env python3
"""
Model Locks Manager
===================

Command-line tool for managing model locks in Auto-Claude specs.

Model locks prevent automatic model changes and ensure specific models are always
used for particular phases or agent types.

Usage:
    python model_locks_manager.py list <spec_dir>
    python model_locks_manager.py lock-phase <spec_dir> <phase> <model_id>
    python model_locks_manager.py lock-agent <spec_dir> <agent_type> <model_id>
    python model_locks_manager.py unlock-phase <spec_dir> <phase>
    python model_locks_manager.py unlock-agent <spec_dir> <agent_type>
    python model_locks_manager.py clear <spec_dir>

Examples:
    # List all locks for a spec
    python model_locks_manager.py list .auto-claude/specs/001-feature

    # Lock the coding phase to sonnet-4.5
    python model_locks_manager.py lock-phase .auto-claude/specs/001-feature coding claude-sonnet-4-5-20250929

    # Lock the coder agent to haiku
    python model_locks_manager.py lock-agent .auto-claude/specs/001-feature coder claude-haiku-4-5-20251001

    # Unlock the coding phase
    python model_locks_manager.py unlock-phase .auto-claude/specs/001-feature coding

    # Unlock the coder agent
    python model_locks_manager.py unlock-agent .auto-claude/specs/001-feature coder

    # Clear all locks
    python model_locks_manager.py clear .auto-claude/specs/001-feature
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# Valid phases for locking
VALID_PHASES = ["spec", "planning", "coding", "qa", "test_generation"]

# Derive valid agent types from phase_config (single source of truth)
VALID_AGENTS = (
    sorted(AGENT_DEFAULT_MODELS.keys())
    + [
        # Additional agent types not in AGENT_DEFAULT_MODELS
    ]
)


def print_locks(locks: ModelLockConfig) -> None:
    """
    Print model locks in a human-readable format.

    Args:
        locks: Model lock configuration
    """
    if not locks:
        print("No model locks configured.")
        return

    print("\n🔒 Model Locks")
    print("=" * 60)

    # Print phase locks
    if locks.get("phaseModels"):
        print("\n📋 Phase Locks:")
        for phase, model_id in locks["phaseModels"].items():
            print(f"  {phase:20} → {model_id}")
    else:
        print("\n📋 Phase Locks: (none)")

    # Print agent locks
    if locks.get("agentModels"):
        print("\n🤖 Agent Locks:")
        for agent_type, model_id in locks["agentModels"].items():
            print(f"  {agent_type:30} → {model_id}")
    else:
        print("\n🤖 Agent Locks: (none)")

    print()


def cmd_list(spec_dir: str) -> int:
    """
    List all model locks for a spec.

    Args:
        spec_dir: Path to spec directory

    Returns:
        Exit code (0 for success, 1 for error)
    """
    spec_path = Path(spec_dir)
    if not spec_path.exists():
        print(f"❌ Error: Spec directory not found: {spec_dir}", file=sys.stderr)
        return 1

    locks = load_model_locks(spec_path)
    print_locks(locks)

    return 0


def cmd_lock_phase(spec_dir: str, phase: str, model_id: str) -> int:
    """
    Lock a phase to a specific model.

    Args:
        spec_dir: Path to spec directory
        phase: Phase to lock
        model_id: Model ID to lock to

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not model_id or not model_id.strip():
        print("❌ Error: model_id must not be empty", file=sys.stderr)
        return 1

    if phase not in VALID_PHASES:
        print(
            f"❌ Error: Invalid phase '{phase}'. Valid phases: {', '.join(VALID_PHASES)}",
            file=sys.stderr,
        )
        return 1

    spec_path = Path(spec_dir)
    if not spec_path.exists():
        print(f"❌ Error: Spec directory not found: {spec_dir}", file=sys.stderr)
        return 1

    try:
        lock_phase_model(spec_path, phase, model_id)  # type: ignore
        print(f"✅ Locked phase '{phase}' to model '{model_id}'")

        # Verify the lock
        if is_phase_model_locked(spec_path, phase):
            locks = load_model_locks(spec_path)
            print_locks(locks)
            return 0
        else:
            print(
                "⚠️  Warning: Lock was created but verification failed",
                file=sys.stderr,
            )
            return 1
    except Exception as e:
        print(f"❌ Error locking phase: {e}", file=sys.stderr)
        return 1


def cmd_lock_agent(spec_dir: str, agent_type: str, model_id: str) -> int:
    """
    Lock an agent type to a specific model.

    Args:
        spec_dir: Path to spec directory
        agent_type: Agent type to lock
        model_id: Model ID to lock to

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not model_id or not model_id.strip():
        print("❌ Error: model_id must not be empty", file=sys.stderr)
        return 1

    if agent_type not in VALID_AGENTS:
        print(
            f"❌ Error: Invalid agent type '{agent_type}'. "
            f"Valid agents: {', '.join(VALID_AGENTS[:10])}...",
            file=sys.stderr,
        )
        return 1

    spec_path = Path(spec_dir)
    if not spec_path.exists():
        print(f"❌ Error: Spec directory not found: {spec_dir}", file=sys.stderr)
        return 1

    try:
        lock_agent_model(spec_path, agent_type, model_id)
        print(f"✅ Locked agent '{agent_type}' to model '{model_id}'")

        # Verify the lock
        if is_agent_model_locked(spec_path, agent_type):
            locks = load_model_locks(spec_path)
            print_locks(locks)
            return 0
        else:
            print(
                "⚠️  Warning: Lock was created but verification failed",
                file=sys.stderr,
            )
            return 1
    except Exception as e:
        print(f"❌ Error locking agent: {e}", file=sys.stderr)
        return 1


def cmd_unlock_phase(spec_dir: str, phase: str) -> int:
    """
    Unlock a phase's model.

    Args:
        spec_dir: Path to spec directory
        phase: Phase to unlock

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if phase not in VALID_PHASES:
        print(
            f"❌ Error: Invalid phase '{phase}'. Valid phases: {', '.join(VALID_PHASES)}",
            file=sys.stderr,
        )
        return 1

    spec_path = Path(spec_dir)
    if not spec_path.exists():
        print(f"❌ Error: Spec directory not found: {spec_dir}", file=sys.stderr)
        return 1

    try:
        unlock_phase_model(spec_path, phase)  # type: ignore
        print(f"✅ Unlocked phase '{phase}'")

        # Show remaining locks
        locks = load_model_locks(spec_path)
        print_locks(locks)

        return 0
    except Exception as e:
        print(f"❌ Error unlocking phase: {e}", file=sys.stderr)
        return 1


def cmd_unlock_agent(spec_dir: str, agent_type: str) -> int:
    """
    Unlock an agent's model.

    Args:
        spec_dir: Path to spec directory
        agent_type: Agent type to unlock

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if agent_type not in VALID_AGENTS:
        print(
            f"❌ Error: Invalid agent type '{agent_type}'. "
            f"Valid agents: {', '.join(VALID_AGENTS[:10])}...",
            file=sys.stderr,
        )
        return 1

    spec_path = Path(spec_dir)
    if not spec_path.exists():
        print(f"❌ Error: Spec directory not found: {spec_dir}", file=sys.stderr)
        return 1

    try:
        unlock_agent_model(spec_path, agent_type)
        print(f"✅ Unlocked agent '{agent_type}'")

        # Show remaining locks
        locks = load_model_locks(spec_path)
        print_locks(locks)

        return 0
    except Exception as e:
        print(f"❌ Error unlocking agent: {e}", file=sys.stderr)
        return 1


def cmd_clear(spec_dir: str) -> int:
    """
    Clear all model locks for a spec.

    Args:
        spec_dir: Path to spec directory

    Returns:
        Exit code (0 for success, 1 for error)
    """
    spec_path = Path(spec_dir)
    if not spec_path.exists():
        print(f"❌ Error: Spec directory not found: {spec_dir}", file=sys.stderr)
        return 1

    try:
        # Save empty locks config
        save_model_locks(spec_path, {})
        print("✅ Cleared all model locks")

        # Verify
        locks = load_model_locks(spec_path)
        if not locks:
            print("✅ Verification: No locks remain")
            return 0
        else:
            print(
                f"⚠️  Warning: Locks may remain: {json.dumps(locks, indent=2)}",
                file=sys.stderr,
            )
            return 1
    except Exception as e:
        print(f"❌ Error clearing locks: {e}", file=sys.stderr)
        return 1


def print_usage() -> None:
    """Print usage information."""
    print(
        """Usage: model_locks_manager.py <command> <args>

Commands:
    list <spec_dir>                    List all model locks
    lock-phase <spec_dir> <phase> <model_id>      Lock a phase to a model
    lock-agent <spec_dir> <agent> <model_id>      Lock an agent to a model
    unlock-phase <spec_dir> <phase>               Unlock a phase
    unlock-agent <spec_dir> <agent>               Unlock an agent
    clear <spec_dir>                    Clear all locks

Valid Phases:
    spec, planning, coding, qa, test_generation

Valid Agents:
    planner, coder, qa_reviewer, qa_fixer, spec_gatherer, spec_writer,
    spec_researcher, spec_critic, insights, merge_resolver, commit_message,
    pr_reviewer, pr_orchestrator_parallel, pr_followup_parallel, analysis,
    batch_analysis, batch_validation, roadmap_discovery, competitor_analysis,
    ideation

Examples:
    # List all locks
    python model_locks_manager.py list .auto-claude/specs/001-feature

    # Lock coding phase to sonnet
    python model_locks_manager.py lock-phase .auto-claude/specs/001-feature \\
        coding claude-sonnet-4-5-20250929

    # Lock coder agent to haiku
    python model_locks_manager.py lock-agent .auto-claude/specs/001-feature \\
        coder claude-haiku-4-5-20251001

    # Unlock coding phase
    python model_locks_manager.py unlock-phase .auto-claude/specs/001-feature coding

    # Clear all locks
    python model_locks_manager.py clear .auto-claude/specs/001-feature
"""
    )


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("❌ Error: No command specified", file=sys.stderr)
        print_usage()
        return 1

    command = sys.argv[1]

    # Handle help flags
    if command in ["--help", "-h", "help"]:
        print("usage: model_locks_manager.py <command> <args>")
        print_usage()
        return 0

    # Dispatch command
    if command == "list":
        if len(sys.argv) < 3:
            print("❌ Error: Missing spec_dir argument", file=sys.stderr)
            print_usage()
            return 1
        return cmd_list(sys.argv[2])

    elif command == "lock-phase":
        if len(sys.argv) < 5:
            print(
                "❌ Error: Missing arguments. Usage: lock-phase <spec_dir> <phase> <model_id>",
                file=sys.stderr,
            )
            print_usage()
            return 1
        return cmd_lock_phase(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "lock-agent":
        if len(sys.argv) < 5:
            print(
                "❌ Error: Missing arguments. Usage: lock-agent <spec_dir> <agent> <model_id>",
                file=sys.stderr,
            )
            print_usage()
            return 1
        return cmd_lock_agent(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "unlock-phase":
        if len(sys.argv) < 4:
            print(
                "❌ Error: Missing arguments. Usage: unlock-phase <spec_dir> <phase>",
                file=sys.stderr,
            )
            print_usage()
            return 1
        return cmd_unlock_phase(sys.argv[2], sys.argv[3])

    elif command == "unlock-agent":
        if len(sys.argv) < 4:
            print(
                "❌ Error: Missing arguments. Usage: unlock-agent <spec_dir> <agent>",
                file=sys.stderr,
            )
            print_usage()
            return 1
        return cmd_unlock_agent(sys.argv[2], sys.argv[3])

    elif command == "clear":
        if len(sys.argv) < 3:
            print("❌ Error: Missing spec_dir argument", file=sys.stderr)
            print_usage()
            return 1
        return cmd_clear(sys.argv[2])

    else:
        print(f"❌ Error: Unknown command '{command}'", file=sys.stderr)
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
