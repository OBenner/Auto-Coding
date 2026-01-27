"""
QA Management Tools
===================

Tools for managing QA status and sign-off in implementation_plan.json.
"""

import json
import logging
from datetime import datetime, timezone
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


def _apply_qa_update(
    plan: dict[str, Any],
    status: str,
    issues: list[Any],
    tests_passed: dict[str, Any],
) -> int:
    """
    Apply QA update to the plan and return the new QA session number.

    Args:
        plan: The implementation plan dict
        status: QA status (pending, in_review, approved, rejected, fixes_applied)
        issues: List of issues found
        tests_passed: Dict of test results

    Returns:
        The new QA session number
    """
    # Get current QA session number
    current_qa = plan.get("qa_signoff", {})
    qa_session = current_qa.get("qa_session", 0)
    if status in ["in_review", "rejected"]:
        qa_session += 1

    plan["qa_signoff"] = {
        "status": status,
        "qa_session": qa_session,
        "issues_found": issues,
        "tests_passed": tests_passed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ready_for_qa_revalidation": status == "fixes_applied",
    }

    # Update plan status to match QA result
    # This ensures the UI shows the correct column after QA
    if status == "approved":
        plan["status"] = "human_review"
        plan["planStatus"] = "review"
    elif status == "rejected":
        plan["status"] = "human_review"
        plan["planStatus"] = "review"

    plan["last_updated"] = datetime.now(timezone.utc).isoformat()

    return qa_session


def create_qa_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create QA management tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of QA tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: update_qa_status
    # -------------------------------------------------------------------------
    @tool(
        "update_qa_status",
        "Update the QA sign-off status in implementation_plan.json. Use after QA review.",
        {"status": str, "issues": str, "tests_passed": str},
    )
    async def update_qa_status(args: dict[str, Any]) -> dict[str, Any]:
        """Update QA status in the implementation plan."""
        status = args["status"]
        issues_str = args.get("issues", "[]")
        tests_str = args.get("tests_passed", "{}")

        valid_statuses = [
            "pending",
            "in_review",
            "approved",
            "rejected",
            "fixes_applied",
        ]
        if status not in valid_statuses:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid QA status '{status}'. Must be one of: {valid_statuses}",
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
            # Parse issues and tests
            try:
                issues = json.loads(issues_str) if issues_str else []
            except json.JSONDecodeError:
                issues = [{"description": issues_str}] if issues_str else []

            try:
                tests_passed = json.loads(tests_str) if tests_str else {}
            except json.JSONDecodeError:
                tests_passed = {}

            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            qa_session = _apply_qa_update(plan, status, issues, tests_passed)

            # Use atomic write to prevent file corruption
            write_json_atomic(plan_file, plan, indent=2)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Updated QA status to '{status}' (session {qa_session})",
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

                    qa_session = _apply_qa_update(plan, status, issues, tests_passed)
                    write_json_atomic(plan_file, plan, indent=2)

                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Updated QA status to '{status}' (session {qa_session}) (after auto-fix)",
                            }
                        ]
                    }
                except Exception as retry_err:
                    logging.warning(
                        f"QA update retry failed after auto-fix: {retry_err} (original error: {e})"
                    )
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: QA update failed after auto-fix: {retry_err} (original JSON error: {e})",
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
                "content": [{"type": "text", "text": f"Error updating QA status: {e}"}]
            }

    tools.append(update_qa_status)

    # -------------------------------------------------------------------------
    # Tool: get_qa_status
    # -------------------------------------------------------------------------
    @tool(
        "get_qa_status",
        "Get the current QA sign-off status from implementation_plan.json. Use this to check if QA has been run and what the results were.",
        {},
    )
    async def get_qa_status(args: dict[str, Any]) -> dict[str, Any]:
        """Get current QA status from the implementation plan."""
        plan_file = spec_dir / "implementation_plan.json"

        if not plan_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "No implementation plan found. Run the planner first.",
                    }
                ]
            }

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            qa_signoff = plan.get("qa_signoff", {})

            if not qa_signoff:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "QA has not been run yet. Status: pending",
                        }
                    ]
                }

            status = qa_signoff.get("status", "pending")
            qa_session = qa_signoff.get("qa_session", 0)
            timestamp = qa_signoff.get("timestamp", "N/A")
            ready_for_revalidation = qa_signoff.get("ready_for_qa_revalidation", False)
            issues = qa_signoff.get("issues_found", [])
            tests_passed = qa_signoff.get("tests_passed", {})

            result = f"""QA Status: {status}
QA Session: {qa_session}
Timestamp: {timestamp}
Ready for QA Revalidation: {ready_for_revalidation}"""

            if issues:
                result += f"\n\nIssues Found: {len(issues)}"
                for i, issue in enumerate(issues, 1):
                    issue_desc = issue.get("description", str(issue))
                    result += f"\n  {i}. {issue_desc}"
            else:
                result += "\n\nIssues Found: None"

            if tests_passed:
                result += "\n\nTests Passed:"
                for test_name, passed in tests_passed.items():
                    status_str = "✓" if passed else "✗"
                    result += f"\n  {status_str} {test_name}"

            return {"content": [{"type": "text", "text": result}]}

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error reading QA status: {e}"}
                ]
            }

    tools.append(get_qa_status)

    return tools
