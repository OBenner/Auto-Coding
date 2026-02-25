#!/usr/bin/env python3
"""
Apply a suggested change from a GitHub PR review comment.

This script accepts a GitHub comment object and:
1. Extracts the suggested code from ```suggestion``` markdown blocks
2. Reads the original file to get the code being replaced
3. Applies the change and creates a commit
4. Pushes to the remote branch

Usage:
    python apply_suggestion.py <project_dir> <pr_number> <comment_json> [commit_message]
"""

import asyncio
import json
import re
import sys
from pathlib import Path


def parse_suggestion_from_comment(comment: dict, project_dir: str) -> dict:
    """
    Parse a GitHub comment to extract suggestion details.

    Args:
        comment: GitHub comment with body, path, line fields
        project_dir: Path to the project directory (for reading original file)

    Returns:
        dict with path, start_line, end_line, original_code, suggested_code, reasoning
    """
    body = comment.get("body", "")
    path = comment.get("path", "")
    line = comment.get("line", 1)

    # Extract suggested code from ```suggestion``` block
    suggestion_match = re.search(r"```suggestion\s*\n([\s\S]*?)\n```", body)
    if not suggestion_match:
        raise ValueError("No suggestion block found in comment body")

    suggested_code = suggestion_match.group(1)

    # Extract reasoning (text before the suggestion block)
    reasoning_text = body.split("```suggestion")[0].strip()
    reasoning = (
        reasoning_text if reasoning_text else "Apply suggested change from code review"
    )

    # Read the original file to get the code being replaced
    file_path = Path(project_dir) / path
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Determine line range based on suggestion length
    # If suggestion has N lines, replace N lines starting from comment.line
    suggested_lines = suggested_code.split("\n")
    num_lines = len(suggested_lines)

    start_line = line
    end_line = line + num_lines - 1

    # Get original code
    if start_line <= len(lines):
        end_line = min(end_line, len(lines))
        original_code = "".join(lines[start_line - 1 : end_line])
    else:
        original_code = ""

    return {
        "path": path,
        "start_line": start_line,
        "end_line": end_line,
        "original_code": original_code,
        "suggested_code": suggested_code,
        "reasoning": reasoning,
    }


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 4:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "Usage: apply_suggestion.py <project_dir> <pr_number> <comment_json> [commit_message]",
                }
            )
        )
        sys.exit(1)

    project_dir = sys.argv[1]
    pr_number = int(sys.argv[2])
    comment_json = sys.argv[3]
    commit_message = sys.argv[4] if len(sys.argv) > 4 else None

    # Parse comment JSON
    try:
        comment = json.loads(comment_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid comment JSON: {e}"}))
        sys.exit(1)

    # Transform comment into suggestion format
    try:
        suggestion = parse_suggestion_from_comment(comment, project_dir)
    except Exception as e:
        print(
            json.dumps({"success": False, "error": f"Failed to parse suggestion: {e}"})
        )
        sys.exit(1)

    # Run the async function
    result = asyncio.run(
        apply_suggestion(project_dir, pr_number, suggestion, commit_message)
    )

    # Print result as JSON
    print(json.dumps(result))

    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


async def apply_suggestion(
    project_dir: str,
    pr_number: int,
    suggestion: dict,
    commit_message: str | None = None,
) -> dict:
    """
    Apply a suggested change to a PR.

    Args:
        project_dir: Path to the project directory
        pr_number: PR number
        suggestion: Suggestion data with path, start_line, end_line, suggested_code
        commit_message: Optional custom commit message

    Returns:
        Dict with success, commit_sha (if successful), and error (if failed)
    """
    try:
        # Import here to avoid issues if backend is not in Python path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from runners.github.gh_client import GHClient

        # Create GHClient instance
        client = GHClient(Path(project_dir))

        # Apply the suggestion
        result = await client.apply_suggestion(pr_number, suggestion, commit_message)

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()
