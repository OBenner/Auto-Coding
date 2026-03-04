"""
GitHub PR Commands Integration Tests
====================================

This test suite verifies the end-to-end command flow:
1. Command parsing from PR comments
2. Command execution with permission validation
3. Feedback posting via PR comments
4. Error handling and edge cases
5. Multiple command execution

Test scenarios:
- End-to-end command flow (merge, resolve, process)
- Permission validation integration
- Error handling and feedback posting
- Multiple commands in sequence
- Audit trail generation
- Integration with orchestrator
"""

import logging
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from runners.github.command_executor import CommandExecutor
from runners.github.command_parser import CommandParser

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST - GITHUB COMMANDS")
    print("=" * 70)

    yield  # Run test

    print("✅ Test completed\n")


class MockGHClient:
    """Mock GHClient for integration testing."""

    def __init__(self):
        self.pr_merge_called = False
        self.pr_comment_called = False
        self.get_inline_comments_called = False
        self.merge_method = None
        self.comments_posted = []
        self.inline_comments = []

    async def pr_merge(
        self, pr_number: int, merge_method: str = "merge"
    ) -> dict[str, Any]:
        """Mock PR merge."""
        self.pr_merge_called = True
        self.merge_method = merge_method
        # Simulate successful merge
        return {"merged": True, "pr_number": pr_number}

    async def pr_comment(self, pr_number: int, body: str) -> None:
        """Mock PR comment posting."""
        self.pr_comment_called = True
        self.comments_posted.append({"pr_number": pr_number, "body": body})
        logger.debug(f"Mock: Posted comment to PR #{pr_number}: {body[:100]}...")

    async def get_inline_comments(self, pr_number: int) -> list[dict[str, Any]]:
        """Mock inline comment retrieval."""
        self.get_inline_comments_called = True
        return self.inline_comments


class MockPermissionChecker:
    """Mock GitHubPermissionChecker for integration testing."""

    def __init__(self, allowed: bool = True, role: str = "OWNER"):
        self.allowed = allowed
        self.role = role
        self.permission_checks = []

    async def is_allowed_for_autofix(self, username: str):
        """Mock permission check for autofix (write operations)."""
        self.permission_checks.append(("is_allowed_for_autofix", username))
        result = MagicMock()
        result.allowed = self.allowed
        result.role = self.role
        result.reason = (
            "User has sufficient permissions"
            if self.allowed
            else "Insufficient permissions"
        )
        return result

    async def get_user_role(self, username: str):
        """Mock get user role."""
        self.permission_checks.append(("get_user_role", username))
        return self.role

    async def verify_token_scopes(self):
        """Mock token scope verification."""
        pass


@pytest.mark.asyncio
async def test_end_to_end_merge_command():
    """Test end-to-end flow for /merge command."""
    print("\nTEST 1: End-to-End Merge Command")
    print("-" * 70)

    # Setup
    project_dir = Path(tempfile.gettempdir()) / "test_project"
    comment_text = "/merge"
    pr_number = 123
    username = "testuser"

    # Mock GHClient
    mock_gh_client = MockGHClient()

    # Mock permission checker
    mock_permission_checker = MockPermissionChecker(allowed=True, role="MEMBER")

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    print(f"  Parsed {len(commands)} command(s): {[c.type for c in commands]}")
    assert len(commands) == 1
    assert commands[0].type == "merge"
    print("  ✓ Command parsed successfully")

    # Create executor with mocked dependencies
    executor = CommandExecutor(
        project_dir=project_dir, gh_client=mock_gh_client, repo="owner/repo"
    )
    # Replace permission checker with mock
    executor._permission_checker = mock_permission_checker

    # Execute command
    result = await executor.execute(commands[0], pr_number, username)

    # Verify result
    assert result.success is True
    assert result.command_type == "merge"
    assert "merged" in result.message.lower()
    print(f"  ✓ Command executed successfully: {result.message}")

    # Verify GHClient was called
    assert mock_gh_client.pr_merge_called is True
    assert mock_gh_client.merge_method == "squash"  # Default method
    print("  ✓ PR merge called via GHClient")

    # Verify feedback was posted
    assert mock_gh_client.pr_comment_called is True
    assert len(mock_gh_client.comments_posted) == 1
    comment_body = mock_gh_client.comments_posted[0]["body"]
    assert "/merge" in comment_body
    assert "✓" in comment_body  # Success indicator
    print("  ✓ Feedback comment posted to PR")

    print("✅ TEST 1 PASSED\n")


