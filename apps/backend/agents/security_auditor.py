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
        # This will be implemented in subtask-1-4
        # For now, we'll do basic pattern scanning

        auth_findings = self._scan_auth_patterns(project_dir)

        for finding in auth_findings:
            report.add_finding(finding)

        report.authentication_review = {
            "findings_count": len(auth_findings),
            "patterns_checked": [
                "hardcoded_credentials",
                "insecure_password_storage",
                "missing_auth_checks",
            ],
        }

        logger.info(f"Authentication analysis found {len(auth_findings)} issues")

    def _scan_auth_patterns(self, project_dir: Path) -> list[SecurityFinding]:
        """
        Scan for authentication security issues.

        Args:
            project_dir: Path to the project root

        Returns:
            List of security findings related to authentication
        """
        findings = []

        # TODO: Implement full authentication flow analysis in subtask-1-4
        # This is a placeholder for basic pattern scanning

        # Scan for hardcoded credentials
        import re

        credential_patterns = {
            r"password\s*=\s*['\"][^'\"]+['\"]": "Hardcoded password detected",
            r"api_key\s*=\s*['\"][^'\"]+['\"]": "Hardcoded API key detected",
            r"secret\s*=\s*['\"][^'\"]+['\"]": "Hardcoded secret detected",
        }

        # Scan Python files
        for py_file in project_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                for pattern, message in credential_patterns.items():
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        line_num = content[:match.start()].count("\n") + 1
                        finding = SecurityFinding(
                            category="auth",
                            owasp_category="A07_2021",
                            severity="high",
                            title=message,
                            description=f"Potential hardcoded credential found in {py_file.name}",
                            file=str(py_file.relative_to(project_dir)),
                            line=line_num,
                            remediation="Remove hardcoded credentials. Use environment variables or a secrets manager.",
                            cwe="CWE-798",
                            references=[
                                "https://owasp.org/www-project-top-ten/A07_2021-Identification_and_Authentication_Failures"
                            ],
                        )
                        findings.append(finding)
            except Exception:
                pass  # Skip files that can't be read

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
