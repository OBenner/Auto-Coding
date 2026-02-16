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

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .gh_client import GHClient, GHCommandError
    from .command_parser import Command
    from .permissions import GitHubPermissionChecker, PermissionError
except (ImportError, ValueError, SystemError):
    from gh_client import GHClient, GHCommandError
    from command_parser import Command
    from permissions import GitHubPermissionChecker, PermissionError

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
        allowed_roles: list[str] | None = None,
    ):
        """
        Initialize the command executor.

        Args:
            project_dir: Project directory for git operations
            gh_client: Optional GHClient instance. If None, creates a new one.
            repo: Repository in 'owner/repo' format. If provided, uses -R flag
                  instead of inferring from git remotes.
            allowed_roles: List of allowed roles for write operations
                          (default: OWNER, MEMBER, COLLABORATOR)
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

        # Store repo for permission checking
        self.repo = repo

        # Initialize permission checker (will be created lazily when needed)
        self._permission_checker: GitHubPermissionChecker | None = None
        self.allowed_roles = allowed_roles or ["OWNER", "MEMBER", "COLLABORATOR"]

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
        Read operations (process) are allowed for any user with repo access.

        Args:
            command: The command to check permissions for
            pr_number: The PR number
            username: The GitHub username

        Returns:
            True if user has permissions, False otherwise
        """
        logger.debug(
            f"Checking permissions for user '{username}' to execute '/{command.type}'"
        )

        try:
            # Get or create permission checker
            checker = await self._get_permission_checker()

            # Write operations require write access
            if command.type in ["merge", "resolve"]:
                # Check if user has sufficient role for write operations
                result = await checker.is_allowed_for_autofix(username)

                if not result.allowed:
                    logger.warning(
                        f"Permission denied for user '{username}' (role: {result.role}) "
                        f"to execute write command '/{command.type}': {result.reason}"
                    )
                    return False

                logger.info(
                    f"✓ User '{username}' (role: {result.role}) has permission "
                    f"to execute '/{command.type}'"
                )
                return True

            # Read operations (process) are allowed for anyone with repo access
            # We still verify the user has at least read access
            role = await checker.get_user_role(username)

            # Allow if user has any relationship to the repo (even CONTRIBUTOR or NONE)
            # We'll let the GitHub API itself reject if they truly can't access the repo
            logger.info(
                f"✓ User '{username}' (role: {role}) has permission to execute '/{command.type}'"
            )
            return True

        except PermissionError as e:
            logger.error(f"Permission check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking permissions: {e}")
            # Fail open for read operations, fail closed for write operations
            return command.type not in ["merge", "resolve"]

    async def _get_permission_checker(self) -> GitHubPermissionChecker:
        """
        Get or create the permission checker instance.

        Returns:
            GitHubPermissionChecker instance

        Raises:
            PermissionError: If repo is not configured or checker cannot be initialized
        """
        if self._permission_checker is None:
            # Infer repo from gh_client if not explicitly provided
            repo = self.repo
            if repo is None:
                # Try to get repo from gh_client
                repo = getattr(self.gh_client, 'repo', None)

            if repo is None:
                raise PermissionError(
                    "Repository must be specified for permission checking. "
                    "Provide 'repo' parameter when initializing CommandExecutor."
                )

            # Create permission checker
            self._permission_checker = GitHubPermissionChecker(
                gh_client=self.gh_client,
                repo=repo,
                allowed_roles=self.allowed_roles,
            )

            # Verify token has required scopes
            await self._permission_checker.verify_token_scopes()

        return self._permission_checker

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

        try:
            # Parse optional merge method from command args
            # Supported methods: merge, squash, rebase (default: squash)
            merge_method = "squash"
            if command.args:
                # First arg might be the merge method
                potential_method = command.args[0].lower()
                if potential_method in ("merge", "squash", "rebase"):
                    merge_method = potential_method

            # Execute the merge using GHClient
            await self.gh_client.pr_merge(
                pr_number=pr_number,
                merge_method=merge_method,
            )

            logger.info(f"Successfully merged PR #{pr_number} using {merge_method} method")

            return CommandResult(
                success=True,
                command_type="merge",
                message=f"✓ Merged PR #{pr_number} using {merge_method} merge",
                data={
                    "pr_number": pr_number,
                    "merge_method": merge_method,
                    "merged_by": username,
                },
            )

        except GHCommandError as e:
            error_msg = str(e)

            # Check for specific merge errors
            if "not mergeable" in error_msg.lower():
                message = f"✗ PR #{pr_number} is not mergeable (likely has conflicts)"
            elif "merge conflict" in error_msg.lower():
                message = f"✗ PR #{pr_number} has merge conflicts that must be resolved"
            elif "required status" in error_msg.lower() or "checks" in error_msg.lower():
                message = f"✗ PR #{pr_number} has failing CI checks that must pass"
            elif "approved" in error_msg.lower() or "review" in error_msg.lower():
                message = f"✗ PR #{pr_number} requires approval before merging"
            elif "draft" in error_msg.lower():
                message = f"✗ PR #{pr_number} is in draft state and cannot be merged"
            else:
                message = f"✗ Failed to merge PR #{pr_number}: {error_msg}"

            logger.error(f"Merge failed for PR #{pr_number}: {error_msg}")

            return CommandResult(
                success=False,
                command_type="merge",
                message=message,
                error=error_msg,
                data={"pr_number": pr_number, "merge_method": merge_method},
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error merging PR #{pr_number}: {error_msg}")

            return CommandResult(
                success=False,
                command_type="merge",
                message=f"✗ Unexpected error merging PR #{pr_number}",
                error=error_msg,
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

        Detects the project's package manager and runs the appropriate install/update
        command to resolve dependencies.

        Supported package managers:
        - Node.js: npm, yarn, pnpm, bun
        - Python: pip, poetry, uv, pdm, hatch, pipenv, conda
        - Rust: cargo
        - Go: go
        - Ruby: gem, bundler
        - PHP: composer
        - Java: maven, gradle
        - .NET: nuget, dotnet

        Args:
            command: The resolve command
            pr_number: The PR number
            username: The user who issued the command

        Returns:
            CommandResult with resolution status
        """
        logger.info(f"Handling resolve command for PR #{pr_number}")

        try:
            # Detect package manager based on project files
            package_manager = await self._detect_package_manager()

            if not package_manager:
                logger.warning(f"No package manager detected in project")
                return CommandResult(
                    success=False,
                    command_type="resolve",
                    message="✗ No package manager detected in project",
                    error="Could not find package.json, requirements.txt, Cargo.lock, or other package manager files",
                    data={"pr_number": pr_number, "detected_manager": None},
                )

            logger.info(f"Detected package manager: {package_manager}")

            # Run the appropriate install command
            install_command, install_args = self._get_install_command(package_manager)

            logger.info(f"Running package install: {install_command} {' '.join(install_args)}")

            # Execute the install command using asyncio
            process = await asyncio.create_subprocess_exec(
                install_command,
                *install_args,
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120.0,  # 2 minute timeout for package installs
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                logger.info(
                    f"Successfully resolved dependencies using {package_manager}"
                )

                return CommandResult(
                    success=True,
                    command_type="resolve",
                    message=f"✓ Resolved dependencies using {package_manager}",
                    data={
                        "pr_number": pr_number,
                        "package_manager": package_manager,
                        "install_command": f"{install_command} {' '.join(install_args)}",
                        "stdout": stdout_str[-500:] if len(stdout_str) > 500 else stdout_str,
                        "resolved_by": username,
                    },
                )
            else:
                error_msg = stderr_str or stdout_str
                logger.error(
                    f"Package install failed with return code {process.returncode}: {error_msg[:200]}"
                )

                return CommandResult(
                    success=False,
                    command_type="resolve",
                    message=f"✗ Failed to resolve dependencies using {package_manager}",
                    error=error_msg[:500] if error_msg else f"Command failed with exit code {process.returncode}",
                    data={
                        "pr_number": pr_number,
                        "package_manager": package_manager,
                        "install_command": f"{install_command} {' '.join(install_args)}",
                        "returncode": process.returncode,
                    },
                )

        except asyncio.TimeoutError:
            logger.error(f"Package install timed out after 120s")
            return CommandResult(
                success=False,
                command_type="resolve",
                message=f"✗ Package install timed out (120s limit)",
                error="Package installation exceeded timeout limit",
                data={"pr_number": pr_number, "package_manager": package_manager},
            )

        except FileNotFoundError:
            logger.error(f"Package manager executable not found: {install_command}")
            return CommandResult(
                success=False,
                command_type="resolve",
                message=f"✗ Package manager not found: {install_command}",
                error=f"The {package_manager} executable is not installed or not in PATH",
                data={"pr_number": pr_number, "package_manager": package_manager, "executable": install_command},
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error resolving dependencies: {error_msg}")

            return CommandResult(
                success=False,
                command_type="resolve",
                message=f"✗ Failed to resolve dependencies",
                error=error_msg[:500],
                data={"pr_number": pr_number, "package_manager": package_manager if 'package_manager' in locals() else None},
            )

    async def _detect_package_manager(self) -> str | None:
        """
        Detect the project's package manager by checking for lock files and config files.

        Returns:
            Package manager name (e.g., "npm", "pip", "cargo") or None if not detected
        """
        # Check for package manager files in order of preference
        package_managers = [
            # Node.js (check for lock files to determine which one)
            ("bun", ["bun.lockb", "bun.lock"]),
            ("pnpm", ["pnpm-lock.yaml"]),
            ("yarn", ["yarn.lock"]),
            ("npm", ["package-lock.json", "package.json"]),
            # Python
            ("pipenv", ["Pipfile.lock", "Pipfile"]),
            ("poetry", ["poetry.lock", "pyproject.toml"]),
            ("hatch", ["pyproject.toml"]),  # hatch uses pyproject.toml
            ("pdm", ["pdm.lock", "pyproject.toml"]),
            ("uv", ["uv.lock"]),
            ("conda", ["environment.yml", "conda.yml"]),
            ("pip", ["requirements.txt", "setup.py", "pyproject.toml"]),
            # Rust
            ("cargo", ["Cargo.toml", "Cargo.lock"]),
            # Go
            ("go", ["go.mod", "go.sum"]),
            # Ruby
            ("bundler", ["Gemfile.lock", "Gemfile"]),
            ("gem", ["Gemfile"]),
            # PHP
            ("composer", ["composer.json", "composer.lock"]),
            # Java
            ("gradle", ["build.gradle", "build.gradle.kts", "gradlew"]),
            ("maven", ["pom.xml"]),
            # .NET
            ("dotnet", ["packages.config", "*.csproj"]),
            # Dart/Flutter
            ("pub", ["pubspec.lock", "pubspec.yaml"]),
        ]

        for pm_name, files in package_managers:
            for file_name in files:
                # Handle wildcards
                if "*" in file_name:
                    import glob
                    matches = glob.glob(str(self.project_dir / file_name))
                    if matches:
                        return pm_name
                else:
                    file_path = self.project_dir / file_name
                    if file_path.exists():
                        return pm_name

        return None

    def _get_install_command(self, package_manager: str) -> tuple[str, list[str]]:
        """
        Get the install command and arguments for a package manager.

        Args:
            package_manager: The package manager name

        Returns:
            Tuple of (command, args) to run for installing dependencies
        """
        install_commands = {
            # Node.js
            "npm": ("npm", ["install"]),
            "yarn": ("yarn", ["install"]),
            "pnpm": ("pnpm", ["install"]),
            "bun": ("bun", ["install"]),
            # Python
            "pip": ("pip", ["install", "-r", "requirements.txt"]),
            "pipenv": ("pipenv", ["install"]),
            "poetry": ("poetry", ["install"]),
            "hatch": ("hatch", ["env", "create"]),
            "pdm": ("pdm", ["install"]),
            "uv": ("uv", ["sync"]),
            "conda": ("conda", ["env", "update", "--file", "environment.yml", "--prune"]),
            # Rust
            "cargo": ("cargo", ["build", "--workspace"]),  # Build to fetch dependencies
            # Go
            "go": ("go", ["mod", "download"]),
            # Ruby
            "bundler": ("bundle", ["install"]),
            "gem": ("bundle", ["install"]),  # Use bundler for Gemfile
            # PHP
            "composer": ("composer", ["install"]),
            # Java
            "gradle": ("gradle", ["build"]),  # or gradlew
            "maven": ("mvn", ["dependency:resolve"]),
            # .NET
            "dotnet": ("dotnet", ["restore"]),
            # Dart/Flutter
            "pub": ("dart", ["pub", "get"]),
        }

        if package_manager in install_commands:
            return install_commands[package_manager]

        # Default fallback
        return (package_manager, ["install"])

    async def _handle_process(
        self,
        command: Command,
        pr_number: int,
        username: str,
    ) -> CommandResult:
        """
        Handle the /process command.

        Processes outstanding PR comments and generates responses.

        This command:
        - Fetches all inline review comments from the PR
        - Generates a summary of outstanding feedback
        - Posts the summary as a PR comment
        - Returns details about processed comments

        Args:
            command: The process command
            pr_number: The PR number
            username: The user who issued the command

        Returns:
            CommandResult with processing status and comment summary
        """
        logger.info(f"Handling process command for PR #{pr_number}")

        try:
            # Fetch inline comments from the PR
            comments = await self.gh_client.get_inline_comments(pr_number)

            if not comments:
                logger.info(f"No inline comments found for PR #{pr_number}")
                return CommandResult(
                    success=True,
                    command_type="process",
                    message=f"✓ No outstanding comments to process on PR #{pr_number}",
                    data={
                        "pr_number": pr_number,
                        "comment_count": 0,
                        "processed_by": username,
                    },
                )

            logger.info(f"Found {len(comments)} inline comments on PR #{pr_number}")

            # Generate summary of comments
            summary_lines = [
                f"## Comment Summary for PR #{pr_number}",
                f"",
                f"Processed by: @{username}",
                f"Total comments: {len(comments)}",
                f"",
                f"### Comment Breakdown",
            ]

            # Group comments by file
            comments_by_file: dict[str, list[dict]] = {}
            for comment in comments:
                path = comment.get("path", "Unknown")
                if path not in comments_by_file:
                    comments_by_file[path] = []
                comments_by_file[path].append(comment)

            # Add per-file summary
            for file_path, file_comments in sorted(comments_by_file.items()):
                summary_lines.append(f"\n**{file_path}**: {len(file_comments)} comment(s)")

                # Add brief excerpts from each comment
                for comment in file_comments[:5]:  # Limit to 5 comments per file
                    body = comment.get("body", "")[:100]
                    if len(comment.get("body", "")) > 100:
                        body += "..."
                    commenter = comment.get("user", {}).get("login", "unknown")
                    line = comment.get("line", "?")
                    summary_lines.append(f"  - Line {line} (@{commenter}): {body}")

                if len(file_comments) > 5:
                    summary_lines.append(f"  - ... and {len(file_comments) - 5} more")

            # Add actionable items section
            summary_lines.extend([
                "",
                "### Next Steps",
                "",
                "Please review the comments above and address the feedback.",
                "Use `/resolve` after making changes to update dependencies.",
                "",
            ])

            summary = "\n".join(summary_lines)

            # Post summary as PR comment
            await self.gh_client.pr_comment(pr_number, summary)

            logger.info(
                f"Successfully processed {len(comments)} comments on PR #{pr_number}"
            )

            return CommandResult(
                success=True,
                command_type="process",
                message=f"✓ Processed {len(comments)} comment(s) on PR #{pr_number}",
                data={
                    "pr_number": pr_number,
                    "comment_count": len(comments),
                    "files_affected": len(comments_by_file),
                    "summary_posted": True,
                    "processed_by": username,
                },
            )

        except GHCommandError as e:
            error_msg = str(e)
            logger.error(f"Failed to process comments for PR #{pr_number}: {error_msg}")

            return CommandResult(
                success=False,
                command_type="process",
                message=f"✗ Failed to process comments on PR #{pr_number}",
                error=error_msg,
                data={"pr_number": pr_number, "processed_by": username},
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error processing comments for PR #{pr_number}: {error_msg}")

            return CommandResult(
                success=False,
                command_type="process",
                message=f"✗ Unexpected error processing comments on PR #{pr_number}",
                error=error_msg[:500],
                data={"pr_number": pr_number, "processed_by": username},
            )

    # =========================================================================
    # Feedback
    # =========================================================================

    async def _post_feedback(self, pr_number: int, result: CommandResult) -> None:
        """
        Post command execution feedback as a PR comment.

        Formats the command result into a structured PR comment with:
- Status indicator (✓/✗)
- Command type
- Execution message
- Error details (if failed)
- Additional context from result data

        Args:
            pr_number: The PR number
            result: The command execution result
        """
        logger.debug(f"Posting feedback for PR #{pr_number}: {result.message}")

        # Skip if gh_client doesn't have pr_comment method (mocked/testing)
        if not hasattr(self.gh_client, "pr_comment"):
            logger.debug("Skipping feedback posting (gh_client not available)")
            return

        # Format the comment body
        comment_body = self._format_feedback_comment(result)

        # Post the comment
        try:
            await self.gh_client.pr_comment(pr_number, comment_body)
            logger.info(f"Posted feedback comment for command '/{result.command_type}' on PR #{pr_number}")
        except GHCommandError as e:
            logger.error(f"Failed to post feedback comment on PR #{pr_number}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error posting feedback comment: {e}")

    def _format_feedback_comment(self, result: CommandResult) -> str:
        """
        Format a command result into a structured PR comment.

        Args:
            result: The command execution result

        Returns:
            Formatted comment body string
        """
        lines = [
            f"### /{result.command_type} Command Result",
            "",
        ]

        # Status line with emoji indicator
        status_emoji = "✓" if result.success else "✗"
        lines.append(f"**Status:** {status_emoji} {result.message}")
        lines.append("")

        # Add error details if command failed
        if not result.success and result.error:
            lines.append("**Error Details:**")
            lines.append("```")
            # Truncate very long errors to avoid comment size limits
            error_text = result.error
            if len(error_text) > 1000:
                error_text = error_text[:1000] + "\n... (truncated)"
            lines.append(error_text)
            lines.append("```")
            lines.append("")

        # Add additional context from result data
        if result.data:
            lines.append("**Details:**")

            # Format specific data fields based on command type
            if result.command_type == "merge":
                merge_method = result.data.get("merge_method", "unknown")
                lines.append(f"- Merge method: `{merge_method}`")
                if result.success:
                    merged_by = result.data.get("merged_by")
                    if merged_by:
                        lines.append(f"- Merged by: @{merged_by}")

            elif result.command_type == "resolve":
                package_manager = result.data.get("package_manager")
                if package_manager:
                    lines.append(f"- Package manager: `{package_manager}`")
                install_command = result.data.get("install_command")
                if install_command:
                    lines.append(f"- Command: `{install_command}`")
                if result.success:
                    resolved_by = result.data.get("resolved_by")
                    if resolved_by:
                        lines.append(f"- Resolved by: @{resolved_by}")
                    # Add stdout snippet if available
                    stdout = result.data.get("stdout", "")
                    if stdout and stdout.strip():
                        lines.append("")
                        lines.append("**Output:**")
                        lines.append("```")
                        lines.append(stdout)
                        lines.append("```")

            elif result.command_type == "process":
                comment_count = result.data.get("comment_count", 0)
                lines.append(f"- Comments processed: {comment_count}")
                if result.success and comment_count > 0:
                    files_affected = result.data.get("files_affected", 0)
                    lines.append(f"- Files affected: {files_affected}")
                    lines.append("- Summary posted to PR")
                    processed_by = result.data.get("processed_by")
                    if processed_by:
                        lines.append(f"- Processed by: @{processed_by}")

            lines.append("")

        # Add footer
        lines.extend([
            "---",
            "*This comment was automatically generated by the command executor.*",
        ])

        return "\n".join(lines)