@pytest.mark.asyncio
async def test_end_to_end_resolve_command():
    """Test end-to-end flow for /resolve command."""
    print("\nTEST 2: End-to-End Resolve Command")
    print("-" * 70)

    # Setup
    comment_text = "/resolve"
    pr_number = 456
    username = "testuser"

    # Create a temporary package.json file for detection
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        package_json = project_dir / "package.json"
        package_json.write_text('{"name": "test", "version": "1.0.0"}')

        # Mock GHClient
        mock_gh_client = MockGHClient()

        # Mock permission checker
        mock_permission_checker = MockPermissionChecker(allowed=True, role="MEMBER")

        # Create parser
        parser = CommandParser()
        commands = parser.parse(comment_text)

        print(f"  Parsed {len(commands)} command(s): {[c.type for c in commands]}")
        assert len(commands) == 1
        assert commands[0].type == "resolve"
        print("  ✓ Command parsed successfully")

        # Create executor
        executor = CommandExecutor(
            project_dir=project_dir, gh_client=mock_gh_client, repo="owner/repo"
        )
        executor._permission_checker = mock_permission_checker

        # Mock asyncio.create_subprocess_exec to avoid actual npm install
        async def mock_subprocess_exec(*args, **kwargs):
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"packages installed", b"")
            )
            return mock_process

        with patch("asyncio.create_subprocess_exec", side_effect=mock_subprocess_exec):
            # Execute command
            result = await executor.execute(commands[0], pr_number, username)

        # Verify result
        assert result.success is True
        assert result.command_type == "resolve"
        assert "resolved" in result.message.lower()
        print(f"  ✓ Command executed successfully: {result.message}")

        # Verify package manager was detected
        assert result.data is not None
        assert result.data.get("package_manager") == "npm"
        print("  ✓ Package manager detected: npm")

        # Verify feedback was posted
        assert mock_gh_client.pr_comment_called is True
        comment_body = mock_gh_client.comments_posted[0]["body"]
        assert "/resolve" in comment_body
        assert "✓" in comment_body
        print("  ✓ Feedback comment posted to PR")

    print("✅ TEST 2 PASSED\n")


@pytest.mark.asyncio
async def test_end_to_end_process_command():
    """Test end-to-end flow for /process command."""
    print("\nTEST 3: End-to-End Process Command")
    print("-" * 70)

    # Setup
    project_dir = Path(tempfile.gettempdir()) / "test_project"
    comment_text = "/process"
    pr_number = 789
    username = "testuser"

    # Mock GHClient with inline comments
    mock_gh_client = MockGHClient()
    mock_gh_client.inline_comments = [
        {
            "id": 1,
            "path": "src/main.py",
            "line": 42,
            "body": "Consider adding error handling here",
            "user": {"login": "reviewer1"},
        },
        {
            "id": 2,
            "path": "src/utils.py",
            "line": 15,
            "body": "This function could be simplified",
            "user": {"login": "reviewer2"},
        },
    ]

    # Mock permission checker (process is read-only, so less strict)
    mock_permission_checker = MockPermissionChecker(allowed=True, role="CONTRIBUTOR")

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    print(f"  Parsed {len(commands)} command(s): {[c.type for c in commands]}")
    assert len(commands) == 1
    assert commands[0].type == "process"
    print("  ✓ Command parsed successfully")

    # Create executor
    executor = CommandExecutor(
        project_dir=project_dir, gh_client=mock_gh_client, repo="owner/repo"
    )
    executor._permission_checker = mock_permission_checker

    # Execute command
    result = await executor.execute(commands[0], pr_number, username)

    # Verify result
    assert result.success is True
    assert result.command_type == "process"
    assert "processed" in result.message.lower()
    print(f"  ✓ Command executed successfully: {result.message}")

    # Verify comments were fetched
    assert mock_gh_client.get_inline_comments_called is True
    print("  ✓ Inline comments fetched from PR")

    # Verify result data
    assert result.data is not None
    assert result.data.get("comment_count") == 2
    assert result.data.get("files_affected") == 2
    print("  ✓ Comment data processed correctly")

    # Verify feedback was posted (2 comments: summary + feedback)
    assert mock_gh_client.pr_comment_called is True
    assert len(mock_gh_client.comments_posted) >= 1
    # The last comment posted should be the feedback
    feedback_comment = mock_gh_client.comments_posted[-1]["body"]
    assert "/process" in feedback_comment
    assert "✓" in feedback_comment
    print("  ✓ Feedback comment posted to PR")

    print("✅ TEST 3 PASSED\n")


