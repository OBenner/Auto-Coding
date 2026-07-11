#!/usr/bin/env python3
"""
Security Scanner Module
=======================

Consolidates security scanning including secrets detection and SAST tools.
This module integrates the existing scan_secrets.py and provides a unified
interface for all security scanning.

The security scanner is used by:
- QA Agent: To verify no secrets are committed
- Validation Strategy: To run security scans for high-risk changes

Usage:
    from analysis.security_scanner import SecurityScanner

    scanner = SecurityScanner()
    results = scanner.scan(project_dir, spec_dir)

    if results.has_critical_issues:
        print("Security issues found - blocking QA approval")
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Import the existing secrets scanner
try:
    from security.scan_secrets import get_all_tracked_files, scan_files

    HAS_SECRETS_SCANNER = True
except ImportError:
    HAS_SECRETS_SCANNER = False

# Import predictive scanner
try:
    from analysis.predictive_scanner import PredictiveScanner

    HAS_PREDICTIVE_SCANNER = True
except ImportError:
    HAS_PREDICTIVE_SCANNER = False


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class SecurityVulnerability:
    """
    Represents a security vulnerability found during scanning.

    Attributes:
        severity: Severity level (critical, high, medium, low, info)
        source: Which scanner found this (secrets, bandit, npm_audit, etc.)
        title: Short title of the vulnerability
        description: Detailed description
        file: File where vulnerability was found (if applicable)
        line: Line number (if applicable)
        cwe: CWE identifier if available
    """

    severity: str  # critical, high, medium, low, info
    source: str  # secrets, bandit, npm_audit, semgrep, etc.
    title: str
    description: str
    file: str | None = None
    line: int | None = None
    cwe: str | None = None


@dataclass
class SecurityScanResult:
    """
    Result of a security scan.

    Attributes:
        secrets: List of detected secrets
        vulnerabilities: List of security vulnerabilities
        scan_errors: List of errors during scanning
        has_critical_issues: Whether any critical issues were found
        should_block_qa: Whether these results should block QA approval
        predictive_scan: Predictive scan results (bug, performance, code smell)
    """

    secrets: list[dict[str, Any]] = field(default_factory=list)
    vulnerabilities: list[SecurityVulnerability] = field(default_factory=list)
    scan_errors: list[str] = field(default_factory=list)
    has_critical_issues: bool = False
    should_block_qa: bool = False
    predictive_scan: dict[str, Any] | None = None


# =============================================================================
# SECURITY SCANNER
# =============================================================================


class SecurityScanner:
    """
    Consolidates all security scanning operations.

    Integrates:
    - scan_secrets.py for secrets detection
    - Bandit for Python SAST (if available)
    - npm audit for JavaScript vulnerabilities (if applicable)
    - PredictiveScanner for bug, performance, and code smell detection (if available)
    """

    def __init__(self, spec_dir: Path | None = None) -> None:
        """
        Initialize the security scanner.

        Args:
            spec_dir: Optional spec directory for predictive scanner historical tracking
        """
        self._bandit_available: bool | None = None
        self._npm_available: bool | None = None
        self._predictive_scanner: PredictiveScanner | None = None

        # Initialize predictive scanner if available
        if HAS_PREDICTIVE_SCANNER and spec_dir:
            try:
                self._predictive_scanner = PredictiveScanner(spec_dir)
            except Exception as e:
                logger.warning(f"Failed to initialize PredictiveScanner: {e}")

    def scan(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        changed_files: list[str] | None = None,
        run_secrets: bool = True,
        run_sast: bool = True,
        run_dependency_audit: bool = True,
        run_predictive_scan: bool = False,
    ) -> SecurityScanResult:
        """
        Run all applicable security scans.

        Args:
            project_dir: Path to the project root
            spec_dir: Path to the spec directory (for storing results)
            changed_files: Optional list of files to scan (if None, scans all)
            run_secrets: Whether to run secrets scanning
            run_sast: Whether to run SAST tools
            run_dependency_audit: Whether to run dependency audits
            run_predictive_scan: Whether to run predictive bug/performance/code smell scans

        Returns:
            SecurityScanResult with all findings
        """
        project_dir = Path(project_dir)
        result = SecurityScanResult()

        # Run secrets scan
        if run_secrets:
            self._run_secrets_scan(project_dir, changed_files, result)

        # Run SAST based on project type
        if run_sast:
            self._run_sast_scans(project_dir, result)

        # Run dependency audits
        if run_dependency_audit:
            self._run_dependency_audits(project_dir, result)

        # Run predictive scan if enabled
        if run_predictive_scan:
            self._run_predictive_scan(project_dir, result)

        # Determine if should block QA
        result.has_critical_issues = (
            any(v.severity in ["critical", "high"] for v in result.vulnerabilities)
            or len(result.secrets) > 0
        )

        # Also check predictive scan for critical issues
        if result.predictive_scan:
            predictive_has_critical = result.predictive_scan.get("summary", {}).get(
                "has_critical_issues", False
            )
            result.has_critical_issues = (
                result.has_critical_issues or predictive_has_critical
            )

        # Any secrets always block, critical vulnerabilities block
        result.should_block_qa = len(result.secrets) > 0 or any(
            v.severity == "critical" for v in result.vulnerabilities
        )

        # Also block on critical predictive issues
        if result.predictive_scan:
            predictive_should_block = result.predictive_scan.get("summary", {}).get(
                "should_block_deployment", False
            )
            result.should_block_qa = result.should_block_qa or predictive_should_block

        # Save results if spec_dir provided
        if spec_dir:
            self._save_results(spec_dir, result)

        return result

    def _run_secrets_scan(
        self,
        project_dir: Path,
        changed_files: list[str] | None,
        result: SecurityScanResult,
    ) -> None:
        """Run secrets scanning using scan_secrets.py."""
        if not HAS_SECRETS_SCANNER:
            result.scan_errors.append("scan_secrets module not available")
            return

        try:
            # Get files to scan
            if changed_files:
                files_to_scan = changed_files
            else:
                files_to_scan = get_all_tracked_files()

            # Run scan
            matches = scan_files(files_to_scan, project_dir)

            # Convert matches to result format
            for match in matches:
                result.secrets.append(
                    {
                        "file": match.file_path,
                        "line": match.line_number,
                        "pattern": match.pattern_name,
                        "matched_text": self._redact_secret(match.matched_text),
                    }
                )

                # Also add as vulnerability
                result.vulnerabilities.append(
                    SecurityVulnerability(
                        severity="critical",
                        source="secrets",
                        title=f"Potential secret: {match.pattern_name}",
                        description=f"Found potential {match.pattern_name} in file",
                        file=match.file_path,
                        line=match.line_number,
                    )
                )

        except Exception as e:
            result.scan_errors.append(f"Secrets scan error: {str(e)}")

    def _run_sast_scans(self, project_dir: Path, result: SecurityScanResult) -> None:
        """Run SAST tools based on project type."""
        # Python SAST with Bandit
        if self._is_python_project(project_dir):
            self._run_bandit(project_dir, result)

        # JavaScript/Node.js - npm audit
        # (handled in dependency audits for Node projects)

        # C/C++ SAST with cppcheck
        if self._is_c_cpp_project(project_dir):
            self._run_cppcheck(project_dir, result)

        # Go SAST with gosec
        if (project_dir / "go.mod").exists():
            self._run_gosec(project_dir, result)

    def _run_bandit(self, project_dir: Path, result: SecurityScanResult) -> None:
        """Run Bandit security scanner for Python projects."""
        if not self._check_bandit_available():
            return

        try:
            # Find Python source directories
            src_dirs = []
            for candidate in ["src", "app", project_dir.name, "."]:
                candidate_path = project_dir / candidate
                if (
                    candidate_path.exists()
                    and (candidate_path / "__init__.py").exists()
                ):
                    src_dirs.append(str(candidate_path))

            if not src_dirs:
                # Try to find any Python files
                py_files = list(project_dir.glob("**/*.py"))
                if not py_files:
                    return
                src_dirs = ["."]

            # Run bandit
            cmd = [
                "bandit",
                "-r",
                *src_dirs,
                "-f",
                "json",
                "--exit-zero",  # Don't fail on findings
            ]

            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )

            if proc.stdout:
                try:
                    bandit_output = json.loads(proc.stdout)
                    for finding in bandit_output.get("results", []):
                        severity = finding.get("issue_severity", "MEDIUM").lower()
                        if severity == "high":
                            severity = "high"
                        elif severity == "medium":
                            severity = "medium"
                        else:
                            severity = "low"

                        result.vulnerabilities.append(
                            SecurityVulnerability(
                                severity=severity,
                                source="bandit",
                                title=finding.get("issue_text", "Unknown issue"),
                                description=finding.get("issue_text", ""),
                                file=finding.get("filename"),
                                line=finding.get("line_number"),
                                cwe=finding.get("issue_cwe", {}).get("id"),
                            )
                        )
                except json.JSONDecodeError:
                    result.scan_errors.append("Failed to parse Bandit output")

        except subprocess.TimeoutExpired:
            result.scan_errors.append("Bandit scan timed out")
        except FileNotFoundError:
            result.scan_errors.append("Bandit not found")
        except Exception as e:
            result.scan_errors.append(f"Bandit error: {str(e)}")

    def _run_dependency_audits(
        self, project_dir: Path, result: SecurityScanResult
    ) -> None:
        """Run dependency vulnerability audits."""
        # npm audit for JavaScript projects
        if (project_dir / "package.json").exists():
            self._run_npm_audit(project_dir, result)

        # pip-audit for Python projects (if available)
        if self._is_python_project(project_dir):
            self._run_pip_audit(project_dir, result)

        # cargo audit for Rust projects (needs Cargo.lock)
        if (project_dir / "Cargo.lock").exists():
            self._run_cargo_audit(project_dir, result)

        # composer audit for PHP projects (needs composer.lock)
        if (project_dir / "composer.lock").exists():
            self._run_composer_audit(project_dir, result)

        # osv-scanner for ecosystems without a dedicated audit tool
        # (JVM, .NET, Elixir, Swift, Dart, Go modules)
        if self._has_osv_manifests(project_dir):
            self._run_osv_scanner(project_dir, result)

    def _run_npm_audit(self, project_dir: Path, result: SecurityScanResult) -> None:
        """Run npm audit for JavaScript projects."""
        try:
            cmd = ["npm", "audit", "--json"]

            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )

            if proc.stdout:
                try:
                    audit_output = json.loads(proc.stdout)

                    # npm audit v2+ format
                    vulnerabilities = audit_output.get("vulnerabilities", {})
                    for pkg_name, vuln_info in vulnerabilities.items():
                        severity = vuln_info.get("severity", "moderate")
                        if severity == "critical":
                            severity = "critical"
                        elif severity == "high":
                            severity = "high"
                        elif severity == "moderate":
                            severity = "medium"
                        else:
                            severity = "low"

                        result.vulnerabilities.append(
                            SecurityVulnerability(
                                severity=severity,
                                source="npm_audit",
                                title=f"Vulnerable dependency: {pkg_name}",
                                description=vuln_info.get("via", [{}])[0].get(
                                    "title", ""
                                )
                                if isinstance(vuln_info.get("via"), list)
                                and vuln_info.get("via")
                                else str(vuln_info.get("via", "")),
                                file="package.json",
                            )
                        )
                except json.JSONDecodeError:
                    pass  # npm audit may return invalid JSON on no findings

        except subprocess.TimeoutExpired:
            result.scan_errors.append("npm audit timed out")
        except FileNotFoundError:
            pass  # npm not available
        except Exception as e:
            result.scan_errors.append(f"npm audit error: {str(e)}")

    def _run_pip_audit(self, project_dir: Path, result: SecurityScanResult) -> None:
        """Run pip-audit for Python projects (if available)."""
        try:
            cmd = ["pip-audit", "--format", "json"]

            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )

            if proc.stdout:
                try:
                    audit_output = json.loads(proc.stdout)
                    for vuln in audit_output:
                        severity = "high" if vuln.get("fix_versions") else "medium"

                        result.vulnerabilities.append(
                            SecurityVulnerability(
                                severity=severity,
                                source="pip_audit",
                                title=f"Vulnerable package: {vuln.get('name')}",
                                description=vuln.get("description", ""),
                                cwe=vuln.get("aliases", [""])[0]
                                if vuln.get("aliases")
                                else None,
                            )
                        )
                except json.JSONDecodeError:
                    logger.debug("Failed to parse pip-audit JSON output")

        except FileNotFoundError:
            logger.debug("pip-audit not available")
        except subprocess.TimeoutExpired:
            logger.debug("pip-audit timed out")
        except (OSError, ValueError, KeyError):
            logger.debug("pip-audit output parsing failed")

    def _run_cppcheck(self, project_dir: Path, result: SecurityScanResult) -> None:
        """Run cppcheck static analysis for C/C++ projects."""
        try:
            # cppcheck writes findings to stderr, one per line via --template
            cmd = [
                "cppcheck",
                "--enable=warning,portability",
                "--template={file}|{line}|{severity}|{id}|{message}",
                "--quiet",
                "--error-exitcode=0",
                ".",
            ]

            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )

            for raw_line in (proc.stderr or "").splitlines():
                parts = raw_line.split("|", 4)
                if len(parts) != 5:
                    continue
                file, line, cpp_severity, check_id, message = parts

                if cpp_severity == "error":
                    severity = "high"
                elif cpp_severity in ("warning", "portability"):
                    severity = "medium"
                else:
                    severity = "low"

                result.vulnerabilities.append(
                    SecurityVulnerability(
                        severity=severity,
                        source="cppcheck",
                        title=f"cppcheck {check_id}",
                        description=message,
                        file=file or None,
                        line=int(line) if line.isdigit() else None,
                    )
                )

        except FileNotFoundError:
            logger.debug("cppcheck not available")
        except subprocess.TimeoutExpired:
            result.scan_errors.append("cppcheck scan timed out")
        except Exception as e:
            result.scan_errors.append(f"cppcheck error: {str(e)}")

    def _run_gosec(self, project_dir: Path, result: SecurityScanResult) -> None:
        """Run gosec security scanner for Go projects."""
        try:
            # gosec exits non-zero when issues are found; parse stdout anyway
            cmd = ["gosec", "-fmt=json", "-quiet", "./..."]

            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )

            if proc.stdout:
                try:
                    gosec_output = json.loads(proc.stdout)
                    for issue in gosec_output.get("Issues", []):
                        severity = issue.get("severity", "MEDIUM").lower()
                        if severity not in ("high", "medium", "low"):
                            severity = "medium"

                        line = issue.get("line", "")
                        result.vulnerabilities.append(
                            SecurityVulnerability(
                                severity=severity,
                                source="gosec",
                                title=issue.get("details", "Unknown issue"),
                                description=issue.get("details", ""),
                                file=issue.get("file"),
                                line=int(line) if str(line).isdigit() else None,
                                cwe=issue.get("cwe", {}).get("id"),
                            )
                        )
                except json.JSONDecodeError:
                    result.scan_errors.append("Failed to parse gosec output")

        except FileNotFoundError:
            logger.debug("gosec not available")
        except subprocess.TimeoutExpired:
            result.scan_errors.append("gosec scan timed out")
        except Exception as e:
            result.scan_errors.append(f"gosec error: {str(e)}")

    def _run_cargo_audit(self, project_dir: Path, result: SecurityScanResult) -> None:
        """Run cargo audit for Rust projects."""
        try:
            # cargo audit exits non-zero when vulns are found; parse stdout anyway
            cmd = ["cargo", "audit", "--json"]

            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )

            if proc.stdout:
                try:
                    audit_output = json.loads(proc.stdout)
                    vulns = audit_output.get("vulnerabilities", {})
                    for vuln in vulns.get("list", []):
                        advisory = vuln.get("advisory", {})
                        package = vuln.get("package", {})

                        result.vulnerabilities.append(
                            SecurityVulnerability(
                                severity="high",
                                source="cargo_audit",
                                title=(
                                    f"Vulnerable crate: {package.get('name', '?')} "
                                    f"({advisory.get('id', '?')})"
                                ),
                                description=advisory.get("title", ""),
                                file="Cargo.lock",
                            )
                        )
                except json.JSONDecodeError:
                    result.scan_errors.append("Failed to parse cargo audit output")

        except FileNotFoundError:
            logger.debug("cargo audit not available")
        except subprocess.TimeoutExpired:
            result.scan_errors.append("cargo audit timed out")
        except Exception as e:
            result.scan_errors.append(f"cargo audit error: {str(e)}")

    def _run_composer_audit(
        self, project_dir: Path, result: SecurityScanResult
    ) -> None:
        """Run composer audit for PHP projects."""
        try:
            # composer audit exits non-zero when advisories exist; parse stdout
            cmd = ["composer", "audit", "--format=json", "--no-interaction"]

            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )

            if proc.stdout:
                try:
                    audit_output = json.loads(proc.stdout)
                    advisories = audit_output.get("advisories", {})
                    for pkg_name, pkg_advisories in advisories.items():
                        for advisory in pkg_advisories:
                            severity = advisory.get("severity", "medium").lower()
                            if severity not in ("critical", "high", "medium", "low"):
                                severity = "medium"

                            result.vulnerabilities.append(
                                SecurityVulnerability(
                                    severity=severity,
                                    source="composer_audit",
                                    title=f"Vulnerable dependency: {pkg_name}",
                                    description=advisory.get("title", ""),
                                    file="composer.json",
                                    cwe=advisory.get("cve"),
                                )
                            )
                except json.JSONDecodeError:
                    pass  # composer audit may return plain text on no findings

        except FileNotFoundError:
            logger.debug("composer not available")
        except subprocess.TimeoutExpired:
            result.scan_errors.append("composer audit timed out")
        except Exception as e:
            result.scan_errors.append(f"composer audit error: {str(e)}")

    # Manifests handled by osv-scanner for ecosystems that have no dedicated
    # audit runner above (npm/pip/cargo/composer manifests are excluded to
    # avoid double-reporting)
    OSV_MANIFESTS = (
        "pom.xml",
        "gradle.lockfile",
        "buildscript-gradle.lockfile",
        "packages.lock.json",
        "mix.lock",
        "Package.resolved",
        "pubspec.lock",
        "go.mod",
    )

    # Vendor/build directories skipped when searching for nested manifests
    _MANIFEST_SKIP_DIRS = frozenset(
        {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            "target",
            "build",
            "dist",
            "vendor",
        }
    )

    def _has_osv_manifests(self, project_dir: Path) -> bool:
        """Check for manifests osv-scanner should audit (recursively)."""
        manifest_names = set(self.OSV_MANIFESTS)
        for _root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in self._MANIFEST_SKIP_DIRS]
            if manifest_names.intersection(files):
                return True
        return False

    def _run_osv_scanner(self, project_dir: Path, result: SecurityScanResult) -> None:
        """Run osv-scanner against known-vulnerability database."""
        try:
            # osv-scanner exits non-zero when vulns are found; parse stdout
            cmd = ["osv-scanner", "--format", "json", "-r", "."]

            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,
            )

            if proc.stdout:
                try:
                    osv_output = json.loads(proc.stdout)
                    self._parse_osv_output(osv_output, result)
                except json.JSONDecodeError:
                    result.scan_errors.append("Failed to parse osv-scanner output")

        except FileNotFoundError:
            logger.debug("osv-scanner not available")
        except subprocess.TimeoutExpired:
            result.scan_errors.append("osv-scanner timed out")
        except Exception as e:
            result.scan_errors.append(f"osv-scanner error: {str(e)}")

    @staticmethod
    def _osv_severity(vuln: dict) -> str:
        """Map an OSV vulnerability payload to a severity level."""
        raw = str(vuln.get("database_specific", {}).get("severity", "")).lower()
        if raw in ("critical", "high", "medium", "low"):
            return raw
        if raw == "moderate":
            return "medium"
        # Unknown severity on a known vulnerability: treat as high
        return "high"

    def _parse_osv_output(self, osv_output: dict, result: SecurityScanResult) -> None:
        """Convert osv-scanner JSON results into vulnerabilities."""
        for scan_result in osv_output.get("results", []):
            source = scan_result.get("source", {}).get("path", "")
            file = Path(source).name if source else None
            for package in scan_result.get("packages", []):
                pkg_name = package.get("package", {}).get("name", "?")
                for vuln in package.get("vulnerabilities", []):
                    result.vulnerabilities.append(
                        SecurityVulnerability(
                            severity=self._osv_severity(vuln),
                            source="osv_scanner",
                            title=(
                                f"Vulnerable dependency: {pkg_name} "
                                f"({vuln.get('id', '?')})"
                            ),
                            description=vuln.get("summary", ""),
                            file=file,
                        )
                    )

    def _run_predictive_scan(
        self, project_dir: Path, result: SecurityScanResult
    ) -> None:
        """Run predictive scan for bugs, performance, and code smells."""
        if not HAS_PREDICTIVE_SCANNER:
            result.scan_errors.append("Predictive scanner not available")
            return

        try:
            # Use instance scanner if available, otherwise create new one
            scanner = self._predictive_scanner
            if not scanner:
                scanner = PredictiveScanner()

            # Run predictive scan
            predictive_result = scanner.scan(
                project_dir,
                run_llm_analysis=False,  # Skip LLM for faster security scans
                record_history=False,  # Don't record during security scans
            )

            # Convert to dict format for storage
            if hasattr(scanner, "to_dict"):
                result.predictive_scan = scanner.to_dict(predictive_result)
            else:
                # Fallback: basic conversion
                result.predictive_scan = {
                    "issues": [
                        {
                            "issue_type": i.issue_type,
                            "severity": i.severity,
                            "category": i.category,
                            "title": i.title,
                            "description": i.description,
                            "file": i.file,
                            "line": i.line,
                        }
                        for i in predictive_result.issues
                    ],
                    "summary": {
                        "total_issues": predictive_result.summary.total_issues,
                        "critical_count": predictive_result.summary.critical_count,
                        "high_count": predictive_result.summary.high_count,
                        "medium_count": predictive_result.summary.medium_count,
                        "low_count": predictive_result.summary.low_count,
                        "has_critical_issues": predictive_result.summary.has_critical_issues,
                        "should_block_deployment": predictive_result.summary.should_block_deployment,
                    },
                }

            # Add any predictive scan errors
            for error in predictive_result.scan_errors:
                result.scan_errors.append(f"Predictive scan: {error}")

        except Exception as e:
            result.scan_errors.append(f"Predictive scan error: {str(e)}")

    def _is_python_project(self, project_dir: Path) -> bool:
        """Check if this is a Python project."""
        indicators = [
            project_dir / "pyproject.toml",
            project_dir / "requirements.txt",
            project_dir / "setup.py",
            project_dir / "setup.cfg",
        ]
        return any(p.exists() for p in indicators)

    def _is_c_cpp_project(self, project_dir: Path) -> bool:
        """Check if this is a C/C++ project."""
        if (project_dir / "CMakeLists.txt").exists():
            return True
        for pattern in ("*.c", "*.cpp", "*.cc", "src/*.c", "src/*.cpp", "src/*.cc"):
            if any(project_dir.glob(pattern)):
                return True
        return False

    def _check_bandit_available(self) -> bool:
        """Check if Bandit is available."""
        if self._bandit_available is None:
            try:
                subprocess.run(
                    ["bandit", "--version"],
                    capture_output=True,
                    timeout=5,
                )
                self._bandit_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._bandit_available = False
        return self._bandit_available

    def _redact_secret(self, text: str) -> str:
        """Redact a secret for safe logging."""
        if len(text) <= 8:
            return "*" * len(text)
        return text[:4] + "*" * (len(text) - 8) + text[-4:]

    def _save_results(self, spec_dir: Path, result: SecurityScanResult) -> None:
        """Save scan results to spec directory."""
        spec_dir = Path(spec_dir)
        spec_dir.mkdir(parents=True, exist_ok=True)

        output_file = spec_dir / "security_scan_results.json"
        output_data = self.to_dict(result)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

    def to_dict(self, result: SecurityScanResult) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        # Redact matched_text to prevent clear-text secret logging
        redacted_secrets = [
            {**secret, "matched_text": "[redacted]"} for secret in result.secrets
        ]
        return {
            "secrets": redacted_secrets,
            "vulnerabilities": [
                {
                    "severity": v.severity,
                    "source": v.source,
                    "title": v.title,
                    "description": v.description,
                    "file": v.file,
                    "line": v.line,
                    "cwe": v.cwe,
                }
                for v in result.vulnerabilities
            ],
            "scan_errors": result.scan_errors,
            "has_critical_issues": result.has_critical_issues,
            "should_block_qa": result.should_block_qa,
            "predictive_scan": result.predictive_scan,
            "summary": {
                "total_secrets": len(result.secrets),
                "total_vulnerabilities": len(result.vulnerabilities),
                "critical_count": sum(
                    1 for v in result.vulnerabilities if v.severity == "critical"
                ),
                "high_count": sum(
                    1 for v in result.vulnerabilities if v.severity == "high"
                ),
                "medium_count": sum(
                    1 for v in result.vulnerabilities if v.severity == "medium"
                ),
                "low_count": sum(
                    1 for v in result.vulnerabilities if v.severity == "low"
                ),
                "predictive_issues": (
                    result.predictive_scan.get("summary", {}).get("total_issues", 0)
                    if result.predictive_scan
                    else 0
                ),
                "predictive_critical": (
                    result.predictive_scan.get("summary", {}).get("critical_count", 0)
                    if result.predictive_scan
                    else 0
                ),
            },
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def scan_for_security_issues(
    project_dir: Path,
    spec_dir: Path | None = None,
    changed_files: list[str] | None = None,
    run_predictive_scan: bool = False,
) -> SecurityScanResult:
    """
    Convenience function to run security scan.

    Args:
        project_dir: Path to project root
        spec_dir: Optional spec directory to save results
        changed_files: Optional list of files to scan
        run_predictive_scan: Whether to run predictive bug/performance/code smell scans

    Returns:
        SecurityScanResult with all findings
    """
    scanner = SecurityScanner(spec_dir)
    return scanner.scan(
        project_dir, spec_dir, changed_files, run_predictive_scan=run_predictive_scan
    )


def has_security_issues(project_dir: Path, include_predictive: bool = False) -> bool:
    """
    Quick check if project has security issues.

    Args:
        project_dir: Path to project root
        include_predictive: Whether to include predictive issues in check

    Returns:
        True if any critical/high issues found
    """
    scanner = SecurityScanner()
    result = scanner.scan(
        project_dir,
        run_sast=False,
        run_dependency_audit=False,
        run_predictive_scan=include_predictive,
    )
    return result.has_critical_issues


def scan_secrets_only(
    project_dir: Path,
    changed_files: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Scan only for secrets (quick scan).

    Args:
        project_dir: Path to project root
        changed_files: Optional list of files to scan

    Returns:
        List of detected secrets
    """
    scanner = SecurityScanner()
    result = scanner.scan(
        project_dir,
        changed_files=changed_files,
        run_sast=False,
        run_dependency_audit=False,
    )
    return result.secrets


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Run security scans")
    parser.add_argument("project_dir", type=Path, help="Path to project root")
    parser.add_argument("--spec-dir", type=Path, help="Path to spec directory")
    parser.add_argument(
        "--secrets-only", action="store_true", help="Only scan for secrets"
    )
    parser.add_argument(
        "--predictive",
        action="store_true",
        help="Include predictive bug/performance/code smell scans",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    scanner = SecurityScanner(args.spec_dir)
    result = scanner.scan(
        args.project_dir,
        spec_dir=args.spec_dir,
        run_sast=not args.secrets_only,
        run_dependency_audit=not args.secrets_only,
        run_predictive_scan=args.predictive,
    )

    if args.json:
        print(json.dumps(scanner.to_dict(result), indent=2))
    else:
        print(f"Secrets Found: {len(result.secrets)}")
        print(f"Vulnerabilities: {len(result.vulnerabilities)}")
        if result.predictive_scan:
            predictive_issues = result.predictive_scan.get("summary", {}).get(
                "total_issues", 0
            )
            print(f"Predictive Issues: {predictive_issues}")
        print(f"Has Critical Issues: {result.has_critical_issues}")
        print(f"Should Block QA: {result.should_block_qa}")

        if result.secrets:
            print(f"\nSecrets Detected ({len(result.secrets)}):")
            for _secret_entry in result.secrets:
                # Only log pattern type and location, never actual secret values
                pattern_type = str(_secret_entry.get("pattern", "unknown"))
                file_loc = str(_secret_entry.get("file", "unknown"))
                line_num = str(_secret_entry.get("line", "?"))
                print(f"  - {pattern_type} in {file_loc}:{line_num}")

        if result.vulnerabilities:
            print(f"\nVulnerabilities ({len(result.vulnerabilities)}):")
            for v in result.vulnerabilities:
                print(f"  [{v.severity.upper()}] {v.title}")
                if v.file:
                    print(f"    File: {v.file}:{v.line or ''}")

        if result.predictive_scan:
            predictive_summary = result.predictive_scan.get("summary", {})
            print("\nPredictive Scan Results:")
            print(f"  Total Issues: {predictive_summary.get('total_issues', 0)}")
            print(f"  Critical: {predictive_summary.get('critical_count', 0)}")
            print(f"  High: {predictive_summary.get('high_count', 0)}")
            print(f"  Medium: {predictive_summary.get('medium_count', 0)}")
            print(f"  Low: {predictive_summary.get('low_count', 0)}")

            # Show top predictive issues
            predictive_issues = result.predictive_scan.get("issues", [])
            if predictive_issues:
                print("\n  Top Issues:")
                for issue in predictive_issues[:10]:
                    severity = issue.get("severity", "unknown").upper()
                    category = issue.get("category", "unknown")
                    title = issue.get("title", "No title")
                    file_loc = f"{issue.get('file', 'unknown')}:{issue.get('line', '')}"
                    print(f"    [{severity}] {category}: {title}")
                    print(f"      Location: {file_loc}")

        if result.scan_errors:
            print(f"\nScan Errors ({len(result.scan_errors)}):")
            for error in result.scan_errors:
                print(f"  - {error}")


if __name__ == "__main__":
    main()
