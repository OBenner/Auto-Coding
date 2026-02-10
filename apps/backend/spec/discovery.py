"""
Discovery Module
================

Project structure analysis and indexing with automatic pattern extraction.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

# Import pattern detectors for auto-extraction during discovery
from analysis.analyzers.error_pattern_detector import detect_error_patterns
from analysis.analyzers.naming_detector import detect_naming_conventions

logger = logging.getLogger(__name__)


def _extract_patterns_sync(spec_dir: Path, project_dir: Path) -> dict[str, int]:
    """
    Synchronous wrapper for pattern extraction during discovery.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory

    Returns:
        Dictionary with counts of patterns saved by category
    """
    try:
        # Import here to avoid circular dependencies
        from agents.memory_manager import detect_and_save_codebase_patterns

        # Run async pattern detection in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            pattern_counts = loop.run_until_complete(
                detect_and_save_codebase_patterns(spec_dir, project_dir)
            )
            return pattern_counts
        finally:
            loop.close()
    except Exception as e:
        logger.warning(f"Pattern extraction failed during discovery: {e}")
        return {}


def run_discovery_script(
    project_dir: Path,
    spec_dir: Path,
    extract_patterns: bool = True,
) -> tuple[bool, str]:
    """Run the analyzer.py script to discover project structure and extract patterns.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        extract_patterns: Whether to auto-extract codebase patterns (default: True)

    Returns:
        (success, output_message)
    """
    spec_index = spec_dir / "project_index.json"
    auto_build_index = project_dir / "auto-claude" / "project_index.json"

    # Check if project_index already exists
    if auto_build_index.exists() and not spec_index.exists():
        # Copy existing index
        shutil.copy(auto_build_index, spec_index)
        message = "Copied existing project_index.json"

        # Extract patterns after copying index
        if extract_patterns:
            pattern_counts = _extract_patterns_sync(spec_dir, project_dir)
            total_patterns = sum(pattern_counts.values())
            if total_patterns > 0:
                message += f" and extracted {total_patterns} codebase patterns"

        return True, message

    if spec_index.exists():
        message = "project_index.json already exists"

        # Extract patterns even if index exists (patterns may not have been extracted yet)
        if extract_patterns:
            pattern_counts = _extract_patterns_sync(spec_dir, project_dir)
            total_patterns = sum(pattern_counts.values())
            if total_patterns > 0:
                message += f", extracted {total_patterns} codebase patterns"

        return True, message

    # Run analyzer - use framework-relative path instead of project_dir
    script_path = Path(__file__).parent.parent / "analyzer.py"
    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    cmd = [sys.executable, str(script_path), "--output", str(spec_index)]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0 and spec_index.exists():
            message = "Created project_index.json"

            # Auto-extract codebase patterns after successful index creation
            if extract_patterns:
                logger.info("Auto-extracting codebase patterns during discovery...")
                pattern_counts = _extract_patterns_sync(spec_dir, project_dir)
                total_patterns = sum(pattern_counts.values())
                if total_patterns > 0:
                    message += f" and extracted {total_patterns} codebase patterns"
                    logger.info(
                        f"Pattern extraction complete: {pattern_counts.get('naming', 0)} naming, "
                        f"{pattern_counts.get('error-handling', 0)} error handling, "
                        f"{pattern_counts.get('code-organization', 0)} organization"
                    )

            return True, message
        else:
            return False, result.stderr or result.stdout

    except subprocess.TimeoutExpired:
        return False, "Script timed out"
    except Exception as e:
        return False, str(e)


def get_project_index_stats(spec_dir: Path) -> dict:
    """Get statistics from project index if available."""
    spec_index = spec_dir / "project_index.json"
    if not spec_index.exists():
        return {}

    try:
        with open(spec_index, encoding="utf-8") as f:
            index_data = json.load(f)

        # Support both old and new analyzer formats
        file_count = 0

        # Old format: top-level "files" array
        if "files" in index_data:
            file_count = len(index_data["files"])
        # New format: count files in services
        elif "services" in index_data:
            services = index_data["services"]

            for service_data in services.values():
                if isinstance(service_data, dict):
                    # Config files
                    file_count += 3  # package.json, tsconfig.json, .env.example

                    # Entry point
                    if service_data.get("entry_point"):
                        file_count += 1

                    # Dependencies indicate source files
                    deps = service_data.get("dependencies", [])
                    dev_deps = service_data.get("dev_dependencies", [])
                    file_count += len(deps) // 2  # Rough estimate: 1 file per 2 deps
                    file_count += len(dev_deps) // 4  # Fewer files for dev deps

                    # Key directories (each represents multiple files)
                    key_dirs = service_data.get("key_directories", {})
                    file_count += len(key_dirs) * 8  # Estimate 8 files per directory

                    # Config files
                    if service_data.get("dockerfile"):
                        file_count += 1
                    if service_data.get("test_directory"):
                        file_count += 3  # Test files

            # Infrastructure files
            if "infrastructure" in index_data:
                infra = index_data["infrastructure"]
                if infra.get("docker_compose"):
                    file_count += len(infra["docker_compose"])
                if infra.get("dockerfiles"):
                    file_count += len(infra["dockerfiles"])

            # Convention files
            if "conventions" in index_data:
                conv = index_data["conventions"]
                if conv.get("linting"):
                    file_count += 1  # eslintrc or similar
                if conv.get("formatting"):
                    file_count += 1  # prettier config
                if conv.get("git_hooks"):
                    file_count += 1  # husky/hooks

        return {
            "file_count": file_count,
            "project_type": index_data.get("project_type", "unknown"),
        }
    except Exception:
        return {}
