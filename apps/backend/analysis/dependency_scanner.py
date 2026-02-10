#!/usr/bin/env python3
"""
Dependency Scanner Module
==========================

Scans project dependencies for outdated packages and security vulnerabilities.
This module integrates with package managers (pip, npm) to detect updates
and assess update risk.

The dependency scanner is used by:
- Dependency Update Agent: To identify packages needing updates
- QA Agent: To verify dependency security before deployment
- Validation Strategy: To assess update risk for dependencies

Usage:
    from analysis.dependency_scanner import DependencyScanner

    scanner = DependencyScanner()
    results = scanner.scan(project_dir, spec_dir)

    if results.has_security_updates:
        print("Security updates available - recommend immediate update")
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class DependencyUpdate:
    """
    Represents an available dependency update.

    Attributes:
        name: Package name
        current_version: Currently installed version
        latest_version: Latest available version
        update_type: Type of update (major, minor, patch)
        ecosystem: Package ecosystem (python, npm, etc.)
        is_security: Whether this update addresses security issues
        cve_ids: List of CVE IDs fixed by this update (if applicable)
        severity: Severity if security update (critical, high, medium, low)
        changelog_url: URL to changelog/release notes
    """

    name: str
    current_version: str
    latest_version: str
    update_type: str  # major, minor, patch
    ecosystem: str  # python, npm, etc.
    is_security: bool = False
    cve_ids: list[str] = field(default_factory=list)
    severity: str | None = None  # critical, high, medium, low
    changelog_url: str | None = None


@dataclass
class DependencyScanResult:
    """
    Result of a dependency scan.

    Attributes:
        updates_available: List of available dependency updates
        security_updates: List of security-related updates
        scan_errors: List of errors during scanning
        has_updates: Whether any updates are available
        has_security_updates: Whether any security updates are available
        scan_metadata: Additional metadata about the scan
    """

    updates_available: list[DependencyUpdate] = field(default_factory=list)
    security_updates: list[DependencyUpdate] = field(default_factory=list)
    scan_errors: list[str] = field(default_factory=list)
    has_updates: bool = False
    has_security_updates: bool = False
    scan_metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# DEPENDENCY SCANNER
# =============================================================================


class DependencyScanner:
    """
    Consolidates all dependency scanning operations.

    Integrates:
    - pip/uv for Python dependency detection
    - npm for JavaScript/Node.js dependency detection
    - CVE databases for security vulnerability detection
    """

    def __init__(self) -> None:
        """Initialize the dependency scanner."""
        self._pip_available: bool | None = None
        self._npm_available: bool | None = None
        self._uv_available: bool | None = None

    def scan(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        scan_python: bool = True,
        scan_node: bool = True,
        check_security: bool = True,
    ) -> DependencyScanResult:
        """
        Run all applicable dependency scans.

        Args:
            project_dir: Path to the project root
            spec_dir: Path to the spec directory (for storing results)
            scan_python: Whether to scan Python dependencies
            scan_node: Whether to scan Node.js dependencies
            check_security: Whether to check for security vulnerabilities

        Returns:
            DependencyScanResult with all findings
        """
        project_dir = Path(project_dir)
        result = DependencyScanResult()

        # Track scan metadata
        result.scan_metadata = {
            "project_dir": str(project_dir),
            "scanned_ecosystems": [],
        }

        # Scan Python dependencies
        if scan_python and self._is_python_project(project_dir):
            self._scan_python_dependencies(project_dir, result)
            result.scan_metadata["scanned_ecosystems"].append("python")

        # Scan Node.js dependencies
        if scan_node and self._is_node_project(project_dir):
            self._scan_node_dependencies(project_dir, result)
            result.scan_metadata["scanned_ecosystems"].append("node")

        # Check for security vulnerabilities
        if check_security:
            self._check_security_vulnerabilities(project_dir, result)

        # Separate security updates
        result.security_updates = [
            u for u in result.updates_available if u.is_security
        ]

        # Update flags
        result.has_updates = len(result.updates_available) > 0
        result.has_security_updates = len(result.security_updates) > 0

        # Save results if spec_dir provided
        if spec_dir:
            self._save_results(spec_dir, result)

        return result

    def _scan_python_dependencies(
        self, project_dir: Path, result: DependencyScanResult
    ) -> None:
        """
        Scan Python dependencies for updates using pip list --outdated.

        Checks for outdated Python packages and adds them to the result.
        Supports both pip and uv package managers.
        """
        # Try uv first (faster), then fall back to pip
        if self._check_uv_available():
            self._scan_python_with_uv(project_dir, result)
        elif self._check_pip_available():
            self._scan_python_with_pip(project_dir, result)
        else:
            result.scan_errors.append(
                "Python dependency scanning skipped - pip/uv not available"
            )

    def _scan_python_with_pip(
        self, project_dir: Path, result: DependencyScanResult
    ) -> None:
        """Scan Python dependencies using pip."""
        try:
            # Run pip list --outdated --format=json
            proc = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_dir,
            )

            if proc.returncode != 0:
                result.scan_errors.append(
                    f"pip list --outdated failed: {proc.stderr.strip()}"
                )
                return

            # Parse JSON output
            outdated_packages = json.loads(proc.stdout)

            for pkg in outdated_packages:
                name = pkg.get("name", "unknown")
                current = pkg.get("version", "unknown")
                latest = pkg.get("latest_version", "unknown")

                # Classify update type
                update_type = self._classify_update_type(current, latest)

                # Create DependencyUpdate object
                update = DependencyUpdate(
                    name=name,
                    current_version=current,
                    latest_version=latest,
                    update_type=update_type,
                    ecosystem="python",
                    changelog_url=f"https://pypi.org/project/{name}/{latest}/",
                )

                result.updates_available.append(update)

        except subprocess.TimeoutExpired:
            result.scan_errors.append(
                "pip list --outdated timed out after 30 seconds"
            )
        except json.JSONDecodeError as e:
            result.scan_errors.append(f"Failed to parse pip output: {e}")
        except Exception as e:
            result.scan_errors.append(f"Python dependency scan error: {e}")

    def _scan_python_with_uv(
        self, project_dir: Path, result: DependencyScanResult
    ) -> None:
        """Scan Python dependencies using uv (faster alternative to pip)."""
        try:
            # Run uv pip list --outdated --format=json
            proc = subprocess.run(
                ["uv", "pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_dir,
            )

            if proc.returncode != 0:
                # Fall back to pip if uv fails
                result.scan_errors.append(
                    f"uv pip list --outdated failed, falling back to pip: {proc.stderr.strip()}"
                )
                if self._check_pip_available():
                    self._scan_python_with_pip(project_dir, result)
                return

            # Parse JSON output (same format as pip)
            outdated_packages = json.loads(proc.stdout)

            for pkg in outdated_packages:
                name = pkg.get("name", "unknown")
                current = pkg.get("version", "unknown")
                latest = pkg.get("latest_version", "unknown")

                # Classify update type
                update_type = self._classify_update_type(current, latest)

                # Create DependencyUpdate object
                update = DependencyUpdate(
                    name=name,
                    current_version=current,
                    latest_version=latest,
                    update_type=update_type,
                    ecosystem="python",
                    changelog_url=f"https://pypi.org/project/{name}/{latest}/",
                )

                result.updates_available.append(update)

        except subprocess.TimeoutExpired:
            result.scan_errors.append(
                "uv pip list --outdated timed out after 30 seconds"
            )
        except json.JSONDecodeError as e:
            result.scan_errors.append(f"Failed to parse uv output: {e}")
        except Exception as e:
            result.scan_errors.append(f"Python dependency scan error (uv): {e}")

    def _scan_node_dependencies(
        self, project_dir: Path, result: DependencyScanResult
    ) -> None:
        """
        Scan Node.js dependencies for updates.

        Will be implemented in subtask-1-3.
        """
        # Placeholder - to be implemented in subtask-1-3
        pass

    def _check_security_vulnerabilities(
        self, project_dir: Path, result: DependencyScanResult
    ) -> None:
        """
        Check for security vulnerabilities in dependencies.

        Will be implemented in subtask-1-4.
        """
        # Placeholder - to be implemented in subtask-1-4
        pass

    def _is_python_project(self, project_dir: Path) -> bool:
        """Check if this is a Python project."""
        indicators = [
            project_dir / "pyproject.toml",
            project_dir / "requirements.txt",
            project_dir / "setup.py",
            project_dir / "setup.cfg",
            project_dir / "Pipfile",
        ]
        return any(p.exists() for p in indicators)

    def _is_node_project(self, project_dir: Path) -> bool:
        """Check if this is a Node.js project."""
        indicators = [
            project_dir / "package.json",
            project_dir / "package-lock.json",
            project_dir / "yarn.lock",
            project_dir / "pnpm-lock.yaml",
        ]
        return any(p.exists() for p in indicators)

    def _check_pip_available(self) -> bool:
        """Check if pip is available."""
        if self._pip_available is None:
            try:
                subprocess.run(
                    ["pip", "--version"],
                    capture_output=True,
                    timeout=5,
                )
                self._pip_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._pip_available = False
        return self._pip_available

    def _check_npm_available(self) -> bool:
        """Check if npm is available."""
        if self._npm_available is None:
            try:
                subprocess.run(
                    ["npm", "--version"],
                    capture_output=True,
                    timeout=5,
                )
                self._npm_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._npm_available = False
        return self._npm_available

    def _check_uv_available(self) -> bool:
        """Check if uv is available."""
        if self._uv_available is None:
            try:
                subprocess.run(
                    ["uv", "--version"],
                    capture_output=True,
                    timeout=5,
                )
                self._uv_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._uv_available = False
        return self._uv_available

    def _classify_update_type(
        self, current: str, latest: str
    ) -> str:
        """
        Classify update type based on semantic versioning.

        Args:
            current: Current version string
            latest: Latest version string

        Returns:
            Update type: "major", "minor", or "patch"
        """
        try:
            # Remove 'v' prefix if present
            current = current.lstrip("v")
            latest = latest.lstrip("v")

            # Parse version numbers
            current_parts = [int(x) for x in current.split(".")[:3]]
            latest_parts = [int(x) for x in latest.split(".")[:3]]

            # Pad to 3 parts if needed
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(latest_parts) < 3:
                latest_parts.append(0)

            # Compare versions
            if latest_parts[0] > current_parts[0]:
                return "major"
            elif latest_parts[1] > current_parts[1]:
                return "minor"
            elif latest_parts[2] > current_parts[2]:
                return "patch"
            else:
                return "unknown"
        except (ValueError, IndexError):
            # If version parsing fails, default to unknown
            return "unknown"

    def _save_results(self, spec_dir: Path, result: DependencyScanResult) -> None:
        """Save scan results to spec directory."""
        spec_dir = Path(spec_dir)
        spec_dir.mkdir(parents=True, exist_ok=True)

        output_file = spec_dir / "dependency_scan_results.json"
        output_data = self.to_dict(result)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

    def to_dict(self, result: DependencyScanResult) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "updates_available": [
                {
                    "name": u.name,
                    "current_version": u.current_version,
                    "latest_version": u.latest_version,
                    "update_type": u.update_type,
                    "ecosystem": u.ecosystem,
                    "is_security": u.is_security,
                    "cve_ids": u.cve_ids,
                    "severity": u.severity,
                    "changelog_url": u.changelog_url,
                }
                for u in result.updates_available
            ],
            "security_updates": [
                {
                    "name": u.name,
                    "current_version": u.current_version,
                    "latest_version": u.latest_version,
                    "update_type": u.update_type,
                    "ecosystem": u.ecosystem,
                    "cve_ids": u.cve_ids,
                    "severity": u.severity,
                }
                for u in result.security_updates
            ],
            "scan_errors": result.scan_errors,
            "has_updates": result.has_updates,
            "has_security_updates": result.has_security_updates,
            "scan_metadata": result.scan_metadata,
            "summary": {
                "total_updates": len(result.updates_available),
                "security_updates": len(result.security_updates),
                "major_updates": sum(
                    1 for u in result.updates_available if u.update_type == "major"
                ),
                "minor_updates": sum(
                    1 for u in result.updates_available if u.update_type == "minor"
                ),
                "patch_updates": sum(
                    1 for u in result.updates_available if u.update_type == "patch"
                ),
                "critical_security": sum(
                    1
                    for u in result.security_updates
                    if u.severity == "critical"
                ),
                "high_security": sum(
                    1
                    for u in result.security_updates
                    if u.severity == "high"
                ),
            },
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def scan_for_updates(
    project_dir: Path,
    spec_dir: Path | None = None,
) -> DependencyScanResult:
    """
    Convenience function to scan for dependency updates.

    Args:
        project_dir: Path to project root
        spec_dir: Optional spec directory to save results

    Returns:
        DependencyScanResult with all findings
    """
    scanner = DependencyScanner()
    return scanner.scan(project_dir, spec_dir)


def has_outdated_dependencies(project_dir: Path) -> bool:
    """
    Quick check if project has outdated dependencies.

    Args:
        project_dir: Path to project root

    Returns:
        True if any updates are available
    """
    scanner = DependencyScanner()
    result = scanner.scan(project_dir, check_security=False)
    return result.has_updates


def scan_security_only(project_dir: Path) -> list[DependencyUpdate]:
    """
    Scan only for security updates (quick scan).

    Args:
        project_dir: Path to project root

    Returns:
        List of security updates
    """
    scanner = DependencyScanner()
    result = scanner.scan(project_dir)
    return result.security_updates


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Scan dependencies for updates")
    parser.add_argument("project_dir", type=Path, help="Path to project root")
    parser.add_argument("--spec-dir", type=Path, help="Path to spec directory")
    parser.add_argument(
        "--security-only", action="store_true", help="Only scan for security updates"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--no-python", action="store_true", help="Skip Python dependencies"
    )
    parser.add_argument(
        "--no-node", action="store_true", help="Skip Node.js dependencies"
    )

    args = parser.parse_args()

    scanner = DependencyScanner()
    result = scanner.scan(
        args.project_dir,
        spec_dir=args.spec_dir,
        scan_python=not args.no_python,
        scan_node=not args.no_node,
        check_security=True,
    )

    if args.json:
        print(json.dumps(scanner.to_dict(result), indent=2))
    else:
        print(f"Total Updates Available: {len(result.updates_available)}")
        print(f"Security Updates: {len(result.security_updates)}")
        print(f"Has Updates: {result.has_updates}")
        print(f"Has Security Updates: {result.has_security_updates}")

        if result.updates_available:
            print(f"\nUpdates Available ({len(result.updates_available)}):")
            for update in result.updates_available:
                security_marker = " [SECURITY]" if update.is_security else ""
                print(
                    f"  [{update.update_type.upper()}] {update.name}: "
                    f"{update.current_version} → {update.latest_version}{security_marker}"
                )
                if update.cve_ids:
                    print(f"    CVEs: {', '.join(update.cve_ids)}")

        if result.scan_errors:
            print(f"\nScan Errors ({len(result.scan_errors)}):")
            for error in result.scan_errors:
                print(f"  - {error}")

        if result.scan_metadata:
            print(f"\nScanned Ecosystems: {', '.join(result.scan_metadata.get('scanned_ecosystems', []))}")


if __name__ == "__main__":
    main()
