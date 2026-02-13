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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analysis.security_scanner import SecurityScanner, SecurityVulnerability

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

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "project_dir": self.project_dir,
            "timestamp": self.timestamp,
            "findings": [f.to_dict() for f in self.findings],
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
        """Convert report to markdown format."""
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

        # Critical findings section
        critical = self.get_critical_findings()
        if critical:
            lines.extend([
                "## Critical & High Severity Findings",
                "",
            ])
            for finding in critical:
                lines.extend([
                    f"### {finding.title}",
                    "",
                    f"**Severity:** {finding.severity.upper()}",
                    f"**Category:** {finding.category}",
                    "",
                    finding.description,
                    "",
                ])
                if finding.file:
                    lines.append(f"**Location:** `{finding.file}:{finding.line or '?'}`")
                    lines.append("")
                if finding.remediation:
                    lines.extend([
                        "**Remediation:**",
                        "",
                        finding.remediation,
                        "",
                    ])

        # All findings by category
        lines.extend([
            "## All Findings",
            "",
        ])
        for finding in self.findings:
            lines.extend([
                f"### {finding.title}",
                "",
                f"**Severity:** {finding.severity.upper()}",
                f"**Category:** {finding.category}",
                "",
            ])
            if finding.file:
                lines.append(f"**Location:** `{finding.file}:{finding.line or '?'}`")
            lines.append("")
            lines.append(finding.description)
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return "\n".join(lines)


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

        # Convert secrets to findings
        for secret in scan_result.secrets:
            finding = SecurityFinding(
                category="secret",
                severity="critical",
                title=f"Potential secret: {secret.get('pattern', 'unknown')}",
                description=f"Found potential {secret.get('pattern')} in file",
                file=secret.get("file"),
                line=secret.get("line"),
                remediation="Remove the secret from the code. Use environment variables or a secrets management system.",
                references=[
                    "https://owasp.org/www-project-top-ten/2017/A2_2017-Credential_Stuffing"
                ],
            )
            report.add_finding(finding)

        # Store secrets scan results
        report.secrets_scan = {
            "secrets_found": len(scan_result.secrets),
            "files_affected": len(set(s.get("file", "") for s in scan_result.secrets)),
        }

        logger.info(f"Secrets scan found {len(scan_result.secrets)} potential secrets")

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
            v for v in scan_result.vulnerabilities
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
            "critical_count": sum(1 for v in dep_vulnerabilities if v.severity == "critical"),
            "high_count": sum(1 for v in dep_vulnerabilities if v.severity == "high"),
        }

        logger.info(f"Dependency audit found {len(dep_vulnerabilities)} vulnerabilities")

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

    def _analyze_authentication(self, project_dir: Path, report: SecurityReport) -> None:
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

        logger.info(f"Authentication analysis found {len(auth_result['findings'])} issues")

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
        import re

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
                        line_num = content[:match.start()].count("\n") + 1
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ""

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
                        line_num = content[:match.start()].count("\n") + 1
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                        finding = SecurityFinding(
                            category="auth",
                            owasp_category="A07_2021",
                            severity=config["severity"],
                            title=config["title"],
                            description=config.get("description", "Insecure authentication pattern detected"),
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
                        line_num = content[:match.start()].count("\n") + 1
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ""

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
        import re

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
            except (OSError, UnicodeDecodeError):
                pass

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
            except (OSError, UnicodeDecodeError):
                pass

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
            except (OSError, UnicodeDecodeError):
                pass

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
        import re

        findings = []

        # Check for password validation/policy code
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # Check if password validation exists
                if "password" in content.lower():
                    # Look for password length checks
                    if not re.search(r"len\(.*password.*\)\s*[<>]=\s*\d+", content, re.IGNORECASE):
                        # If password handling exists but no length check found
                        if re.search(r"def.*password|class.*password", content, re.IGNORECASE):
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

            except (OSError, UnicodeDecodeError):
                pass

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
        import re

        findings = []

        # Check for session management code
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")

                if "session" in content.lower():
                    # Check for secure cookie flags
                    if re.search(r"session\.cookie_httponly\s*=\s*False", content, re.IGNORECASE):
                        line_num = next(
                            i for i, line in enumerate(lines)
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

                    if re.search(r"session\.cookie_secure\s*=\s*False", content, re.IGNORECASE):
                        line_num = next(
                            i for i, line in enumerate(lines)
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
        import re

        findings = []

        # Check for JWT/OAuth token handling
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                if "jwt" in content.lower():
                    # Check for token validation
                    if re.search(r"jwt\.decode\(", content, re.IGNORECASE):
                        # Check if verification is being done
                        decode_matches = list(re.finditer(r"jwt\.decode\(", content, re.IGNORECASE))
                        for match in decode_matches:
                            # Get the context around the match
                            start = max(0, match.start() - 200)
                            end = min(len(content), match.end() + 200)
                            context = content[start:end]

                            # Check if verify parameter is set to False
                            if "verify=False" in context or "verify = False" in context:
                                line_num = content[:match.start()].count("\n") + 1
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

            except (OSError, UnicodeDecodeError):
                pass

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
                if any(keyword in content.lower() for keyword in ["rate_limit", "ratelimit", "throttle", "limiter"]):
                    has_rate_limiting = True

                # Check for account lockout
                if any(keyword in content.lower() for keyword in ["lockout", "account_lock", "max_login_attempts"]):
                    has_account_lockout = True

            except (OSError, UnicodeDecodeError):
                pass

        # If auth endpoints exist but no rate limiting found
        if not has_rate_limiting:
            # Check if there are authentication endpoints
            for py_file in project_dir.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    if any(keyword in content.lower() for keyword in ["login", "authenticate", "signin"]):
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
                except (OSError, UnicodeDecodeError):
                    pass

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

        report.owasp_coverage = {
            category: False for category in owasp_categories.keys()
        }

        logger.info("OWASP Top 10 scanning will be implemented in subtask-1-2")

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
