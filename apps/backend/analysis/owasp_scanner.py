#!/usr/bin/env python3
"""
OWASP Top 10 Scanner Module
===========================

Scans code for OWASP Top 10 (2021) security vulnerabilities:
1. Broken Access Control (A01)
2. Cryptographic Failures (A02)
3. Injection (A03)
4. Insecure Design (A04)
5. Security Misconfiguration (A05)
6. Vulnerable and Outdated Components (A06)
7. Identification and Authentication Failures (A07)
8. Software and Data Integrity Failures (A08)
9. Security Logging and Monitoring Failures (A09)
10. Server-Side Request Forgery (A10)

This scanner provides pattern-based detection of common vulnerabilities
and is used by the security audit agent for comprehensive analysis.

Usage:
    from analysis.owasp_scanner import OWASPScanner

    scanner = OWASPScanner()
    results = scanner.scan(project_dir)

    if results.has_critical_issues:
        print("OWASP Top 10 vulnerabilities found")
"""

from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class OWASPVulnerability:
    """
    Represents an OWASP Top 10 vulnerability found during scanning.

    Attributes:
        category: OWASP category (A01-A10)
        category_name: Full name of the OWASP category
        severity: Severity level (critical, high, medium, low)
        title: Short title of the vulnerability
        description: Detailed description
        file: File where vulnerability was found
        line: Line number
        code_snippet: Relevant code snippet (if available)
        recommendation: Fix recommendation
    """

    category: str  # A01-A10
    category_name: str
    severity: str  # critical, high, medium, low
    title: str
    description: str
    file: str
    line: int
    code_snippet: str | None = None
    recommendation: str | None = None


@dataclass
class OWASPScanResult:
    """
    Result of an OWASP Top 10 scan.

    Attributes:
        vulnerabilities: List of OWASP vulnerabilities found
        summary: Summary statistics by category
        scan_errors: List of errors during scanning
        has_critical_issues: Whether any critical issues were found
        total_vulnerabilities: Total count of vulnerabilities
    """

    vulnerabilities: list[OWASPVulnerability] = field(default_factory=list)
    summary: dict[str, dict[str, int]] = field(default_factory=dict)
    scan_errors: list[str] = field(default_factory=list)
    has_critical_issues: bool = False
    total_vulnerabilities: int = 0


# =============================================================================
# OWASP TOP 10 CATEGORIES
# =============================================================================

OWASP_CATEGORIES = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Vulnerable and Outdated Components",
    "A07": "Identification and Authentication Failures",
    "A08": "Software and Data Integrity Failures",
    "A09": "Security Logging and Monitoring Failures",
    "A10": "Server-Side Request Forgery",
}


# =============================================================================
# CONSTANTS
# =============================================================================

SCANNABLE_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".go",
        ".rs",
    }
)

# Regex for redacting sensitive values in code snippets
_SENSITIVE_VALUE_RE = re.compile(
    r"""(?<=['"])[a-zA-Z0-9_\-/+=]{16,}(?=['"])""",
)


def _redact_snippet(snippet: str) -> str:
    """Redact potential sensitive values from a code snippet."""
    return _SENSITIVE_VALUE_RE.sub("<REDACTED>", snippet)


def _safe_relative(file_path: Path, project_dir: Path | None = None) -> str:
    """Compute relative path against project_dir with fallback."""
    if project_dir:
        try:
            return str(file_path.relative_to(project_dir))
        except ValueError:
            pass
    return file_path.name


# =============================================================================
# OWASP SCANNER
# =============================================================================


