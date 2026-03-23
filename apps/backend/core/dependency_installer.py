"""
Dependency Installer
====================

Installs dependencies for detected package managers with dry-run support.
Handles monorepo scenarios with multiple services using different package managers.
"""

import subprocess
from pathlib import Path


class InstallResult:
    """
    Result of a dependency installation operation.

    Attributes:
        success: True if all installations succeeded
        installed: List of (package_manager, directory) tuples that were installed
        failed: List of (package_manager, directory, error) tuples that failed
        skipped: List of (package_manager, directory, reason) tuples that were skipped
        dry_run: True if this was a dry-run (no actual installation)
    """

    def __init__(self, dry_run: bool = False):
        self.success = True
        self.installed: list[tuple[str, str]] = []
        self.failed: list[tuple[str, str, str]] = []
        self.skipped: list[tuple[str, str, str]] = []
        self.dry_run = dry_run

    def add_installed(self, package_manager: str, directory: str) -> None:
        """Record a successful installation."""
        self.installed.append((package_manager, directory))

    def add_failed(self, package_manager: str, directory: str, error: str) -> None:
        """Record a failed installation."""
        self.failed.append((package_manager, directory, error))
        self.success = False

    def add_skipped(self, package_manager: str, directory: str, reason: str) -> None:
        """Record a skipped installation."""
        self.skipped.append((package_manager, directory, reason))

    def __repr__(self) -> str:
        status = (
            "DRY-RUN" if self.dry_run else ("SUCCESS" if self.success else "FAILED")
        )
        return (
            f"InstallResult({status}, "
            f"installed={len(self.installed)}, "
            f"failed={len(self.failed)}, "
            f"skipped={len(self.skipped)})"
        )


