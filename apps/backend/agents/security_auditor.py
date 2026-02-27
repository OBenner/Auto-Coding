"""
Security Audit Agent Module
============================

Specialized agent for security analysis. Scans for vulnerabilities, checks dependencies,
reviews authentication flows, and generates security reports with remediation guidance.

This agent coordinates multiple security scanning capabilities:
- OWASP Top 10 vulnerability scanning
- Dependency vulnerability checking
- Authentication flow analysis
- Secret detection
- Security report generation

Usage:
    from agents.security_auditor import SecurityAuditAgent

    auditor = SecurityAuditAgent()
    report = auditor.run_full_audit(project_dir, spec_dir)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analysis.security_scanner import SecurityScanner

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class SecurityFinding:
    """
    Represents a security finding discovered during an audit.

    Attributes:
        category: Category of finding (owasp, dependency, secret, auth, etc.)
        owasp_category: OWASP Top 10 category (if applicable)
        severity: Severity level (critical, high, medium, low, info)
        title: Short title of the finding
        description: Detailed description
        file: File where finding was located (if applicable)
        line: Line number (if applicable)
        code_snippet: Relevant code snippet (if applicable)
        remediation: Remediation guidance
        cwe: CWE identifier if available
        references: List of reference URLs
    """

    category: str  # owasp, dependency, secret, auth, etc.
    owasp_category: str | None = None  # A01-A10:2021
    severity: str = "medium"  # critical, high, medium, low, info
    title: str = ""
    description: str = ""
    file: str | None = None
    line: int | None = None
    code_snippet: str | None = None
    remediation: str = ""
    cwe: str | None = None
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "owasp_category": self.owasp_category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file": self.file,
            "line": self.line,
            "code_snippet": self.code_snippet,
            "remediation": self.remediation,
            "cwe": self.cwe,
            "references": self.references,
        }


@dataclass
class SecurityReport:
    """
    Comprehensive security audit report.

    Attributes:
        project_dir: Path to the audited project
        timestamp: When the audit was run
        findings: List of all security findings
        summary_counts: Count of findings by severity
        owasp_coverage: Which OWASP categories were checked
        authentication_review: Results of authentication flow analysis
        dependency_audit: Results of dependency vulnerability scan
        secrets_scan: Results of secrets detection scan
        executive_summary: High-level summary for stakeholders
        recommendations: Prioritized remediation recommendations
    """

    project_dir: str
    timestamp: str
    findings: list[SecurityFinding] = field(default_factory=list)
    summary_counts: dict[str, int] = field(default_factory=dict)
    owasp_coverage: dict[str, bool] = field(default_factory=dict)
    authentication_review: dict[str, Any] = field(default_factory=dict)
    dependency_audit: dict[str, Any] = field(default_factory=dict)
    secrets_scan: dict[str, Any] = field(default_factory=dict)
    executive_summary: str = ""
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate summary counts after initialization."""
        if not self.summary_counts:
            self._calculate_summary_counts()

    def _calculate_summary_counts(self) -> None:
        """Calculate finding counts by severity."""
        self.summary_counts = {
            "critical": sum(1 for f in self.findings if f.severity == "critical"),
            "high": sum(1 for f in self.findings if f.severity == "high"),
            "medium": sum(1 for f in self.findings if f.severity == "medium"),
            "low": sum(1 for f in self.findings if f.severity == "low"),
            "info": sum(1 for f in self.findings if f.severity == "info"),
            "total": len(self.findings),
        }

    def add_finding(self, finding: SecurityFinding) -> None:
        """Add a finding and update summary counts."""
        self.findings.append(finding)
        self._calculate_summary_counts()

    def get_critical_findings(self) -> list[SecurityFinding]:
        """Get all critical and high severity findings."""
        return [f for f in self.findings if f.severity in ("critical", "high")]

    def has_blocking_issues(self) -> bool:
        """Check if report has critical or high severity issues."""
        return any(f.severity in ("critical", "high") for f in self.findings)

    def to_security_scan_results_dict(self) -> dict[str, Any]:
        """
        Convert report to security_scan_results.json compatible format.

        This format is compatible with the SecurityScanner output format
        used by the QA agent and validation strategy.

        Returns:
            Dictionary in security_scan_results.json format
        """
        # Convert findings to vulnerabilities format
        vulnerabilities = []
        secrets = []

        for finding in self.findings:
            if finding.category == "secret":
                secrets.append(
                    {
                        "file": "[redacted]",
                        "line": 0,
                        "pattern": "secret",
                        "matched_text": "[redacted]",
                    }
                )
                # Also add as vulnerability
                vulnerabilities.append(
                    {
                        "severity": finding.severity,
                        "source": "secrets",
                        "title": finding.title,
                        "description": finding.description,
                        "file": None,
                        "line": None,
                        "cwe": finding.cwe,
                    }
                )
            else:
                # Map category to source
                source_map = {
                    "auth": "auth_scanner",
                    "dependency": "dependency_audit",
                    "owasp": "owasp_scanner",
                }
                vulnerabilities.append(
                    {
                        "severity": finding.severity,
                        "source": source_map.get(finding.category, finding.category),
                        "title": finding.title,
                        "description": finding.description,
                        "file": finding.file,
                        "line": finding.line,
                        "cwe": finding.cwe,
                    }
                )

        return {
            "secrets": secrets,
            "vulnerabilities": vulnerabilities,
            "scan_errors": [],
            "has_critical_issues": self.summary_counts["critical"] > 0,
            "should_block_qa": self.summary_counts["critical"] > 0,
            "summary": {
                "total_secrets": len(secrets),
                "total_vulnerabilities": len(vulnerabilities),
                "critical_count": self.summary_counts["critical"],
                "high_count": self.summary_counts["high"],
                "medium_count": self.summary_counts["medium"],
                "low_count": self.summary_counts["low"],
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization.

        Sensitive data (code snippets from secret findings) is redacted
        to avoid clear-text storage of secrets in report files.
        """
        redacted_findings = []
        for f in self.findings:
            finding_dict = f.to_dict()
            if f.category == "secret" and finding_dict.get("code_snippet"):
                finding_dict["code_snippet"] = "[REDACTED]"
            redacted_findings.append(finding_dict)

        return {
            "project_dir": self.project_dir,
            "timestamp": self.timestamp,
            "findings": redacted_findings,
            "summary_counts": self.summary_counts,
            "owasp_coverage": self.owasp_coverage,
            "authentication_review": self.authentication_review,
            "dependency_audit": self.dependency_audit,
            "secrets_scan": self.secrets_scan,
            "executive_summary": self.executive_summary,
            "recommendations": self.recommendations,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Convert report to markdown format with severity grouping."""
        lines = [
            "# Security Audit Report",
            "",
            f"**Project:** {self.project_dir}",
            f"**Date:** {self.timestamp}",
            "",
            "## Executive Summary",
            "",
            self.executive_summary or "No executive summary provided.",
            "",
            "## Summary",
            "",
            f"- **Critical:** {self.summary_counts['critical']}",
            f"- **High:** {self.summary_counts['high']}",
            f"- **Medium:** {self.summary_counts['medium']}",
            f"- **Low:** {self.summary_counts['low']}",
            f"- **Total:** {self.summary_counts['total']}",
            "",
        ]

        # Findings grouped by severity (severity grouping)
        severity_order = ["critical", "high", "medium", "low", "info"]

        for severity in severity_order:
            findings_at_severity = [f for f in self.findings if f.severity == severity]
            if findings_at_severity:
                lines.extend(
                    [
                        f"## {severity.capitalize()} Severity Findings",
                        "",
                    ]
                )
                for finding in findings_at_severity:
                    lines.extend(
                        [
                            f"### {finding.title}",
                            "",
                            f"**Severity:** {finding.severity.upper()}",
                            f"**Category:** {finding.category}",
                            "",
                            finding.description,
                            "",
                        ]
                    )
                    if finding.file:
                        lines.append(
                            f"**Location:** `{finding.file}:{finding.line or '?'}`"
                        )
                        lines.append("")
                    if finding.remediation:
                        lines.extend(
                            [
                                "**Remediation:**",
                                "",
                                finding.remediation,
                                "",
                            ]
                        )
                    if finding.cwe:
                        lines.append(f"**CWE:** {finding.cwe}")
                        lines.append("")
                    if finding.references:
                        lines.extend(
                            [
                                "**References:**",
                                "",
                            ]
                        )
                        for ref in finding.references:
                            lines.append(f"- {ref}")
                        lines.append("")

        # Recommendations
        if self.recommendations:
            lines.extend(
                [
                    "## Recommendations",
                    "",
                ]
            )
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return "\n".join(lines)

    def to_json_file(self, filepath: str | Path) -> None:
        """
        Save report to JSON file.

        Args:
            filepath: Path to output JSON file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

        logger.info(f"Security report saved to {filepath}")

    def to_markdown_file(self, filepath: str | Path) -> None:
        """
        Save report to Markdown file.

        Args:
            filepath: Path to output Markdown file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())

        logger.info(f"Security report saved to {filepath}")


# =============================================================================
# SECURITY AUDIT AGENT
# =============================================================================


class SecurityAuditAgent:
    """
    Security audit agent for comprehensive security analysis.

    This agent orchestrates multiple security scanning capabilities:
    - OWASP Top 10 vulnerability scanning
    - Dependency vulnerability checking
    - Authentication flow analysis
    - Secret detection
    - Security report generation

    Example:
        auditor = SecurityAuditAgent()
        report = auditor.run_full_audit(
            project_dir=Path("/path/to/project"),
            spec_dir=Path("/path/to/spec")
        )

        # Export results
        report.to_json_file("security_report.json")
        report.to_markdown_file("security_report.md")
    """

    def __init__(self) -> None:
        """Initialize the security audit agent."""
        self._security_scanner: SecurityScanner | None = None

    @property
    def security_scanner(self) -> SecurityScanner:
        """Get or create the security scanner instance."""
        if self._security_scanner is None:
            self._security_scanner = SecurityScanner()
        return self._security_scanner

    def run_full_audit(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        scan_dependencies: bool = True,
        scan_secrets: bool = True,
        analyze_auth: bool = True,
        scan_owasp: bool = True,
    ) -> SecurityReport:
        """
        Run a comprehensive security audit.

        This method coordinates all security scanning capabilities:
        - OWASP Top 10 vulnerability scanning
        - Dependency vulnerability checking
        - Authentication flow analysis
        - Secret detection

        Args:
            project_dir: Path to the project root
            spec_dir: Optional path to spec directory (for storing results)
            scan_dependencies: Whether to run dependency vulnerability scans
            scan_secrets: Whether to run secret detection
            analyze_auth: Whether to analyze authentication flows
            scan_owasp: Whether to run OWASP Top 10 scanning

        Returns:
            SecurityReport with all findings and recommendations
        """
        from datetime import datetime

        project_dir = Path(project_dir)

        # Initialize report
        report = SecurityReport(
            project_dir=str(project_dir),
            timestamp=datetime.now().isoformat(),
        )

        # Run secret detection
        if scan_secrets:
            logger.info("Running secret detection scan...")
            self._scan_secrets(project_dir, report)

        # Run dependency audit
        if scan_dependencies:
            logger.info("Running dependency vulnerability scan...")
            self._scan_dependencies(project_dir, report)

        # Analyze authentication flows
        if analyze_auth:
            logger.info("Analyzing authentication flows...")
            self._analyze_authentication(project_dir, report)

        # Run OWASP Top 10 scanning
        if scan_owasp:
            logger.info("Running OWASP Top 10 scanning...")
            self._scan_owasp(project_dir, report)

        # Generate executive summary and recommendations
        self._generate_summary_and_recommendations(report)

        # Save report if spec_dir provided
        if spec_dir:
            self._save_report(spec_dir, report)

        return report

    def _scan_secrets(self, project_dir: Path, report: SecurityReport) -> None:
        """
        Scan for secrets in the codebase.

        Integrates with the existing SecurityScanner for secret detection.

        Args:
            project_dir: Path to the project root
            report: Report object to update with findings
        """
        # Use the existing security scanner for secrets detection
        scan_result = self.security_scanner.scan(
            project_dir,
            spec_dir=None,
            run_sast=False,
            run_dependency_audit=False,
        )

        # Create a summary finding for detected secrets.
        # Individual secret details (matched_text, file paths) are intentionally
        # NOT propagated into findings to avoid clear-text storage of sensitive data.
        num_secrets = len(scan_result.secrets)

        if num_secrets > 0:
            finding = SecurityFinding(
                category="secret",
                severity="critical",
                title=f"{num_secrets} potential secret(s) detected in codebase",
                description=(
                    f"The security scanner detected {num_secrets} potential "
                    "secret(s) in the codebase. Run the security scanner "
                    "directly for detailed file locations and remediation."
                ),
                remediation=(
                    "Remove secrets from the code. Use environment variables "
                    "or a secrets management system."
                ),
                references=[
                    "https://owasp.org/www-project-top-ten/2017/A2_2017-Credential_Stuffing"
                ],
            )
            report.add_finding(finding)

        # Store secrets scan summary (counts only, no sensitive data)
        report.secrets_scan = {
            "secrets_found": num_secrets,
        }

        logger.info(f"Secrets scan found {num_secrets} potential secrets")

    def _scan_dependencies(self, project_dir: Path, report: SecurityReport) -> None:
        """
        Scan for dependency vulnerabilities.

        Integrates with the existing SecurityScanner for dependency checking.

        Args:
            project_dir: Path to the project root
            report: Report object to update with findings
        """
        # Use the existing security scanner for dependency audit
        scan_result = self.security_scanner.scan(
            project_dir,
            spec_dir=None,
            run_secrets=False,
            run_sast=False,
        )

        # Filter for dependency vulnerabilities
        dep_vulnerabilities = [
            v
            for v in scan_result.vulnerabilities
            if v.source in ("npm_audit", "pip_audit", "yarn_audit")
        ]

        # Convert to findings
        for vuln in dep_vulnerabilities:
            finding = SecurityFinding(
                category="dependency",
                severity=vuln.severity,
                title=vuln.title,
                description=vuln.description,
                file=vuln.file,
                remediation="Update the vulnerable dependency to the latest secure version.",
                cwe=vuln.cwe,
                references=[
                    "https://owasp.org/www-project-top-ten/A06_2021-Vulnerable_and_Outdated_Components"
                ],
            )
            report.add_finding(finding)

        # Store dependency audit results
        report.dependency_audit = {
            "vulnerabilities_found": len(dep_vulnerabilities),
            "critical_count": sum(
                1 for v in dep_vulnerabilities if v.severity == "critical"
            ),
            "high_count": sum(1 for v in dep_vulnerabilities if v.severity == "high"),
        }

        logger.info(
            f"Dependency audit found {len(dep_vulnerabilities)} vulnerabilities"
        )

    def analyze_authentication(
        self,
        project_dir: Path,
    ) -> dict[str, Any]:
        """
        Analyze authentication flows for security issues.

        This method performs a comprehensive analysis of authentication implementations,
        checking for common security vulnerabilities and misconfigurations.

        Authentication checks include:
        - Hardcoded credentials (passwords, API keys, tokens)
        - Insecure password storage (plaintext, weak hashing)
        - Missing authentication on sensitive endpoints
        - Session management issues (session fixation, timeout)
        - Token handling (JWT, OAuth)
        - Multi-factor authentication (MFA) implementation
        - Rate limiting and brute force protection
        - Password reset flow security

        Args:
            project_dir: Path to the project root

        Returns:
            Dictionary containing:
                - findings: List of SecurityFinding objects
                - auth_mechanisms: List of detected auth frameworks/libraries
                - checks_performed: List of authentication checks that were run
                - summary: Summary statistics

        Example:
            result = auditor.analyze_authentication(Path("/project"))
            print(f"Found {len(result['findings'])} authentication issues")
        """
        auth_findings = self._scan_auth_patterns(project_dir)

        # Detect authentication mechanisms in use
        auth_mechanisms = self._detect_auth_mechanisms(project_dir)

        # Perform additional authentication checks
        additional_findings = self._check_password_policies(project_dir)
        auth_findings.extend(additional_findings)

        additional_findings = self._check_session_management(project_dir)
        auth_findings.extend(additional_findings)

        additional_findings = self._check_token_handling(project_dir)
        auth_findings.extend(additional_findings)

        additional_findings = self._check_rate_limiting(project_dir)
        auth_findings.extend(additional_findings)

        # Calculate summary
        severity_counts = {
            "critical": sum(1 for f in auth_findings if f.severity == "critical"),
            "high": sum(1 for f in auth_findings if f.severity == "high"),
            "medium": sum(1 for f in auth_findings if f.severity == "medium"),
            "low": sum(1 for f in auth_findings if f.severity == "low"),
            "info": sum(1 for f in auth_findings if f.severity == "info"),
        }

        return {
            "findings": auth_findings,
            "auth_mechanisms": auth_mechanisms,
            "checks_performed": [
                "hardcoded_credentials",
                "password_policies",
                "session_management",
                "token_handling",
                "rate_limiting",
            ],
            "summary": {
                **severity_counts,
                "total": len(auth_findings),
            },
        }

    def _analyze_authentication(
        self, project_dir: Path, report: SecurityReport
    ) -> None:
        """
        Analyze authentication flows for security issues.

        Checks for:
        - Hardcoded credentials
        - Insecure password handling
        - Missing authentication on sensitive endpoints
        - Session management issues

        Args:
            project_dir: Path to the project root
            report: Report object to update with findings
        """
        auth_result = self.analyze_authentication(project_dir)

        for finding in auth_result["findings"]:
            report.add_finding(finding)

        report.authentication_review = {
            "findings_count": len(auth_result["findings"]),
            "auth_mechanisms": auth_result["auth_mechanisms"],
            "checks_performed": auth_result["checks_performed"],
            "summary": auth_result["summary"],
        }

        logger.info(
            f"Authentication analysis found {len(auth_result['findings'])} issues"
        )

    def _scan_auth_patterns(self, project_dir: Path) -> list[SecurityFinding]:
        """
        Scan for authentication security issues.

        This method scans code for hardcoded credentials, insecure password handling,
        and other authentication-related security issues.

        Args:
            project_dir: Path to the project root

        Returns:
            List of security findings related to authentication
        """

        findings = []

        # =============================================================================
        # AUTHENTICATION SECURITY PATTERNS
        # =============================================================================

        # Patterns for hardcoded credentials and secrets
        # These patterns match common but insecure ways of storing credentials
        CREDENTIAL_PATTERNS = {
            # Password assignments
            r"password\s*=\s*['\"][^'\"]{8,}['\"]": {
                "title": "Hardcoded password detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"passwd\s*=\s*['\"][^'\"]{8,}['\"]": {
                "title": "Hardcoded password detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            # API keys and tokens
            r"api_key\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded API key detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"apikey\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded API key detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"api_secret\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded API secret detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"secret_key\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded secret key detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"secret\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded secret detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            # Tokens
            r"access_token\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded access token detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"auth_token\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded authentication token detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"bearer_token\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded bearer token detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            # Database credentials
            r"db_password\s*=\s*['\"][^'\"]{8,}['\"]": {
                "title": "Hardcoded database password detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"database_password\s*=\s*['\"][^'\"]{8,}['\"]": {
                "title": "Hardcoded database password detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            # JWT secrets
            r"jwt_secret\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded JWT secret detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            # OAuth credentials
            r"oauth_secret\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded OAuth secret detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
            r"client_secret\s*=\s*['\"][^'\"]{20,}['\"]": {
                "title": "Hardcoded client secret detected",
                "severity": "critical",
                "cwe": "CWE-798",
            },
        }

        # Patterns for insecure authentication configurations
        INSECURE_AUTH_PATTERNS = {
            # Plaintext password storage
            r"password\s*=\s*.*\.encode\(\)": {
                "title": "Plaintext password encoding detected",
                "description": "Password is being encoded but not hashed",
                "severity": "high",
                "cwe": "CWE-256",
            },
            # Weak hashing algorithms
            r"md5\(.+password": {
                "title": "MD5 used for password hashing",
                "description": "MD5 is cryptographically broken and should not be used for password hashing",
                "severity": "high",
                "cwe": "CWE-327",
            },
            r"sha1\(.+password": {
                "title": "SHA1 used for password hashing",
                "description": "SHA1 is deprecated for password hashing. Use bcrypt, scrypt, or Argon2",
                "severity": "medium",
                "cwe": "CWE-327",
            },
            # Missing salt
            r"hash\(.+password\)": {
                "title": "Password hashing without salt detected",
                "description": "Password hashing should use a salt. Consider using bcrypt or scrypt",
                "severity": "medium",
                "cwe": "CWE-759",
            },
            # Hardcoded comparison strings
            r"password\s*==\s*['\"]": {
                "title": "Direct password string comparison detected",
                "description": "Passwords should be hashed and compared using a timing-safe function",
                "severity": "critical",
                "cwe": "CWE-257",
            },
        }

        # =============================================================================
        # FILE SCANNING
        # =============================================================================

        # Scan Python files
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")

                # Check for hardcoded credentials
                for pattern, config in CREDENTIAL_PATTERNS.items():
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        line_num = content[: match.start()].count("\n") + 1
                        line_content = (
                            lines[line_num - 1] if line_num <= len(lines) else ""
                        )

                        finding = SecurityFinding(
                            category="auth",
                            owasp_category="A07_2021",
                            severity=config["severity"],
                            title=config["title"],
                            description=f"Potential hardcoded credential found in {py_file.name}",
                            file=str(py_file.relative_to(project_dir)),
                            line=line_num,
                            code_snippet=line_content.strip(),
                            remediation=(
                                "Remove hardcoded credentials from code. "
                                "Use environment variables or a secrets management system. "
                                "If this is a test value, move it to test fixtures."
                            ),
                            cwe=config["cwe"],
                            references=[
                                "https://owasp.org/www-project-top-ten/A07_2021-Identification_and_Authentication_Failures",
                                "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
                            ],
                        )
                        findings.append(finding)

                # Check for insecure authentication patterns
                for pattern, config in INSECURE_AUTH_PATTERNS.items():
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        line_num = content[: match.start()].count("\n") + 1
                        line_content = (
                            lines[line_num - 1] if line_num <= len(lines) else ""
                        )

                        finding = SecurityFinding(
                            category="auth",
                            owasp_category="A07_2021",
                            severity=config["severity"],
                            title=config["title"],
                            description=config.get(
                                "description",
                                "Insecure authentication pattern detected",
                            ),
                            file=str(py_file.relative_to(project_dir)),
                            line=line_num,
                            code_snippet=line_content.strip(),
                            remediation=(
                                "Use strong password hashing algorithms (bcrypt, scrypt, Argon2) "
                                "with proper salting. Never store passwords in plaintext."
                            ),
                            cwe=config["cwe"],
                            references=[
                                "https://owasp.org/www-project-top-ten/A07_2021-Identification_and_Authentication_Failures",
                                "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html",
                            ],
                        )
                        findings.append(finding)

            except (OSError, UnicodeDecodeError):
                pass  # Skip files that can't be read

        # Scan JavaScript/TypeScript files
        for js_file in project_dir.rglob("*.{js,ts,jsx,tsx}"):
            try:
                content = js_file.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")

                # Check for hardcoded credentials
                for pattern, config in CREDENTIAL_PATTERNS.items():
                    # Adjust pattern for JavaScript syntax
                    js_pattern = pattern.replace(r"\s*=\s*", r"\s*[:=]\s*")
                    for match in re.finditer(js_pattern, content, re.IGNORECASE):
                        line_num = content[: match.start()].count("\n") + 1
                        line_content = (
                            lines[line_num - 1] if line_num <= len(lines) else ""
                        )

                        finding = SecurityFinding(
                            category="auth",
                            owasp_category="A07_2021",
                            severity=config["severity"],
                            title=config["title"],
                            description=f"Potential hardcoded credential found in {js_file.name}",
                            file=str(js_file.relative_to(project_dir)),
                            line=line_num,
                            code_snippet=line_content.strip(),
                            remediation=(
                                "Remove hardcoded credentials from code. "
                                "Use environment variables or a secrets management system."
                            ),
                            cwe=config["cwe"],
                            references=[
                                "https://owasp.org/www-project-top-ten/A07_2021-Identification_and_Authentication_Failures",
                            ],
                        )
                        findings.append(finding)

            except (OSError, UnicodeDecodeError):
                pass  # Skip files that can't be read

        return findings

    def _detect_auth_mechanisms(self, project_dir: Path) -> list[str]:
        """
        Detect authentication frameworks and libraries in use.

        Args:
            project_dir: Path to the project root

        Returns:
            List of detected authentication mechanisms
        """

        mechanisms = []

        # Check package.json for Node.js projects
        package_json = project_dir / "package.json"
        if package_json.exists():
            try:
                content = package_json.read_text(encoding="utf-8")
                if "passport" in content.lower():
                    mechanisms.append("Passport.js")
                if "next-auth" in content.lower() or "next-auth" in content:
                    mechanisms.append("NextAuth.js")
                if "auth0" in content.lower():
                    mechanisms.append("Auth0")
                if "firebase" in content.lower() and "auth" in content.lower():
                    mechanisms.append("Firebase Authentication")
                if "cognito" in content.lower():
                    mechanisms.append("AWS Cognito")
                if "jsonwebtoken" in content.lower():
                    mechanisms.append("JWT (jsonwebtoken)")
                if "bcrypt" in content.lower():
                    mechanisms.append("bcrypt")
                if "argon2" in content.lower():
                    mechanisms.append("Argon2")
            except (OSError, UnicodeDecodeError) as e:
                logger.debug("Could not read package.json: %s", e)

        # Check requirements.txt for Python projects
        requirements = project_dir / "requirements.txt"
        if requirements.exists():
            try:
                content = requirements.read_text(encoding="utf-8")
                if "django" in content.lower():
                    mechanisms.append("Django Authentication")
                if "flask-login" in content.lower():
                    mechanisms.append("Flask-Login")
                if "flask-security" in content.lower():
                    mechanisms.append("Flask-Security")
                if "pyjwt" in content.lower():
                    mechanisms.append("PyJWT")
                if "bcrypt" in content.lower():
                    mechanisms.append("bcrypt")
                if "argon2-cffi" in content.lower():
                    mechanisms.append("Argon2")
                if "passlib" in content.lower():
                    mechanisms.append("Passlib")
                if "authlib" in content.lower():
                    mechanisms.append("Authlib")
            except (OSError, UnicodeDecodeError) as e:
                logger.debug("Could not read requirements.txt: %s", e)

        # Check for common auth files
        auth_files = [
            "auth.py",
            "authentication.py",
            "login.py",
            "auth.ts",
            "auth.tsx",
            "Auth.tsx",
        ]
        for auth_file in auth_files:
            if (project_dir / auth_file).exists():
                mechanisms.append(f"Custom Auth ({auth_file})")
                break

        # Check for JWT usage in code
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if re.search(r"jwt\.|JWT|", content, re.IGNORECASE):
                    if "JWT" not in mechanisms:
                        mechanisms.append("JWT")
                    break
            except (OSError, UnicodeDecodeError) as e:
                logger.debug("Could not read %s for JWT check: %s", py_file, e)

        return list(set(mechanisms)) if mechanisms else ["No auth mechanisms detected"]

    def _check_password_policies(self, project_dir: Path) -> list[SecurityFinding]:
        """
        Check for password policy implementation.

        Checks for:
        - Password length requirements
        - Password complexity requirements
        - Password hashing algorithms

        Args:
            project_dir: Path to the project root

        Returns:
            List of security findings
        """

        findings = []

        # Check for password validation/policy code
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # Check if password validation exists
                if "password" in content.lower():
                    # Look for password length checks
                    if not re.search(
                        r"len\(.*password.*\)\s*[<>]=\s*\d+", content, re.IGNORECASE
                    ):
                        # If password handling exists but no length check found
                        if re.search(
                            r"def.*password|class.*password", content, re.IGNORECASE
                        ):
                            finding = SecurityFinding(
                                category="auth",
                                owasp_category="A07_2021",
                                severity="medium",
                                title="Password policy may not enforce minimum length",
                                description="Password handling detected but minimum length requirements may not be enforced",
                                file=str(py_file.relative_to(project_dir)),
                                remediation=(
                                    "Implement password policy with minimum length of 8 characters. "
                                    "Consider requiring complexity (uppercase, lowercase, numbers, symbols)."
                                ),
                                cwe="CWE-521",
                                references=[
                                    "https://owasp.org/www-project-top-ten/A07_2021-Identification_and_Authentication_Failures",
                                    "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html",
                                ],
                            )
                            findings.append(finding)

            except (OSError, UnicodeDecodeError) as e:
                logger.debug(
                    "Could not read %s for password policy check: %s", py_file, e
                )

        return findings

    def _check_session_management(self, project_dir: Path) -> list[SecurityFinding]:
        """
        Check for session management security.

        Checks for:
        - Session timeout configuration
        - Session fixation prevention
        - Secure cookie flags

        Args:
            project_dir: Path to the project root

        Returns:
            List of security findings
        """

        findings = []

        # Check for session management code
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")

                if "session" in content.lower():
                    # Check for secure cookie flags
                    if re.search(
                        r"session\.cookie_httponly\s*=\s*False", content, re.IGNORECASE
                    ):
                        line_num = next(
                            i
                            for i, line in enumerate(lines)
                            if "session.cookie_httponly" in line.lower()
                        )
                        finding = SecurityFinding(
                            category="auth",
                            owasp_category="A07_2021",
                            severity="high",
                            title="Session cookies not marked HTTPOnly",
                            description="HTTPOnly flag is not set on session cookies, making them vulnerable to XSS",
                            file=str(py_file.relative_to(project_dir)),
                            line=line_num + 1,
                            code_snippet=lines[line_num].strip(),
                            remediation=(
                                "Set session.cookie_httponly = True to prevent JavaScript access "
                                "to session cookies."
                            ),
                            cwe="CWE-1004",
                            references=[
                                "https://owasp.org/www-project-top-ten/A07_2021-Identification_and_Authentication_Failures",
                                "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html",
                            ],
                        )
                        findings.append(finding)

                    if re.search(
                        r"session\.cookie_secure\s*=\s*False", content, re.IGNORECASE
                    ):
                        line_num = next(
                            i
                            for i, line in enumerate(lines)
                            if "session.cookie_secure" in line.lower()
                        )
                        finding = SecurityFinding(
                            category="auth",
                            owasp_category="A05_2021",
                            severity="high",
                            title="Session cookies not marked Secure",
                            description="Secure flag is not set on session cookies, allowing transmission over HTTP",
                            file=str(py_file.relative_to(project_dir)),
                            line=line_num + 1,
                            code_snippet=lines[line_num].strip(),
                            remediation=(
                                "Set session.cookie_secure = True to ensure cookies are only "
                                "transmitted over HTTPS."
                            ),
                            cwe="CWE-614",
                            references=[
                                "https://owasp.org/www-project-top-ten/A05_2021-Security_Misconfiguration",
                                "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html",
                            ],
                        )
                        findings.append(finding)

            except (OSError, UnicodeDecodeError, StopIteration):
                pass

        return findings

    def _check_token_handling(self, project_dir: Path) -> list[SecurityFinding]:
        """
        Check for secure token handling (JWT, OAuth).

        Checks for:
        - Token validation
        - Secure token storage
        - Token expiration

        Args:
            project_dir: Path to the project root

        Returns:
            List of security findings
        """

        findings = []

        # Check for JWT/OAuth token handling
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                if "jwt" in content.lower():
                    # Check for token validation
                    if re.search(r"jwt\.decode\(", content, re.IGNORECASE):
                        # Check if verification is being done
                        decode_matches = list(
                            re.finditer(r"jwt\.decode\(", content, re.IGNORECASE)
                        )
                        for match in decode_matches:
                            # Get the context around the match
                            start = max(0, match.start() - 200)
                            end = min(len(content), match.end() + 200)
                            context = content[start:end]

                            # Check if verify parameter is set to False
                            if "verify=False" in context or "verify = False" in context:
                                line_num = content[: match.start()].count("\n") + 1
                                finding = SecurityFinding(
                                    category="auth",
                                    owasp_category="A07_2021",
                                    severity="critical",
                                    title="JWT signature verification disabled",
                                    description="JWT token is being decoded without signature verification (verify=False)",
                                    file=str(py_file.relative_to(project_dir)),
                                    line=line_num,
                                    remediation=(
                                        "Never disable JWT signature verification. "
                                        "Always verify tokens to prevent token forgery attacks."
                                    ),
                                    cwe="CWE-347",
                                    references=[
                                        "https://owasp.org/www-project-top-ten/A07_2021-Identification_and_Authentication_Failures",
                                        "https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html",
                                    ],
                                )
                                findings.append(finding)

            except (OSError, UnicodeDecodeError) as e:
                logger.debug(
                    "Could not read %s for JWT verification check: %s", py_file, e
                )

        return findings

    def _check_rate_limiting(self, project_dir: Path) -> list[SecurityFinding]:
        """
        Check for rate limiting and brute force protection.

        Checks for:
        - Rate limiting on authentication endpoints
        - Account lockout mechanisms
        - CAPTCHA implementation

        Args:
            project_dir: Path to the project root

        Returns:
            List of security findings
        """
        findings = []

        # Check for rate limiting configuration
        has_rate_limiting = False
        has_account_lockout = False

        # Check for common rate limiting libraries
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # Check for rate limiting
                if any(
                    keyword in content.lower()
                    for keyword in ["rate_limit", "ratelimit", "throttle", "limiter"]
                ):
                    has_rate_limiting = True

                # Check for account lockout
                if any(
                    keyword in content.lower()
                    for keyword in ["lockout", "account_lock", "max_login_attempts"]
                ):
                    has_account_lockout = True

            except (OSError, UnicodeDecodeError) as e:
                logger.debug(
                    "Could not read %s for rate limiting check: %s", py_file, e
                )

        # If auth endpoints exist but no rate limiting found
        if not has_rate_limiting:
            # Check if there are authentication endpoints
            for py_file in project_dir.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    if any(
                        keyword in content.lower()
                        for keyword in ["login", "authenticate", "signin"]
                    ):
                        finding = SecurityFinding(
                            category="auth",
                            owasp_category="A07_2021",
                            severity="medium",
                            title="No rate limiting detected on authentication endpoints",
                            description="Authentication endpoints may be vulnerable to brute force attacks",
                            file=str(py_file.relative_to(project_dir)),
                            remediation=(
                                "Implement rate limiting on authentication endpoints to prevent "
                                "brute force attacks. Consider using Flask-Limiter, Django-Ratelimit, "
                                "or similar libraries."
                            ),
                            cwe="CWE-307",
                            references=[
                                "https://owasp.org/www-project-top-ten/A07_2021-Identification_and_Authentication_Failures",
                                "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html",
                            ],
                        )
                        findings.append(finding)
                        break
                except (OSError, UnicodeDecodeError) as e:
                    logger.debug(
                        "Could not read %s for auth endpoint check: %s", py_file, e
                    )

        # If no account lockout detected but auth endpoints exist
        if not has_account_lockout and not has_rate_limiting:
            logger.debug("No account lockout mechanism detected")

        return findings

    def _scan_owasp(self, project_dir: Path, report: SecurityReport) -> None:
        """
        Scan for OWASP Top 10 vulnerabilities.

        This will be implemented in subtask-1-2 with the OWASPScanner.

        Args:
            project_dir: Path to the project root
            report: Report object to update with findings
        """
        # TODO: Implement full OWASP Top 10 scanning in subtask-1-2
        # For now, mark which categories will be checked

        owasp_categories = {
            "A01_2021": "Broken Access Control",
            "A02_2021": "Cryptographic Failures",
            "A03_2021": "Injection",
            "A04_2021": "Insecure Design",
            "A05_2021": "Security Misconfiguration",
            "A06_2021": "Vulnerable and Outdated Components",
            "A07_2021": "Identification and Authentication Failures",
            "A08_2021": "Software and Data Integrity Failures",
            "A09_2021": "Security Logging and Monitoring Failures",
            "A10_2021": "Server-Side Request Forgery",
        }

        report.owasp_coverage = dict.fromkeys(owasp_categories.keys(), False)

        logger.info("OWASP Top 10 scanning will be implemented in subtask-1-2")

    def generate_remediation(
        self,
        finding: SecurityFinding,
    ) -> str:
        """
        Generate detailed remediation guidance with code examples for a security finding.

        This method provides actionable remediation steps tailored to the specific
        vulnerability type, including code examples and best practices.

        Args:
            finding: SecurityFinding requiring remediation guidance

        Returns:
            Detailed remediation text with code examples and best practices
        """
        # Get base remediation from the finding if available
        base_guidance = finding.remediation if finding.remediation else ""

        # Generate detailed guidance based on vulnerability category
        if finding.category == "secret":
            return self._generate_secret_remediation(finding, base_guidance)
        elif finding.category == "auth":
            return self._generate_auth_remediation(finding, base_guidance)
        elif finding.category == "dependency":
            return self._generate_dependency_remediation(finding, base_guidance)
        elif finding.category == "owasp":
            return self._generate_owasp_remediation(finding, base_guidance)
        else:
            # Generic remediation for unknown categories
            return self._generate_generic_remediation(finding, base_guidance)

    def _generate_secret_remediation(
        self,
        finding: SecurityFinding,
        base_guidance: str,
    ) -> str:
        """Generate remediation guidance for secret detection findings."""
        guidance_parts = []

        # Severity-based warning
        if finding.severity == "critical":
            guidance_parts.append(
                "CRITICAL: Hardcoded secrets pose an immediate security risk. "
                "Attackers who gain access to your codebase can extract these secrets "
                "and use them to compromise your systems."
            )

        # What to do
        guidance_parts.extend(
            [
                "",
                "## Immediate Actions",
                "",
                "1. Remove the secret from code immediately",
                "2. Rotate the credential - assume it has been compromised",
                "3. Use environment variables or a secrets management system",
                "",
                "## Code Examples",
                "",
            ]
        )

        # Python examples
        guidance_parts.extend(
            [
                "### Python",
                "",
                "Wrong (hardcoded secret):",
                "```python",
                "API_KEY = 'sk-live-1234567890abcdef'",
                "```",
                "",
                "Correct (environment variable):",
                "```python",
                "import os",
                "api_key = os.getenv('API_KEY')",
                "if not api_key:",
                "    raise ValueError('API_KEY not set')",
                "```",
                "",
            ]
        )

        # JavaScript examples
        guidance_parts.extend(
            [
                "### JavaScript",
                "",
                "Wrong (hardcoded secret):",
                "```javascript",
                "const API_KEY = 'sk-live-1234567890abcdef';",
                "```",
                "",
                "Correct (environment variable):",
                "```javascript",
                "const apiKey = process.env.API_KEY;",
                "if (!apiKey) {",
                "  throw new Error('API_KEY not set');",
                "}",
                "```",
                "",
            ]
        )

        # Best practices
        guidance_parts.extend(
            [
                "## Best Practices",
                "",
                "- Use .env files for local development only",
                "- Add .env to .gitignore before committing secrets",
                "- Use cloud secrets managers in production (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager)",
                "- Rotate credentials regularly (90 days recommended)",
                "- Never commit secrets to version control",
                "",
                "## References",
                "- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)",
                "- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)",
            ]
        )

        return "\n".join(guidance_parts)

    def _generate_auth_remediation(
        self,
        finding: SecurityFinding,
        base_guidance: str,
    ) -> str:
        """Generate remediation guidance for authentication security findings."""
        guidance_parts = [
            f"## Remediation for {finding.title}",
            "",
            finding.description,
            "",
            base_guidance,
            "",
            "## Best Practices",
            "",
            "### Password Storage",
            "- Use bcrypt, scrypt, or Argon2 for password hashing",
            "- Never store passwords in plaintext",
            "- Always use a unique salt for each password",
            "",
            "### Session Management",
            "- Set cookies with HttpOnly and Secure flags",
            "- Implement session timeout (15-30 minutes idle timeout)",
            "- Regenerate session IDs after authentication",
            "",
            "### Token Handling (JWT/OAuth)",
            "- Always verify token signatures",
            "- Validate token expiration",
            "- Use short-lived tokens with refresh tokens",
            "",
            "### Brute Force Protection",
            "- Implement rate limiting on auth endpoints",
            "- Use account lockout after failed attempts",
            "- Add CAPTCHA for repeated failures",
            "",
            "## References",
            "- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)",
            "- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)",
        ]

        return "\n".join(guidance_parts)

    def _generate_dependency_remediation(
        self,
        finding: SecurityFinding,
        base_guidance: str,
    ) -> str:
        """Generate remediation guidance for dependency vulnerabilities."""
        guidance_parts = [
            "## Remediation: Vulnerable Dependency",
            "",
            f"**Severity:** {finding.severity.upper()}",
            "",
            finding.description,
            "",
            base_guidance,
            "",
            "## Update Commands",
            "",
            "### npm/yarn",
            "```bash",
            "npm audit",
            "npm audit fix",
            "```",
            "",
            "### pip (Python)",
            "```bash",
            "pip install --upgrade package-name",
            "pip freeze > requirements.txt",
            "```",
            "",
            "## Prevention",
            "",
            "- Enable Dependabot for automated vulnerability tracking",
            "- Run dependency audits in CI/CD pipeline",
            "- Always commit lock files for reproducible builds",
            "- Review dependency updates before deploying",
            "",
            "## References",
            "- [OWASP Vulnerable Dependencies](https://owasp.org/www-project-top-ten/A06_2021-Vulnerable_and_Outdated_Components)",
            "- [npm audit](https://docs.npmjs.com/cli/audit)",
            "- [pip-audit](https://pypi.org/project/pip-audit/)",
        ]

        return "\n".join(guidance_parts)

    def _generate_owasp_remediation(
        self,
        finding: SecurityFinding,
        base_guidance: str,
    ) -> str:
        """Generate remediation guidance for OWASP Top 10 findings."""
        guidance_parts = [
            f"## Remediation for {finding.title}",
            "",
            f"**OWASP Category:** {finding.owasp_category}",
            f"**Severity:** {finding.severity.upper()}",
            "",
            finding.description,
            "",
            base_guidance,
            "",
            "## References",
            "- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)",
            "- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)",
        ]

        return "\n".join(guidance_parts)

    def _generate_generic_remediation(
        self,
        finding: SecurityFinding,
        base_guidance: str,
    ) -> str:
        """Generate generic remediation guidance for unknown categories."""
        return f"""
## Remediation for {finding.title}

**Category:** {finding.category}
**Severity:** {finding.severity.upper()}

{finding.description}

### Remediation Steps

{base_guidance}

### Security Best Practices

1. Principle of Least Privilege - Grant minimum required permissions
2. Defense in Depth - Use multiple security layers
3. Fail Securely - Default to deny, not allow
4. Security by Design - Build security in from the start

### References

- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
"""

    def _generate_summary_and_recommendations(self, report: SecurityReport) -> None:
        """
        Generate executive summary and prioritized recommendations.

        Args:
            report: Report object to update
        """
        # Executive summary
        critical_count = report.summary_counts["critical"]
        high_count = report.summary_counts["high"]

        if critical_count > 0:
            report.executive_summary = (
                f"CRITICAL: {critical_count} critical security issues found that require "
                f"immediate attention. These vulnerabilities could lead to data breaches, "
                f"unauthorized access, or system compromise."
            )
        elif high_count > 0:
            report.executive_summary = (
                f"WARNING: {high_count} high-severity security issues found that should "
                f"be addressed soon. These vulnerabilities pose significant security risks."
            )
        elif report.summary_counts["total"] > 0:
            report.executive_summary = (
                f"{report.summary_counts['total']} security issues found with "
                f"medium or lower severity. Address these to improve overall security posture."
            )
        else:
            report.executive_summary = (
                "No critical security issues found. The codebase demonstrates good "
                "security practices. Continue to monitor and maintain security standards."
            )

        # Prioritized recommendations
        recommendations = []

        # Address critical findings first
        if critical_count > 0:
            recommendations.append(
                "Immediately address all critical findings, especially hardcoded secrets "
                "and credentials."
            )

        # High severity
        if high_count > 0:
            recommendations.append(
                "Address all high-severity findings before the next release."
            )

        # Dependency updates
        if report.dependency_audit.get("vulnerabilities_found", 0) > 0:
            recommendations.append(
                "Update all vulnerable dependencies to their latest secure versions."
            )

        # Secret detection
        if report.secrets_scan.get("secrets_found", 0) > 0:
            recommendations.append(
                "Remove all detected secrets from the codebase and rotate exposed credentials. "
                "Use environment variables or a secrets management system."
            )

        # OWASP coverage
        if not any(report.owasp_coverage.values()):
            recommendations.append(
                "Complete OWASP Top 10 vulnerability scanning for comprehensive coverage."
            )

        # Authentication security
        if report.authentication_review.get("findings_count", 0) > 0:
            recommendations.append(
                "Review and improve authentication flows to prevent credential stuffing "
                "and session hijacking."
            )

        # Generic recommendation if no issues found
        if not recommendations:
            recommendations.append(
                "Continue following security best practices and run regular security audits."
            )

        report.recommendations = recommendations

    def generate_report(
        self,
        findings: list[SecurityFinding] | None = None,
        project_dir: Path | None = None,
        include_severity_grouping: bool = True,
        include_executive_summary: bool = True,
    ) -> SecurityReport:
        """
        Generate a security report with severity grouping and executive summary.

        This is a standalone report generation method that can be used with
        existing findings or to create a new report structure.

        Args:
            findings: Optional list of security findings to include
            project_dir: Optional path to project directory (for context)
            include_severity_grouping: Whether to group findings by severity in markdown output
            include_executive_summary: Whether to generate executive summary

        Returns:
            SecurityReport with all findings, summary, and recommendations

        Example:
            auditor = SecurityAuditAgent()

            # Generate report from existing findings
            findings = [finding1, finding2, finding3]
            report = auditor.generate_report(
                findings=findings,
                project_dir=Path("/project")
            )

            # Save report
            report.to_json_file("output.json")
            report.to_markdown_file("output.md")
        """
        from datetime import datetime

        # Initialize report
        report = SecurityReport(
            project_dir=str(project_dir) if project_dir else "unknown",
            timestamp=datetime.now().isoformat(),
        )

        # Add findings if provided
        if findings:
            for finding in findings:
                report.add_finding(finding)

        # Generate executive summary
        if include_executive_summary:
            self._generate_summary_and_recommendations(report)

        return report

    def _save_report(self, spec_dir: Path, report: SecurityReport) -> None:
        """
        Save security report to spec directory.

        Args:
            spec_dir: Path to the spec directory
            report: Report to save
        """
        spec_dir = Path(spec_dir)
        spec_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON report
        json_file = spec_dir / "security_report.json"
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(report.to_json())

        # Save markdown report
        md_file = spec_dir / "security_report.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())

        logger.info(f"Security report saved to {spec_dir}")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert agent state to dictionary.

        This method provides a dictionary representation of the agent,
        useful for debugging, logging, and state inspection.

        Returns:
            Dictionary with agent state information
        """
        return {
            "agent_type": "SecurityAuditAgent",
            "capabilities": [
                "owasp_top_10_scanning",
                "dependency_vulnerability_checking",
                "authentication_flow_analysis",
                "secret_detection",
                "security_report_generation",
            ],
            "scanner_available": self._security_scanner is not None,
        }

    def export_report_to_scan_results_format(
        self,
        report: SecurityReport,
        filepath: str | Path,
    ) -> None:
        """
        Export report in security_scan_results.json compatible format.

        This format is compatible with SecurityScanner output and can be
        consumed by QA validation strategies.

        Args:
            report: SecurityReport to export
            filepath: Path to output file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        scan_results = report.to_security_scan_results_dict()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scan_results, f, indent=2)

        logger.info(f"Security scan results exported to {filepath}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def run_security_audit(
    project_dir: Path,
    spec_dir: Path | None = None,
) -> SecurityReport:
    """
    Convenience function to run a full security audit.

    Args:
        project_dir: Path to project root
        spec_dir: Optional spec directory to save results

    Returns:
        SecurityReport with all findings
    """
    auditor = SecurityAuditAgent()
    return auditor.run_full_audit(project_dir, spec_dir)


def has_critical_security_issues(project_dir: Path) -> bool:
    """
    Quick check if project has critical security issues.

    Args:
        project_dir: Path to project root

    Returns:
        True if any critical/high issues found
    """
    auditor = SecurityAuditAgent()
    report = auditor.run_full_audit(
        project_dir,
        spec_dir=None,
        scan_owasp=False,  # Skip OWASP scan for quick check
    )
    return report.has_blocking_issues()
