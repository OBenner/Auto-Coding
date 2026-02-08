#!/usr/bin/env python3
"""
Feedback Recorder
==================

Records user feedback (accept/reject/modify) to preference profiles.
This script is called by the frontend when users provide feedback on agent outputs.

Usage:
    python feedback_recorder.py --feedback-type accepted --agent-type planner --task-description "Add login feature"
    python feedback_recorder.py --feedback-type modified --agent-type coder --task-description "Fix button" --context '{"issue": "too verbose"}'

The script calls save_feedback() from memory_manager to update the user's preference profile.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Record user feedback to preference profile'
    )
    parser.add_argument(
        '--feedback-type',
        required=True,
        choices=['accepted', 'rejected', 'modified'],
        help='Type of feedback: accepted, rejected, or modified'
    )
    parser.add_argument(
        '--agent-type',
        required=True,
        help='Type of agent that generated the output (e.g., planner, coder, qa_reviewer)'
    )
    parser.add_argument(
        '--task-description',
        required=True,
        help='Description of the task the agent was working on'
    )
    parser.add_argument(
        '--context',
        default='{}',
        help='Additional context as JSON string (e.g., {"issue": "too verbose"})'
    )
    parser.add_argument(
        '--spec-dir',
        default=None,
        help='Spec directory path (optional, inferred from current directory if not provided)'
    )
    parser.add_argument(
        '--project-dir',
        default=None,
        help='Project directory path (optional, inferred from current directory if not provided)'
    )

    return parser.parse_args()


def infer_directories():
    """
    Infer spec_dir and project_dir from current working directory.

    The frontend may call this script from various contexts:
    - From project root: cwd is the project directory
    - From spec worktree: cwd is inside .worktrees/{spec-name}/

    Returns:
        tuple: (spec_dir, project_dir) as Path objects
    """
    cwd = Path.cwd()

    # Check if we're in a worktree
    # Worktrees are typically at .worktrees/{spec-name}/ or similar
    if '.worktrees' in cwd.parts:
        # We're in a worktree - find project root by going up past .worktrees
        worktree_idx = cwd.parts.index('.worktrees')
        project_dir = Path(*cwd.parts[:worktree_idx])

        # Find spec directory (usually .auto-claude/specs/{spec-id})
        spec_name = cwd.parts[worktree_idx + 1] if worktree_idx + 1 < len(cwd.parts) else None
        if spec_name:
            # Try common spec directory locations
            for spec_base in ['.auto-claude/specs', 'specs']:
                spec_dir = project_dir / spec_base / spec_name
                if spec_dir.exists():
                    return spec_dir, project_dir

        # Fallback: return worktree path as spec_dir, project root as project_dir
        return cwd, project_dir

    # We're in the project root or a subdirectory
    # Find project root by looking for .auto-claude directory
    current = cwd
    while current != current.parent:
        if (current / '.auto-claude').exists():
            return None, current  # spec_dir is None (will be inferred by backend)
        current = current.parent

    # Couldn't find project root - use cwd as project_dir
    return None, cwd


async def record_feedback(args):
    """
    Record feedback to preference profile.

    Args:
        args: Parsed command-line arguments

    Returns:
        dict: Result with success status and message
    """
    try:
        # Parse context JSON
        try:
            context = json.loads(args.context) if args.context else {}
        except json.JSONDecodeError:
            context = {"raw": args.context} if args.context else {}

        # Determine directories
        if args.spec_dir and args.project_dir:
            spec_dir = Path(args.spec_dir)
            project_dir = Path(args.project_dir)
        else:
            spec_dir, project_dir = infer_directories()

        # Import save_feedback from memory_manager
        from agents.memory_manager import save_feedback

        # Call save_feedback
        result = await save_feedback(
            spec_dir=spec_dir,
            project_dir=project_dir,
            feedback_type=args.feedback_type,
            task_description=args.task_description,
            agent_type=args.agent_type,
            context=context,
        )

        if result:
            return {
                "success": True,
                "message": f"Recorded {args.feedback_type} feedback for {args.agent_type}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to save feedback to memory"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def main():
    """Main entry point."""
    args = parse_args()

    # Record feedback
    result = await record_feedback(args)

    # Output result as JSON
    print(json.dumps(result))

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == '__main__':
    asyncio.run(main())