class DependencyInstaller:
    """
    Dependency installer with dry-run support.

    Installs dependencies for multiple package managers in correct order.
    Supports monorepo scenarios with multiple services.

    Example:
        installer = DependencyInstaller(project_dir="/path/to/project")
        detected = detect_package_managers(project_dir)
        result = installer.install(detected, dry_run=False)

        if result.success:
            print(f"Installed {len(result.installed)} package managers")
        else:
            for pm, dir, error in result.failed:
                print(f"Failed to install {pm} in {dir}: {error}")
    """

    # Package manager installation commands
    # Order matters: dependencies should be installed in this order
    INSTALL_COMMANDS = {
        "pip": ["pip", "install", "-r", "requirements.txt"],
        "npm": ["npm", "install"],
        "cargo": ["cargo", "build", "--release"],
        "go": ["go", "mod", "download"],
    }

    # Alternative pip install commands for different project types
    PIP_INSTALL_VARIANTS = {
        "requirements.txt": ["pip", "install", "-r", "requirements.txt"],
        "pyproject.toml": ["pip", "install", "."],
        "setup.py": ["pip", "install", "."],
    }

    # Installation order (dependencies first)
    INSTALL_ORDER = ["pip", "npm", "go", "cargo"]

    def __init__(self, project_dir: str, timeout: int = 300):
        """
        Initialize dependency installer.

        Args:
            project_dir: Root directory of the project
            timeout: Timeout in seconds for each install command (default: 300)

        Raises:
            ValueError: If project_dir does not exist
        """
        self.project_dir = Path(project_dir).resolve()
        if not self.project_dir.exists():
            raise ValueError(f"Project directory does not exist: {project_dir}")

        self.timeout = timeout

    def install(
        self, detected: dict[str, list[str]], dry_run: bool = False
    ) -> InstallResult:
        """
        Install dependencies for detected package managers.

        Args:
            detected: Dictionary from detect_package_managers() mapping
                     package manager names to lists of directories
            dry_run: If True, only print what would be done without executing

        Returns:
            InstallResult with success/failure details

        Example:
            detected = {
                "npm": [".", "apps/frontend"],
                "pip": ["apps/backend"],
                "cargo": []
            }
            result = installer.install(detected, dry_run=False)
        """
        result = InstallResult(dry_run=dry_run)

        # Install in order (dependencies first)
        for pm_name in self.INSTALL_ORDER:
            if pm_name not in detected:
                continue

            directories = detected[pm_name]
            if not directories:
                continue

            for directory in directories:
                self._install_single(pm_name, directory, result, dry_run)

        return result

    def _install_single(
        self,
        package_manager: str,
        directory: str,
        result: InstallResult,
        dry_run: bool,
    ) -> None:
        """
        Install dependencies for a single package manager in a single directory.

        Args:
            package_manager: Package manager name (npm, pip, etc.)
            directory: Directory containing the manifest file (relative to project_dir)
            result: InstallResult to update
            dry_run: If True, only print what would be done
        """
        # Get install command
        install_cmd = self.INSTALL_COMMANDS.get(package_manager)
        if not install_cmd:
            result.add_skipped(
                package_manager,
                directory,
                f"No install command defined for {package_manager}",
            )
            return

        # Resolve target directory
        target_dir = self.project_dir / directory
        if not target_dir.exists():
            result.add_failed(
                package_manager, directory, f"Directory does not exist: {target_dir}"
            )
            return

        # For pip, choose the correct install command based on available files
        if package_manager == "pip":
            install_cmd = self._get_pip_command(target_dir)

        if dry_run:
            # Dry-run: just record what would be done
            result.add_installed(package_manager, directory)
            return

        # Execute install command
        # TODO: migrate to platform abstraction (core/platform/) for cross-platform
        # executable resolution (e.g., .cmd/.bat wrappers on Windows).
        try:
            proc_result = subprocess.run(
                install_cmd,
                cwd=target_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
            )

            if proc_result.returncode == 0:
                result.add_installed(package_manager, directory)
            else:
                # Extract meaningful error from stderr
                error_msg = proc_result.stderr.strip() or proc_result.stdout.strip()
                if not error_msg:
                    error_msg = f"Command exited with code {proc_result.returncode}"
                # Truncate very long error messages
                if len(error_msg) > 500:
                    error_msg = error_msg[:500] + "... (truncated)"

                result.add_failed(package_manager, directory, error_msg)

        except subprocess.TimeoutExpired:
            result.add_failed(
                package_manager,
                directory,
                f"Installation timed out after {self.timeout}s",
            )
        except FileNotFoundError:
            result.add_failed(
                package_manager,
                directory,
                f"Command not found: {install_cmd[0]}. Is it installed?",
            )
        except Exception as e:
            result.add_failed(package_manager, directory, str(e))

    def _get_pip_command(self, target_dir: Path) -> list[str]:
        """
        Determine the correct pip install command based on available project files.

        Checks for requirements.txt first, then pyproject.toml, then setup.py.

        Args:
            target_dir: Directory containing the Python project

        Returns:
            List of command arguments for pip install
        """
        for filename, cmd in self.PIP_INSTALL_VARIANTS.items():
            if (target_dir / filename).exists():
                return list(cmd)
        # Default fallback
        return list(self.INSTALL_COMMANDS["pip"])

    def get_install_command(self, package_manager: str, directory: str) -> str | None:
        """
        Get the full install command for a package manager in a directory.

        Useful for displaying what command will be run or for manual execution.

        Args:
            package_manager: Package manager name (npm, pip, etc.)
            directory: Directory containing the manifest file

        Returns:
            Shell command string, or None if package manager is unknown

        Example:
            cmd = installer.get_install_command("npm", "apps/frontend")
            # Returns: "cd /path/to/project/apps/frontend && npm install"
        """
        install_cmd = self.INSTALL_COMMANDS.get(package_manager)
        if not install_cmd:
            return None

        target_dir = self.project_dir / directory
        return f"cd {target_dir} && {' '.join(install_cmd)}"


def install_dependencies(
    project_dir: str,
    detected: dict[str, list[str]],
    dry_run: bool = False,
    timeout: int = 300,
) -> InstallResult:
    """
    Convenience function to install dependencies.

    Args:
        project_dir: Root directory of the project
        detected: Dictionary from detect_package_managers()
        dry_run: If True, only show what would be done
        timeout: Timeout in seconds for each install command

    Returns:
        InstallResult with success/failure details

    Example:
        from apps.backend.core.package_detector import detect_package_managers
        from apps.backend.core.dependency_installer import install_dependencies

        detected = detect_package_managers(".")
        result = install_dependencies(".", detected, dry_run=True)

        if result.success:
            print(f"Would install {len(result.installed)} package managers")
    """
    installer = DependencyInstaller(project_dir, timeout=timeout)
    return installer.install(detected, dry_run=dry_run)
