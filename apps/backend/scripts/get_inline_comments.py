#!/usr/bin/env python3
"""
Get inline review comments from a GitHub PR.

This script:
1. Reads the PR number from command line
2. Creates a GHClient instance
3. Fetches all inline review comments for the PR
4. Returns the comments as JSON

Usage:
    python get_inline_comments.py <project_dir> <pr_number>
"""

import asyncio
import json
import sys
from pathlib import Path


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 3:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "Usage: get_inline_comments.py <project_dir> <pr_number>",
                }
            )
        )
        sys.exit(1)

    project_dir = sys.argv[1]
    try:
        pr_number = int(sys.argv[2])
    except ValueError:
        print(json.dumps({"success": False, "error": "PR number must be an integer"}))
        sys.exit(1)

    # Run the async function
    result = asyncio.run(get_inline_comments(project_dir, pr_number))

    # Print result as JSON
    print(json.dumps(result))

    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


async def get_inline_comments(project_dir: str, pr_number: int) -> dict:
    """
    Get all inline review comments for a PR.

    Args:
        project_dir: Path to the project directory
        pr_number: PR number

    Returns:
        Dict with success status, comments list (if successful), and error (if failed)
    """
    try:
        # Import here to avoid issues if backend is not in Python path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from runners.github.gh_client import GHClient

        # Create GHClient instance
        client = GHClient(Path(project_dir))

        # Fetch inline comments
        comments = await client.get_inline_comments(pr_number)

        return {"success": True, "comments": comments}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()
