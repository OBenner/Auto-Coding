#!/usr/bin/env python3
"""
Reply to an inline review comment on a GitHub PR.

This script:
1. Reads the comment ID and reply body from command line
2. Creates a GHClient instance
3. Posts a reply to the inline comment
4. Returns the result as JSON

Usage:
    python reply_to_comment.py <project_dir> <comment_id> <body>
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
                    "error": "Usage: reply_to_comment.py <project_dir> <comment_id> <body>",
                }
            )
        )
        sys.exit(1)

    project_dir = sys.argv[1]
    try:
        comment_id = int(sys.argv[2])
    except ValueError:
        print(json.dumps({"success": False, "error": "Comment ID must be an integer"}))
        sys.exit(1)

    body = sys.argv[3]

    # Validate body is not empty
    if not body or not body.strip():
        print(json.dumps({"success": False, "error": "Reply body cannot be empty"}))
        sys.exit(1)

    # Run the async function
    result = asyncio.run(reply_to_comment(project_dir, comment_id, body))

    # Print result as JSON
    print(json.dumps(result))

    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


async def reply_to_comment(project_dir: str, comment_id: int, body: str) -> dict:
    """
    Reply to an inline review comment.

    Args:
        project_dir: Path to the project directory
        comment_id: ID of the comment to reply to
        body: Reply text

    Returns:
        Dict with success status, reply data (if successful), and error (if failed)
    """
    try:
        # Import here to avoid issues if backend is not in Python path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from runners.github.gh_client import GHClient

        # Create GHClient instance
        client = GHClient(Path(project_dir))

        # Post reply
        reply = await client.reply_to_comment(comment_id, body)

        return {"success": True, "reply": reply}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()