class OWASPScanner:
    """
    OWASP Top 10 vulnerability scanner.

    Detects patterns related to OWASP Top 10 (2021) vulnerabilities:
    - A01: Broken Access Control
    - A02: Cryptographic Failures
    - A03: Injection (SQL, NoSQL, OS command, LDAP, etc.)
    - A04: Insecure Design
    - A05: Security Misconfiguration
    - A06: Vulnerable Components
    - A07: Authentication Failures
    - A08: Integrity Failures
    - A09: Logging/Monitoring Failures
    - A10: Server-Side Request Forgery
    """

    # Pattern definitions for each category
    PATTERNS = {
        "A01": [  # Broken Access Control
            (r"@\w*\.route\(.*/<int:\w+>", "IDOR - Direct object reference via ID"),
            (r"permission.*required.*False", "Permission check disabled"),
            (r"@login_required.*is False", "Login requirement bypassed"),
            (r"authorize.*=.*False", "Authorization explicitly disabled"),
            (r"check_access.*return.*True", "Access check always returns True"),
        ],
        "A02": [  # Cryptographic Failures
            (r"hashlib\.md5\(", "MD5 hash - weak cryptographic algorithm"),
            (r"hashlib\.sha1\(", "SHA1 hash - weak cryptographic algorithm"),
            (
                r"base64\.b(?:64|32|16)(?:encode|decode)\(.*(?:key|secret|password|token|cipher|encrypt|iv)",
                "Base64 encoding used with sensitive data - verify not used as encryption",
            ),
            (r"cipher.*AES.*ecb", "AES in ECB mode - insecure"),
            (r"crypto\.Cipher\.(ARC4|DES)", "Weak cipher algorithm"),
            (r"password.*=.*['\"]\w+['\"]", "Hardcoded password"),
            (r"api_key.*=.*['\"][a-zA-Z0-9]{16,}['\"]", "Hardcoded API key"),
        ],
        "A03": [  # Injection
            (r'f".*{.*}.*["\'].*["\']', "Possible SQL injection via f-string"),
            (
                r'\+.*["\'].*["\'].*(execute|executemany|query)',
                "SQL injection via string concatenation",
            ),
            (r"os\.system\(.+[^)]\)", "OS command injection vulnerability"),
            (
                r"subprocess\.(call|run|Popen)\(.+shell=True",
                "OS command injection via shell=True",
            ),
            (r"eval\(", "Code injection via eval()"),
            (r"exec\(", "Code injection via exec()"),
            (r"pickle\.loads?\(", "Deserialization vulnerability"),
            (r"yaml\.load\(", "Unsafe YAML loading"),
            (r"cursor\.execute.*%", "SQL injection via format string"),
        ],
        "A04": [  # Insecure Design
            (r"csrf.*protection.*False", "CSRF protection disabled"),
            (r"security.*=.*False", "Security feature disabled"),
            (r"validate.*=.*False", "Input validation disabled"),
            (r"sanitize.*=.*False", "Sanitization disabled"),
        ],
        "A05": [  # Security Misconfiguration
            (r"DEBUG.*=.*True", "Debug mode enabled in production"),
            (r"ALLOWED_HOSTS.*=.*\[\]", "Empty ALLOWED_HOSTS configuration"),
            (r"SECURE.*=.*False", "Security setting disabled"),
            (r"SESSION_COOKIE_SECURE.*=.*False", "Insecure session cookie"),
            (r"CSRF_COOKIE_SECURE.*=.*False", "Insecure CSRF cookie"),
            (r"CORS.*allow.*\*", "CORS configured to allow all origins"),
            (r"ssl.*verify.*=.*False", "SSL certificate verification disabled"),
        ],
        "A06": [  # Vulnerable Components
            (r"django.*==.*1\.\d+", "Outdated Django version (v1.x)"),
            (r"flask.*==.*0\.\d+", "Outdated Flask version (v0.x)"),
            (r"requests.*==.*2\.[0-5]\.", "Outdated requests version"),
            (r"pillow.*<.*7\.0", "Outdated Pillow version"),
        ],
        "A07": [  # Authentication Failures
            (r"password.*==.*password", "Password comparison without hash"),
            (r"authenticate.*return.*True", "Authentication bypass"),
            (r"is_authenticated.*=.*True", "Forced authentication"),
            (r"login.*username.*password.*GET", "Credentials via GET request"),
            (r"session.*in.*url", "Session ID in URL"),
        ],
        "A08": [  # Software and Data Integrity Failures
            (r"requests\.get\(.+verify=False", "Certificate verification disabled"),
            (r"urllib\.request\.urlopen", "Unverified URL request"),
            (r"subprocess.*pip.*install", "Unverified package installation"),
            (r"os\.system.*pip", "Unverified package installation"),
        ],
        "A09": [  # Security Logging and Monitoring Failures
            (r"except.*:.*pass", "Silent exception - no logging"),
            (r"except.*:.*return.*None", "Swallowed exception"),
            (r"except.*Exception:\s*$", "Generic exception without logging"),
            (r"password.*log", "Password logged in plain text"),
            (r"credit.*card.*log", "Credit card logged"),
            (r"ssn.*log", "SSN logged"),
        ],
        "A10": [  # Server-Side Request Forgery
            (r"requests\.(get|post)\(.*request\.", "SSRF via user-controlled URL"),
            (r"urllib\.open\(.*request\.", "SSRF via user-controlled URL"),
            (r"url.*=.*request\.", "User-controlled URL"),
            (r"fetch\(.*request\.", "SSRF via fetch request"),
        ],
    }

    def __init__(self) -> None:
        """Initialize the OWASP scanner."""
        # Compile regex patterns for better performance
        self._compiled_patterns: dict[str, list[tuple[re.Pattern[str], str]]] = {}
        for category, patterns in self.PATTERNS.items():
            self._compiled_patterns[category] = [
                (re.compile(pattern), description) for pattern, description in patterns
            ]

        # Validate that all OWASP Top 10 categories are covered
        self._validate_coverage()

    def _validate_coverage(self) -> None:
        """
        Validate that all OWASP Top 10 (2021) categories are covered.

        Raises:
            ValueError: If any OWASP category is missing patterns or configuration
        """
        missing_patterns = []
        missing_severity = []
        missing_recommendations = []

        for category in OWASP_CATEGORIES.keys():
            # Check if category exists in PATTERNS
            if category not in self.PATTERNS:
                missing_patterns.append(category)
            elif not self.PATTERNS[category]:
                missing_patterns.append(f"{category} (empty)")

            # Check if category has severity mapping
            severity = self._get_severity_for_category(category)
            if severity == "medium" and category not in {"A04", "A05", "A08"}:
                # Only A04, A05, A08 should default to medium
                missing_severity.append(category)

            # Check if category has recommendation
            recommendation = self._get_recommendation(category, "test")
            if recommendation == "Review and fix the vulnerability":
                missing_recommendations.append(category)

        # Report any missing coverage
        errors = []
        if missing_patterns:
            errors.append(f"Missing detection patterns: {', '.join(missing_patterns)}")
        if missing_severity:
            errors.append(f"Missing severity mapping: {', '.join(missing_severity)}")
        if missing_recommendations:
            errors.append(
                f"Missing recommendations: {', '.join(missing_recommendations)}"
            )

        if errors:
            raise ValueError("OWASP coverage validation failed:\n" + "\n".join(errors))

        logger.info(
            f"✓ All OWASP Top 10 (2021) categories covered: {len(OWASP_CATEGORIES)} categories"
        )

    def validate_owasp_coverage(self) -> dict[str, Any]:
        """
        Validate and return OWASP Top 10 coverage information.

        Returns:
            Dictionary with coverage details for each category
        """
        coverage = {}

        for category, category_name in OWASP_CATEGORIES.items():
            pattern_count = len(self.PATTERNS.get(category, []))
            severity = self._get_severity_for_category(category)
            recommendation = self._get_recommendation(category, "test")

            coverage[category] = {
                "category_name": category_name,
                "pattern_count": pattern_count,
                "severity": severity,
                "has_recommendation": recommendation
                != "Review and fix the vulnerability",
                "has_patterns": pattern_count > 0,
                "is_covered": pattern_count > 0,
            }

        return {
            "total_categories": len(OWASP_CATEGORIES),
            "covered_categories": sum(1 for c in coverage.values() if c["is_covered"]),
            "total_patterns": sum(c["pattern_count"] for c in coverage.values()),
            "categories": coverage,
            "all_covered": all(c["is_covered"] for c in coverage.values()),
        }

    def scan_injection_risks(
        self,
        project_dir: Path,
        files_to_scan: list[str] | None = None,
    ) -> list[OWASPVulnerability]:
        """
        Scan specifically for injection vulnerabilities (OWASP A03).

        Args:
            project_dir: Path to the project root
            files_to_scan: Optional list of files to scan (if None, scans all)

        Returns:
            List of injection vulnerabilities found
        """
        project_dir = Path(project_dir)
        injection_vulns: list[OWASPVulnerability] = []

        # Find files to scan
        if files_to_scan:
            file_paths = [
                project_dir / f for f in files_to_scan if self._is_scannable_file(f)
            ]
        else:
            file_paths = self._find_scannable_files(project_dir)

        # Scan each file for injection patterns
        for file_path in file_paths:
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    lines = content.splitlines()

                # Check injection patterns (A03)
                patterns = self._compiled_patterns.get("A03", [])
                if not patterns:
                    patterns = self.PATTERNS.get("A03", [])
                    patterns = [(re.compile(p), desc) for p, desc in patterns]

                for regex, description in patterns:
                    for line_num, line in enumerate(lines, start=1):
                        if regex.search(line):
                            injection_vulns.append(
                                OWASPVulnerability(
                                    category="A03",
                                    category_name=OWASP_CATEGORIES["A03"],
                                    severity="critical",
                                    title=description,
                                    description=f"Pattern matched: {description}",
                                    file=str(file_path.relative_to(project_dir)),
                                    line=line_num,
                                    code_snippet=_redact_snippet(line.strip()),
                                    recommendation=self._get_recommendation(
                                        "A03", description
                                    ),
                                )
                            )

                # Python-specific AST analysis for injection
                if file_path.suffix == ".py":
                    injection_vulns.extend(
                        self._analyze_python_for_injection(
                            file_path, content, project_dir
                        )
                    )

            except Exception as e:
                logger.warning(f"Error scanning {file_path} for injection: {e}")

        return injection_vulns

    def _analyze_python_for_injection(
        self,
        file_path: Path,
        content: str,
        project_dir: Path | None = None,
    ) -> list[OWASPVulnerability]:
        """
        Analyze Python AST for injection vulnerabilities.

        Args:
            file_path: Path to the file
            content: File content
            project_dir: Project root for computing relative paths

        Returns:
            List of injection vulnerabilities found
        """

        injection_vulns: list[OWASPVulnerability] = []

        try:
            tree = ast.parse(content)
            lines = content.splitlines()

            for node in ast.walk(tree):
                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    # Check for eval/exec
                    if isinstance(node.func, ast.Name):
                        if node.func.id in {"eval", "exec", "compile"}:
                            injection_vulns.append(
                                OWASPVulnerability(
                                    category="A03",
                                    category_name=OWASP_CATEGORIES["A03"],
                                    severity="critical",
                                    title=f"Dangerous function: {node.func.id}",
                                    description=f"Use of {node.func.id}() allows code injection",
                                    file=str(_safe_relative(file_path, project_dir)),
                                    line=node.lineno,
                                    code_snippet=_redact_snippet(
                                        lines[node.lineno - 1].strip()
                                    )
                                    if node.lineno <= len(lines)
                                    else "",
                                    recommendation="Avoid eval/exec; use safer alternatives",
                                )
                            )

                    # Check for shell=True in subprocess
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in {"call", "run", "Popen"}:
                            # Check if shell=True keyword argument
                            for keyword in node.keywords:
                                if keyword.arg == "shell":
                                    if isinstance(keyword.value, ast.Constant):
                                        if keyword.value.value is True:
                                            injection_vulns.append(
                                                OWASPVulnerability(
                                                    category="A03",
                                                    category_name=OWASP_CATEGORIES[
                                                        "A03"
                                                    ],
                                                    severity="critical",
                                                    title=f"OS command injection via {node.func.attr}",
                                                    description=f"Use of {node.func.attr}(shell=True) allows command injection",
                                                    file=_safe_relative(
                                                        file_path, project_dir
                                                    ),
                                                    line=node.lineno,
                                                    code_snippet=_redact_snippet(
                                                        lines[node.lineno - 1].strip()
                                                    )
                                                    if node.lineno <= len(lines)
                                                    else "",
                                                    recommendation="Avoid shell=True; use list arguments for subprocess",
                                                )
                                            )

                # Check for SQL string concatenation patterns
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                    if isinstance(node.left, ast.Constant) and isinstance(
                        node.left.value, str
                    ):
                        # Could be SQL concatenation - flag for review
                        pass  # This is noisy, so we skip it

        except SyntaxError:
            # Expected for non-standard Python files or files under development;
            # safe to skip as we continue scanning other files
            logger.debug("Skipping %s: syntax error in AST parsing", file_path)
        except Exception as e:
            logger.debug(f"AST injection analysis error for {file_path}: {e}")

        return injection_vulns

    def scan(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        changed_files: list[str] | None = None,
        include_patterns: list[str] | None = None,
    ) -> OWASPScanResult:
        """
        Run OWASP Top 10 vulnerability scan.

        Args:
            project_dir: Path to the project root
            spec_dir: Path to spec directory (for storing results)
            changed_files: Optional list of files to scan (if None, scans all)
            include_patterns: Optional list of OWASP categories to include (e.g., ['A01', 'A02'])

        Returns:
            OWASPScanResult with all findings
        """
        project_dir = Path(project_dir)
        result = OWASPScanResult()

        # Determine which categories to scan
        categories_to_scan = include_patterns or list(OWASP_CATEGORIES.keys())

        # Find files to scan
        if changed_files:
            files_to_scan = [
                project_dir / f for f in changed_files if self._is_scannable_file(f)
            ]
        else:
            files_to_scan = self._find_scannable_files(project_dir)

        # Scan each file
        for file_path in files_to_scan:
            self._scan_file(file_path, categories_to_scan, result, project_dir)

        # Calculate summary
        self._calculate_summary(result)

        # Save results if spec_dir provided
        if spec_dir:
            self._save_results(spec_dir, result)

        return result

    def _is_scannable_file(self, file_path: str) -> bool:
        """Check if file should be scanned."""
        return any(file_path.endswith(ext) for ext in SCANNABLE_EXTENSIONS)

    def _find_scannable_files(self, project_dir: Path) -> list[Path]:
        """Find all scannable files in the project."""
        files = []

        for ext in SCANNABLE_EXTENSIONS:
            files.extend(project_dir.glob(f"**/*{ext}"))

        # Exclude common directories
        excluded_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
        }
        files = [
            f
            for f in files
            if not any(excluded in f.parts for excluded in excluded_dirs)
        ]

        return files

    def _scan_file(
        self,
        file_path: Path,
        categories: list[str],
        result: OWASPScanResult,
        project_dir: Path | None = None,
    ) -> None:
        """Scan a single file for OWASP vulnerabilities."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.splitlines()

            # Scan for each category using pre-compiled patterns
            for category in categories:
                compiled = self._compiled_patterns.get(category, [])
                for regex, description in compiled:
                    self._scan_for_pattern(
                        file_path,
                        lines,
                        category,
                        regex,
                        description,
                        result,
                        project_dir,
                    )

            # Python-specific AST analysis
            if file_path.suffix == ".py":
                self._analyze_python_ast(file_path, content, result, project_dir)

        except Exception as e:
            result.scan_errors.append(f"Error scanning {file_path}: {str(e)}")

    def _scan_for_pattern(
        self,
        file_path: Path,
        lines: list[str],
        category: str,
        compiled_pattern: re.Pattern[str],
        description: str,
        result: OWASPScanResult,
        project_dir: Path | None = None,
    ) -> None:
        """Scan file content for a specific regex pattern."""
        try:
            regex = compiled_pattern
            for line_num, line in enumerate(lines, start=1):
                if regex.search(line):
                    # Determine severity based on category
                    severity = self._get_severity_for_category(category)

                    result.vulnerabilities.append(
                        OWASPVulnerability(
                            category=category,
                            category_name=OWASP_CATEGORIES[category],
                            severity=severity,
                            title=description,
                            description=f"Pattern matched: {description}",
                            file=str(
                                _safe_relative(file_path, project_dir)
                            ),  # Relative path
                            line=line_num,
                            code_snippet=_redact_snippet(line.strip()),
                            recommendation=self._get_recommendation(
                                category, description
                            ),
                        )
                    )
        except re.error as e:
            logger.warning(
                "Invalid regex pattern: %s - %s", compiled_pattern.pattern, e
            )

    def _analyze_python_ast(
        self,
        file_path: Path,
        content: str,
        result: OWASPScanResult,
        project_dir: Path | None = None,
    ) -> None:
        """Analyze Python AST for additional vulnerabilities."""
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Check for hardcoded credentials
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if target.id.lower() in {
                                "password",
                                "api_key",
                                "secret",
                                "token",
                                "private_key",
                            }:
                                if isinstance(node.value, ast.Constant):
                                    if (
                                        isinstance(node.value.value, str)
                                        and len(node.value.value) > 8
                                    ):
                                        result.vulnerabilities.append(
                                            OWASPVulnerability(
                                                category="A02",
                                                category_name=OWASP_CATEGORIES["A02"],
                                                severity="high",
                                                title="Hardcoded credential",
                                                description=f"Hardcoded {target.id} value",
                                                file=_safe_relative(
                                                    file_path, project_dir
                                                ),
                                                line=node.lineno,
                                                code_snippet=_redact_snippet(
                                                    content.splitlines()[
                                                        node.lineno - 1
                                                    ].strip()
                                                ),
                                                recommendation="Use environment variables or secret management",
                                            )
                                        )

                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in {"eval", "exec", "compile"}:
                            result.vulnerabilities.append(
                                OWASPVulnerability(
                                    category="A03",
                                    category_name=OWASP_CATEGORIES["A03"],
                                    severity="critical",
                                    title=f"Dangerous function: {node.func.attr}",
                                    description=f"Use of {node.func.attr}() function",
                                    file=str(_safe_relative(file_path, project_dir)),
                                    line=node.lineno,
                                    code_snippet=_redact_snippet(
                                        content.splitlines()[node.lineno - 1].strip()
                                    ),
                                    recommendation="Avoid eval/exec; use safer alternatives",
                                )
                            )

        except SyntaxError:
            # Expected for non-standard Python files or files under development;
            # safe to skip as we continue scanning other files
            logger.debug("Skipping %s: syntax error in AST parsing", file_path)
        except Exception as e:
            logger.debug(f"AST analysis error for {file_path}: {e}")

    def _get_severity_for_category(self, category: str) -> str:
        """Get default severity level for an OWASP category."""
        severity_map = {
            "A01": "high",  # Broken Access Control
            "A02": "high",  # Cryptographic Failures
            "A03": "critical",  # Injection
            "A04": "medium",  # Insecure Design
            "A05": "medium",  # Security Misconfiguration
            "A06": "high",  # Vulnerable Components
            "A07": "high",  # Authentication Failures
            "A08": "medium",  # Integrity Failures
            "A09": "low",  # Logging Failures
            "A10": "high",  # SSRF
        }
        return severity_map.get(category, "medium")

    def _get_recommendation(self, category: str, description: str) -> str:
        """Get fix recommendation for a vulnerability."""
        recommendations = {
            "A01": "Implement proper access controls and authorization checks",
            "A02": "Use strong encryption and secure key management",
            "A03": "Use parameterized queries and input validation",
            "A04": "Implement secure design patterns",
            "A05": "Review and harden security configuration",
            "A06": "Update to latest secure versions",
            "A07": "Implement strong authentication mechanisms",
            "A08": "Verify integrity of software and data",
            "A09": "Implement comprehensive logging and monitoring",
            "A10": "Validate and sanitize URLs for SSRF",
        }
        return recommendations.get(category, "Review and fix the vulnerability")

    def _calculate_summary(self, result: OWASPScanResult) -> None:
        """Calculate summary statistics."""
        result.total_vulnerabilities = len(result.vulnerabilities)
        result.has_critical_issues = any(
            v.severity in ["critical", "high"] for v in result.vulnerabilities
        )

        # Count by category and severity
        for vuln in result.vulnerabilities:
            if vuln.category not in result.summary:
                result.summary[vuln.category] = {
                    "category_name": vuln.category_name,
                    "total": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                }
            result.summary[vuln.category]["total"] += 1
            result.summary[vuln.category][vuln.severity] += 1

    def _save_results(self, spec_dir: Path, result: OWASPScanResult) -> None:
        """Save scan results to spec directory."""
        spec_dir = Path(spec_dir)
        spec_dir.mkdir(parents=True, exist_ok=True)

        output_file = spec_dir / "owasp_scan_results.json"
        output_data = self.to_dict(result)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

    def to_dict(self, result: OWASPScanResult) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "vulnerabilities": [
                {
                    "category": v.category,
                    "category_name": v.category_name,
                    "severity": v.severity,
                    "title": v.title,
                    "description": v.description,
                    "file": v.file,
                    "line": v.line,
                    "code_snippet": v.code_snippet,
                    "recommendation": v.recommendation,
                }
                for v in result.vulnerabilities
            ],
            "summary": result.summary,
            "scan_errors": result.scan_errors,
            "has_critical_issues": result.has_critical_issues,
            "total_vulnerabilities": result.total_vulnerabilities,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def scan_for_owasp_issues(
    project_dir: Path,
    spec_dir: Path | None = None,
    changed_files: list[str] | None = None,
) -> OWASPScanResult:
    """
    Convenience function to run OWASP scan.

    Args:
        project_dir: Path to project root
        spec_dir: Optional spec directory to save results
        changed_files: Optional list of files to scan

    Returns:
        OWASPScanResult with all findings
    """
    scanner = OWASPScanner()
    return scanner.scan(project_dir, spec_dir, changed_files)


def has_owasp_issues(project_dir: Path) -> bool:
    """
    Quick check if project has OWASP vulnerabilities.

    Args:
        project_dir: Path to project root

    Returns:
        True if any critical/high issues found
    """
    scanner = OWASPScanner()
    result = scanner.scan(project_dir)
    return result.has_critical_issues


def validate_owasp_coverage() -> dict[str, Any]:
    """
    Validate that all OWASP Top 10 (2021) categories are covered.

    Returns:
        Dictionary with coverage information for all categories

    Raises:
        ValueError: If any category is missing patterns or configuration
    """
    scanner = OWASPScanner()
    return scanner.validate_owasp_coverage()


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Run OWASP Top 10 scans")
    parser.add_argument(
        "project_dir", type=Path, nargs="?", help="Path to project root"
    )
    parser.add_argument("--spec-dir", type=Path, help="Path to spec directory")
    parser.add_argument(
        "--categories",
        type=str,
        help="Comma-separated list of OWASP categories (e.g., A01,A02,A03)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--validate-coverage",
        action="store_true",
        help="Validate that all OWASP Top 10 categories are covered",
    )

    args = parser.parse_args()

    # Handle coverage validation
    if args.validate_coverage:
        try:
            coverage = validate_owasp_coverage()
            if args.json:
                print(json.dumps(coverage, indent=2))
            else:
                print("OWASP Top 10 (2021) Coverage Validation")
                print("=" * 50)
                print(f"Total Categories: {coverage['total_categories']}")
                print(f"Covered Categories: {coverage['covered_categories']}")
                print(f"Total Detection Patterns: {coverage['total_patterns']}")
                print(
                    f"All Categories Covered: {'✓ YES' if coverage['all_covered'] else '✗ NO'}"
                )
                print("\nCategory Details:")
                for cat, details in coverage["categories"].items():
                    status = "✓" if details["is_covered"] else "✗"
                    print(
                        f"  {status} {cat} - {details['category_name']}: "
                        f"{details['pattern_count']} patterns, "
                        f"severity={details['severity']}"
                    )
        except ValueError as e:
            print(f"ERROR: {e}")
            exit(1)
        return

    # Require project_dir for scanning
    if not args.project_dir:
        parser.error("project_dir is required when not using --validate-coverage")

    scanner = OWASPScanner()
    categories = args.categories.split(",") if args.categories else None

    result = scanner.scan(
        args.project_dir,
        spec_dir=args.spec_dir,
        include_patterns=categories,
    )

    if args.json:
        print(json.dumps(scanner.to_dict(result), indent=2))
    else:
        print(f"Total Vulnerabilities: {result.total_vulnerabilities}")
        print(f"Has Critical Issues: {result.has_critical_issues}")

        if result.summary:
            print("\nVulnerabilities by Category:")
            for cat, stats in result.summary.items():
                print(
                    f"  {cat} - {stats['category_name']}: {stats['total']} "
                    f"(Critical: {stats['critical']}, High: {stats['high']}, "
                    f"Medium: {stats['medium']}, Low: {stats['low']})"
                )

        if result.vulnerabilities:
            print("\nTop Vulnerabilities:")
            for v in result.vulnerabilities[:10]:
                print(
                    f"  [{v.severity.upper()}] {v.category} - {v.title} "
                    f"in {v.file}:{v.line}"
                )

        if result.scan_errors:
            print(f"\nScan Errors ({len(result.scan_errors)}):")
            for error in result.scan_errors:
                print(f"  - {error}")


if __name__ == "__main__":
    main()
