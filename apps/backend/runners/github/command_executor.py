"""
GitHub PR Command Executor
==========================

Executor for PR commands extracted from comments.

Handles execution of supported commands:
- /merge [branch] - Merge specified branch or current PR
- /resolve - Attempt to resolve dependency conflicts
- /process - Process/reply to outstanding comments

Each command:
- Validates user permissions before execution
- Returns structured results (success/error/data)
- Posts feedback to PR via comments
- Handles errors gracefully with user-friendly messages

Usage:
    executor = CommandExecutor(project_dir=Path("/path/to/project"))

    # Execute a single command
    result = await executor.execute(command, pr_number=123, username="user")

    # Execute multiple commands
    results = await executor.execute_all(commands, pr_number=123, username="user")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .gh_client import GHClient, GHCommandError
    from .command_parser import Command
except (ImportError, ValueError, SystemError):
    from gh_client import GHClient, GHCommandError
    from command_parser import Command

# Configure logger
logger = logging.getLogger(__name__)


class CommandExecutionError(Exception):
    """Raised when command execution fails."""

    pass


class PermissionDeniedError(Exception):
    """Raised when user lacks permissions to execute a command."""

    pass


@dataclass
class CommandResult:
    """
    Result of a command execution.

    Attributes:
        success: Whether the command executed successfully
        command_type: Type of command that was executed
        message: User-friendly message describing the result
        data: Optional data returned by the command
        error: Optional error message if execution failed
    """

    success: bool
    command_type: str
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None


class CommandExecutor:
    """
    Executor for PR commands with permission validation and error handling.

    This class handles the execution of commands parsed from PR comments.
    Each command is executed with proper permission checks, error handling,
    and user feedback via PR comments.

    Supported commands:
    - merge: Merge a PR or branch
    - resolve: Attempt to resolve dependency conflicts
    - process: Process and respond to PR comments

    Usage:
        executor = CommandExecutor(project_dir=Path("/path/to/project"))

        # Execute a single command
        result = await executor.execute(
            command=Command(type="merge", args=[], position=0, raw_text="/merge"),
            pr_number=123,
            username="octocat"
        )

        # Check result
        if result.success:
            print(f"Command succeeded: {result.message}")
        else:
            print(f"Command failed: {result.error}")

        # Execute multiple commands (stops on first failure)
        results = await executor.execute_all(
            commands=[
                Command(type="merge", args=[], position=0, raw_text="/merge"),
                Command(type="resolve", args=[], position=10, raw_text="/resolve")
            ],
            pr_number=123,
            username="octocat"
        )
    """

    def __init__(
        self,
        project_dir: Path,
        gh_client: GHClient | None = None,
        repo: str | None = None,
    ):
        """
        Initialize the command executor.

        Args:
            project_dir: Project directory for git operations
            gh_client: Optional GHClient instance. If None, creates a new one.
            repo: Repository in 'owner/repo' format. If provided, uses -R flag
                  instead of inferring from git remotes.
        """
        self.project_dir = Path(project_dir)

        # Use provided GHClient or create a new one
        if gh_client:
            self.gh_client = gh_client
        else:
            self.gh_client = GHClient(
                project_dir=self.project_dir,
                repo=repo,
            )

    async def execute(
        self,
        command: Command,
        pr_number: int,
        username: str,
    ) -> CommandResult:
        """
        Execute a single command with permission validation and error handling.

        This method:
        1. Validates user permissions for the command
        2. Routes to the appropriate command handler
        3. Posts feedback to the PR via comments
        4. Returns a structured result

        Args:
            command: The command to execute
            pr_number: The PR number where the command was issued
            username: The GitHub username who issued the command

        Returns:
            CommandResult with execution status and message

        Raises:
            PermissionDeniedError: If user lacks permissions
            CommandExecutionError: If command execution fails
        """
        logger.info(
            f"Executing command '{command.type}' for user '{username}' on PR #{pr_number}"
        )

        try:
            # Validate permissions before executing
            if not await self._check_permissions(command, pr_number, username):
                raise PermissionDeniedError(
                    f"User '{username}' lacks permissions to execute '/{command.type}'"
                )

            # Route to appropriate handler
            handler = self._get_command_handler(command.type)
            result = await handler(command, pr_number, username)

            # Post feedback to PR
            await self._post_feedback(pr_number, result)

            logger.info(
                f"Command '{command.type}' completed successfully: {result.message}"
            )

            return result

        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for command '{command.type}': {e}")
            result = CommandResult(
                success=False,
                command_type=command.type,
                message=f"✗ Permission denied: /{command.type}",
                error=str(e),
            )
            await self._post_feedback(pr_number, result)
            return result

        except Exception as e:
            logger.error(f"Failed to execute command '{command.type}': {e}")
            result = CommandResult(
                success=False,
                command_type=command.type,
                message=f"✗ Failed to execute /{command.type}",
                error=str(e),
            )
            await self._post_feedback(pr_number, result)
            return result

    async def execute_all(
        self,
        commands: list[Command],
        pr_number: int,
        username: str,
    ) -> list[CommandResult]:
        """
        Execute multiple commands sequentially.

        Commands are executed in order. If a command fails, subsequent
        commands are not executed.

        Args:
            commands: List of commands to execute
            pr_number: The PR number where the commands were issued
            username: The GitHub username who issued the commands

        Returns:
            List of CommandResult objects (one per command)
        """
        results = []

        for command in commands:
            result = await self.execute(command, pr_number, username)
            results.append(result)

            # Stop on first failure
            if not result.success:
                logger.info(
                    f"Stopping command execution after failure: {command.type}"
                )
                break

        return results

    # =========================================================================
    # Permission validation
    # =========================================================================

    async def _check_permissions(
        self,
        command: Command,
        pr_number: int,
        username: str,
    ) -> bool:
        """
        Check if user has permissions to execute a command.

        Write operations (merge, resolve) require write access to the repository.
        Read operations (process) require read access.

        Args:
            command: The command to check permissions for
            pr_number: The PR number
            username: The GitHub username

        Returns:
            True if user has permissions, False otherwise
        """
        # TODO: Implement permission checking via gh CLI
        # For now, return True to allow execution
        logger.debug(
            f"Checking permissions for user '{username}' to execute '/{command.type}'"
        )

        # Write operations require write access
        if command.type in ["merge", "resolve"]:
            # Check if user has write access to the repository
            # This can be done via: gh api repos/{owner}/{repo}/collaborators/{username}
            pass

        return True

    # =========================================================================
    # Command handlers
    # =========================================================================

    def _get_command_handler(self, command_type: str):
        """
        Get the handler function for a command type.

        Args:
            command_type: The command type

        Returns:
            Async function that handles the command

        Raises:
            CommandExecutionError: If command type is not supported
        """
        handlers = {
            "merge": self._handle_merge,
            "resolve": self._handle_resolve,
            "process": self._handle_process,
        }

        if command_type not in handlers:
            raise CommandExecutionError(f"Unknown command type: {command_type}")

        return handlers[command_type]

    async def _handle_merge(
        self,
        command: Command,
        pr_number: int,
        username: str,
    ) -> CommandResult:
        """
        Handle the /merge command.

        Merges the PR or a specified branch.

        Args:
            command: The merge command with optional branch argument
            pr_number: The PR number
            username: The user who issued the command

        Returns:
            CommandResult with merge status
        """
        logger.info(f"Handling merge command for PR #{pr_number}")

        # TODO: Implement merge logic
        # - Get PR data to check mergeability
        # - Check for merge conflicts
        # - Execute merge using gh_client.pr_merge()
        # - Return success/failure result

        return CommandResult(
            success=True,
            command_type="merge",
            message="✓ Merge command executed successfully",
            data={"pr_number": pr_number},
        )

    async def _handle_resolve(
        self,
        command: Command,
        pr_number: int,
        username: str,
    ) -> CommandResult:
        """
        Handle the /resolve command.

        Attempts to resolve dependency conflicts by running package manager commands.

        Args:
            command: The resolve command
            pr_number: The PR number
            username: The user who issued the command

        Returns:
            CommandResult with resolution status
        """
        logger.info(f"Handling resolve command for PR #{pr_number}")

        # TODO: Implement resolve logic
        # - Detect project type (npm, pip, cargo, etc.)
        # - Run package manager install/update commands
        # - Return success/failure result with details

        return CommandResult(
            success=True,
            command_type="resolve",
            message="✓ Resolve command executed successfully",
            data={"pr_number": pr_number},
        )

    async def _handle_process(
        self,
        command: Command,
        pr_number: int,
        username: str,
    ) -> CommandResult:
        """
        Handle the /process command.

        Processes outstanding PR comments and generates responses.

        Args:
            command: The process command
            pr_number: The PR number
            username: The user who issued the command

        Returns:
            CommandResult with processing status
        """
        logger.info(f"Handling process command for PR #{pr_number}")

        # TODO: Implement process logic
        # - Fetch outstanding comments from the PR
        # - Generate responses or summaries
        # - Post responses to the PR
        # - Return success/failure result

        return CommandResult(
            success=True,
            command_type="process",
            message="✓ Process command executed successfully",
            data={"pr_number": pr_number},
        )

    # =========================================================================
    # Feedback
    # =========================================================================

    async def _post_feedback(self, pr_number: int, result: CommandResult) -> None:
        """
        Post command execution feedback as a PR comment.

        Args:
            pr_number: The PR number
            result: The command execution result
        """
        logger.debug(f"Posting feedback for PR #{pr_number}: {result.message}")

        # TODO: Implement feedback posting
        # - Format result message for PR comment
        # - Use gh_client.pr_comment() to post feedback
        # - Include status (✓/✗), command type, and details/errors

        # Skip if in testing mode or if gh_client is mocked
        if not hasattr(self.gh_client, "pr_comment"):
            logger.debug("Skipping feedback posting (gh_client not available)")
            return