@pytest.mark.asyncio
async def test_permission_denied_flow():
    """Test end-to-end flow when user lacks permissions."""
    print("\nTEST 4: Permission Denied Flow")
    print("-" * 70)

    # Setup
    project_dir = Path(tempfile.gettempdir()) / "test_project"
    comment_text = "/merge"
    pr_number = 999
    username = "unauthorized_user"

    # Mock GHClient
    mock_gh_client = MockGHClient()

    # Mock permission checker - user not allowed
    mock_permission_checker = MockPermissionChecker(allowed=False, role="NONE")

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    print(f"  Parsed {len(commands)} command(s): {[c.type for c in commands]}")
    print("  ✓ Command parsed successfully")

    # Create executor
    executor = CommandExecutor(
        project_dir=project_dir, gh_client=mock_gh_client, repo="owner/repo"
    )
    executor._permission_checker = mock_permission_checker

    # Execute command
    result = await executor.execute(commands[0], pr_number, username)

    # Verify permission was denied
    assert result.success is False
    assert result.command_type == "merge"
    assert "permission" in result.message.lower()
    print(f"  ✓ Permission denied correctly: {result.message}")

    # Verify GHClient merge was NOT called
    assert mock_gh_client.pr_merge_called is False
    print("  ✓ PR merge was NOT called (permission denied)")

    # Verify feedback was still posted
    assert mock_gh_client.pr_comment_called is True
    comment_body = mock_gh_client.comments_posted[0]["body"]
    assert "✗" in comment_body  # Failure indicator
    assert "permission" in comment_body.lower()
    print("  ✓ Feedback comment posted with permission error")

    print("✅ TEST 4 PASSED\n")


@pytest.mark.asyncio
async def test_multiple_commands_sequential_execution():
    """Test executing multiple commands sequentially with stop on failure."""
    print("\nTEST 5: Multiple Commands Sequential Execution")
    print("-" * 70)

    # Setup
    project_dir = Path(tempfile.gettempdir()) / "test_project"
    comment_text = "/process and /merge"
    pr_number = 111
    username = "testuser"

    # Mock GHClient
    mock_gh_client = MockGHClient()
    mock_gh_client.inline_comments = []  # No comments

    # Mock permission checker
    mock_permission_checker = MockPermissionChecker(allowed=True, role="MEMBER")

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    print(f"  Parsed {len(commands)} command(s): {[c.type for c in commands]}")
    assert len(commands) == 2
    print("  ✓ Commands parsed successfully")

    # Create executor
    executor = CommandExecutor(
        project_dir=project_dir, gh_client=mock_gh_client, repo="owner/repo"
    )
    executor._permission_checker = mock_permission_checker

    # Execute all commands
    results = await executor.execute_all(commands, pr_number, username)

    # Verify both commands executed
    assert len(results) == 2
    assert results[0].command_type == "process"
    assert results[0].success is True
    assert results[1].command_type == "merge"
    assert results[1].success is True
    print("  ✓ Both commands executed successfully")

    # Verify feedback posted for both (at least one per command)
    assert len(mock_gh_client.comments_posted) >= 2
    print("  ✓ Feedback comments posted for both commands")

    print("✅ TEST 5 PASSED\n")


@pytest.mark.asyncio
async def test_command_failure_stops_execution():
    """Test that command execution stops on first failure."""
    print("\nTEST 6: Command Failure Stops Execution")
    print("-" * 70)

    # Setup
    project_dir = Path(tempfile.gettempdir()) / "test_project"
    comment_text = "/merge and /resolve"
    pr_number = 222
    username = "testuser"

    # Mock GHClient - make merge fail
    mock_gh_client = MockGHClient()

    async def mock_failing_merge(pr_number: int, merge_method: str = "merge"):
        # Raise generic Exception which will be caught by the generic Exception handler
        # This simulates an unexpected error during merge
        raise Exception("Merge failed due to conflicts")

    mock_gh_client.pr_merge = mock_failing_merge

    # Mock permission checker
    mock_permission_checker = MockPermissionChecker(allowed=True, role="MEMBER")

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    print(f"  Parsed {len(commands)} command(s): {[c.type for c in commands]}")
    assert len(commands) == 2
    print("  ✓ Commands parsed successfully")

    # Create executor
    executor = CommandExecutor(
        project_dir=project_dir, gh_client=mock_gh_client, repo="owner/repo"
    )
    executor._permission_checker = mock_permission_checker

    # Execute all commands
    results = await executor.execute_all(commands, pr_number, username)

    # Verify only first command executed (failed)
    assert len(results) == 1
    assert results[0].command_type == "merge"
    assert results[0].success is False
    # Verify it's an error (regardless of the specific message)
    assert (
        "failed" in results[0].message.lower() or "error" in results[0].message.lower()
    )
    print(f"  ✓ First command failed as expected: {results[0].message}")

    # Verify second command was NOT executed
    print("  ✓ Second command was not executed (stopped on failure)")

    print("✅ TEST 6 PASSED\n")


