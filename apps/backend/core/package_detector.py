"""
Package Manager Detector
========================

Detects package managers and their locations in a project directory.
Supports monorepos with multiple services using different package managers.
"""

import os
from pathlib import Path

# Directories to skip (common ignore patterns)
_SKIP_DIRS = {
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


def detect_package_managers(project_dir: str) -> dict[str, list[str]]:
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

    results: dict[str, list[str]] = {pm: [] for pm in package_files}

    # Additional Python package files to check (lower priority than requirements.txt)
    python_files = ["setup.py", "pyproject.toml"]

    # Build a set of all filenames to look for in a single walk
    target_filenames = {filename for filename, _ in package_files.values()}
    filename_to_pm = {filename: pm for pm, (filename, _) in package_files.items()}

    # Walk directory tree, pruning ignored directories
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in-place to prevent descending into them
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

        for filename in filenames:
            if filename in target_filenames:
                pm_name = filename_to_pm[filename]
                manifest_dir = Path(dirpath)
                try:
                    rel_path = manifest_dir.relative_to(root)
                    rel_str = (
                        "."
                        if str(rel_path) == "."
                        else str(rel_path).replace("\\", "/")
                    )
                    if rel_str not in results[pm_name]:
                        results[pm_name].append(rel_str)
                except ValueError:
                    continue

    # Add Python projects without requirements.txt but with setup.py or pyproject.toml
    _detect_additional_python_projects(root, results, python_files)

    # Sort results for consistent output
    for pm_name in results:
        results[pm_name].sort()

    return results


def _detect_additional_python_projects(
    root: Path,
    results: dict[str, list[str]],
    python_files: list[str],
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
    target_set = set(python_files)

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

        for filename in filenames:
            if filename in target_set:
                manifest_dir = Path(dirpath)
                try:
                    rel_path = manifest_dir.relative_to(root)
                    rel_str = (
                        "."
                        if str(rel_path) == "."
                        else str(rel_path).replace("\\", "/")
                    )

                    # Only add if not already detected via requirements.txt
                    if rel_str not in existing_pip_dirs:
                        results["pip"].append(rel_str)
                        existing_pip_dirs.add(rel_str)
                except ValueError:
                    continue
