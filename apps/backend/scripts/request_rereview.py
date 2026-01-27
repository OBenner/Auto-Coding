#!/usr/bin/env python3
"""
Request re-review on a GitHub PR from specified reviewers.

This script:
1. Reads the PR number and reviewers from command line
2. Creates a GHClient instance
3. Requests re-review from the specified reviewers
4. Returns the result as JSON

Usage:
    python request_rereview.py <project_dir> <pr_number> <reviewers_json> [team_reviewers_json]
"""

import asyncio
import json
import sys
from pathlib import Path


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 4:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "Usage: request_rereview.py <project_dir> <pr_number> <reviewers_json> [team_reviewers_json]",
                }
            )
        )
        sys.exit(1)

    project_dir = sys.argv[1]
    pr_number = int(sys.argv[2])
    reviewers_json = sys.argv[3]
    team_reviewers_json = sys.argv[4] if len(sys.argv) > 4 else "[]"

    # Parse reviewers JSON
    try:
        reviewers = json.loads(reviewers_json)
        team_reviewers = json.loads(team_reviewers_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    # Run the async function
    result = asyncio.run(request_rereview(project_dir, pr_number, reviewers, team_reviewers))

    # Print result as JSON
    print(json.dumps(result))

    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


async def request_rereview(
    project_dir: str, pr_number: int, reviewers: list[str], team_reviewers: list[str] | None = None
) -> dict:
    """
    Request re-review on a GitHub PR.

    Args:
        project_dir: Path to the project directory
        pr_number: PR number
        reviewers: List of GitHub usernames to request review from
        team_reviewers: Optional list of GitHub team slugs to request review from

    Returns:
        Dict with success status and error (if failed)
    """
    try:
        # Import here to avoid issues if backend is not in Python path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from runners.github.gh_client import GHClient

        # Create GHClient instance
        client = GHClient(Path(project_dir))

        # Request re-review
        await client.request_rereview(pr_number, reviewers, team_reviewers)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()
