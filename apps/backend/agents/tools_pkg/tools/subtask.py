"""
Subtask Management Tools
========================

Tools for managing subtask status in implementation_plan.json.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.file_utils import write_json_atomic
from spec.validate_pkg.auto_fix import auto_fix_plan

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None


def _update_subtask_in_plan(
    plan: dict[str, Any],
    subtask_id: str,
    status: str,
    notes: str,
) -> bool:
    """
    Update a subtask in the plan.

    Args:
        plan: The implementation plan dict
        subtask_id: ID of the subtask to update
        status: New status (pending, in_progress, completed, failed)
        notes: Optional notes to add

    Returns:
        True if subtask was found and updated, False otherwise
    """
    subtask_found = False
    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            if subtask.get("id") == subtask_id:
                subtask["status"] = status
                if notes:
                    subtask["notes"] = notes
                subtask["updated_at"] = datetime.now(UTC).isoformat()
                subtask_found = True
                break
        if subtask_found:
            break

    if subtask_found:
        plan["last_updated"] = datetime.now(UTC).isoformat()

    return subtask_found


def create_subtask_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create subtask management tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of subtask tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: update_subtask_status
    # -------------------------------------------------------------------------
    @tool(
        "update_subtask_status",
        "Update the status of a subtask in implementation_plan.json. Use this when completing or starting a subtask.",
        {"subtask_id": str, "status": str, "notes": str},
    )
    async def update_subtask_status(args: dict[str, Any]) -> dict[str, Any]:
        """Update subtask status in the implementation plan."""
        subtask_id = args["subtask_id"]
        status = args["status"]
        notes = args.get("notes", "")

        valid_statuses = ["pending", "in_progress", "completed", "failed"]
        if status not in valid_statuses:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid status '{status}'. Must be one of: {valid_statuses}",
                    }
                ]
            }

        plan_file = spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: implementation_plan.json not found",
                    }
                ]
            }

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            subtask_found = _update_subtask_in_plan(plan, subtask_id, status, notes)

            if not subtask_found:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Subtask '{subtask_id}' not found in implementation plan",
                        }
                    ]
                }

            # Use atomic write to prevent file corruption
            write_json_atomic(plan_file, plan, indent=2)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully updated subtask '{subtask_id}' to status '{status}'",
                    }
                ]
            }

        except json.JSONDecodeError as e:
            # Attempt to auto-fix the plan and retry
            if auto_fix_plan(spec_dir):
                # Retry after fix
                try:
                    with open(plan_file, encoding="utf-8") as f:
                        plan = json.load(f)

                    subtask_found = _update_subtask_in_plan(
                        plan, subtask_id, status, notes
                    )

                    if subtask_found:
                        write_json_atomic(plan_file, plan, indent=2)
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Successfully updated subtask '{subtask_id}' to status '{status}' (after auto-fix)",
                                }
                            ]
                        }
                    else:
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error: Subtask '{subtask_id}' not found in implementation plan (after auto-fix)",
                                }
                            ]
                        }
                except Exception as retry_err:
                    logging.warning(
                        f"Subtask update retry failed after auto-fix: {retry_err}"
                    )
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Subtask update failed after auto-fix: {retry_err}",
                            }
                        ]
                    }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid JSON in implementation_plan.json: {e}",
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error updating subtask status: {e}"}
                ]
            }

    tools.append(update_subtask_status)

    # -------------------------------------------------------------------------
    # Tool: batch_update_subtask_statuses
    # -------------------------------------------------------------------------
    @tool(
        "batch_update_subtask_statuses",
        "Update the status of multiple subtasks in implementation_plan.json in a single operation. Use this when completing multiple related subtasks.",
        {"updates": list},
    )
    async def batch_update_subtask_statuses(args: dict[str, Any]) -> dict[str, Any]:
        """Batch update subtask statuses in the implementation plan."""
        updates = args.get("updates", [])

        if not updates:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: No updates provided. 'updates' must be a non-empty list.",
                    }
                ]
            }

        valid_statuses = ["pending", "in_progress", "completed", "failed"]

        # Validate all updates before applying
        validation_errors = []
        for i, update in enumerate(updates):
            if not isinstance(update, dict):
                validation_errors.append(f"Update {i}: Must be a dictionary")
                continue

            if "subtask_id" not in update:
                validation_errors.append(f"Update {i}: Missing 'subtask_id'")
                continue

            if "status" not in update:
                validation_errors.append(f"Update {i}: Missing 'status'")
                continue

            status = update["status"]
            if status not in valid_statuses:
                validation_errors.append(
                    f"Update {i}: Invalid status '{status}'. Must be one of: {valid_statuses}"
                )

        if validation_errors:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Validation failed:\n" + "\n".join(validation_errors),
                    }
                ]
            }

        plan_file = spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: implementation_plan.json not found",
                    }
                ]
            }

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            # Track results
            successful_updates = []
            failed_updates = []

            for update in updates:
                subtask_id = update["subtask_id"]
                status = update["status"]
                notes = update.get("notes", "")

                subtask_found = _update_subtask_in_plan(
                    plan, subtask_id, status, notes
                )

                if subtask_found:
                    successful_updates.append(f"{subtask_id} -> {status}")
                else:
                    failed_updates.append(subtask_id)

            # Use atomic write to prevent file corruption
            write_json_atomic(plan_file, plan, indent=2)

            # Build response message
            response_parts = []
            if successful_updates:
                response_parts.append(
                    f"Successfully updated {len(successful_updates)} subtask(s):\n"
                    + "\n".join(f"  - {update}" for update in successful_updates)
                )
            if failed_updates:
                response_parts.append(
                    f"\nFailed to find {len(failed_updates)} subtask(s):\n"
                    + "\n".join(f"  - {subtask_id}" for subtask_id in failed_updates)
                )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(response_parts),
                    }
                ]
            }

        except json.JSONDecodeError as e:
            # Attempt to auto-fix the plan and retry
            if auto_fix_plan(spec_dir):
                # Retry after fix
                try:
                    with open(plan_file, encoding="utf-8") as f:
                        plan = json.load(f)

                    # Track results
                    successful_updates = []
                    failed_updates = []

                    for update in updates:
                        subtask_id = update["subtask_id"]
                        status = update["status"]
                        notes = update.get("notes", "")

                        subtask_found = _update_subtask_in_plan(
                            plan, subtask_id, status, notes
                        )

                        if subtask_found:
                            successful_updates.append(f"{subtask_id} -> {status}")
                        else:
                            failed_updates.append(subtask_id)

                    if successful_updates or failed_updates:
                        write_json_atomic(plan_file, plan, indent=2)

                    # Build response message
                    response_parts = ["(after auto-fix)"]
                    if successful_updates:
                        response_parts.append(
                            f"Successfully updated {len(successful_updates)} subtask(s):\n"
                            + "\n".join(f"  - {update}" for update in successful_updates)
                        )
                    if failed_updates:
                        response_parts.append(
                            f"\nFailed to find {len(failed_updates)} subtask(s):\n"
                            + "\n".join(f"  - {subtask_id}" for subtask_id in failed_updates)
                        )

                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "\n".join(response_parts),
                            }
                        ]
                    }

                except Exception as retry_err:
                    logging.warning(
                        f"Batch subtask update retry failed after auto-fix: {retry_err}"
                    )
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Batch subtask update failed after auto-fix: {retry_err}",
                            }
                        ]
                    }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid JSON in implementation_plan.json: {e}",
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error batch updating subtask statuses: {e}"}
                ]
            }

    tools.append(batch_update_subtask_statuses)

    return tools
