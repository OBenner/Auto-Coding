"""
Package Manager Detector
========================

Detects package managers and their locations in a project directory.
Supports monorepos with multiple services using different package managers.
"""

from pathlib import Path
from typing import Dict, List


def detect_package_managers(project_dir: str) -> Dict[str, List[str]]:
    """
    Detect all package managers in a project directory.

    Scans recursively for package manager manifest files and groups
    them by package manager type. Useful for monorepos with multiple
    services using different package managers.

    Args:
        project_dir: Root directory to scan for package managers

    Returns:
        Dictionary mapping package manager names to lists of directories
        containing their manifest files. Directories are relative to project_dir.

        Example:
        {
            "npm": [".", "apps/frontend"],
            "pip": ["apps/backend", "apps/web-backend"],
            "cargo": []
        }

    Raises:
        ValueError: If project_dir does not exist
    """
    root = Path(project_dir).resolve()
    if not root.exists():
        raise ValueError(f"Project directory does not exist: {project_dir}")

    # Package manager manifest file patterns
    # Maps package manager name to (filename, description)
    package_files = {
        "npm": ("package.json", "Node.js package manager"),
        "pip": ("requirements.txt", "Python package manager"),
        "cargo": ("Cargo.toml", "Rust package manager"),
        "go": ("go.mod", "Go module manager"),
    }

    results: Dict[str, List[str]] = {pm: [] for pm in package_files}

    # Additional Python package files to check (lower priority than requirements.txt)
    python_files = ["setup.py", "pyproject.toml"]

    # Scan for package manager files
    for pm_name, (filename, _) in package_files.items():
        matches = root.rglob(filename)
        for match in matches:
            # Skip node_modules, venv, .git, and other common ignore dirs
            if _should_skip_directory(match, root):
                continue

            # Get directory containing the manifest file
            manifest_dir = match.parent
            # Convert to relative path from root
            try:
                rel_path = manifest_dir.relative_to(root)
                # Use "." for root directory
                rel_str = "." if str(rel_path) == "." else str(rel_path).replace("\\", "/")
                if rel_str not in results[pm_name]:
                    results[pm_name].append(rel_str)
            except ValueError:
                # Path is not relative to root, skip it
                continue

    # Add Python projects without requirements.txt but with setup.py or pyproject.toml
    _detect_additional_python_projects(root, results, python_files)

    # Sort results for consistent output
    for pm_name in results:
        results[pm_name].sort()

    return results


def _should_skip_directory(path: Path, root: Path) -> bool:
    """
    Check if a directory should be skipped during package detection.

    Only checks path components between root and path (not parent directories
    above root). This allows detection to work even when run from inside
    normally-ignored directories like .auto-claude.

    Args:
        path: Path to check
        root: Project root directory

    Returns:
        True if the directory should be skipped, False otherwise
    """
    # Directories to skip (common ignore patterns)
    skip_dirs = {
        "node_modules",
        ".venv",
        "venv",
        ".env",
        ".git",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "target",  # Rust build output
        "vendor",  # Go vendor directory
    }

    # Only check path components between root and path
    try:
        rel_path = path.relative_to(root)
        # Check each component in the relative path
        for part in rel_path.parts:
            if part in skip_dirs:
                return True
    except ValueError:
        # Path is not relative to root, skip it
        return True

    return False


def _detect_additional_python_projects(
    root: Path,
    results: Dict[str, List[str]],
    python_files: List[str],
) -> None:
    """
    Detect Python projects without requirements.txt.

    Adds directories with setup.py or pyproject.toml to pip results
    if they don't already have requirements.txt.

    Args:
        root: Project root directory
        results: Results dictionary to update (modified in place)
        python_files: List of additional Python manifest files to check
    """
    existing_pip_dirs = set(results["pip"])

    for filename in python_files:
        matches = root.rglob(filename)
        for match in matches:
            if _should_skip_directory(match, root):
                continue

            manifest_dir = match.parent
            try:
                rel_path = manifest_dir.relative_to(root)
                rel_str = "." if str(rel_path) == "." else str(rel_path).replace("\\", "/")

                # Only add if not already detected via requirements.txt
                if rel_str not in existing_pip_dirs:
                    results["pip"].append(rel_str)
                    existing_pip_dirs.add(rel_str)
            except ValueError:
                # Path is not relative to root, skip it
                continue