@pytest.mark.asyncio
async def test_no_commands_in_comment():
    """Test handling when no commands are present in comment."""
    print("\nTEST 7: No Commands in Comment")
    print("-" * 70)

    # Setup
    comment_text = "This is just a regular comment with no commands"

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    print(f"  Parsed {len(commands)} command(s)")
    assert len(commands) == 0
    print("  ✓ No commands detected (correct)")

    print("✅ TEST 7 PASSED\n")


@pytest.mark.asyncio
async def test_unknown_command_ignored():
    """Test that unknown commands are ignored gracefully."""
    print("\nTEST 8: Unknown Command Ignored")
    print("-" * 70)

    # Setup
    comment_text = "/unknown-command"

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    print(f"  Parsed {len(commands)} command(s)")
    assert len(commands) == 0
    print("  ✓ Unknown command ignored (correct)")

    print("✅ TEST 8 PASSED\n")


@pytest.mark.asyncio
async def test_mixed_known_and_unknown_commands():
    """Test parsing mixed known and unknown commands."""
    print("\nTEST 9: Mixed Known and Unknown Commands")
    print("-" * 70)

    # Setup
    project_dir = Path(tempfile.gettempdir()) / "test_project"
    comment_text = "/process and /unknown then /merge"
    pr_number = 333
    username = "testuser"

    # Mock GHClient
    mock_gh_client = MockGHClient()
    mock_gh_client.inline_comments = []

    # Mock permission checker
    mock_permission_checker = MockPermissionChecker(allowed=True, role="MEMBER")

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    print(f"  Parsed {len(commands)} command(s): {[c.type for c in commands]}")
    # Should only parse known commands (process, merge)
    assert len(commands) == 2
    assert commands[0].type == "process"
    assert commands[1].type == "merge"
    print("  ✓ Unknown commands filtered out correctly")

    # Create executor
    executor = CommandExecutor(
        project_dir=project_dir, gh_client=mock_gh_client, repo="owner/repo"
    )
    executor._permission_checker = mock_permission_checker

    # Execute all commands
    results = await executor.execute_all(commands, pr_number, username)

    # Verify both known commands executed
    assert len(results) == 2
    assert all(r.success for r in results)
    print("  ✓ All known commands executed successfully")

    print("✅ TEST 9 PASSED\n")


@pytest.mark.asyncio
async def test_audit_trail_logging(caplog):
    """Test that audit trail is logged for command execution."""
    print("\nTEST 10: Audit Trail Logging")
    print("-" * 70)

    # Setup
    project_dir = Path(tempfile.gettempdir()) / "test_project"
    comment_text = "/merge"
    pr_number = 444
    username = "audituser"

    # Mock GHClient
    mock_gh_client = MockGHClient()

    # Mock permission checker
    mock_permission_checker = MockPermissionChecker(allowed=True, role="MEMBER")

    # Create parser
    parser = CommandParser()
    commands = parser.parse(comment_text)

    # Create executor with audit capture
    executor = CommandExecutor(
        project_dir=project_dir, gh_client=mock_gh_client, repo="owner/repo"
    )
    executor._permission_checker = mock_permission_checker

    # Execute command and capture logs via pytest caplog fixture
    with caplog.at_level(logging.INFO, logger="runners.github.command_executor"):
        await executor.execute(commands[0], pr_number, username)

    # Verify audit logging
    assert "AUDIT:" in caplog.text
    assert "attempt" in caplog.text
    assert "success" in caplog.text
    assert username in caplog.text
    assert str(pr_number) in caplog.text
    print("  ✓ Audit trail logged correctly")

    print("✅ TEST 10 PASSED\n")


def main():
    """Run all integration tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "GITHUB COMMANDS INTEGRATION TESTS" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")

    # Run pytest programmatically
    import pytest as pt

    exit_code = pt.main([__file__, "-v", "-s"])

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
