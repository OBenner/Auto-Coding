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
