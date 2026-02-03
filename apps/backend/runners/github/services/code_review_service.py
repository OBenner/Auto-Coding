"""
Code Review Service
===================

Integrates security scanner with PR code review workflow.
Converts security vulnerabilities to PR review findings and provides
a unified interface for code review operations.

Usage:
    from runners.github.services.code_review_service import CodeReviewService

    service = CodeReviewService(project_dir, github_dir, config)
    findings = await service.review_code_changes(context)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from ...analysis.security_scanner import SecurityScanner, SecurityVulnerability
    from ..context_gatherer import PRContext
    from ..gh_client import GHClient
    from ..models import (
        GitHubRunnerConfig,
        PRReviewFinding,
        ReviewCategory,
        ReviewSeverity,
    )
    from .io_utils import safe_print
except (ImportError, ValueError, SystemError):
    from analysis.security_scanner import SecurityScanner, SecurityVulnerability
    from context_gatherer import PRContext
    from gh_client import GHClient
    from models import (
        GitHubRunnerConfig,
        PRReviewFinding,
        ReviewCategory,
        ReviewSeverity,
    )
    from services.io_utils import safe_print


# Define a local ProgressCallback to avoid circular import
@dataclass
class ProgressCallback:
    """Callback for progress updates - local definition to avoid circular import."""

    phase: str
    progress: int
    message: str
    pr_number: int | None = None
    extra: dict[str, Any] | None = None


class CodeReviewService:
    """
    Service for running code reviews using security scanner.

    Integrates with the security scanner to detect vulnerabilities
    and converts them to PR review findings.
    """

    def __init__(
        self,
        project_dir: Path,
        github_dir: Path,
        config: GitHubRunnerConfig,
        progress_callback=None,
    ):
        """
        Initialize code review service.

        Args:
            project_dir: Project root directory
            github_dir: GitHub automation directory
            config: GitHub runner configuration
            progress_callback: Optional callback for progress updates
        """
        self.project_dir = Path(project_dir)
        self.github_dir = Path(github_dir)
        self.config = config
        self.progress_callback = progress_callback
        self.scanner = SecurityScanner()

    def _report_progress(self, phase: str, progress: int, message: str, **kwargs):
        """Report progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(
                ProgressCallback(
                    phase=phase, progress=progress, message=message, **kwargs
                )
            )

    def _generate_finding_id(self, file: str, line: int, title: str) -> str:
        """Generate unique finding ID from file, line, and title."""
        key = f"{file}:{line}:{title}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def _map_severity(self, scanner_severity: str) -> ReviewSeverity:
        """
        Map security scanner severity to PR review severity.

        Args:
            scanner_severity: Severity from security scanner (critical, high, medium, low, info)

        Returns:
            ReviewSeverity enum value
        """
        severity_map = {
            "critical": ReviewSeverity.CRITICAL,
            "high": ReviewSeverity.HIGH,
            "medium": ReviewSeverity.MEDIUM,
            "low": ReviewSeverity.LOW,
            "info": ReviewSeverity.LOW,
        }
        return severity_map.get(scanner_severity.lower(), ReviewSeverity.MEDIUM)

    def _map_category(self, scanner_source: str) -> ReviewCategory:
        """
        Map security scanner source to PR review category.

        Args:
            scanner_source: Source scanner (secrets, bandit, npm_audit, etc.)

        Returns:
            ReviewCategory enum value
        """
        category_map = {
            "secrets": ReviewCategory.SECURITY,
            "bandit": ReviewCategory.SECURITY,
            "npm_audit": ReviewCategory.SECURITY,
            "semgrep": ReviewCategory.SECURITY,
            "dependency_check": ReviewCategory.SECURITY,
        }
        return category_map.get(scanner_source.lower(), ReviewCategory.SECURITY)

    def _convert_vulnerability_to_finding(
        self, vuln: SecurityVulnerability
    ) -> PRReviewFinding:
        """
        Convert security vulnerability to PR review finding.

        Args:
            vuln: Security vulnerability from scanner

        Returns:
            PRReviewFinding object
        """
        file_path = vuln.file if vuln.file else "project-wide"
        line_num = vuln.line if vuln.line else 1

        finding_id = self._generate_finding_id(file_path, line_num, vuln.title)

        # Build description with CWE reference if available
        description = vuln.description
        if vuln.cwe:
            description += f"\n\n**CWE Reference**: {vuln.cwe}"

        return PRReviewFinding(
            id=finding_id,
            severity=self._map_severity(vuln.severity),
            category=self._map_category(vuln.source),
            title=vuln.title,
            description=description,
            file=file_path,
            line=line_num,
            end_line=None,
            suggested_fix=None,  # Security scanner doesn't provide fixes
            fixable=False,  # Manual review required for security issues
            evidence=f"Detected by {vuln.source} scanner",
            confidence=0.8,  # Security scanners are generally reliable
            source_agents=["security_scanner"],
        )

    def _convert_secret_to_finding(self, secret: dict) -> PRReviewFinding:
        """
        Convert detected secret to PR review finding.

        Args:
            secret: Secret detection result

        Returns:
            PRReviewFinding object
        """
        file_path = secret.get("file", "unknown")
        line_num = secret.get("line", 1)
        pattern = secret.get("pattern", "unknown")

        finding_id = self._generate_finding_id(
            file_path, line_num, f"Secret detected: {pattern}"
        )

        return PRReviewFinding(
            id=finding_id,
            severity=ReviewSeverity.CRITICAL,  # Secrets are always critical
            category=ReviewCategory.SECURITY,
            title=f"Detected secret: {pattern}",
            description=(
                f"A potential secret or credential was detected in this file.\n\n"
                f"**Pattern**: {pattern}\n"
                f"**Matched Text**: {secret.get('matched_text', '[REDACTED]')}\n\n"
                "**Action Required**: Remove this secret immediately and rotate the credential."
            ),
            file=file_path,
            line=line_num,
            end_line=None,
            suggested_fix="Remove the secret and use environment variables or a secrets manager",
            fixable=False,  # Requires manual intervention
            evidence=f"Matched pattern: {pattern}",
            confidence=0.9,  # High confidence for pattern-based detection
            source_agents=["secrets_scanner"],
        )

    async def review_code_changes(
        self,
        context: PRContext,
        changed_files: list[str] | None = None,
    ) -> list[PRReviewFinding]:
        """
        Run code review on changed files using security scanner.

        Args:
            context: PR context with changed files and metadata
            changed_files: Optional list of specific files to scan (if None, uses all changed files)

        Returns:
            List of PR review findings
        """
        self._report_progress(
            "code_review",
            10,
            "Starting security scan...",
            pr_number=getattr(context, "pr_number", None),
        )

        safe_print("[CodeReview] Running security scanner...", flush=True)

        # Extract file paths from context
        if changed_files is None:
            changed_files = [f.path for f in context.changed_files]

        # Run security scan
        spec_dir = self.github_dir / "pr" / f"pr_{getattr(context, 'pr_number', 0)}"
        scan_result = self.scanner.scan(
            project_dir=self.project_dir,
            spec_dir=spec_dir if spec_dir.exists() else None,
            changed_files=changed_files,
            run_secrets=True,
            run_sast=True,
            run_dependency_audit=False,  # Skip dependency audit for code review
        )

        self._report_progress(
            "code_review",
            50,
            f"Security scan complete: {len(scan_result.vulnerabilities)} issues, {len(scan_result.secrets)} secrets",
            pr_number=getattr(context, "pr_number", None),
        )

        safe_print(
            f"[CodeReview] Found {len(scan_result.vulnerabilities)} vulnerabilities, {len(scan_result.secrets)} secrets",
            flush=True,
        )

        # Convert scan results to PR findings
        findings: list[PRReviewFinding] = []

        # Convert secrets
        for secret in scan_result.secrets:
            finding = self._convert_secret_to_finding(secret)
            findings.append(finding)
            safe_print(
                f"[CodeReview] Secret detected: {finding.file}:{finding.line}",
                flush=True,
            )

        # Convert vulnerabilities
        for vuln in scan_result.vulnerabilities:
            finding = self._convert_vulnerability_to_finding(vuln)
            findings.append(finding)
            safe_print(
                f"[CodeReview] {vuln.severity.upper()} issue: {vuln.title} in {vuln.file or 'project-wide'}",
                flush=True,
            )

        # Report scan errors if any
        if scan_result.scan_errors:
            safe_print(
                f"[CodeReview] Warning: {len(scan_result.scan_errors)} scan errors occurred",
                flush=True,
            )
            for error in scan_result.scan_errors:
                safe_print(f"  - {error}", flush=True)

        self._report_progress(
            "code_review",
            100,
            f"Code review complete: {len(findings)} findings",
            pr_number=getattr(context, "pr_number", None),
            extra={
                "findings_count": len(findings),
                "critical_count": sum(
                    1 for f in findings if f.severity == ReviewSeverity.CRITICAL
                ),
                "high_count": sum(
                    1 for f in findings if f.severity == ReviewSeverity.HIGH
                ),
            },
        )

        safe_print(
            f"[CodeReview] Review complete: {len(findings)} total findings", flush=True
        )

        return findings

    def should_block_merge(self, findings: list[PRReviewFinding]) -> bool:
        """
        Determine if findings should block merge.

        Args:
            findings: List of PR review findings

        Returns:
            True if merge should be blocked (critical issues found)
        """
        critical_count = sum(
            1 for f in findings if f.severity == ReviewSeverity.CRITICAL
        )
        return critical_count > 0

    def get_findings_summary(self, findings: list[PRReviewFinding]) -> dict:
        """
        Get summary statistics for findings.

        Args:
            findings: List of PR review findings

        Returns:
            Dictionary with summary statistics
        """
        severity_counts = {
            "critical": sum(
                1 for f in findings if f.severity == ReviewSeverity.CRITICAL
            ),
            "high": sum(1 for f in findings if f.severity == ReviewSeverity.HIGH),
            "medium": sum(1 for f in findings if f.severity == ReviewSeverity.MEDIUM),
            "low": sum(1 for f in findings if f.severity == ReviewSeverity.LOW),
        }

        category_counts = {}
        for finding in findings:
            cat = finding.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total": len(findings),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "should_block": self.should_block_merge(findings),
        }

    def _format_review_body(self, findings: list[PRReviewFinding]) -> str:
        """
        Format findings into a markdown review body.

        Args:
            findings: List of PR review findings

        Returns:
            Markdown formatted review body
        """
        if not findings:
            return "✅ No security issues found in this PR."

        summary = self.get_findings_summary(findings)

        # Build header with summary
        body_parts = ["## 🔒 Security Review Results\n"]

        # Add severity summary
        severity_counts = summary["by_severity"]
        if severity_counts["critical"] > 0:
            body_parts.append(f"🚨 **Critical**: {severity_counts['critical']}")
        if severity_counts["high"] > 0:
            body_parts.append(f"⚠️ **High**: {severity_counts['high']}")
        if severity_counts["medium"] > 0:
            body_parts.append(f"⚡ **Medium**: {severity_counts['medium']}")
        if severity_counts["low"] > 0:
            body_parts.append(f"ℹ️ **Low**: {severity_counts['low']}")

        body_parts.append(f"\n**Total Issues**: {summary['total']}\n")

        # Add merge recommendation
        if summary["should_block"]:
            body_parts.append(
                "❌ **Recommendation**: Do not merge until critical issues are resolved.\n"
            )
        else:
            body_parts.append(
                "⚠️ **Recommendation**: Review findings before merging.\n"
            )

        # Group findings by severity
        by_severity = {
            ReviewSeverity.CRITICAL: [],
            ReviewSeverity.HIGH: [],
            ReviewSeverity.MEDIUM: [],
            ReviewSeverity.LOW: [],
        }

        for finding in findings:
            by_severity[finding.severity].append(finding)

        # Add findings in severity order
        for severity in [
            ReviewSeverity.CRITICAL,
            ReviewSeverity.HIGH,
            ReviewSeverity.MEDIUM,
            ReviewSeverity.LOW,
        ]:
            severity_findings = by_severity[severity]
            if not severity_findings:
                continue

            severity_icons = {
                ReviewSeverity.CRITICAL: "🚨",
                ReviewSeverity.HIGH: "⚠️",
                ReviewSeverity.MEDIUM: "⚡",
                ReviewSeverity.LOW: "ℹ️",
            }

            body_parts.append(
                f"\n### {severity_icons[severity]} {severity.value.title()} Severity\n"
            )

            for finding in severity_findings:
                body_parts.append(f"#### {finding.title}\n")
                body_parts.append(f"**Location**: `{finding.file}:{finding.line}`\n")
                body_parts.append(f"{finding.description}\n")

                if finding.suggested_fix:
                    body_parts.append(f"**Suggested Fix**: {finding.suggested_fix}\n")

                if finding.evidence:
                    body_parts.append(f"**Evidence**: {finding.evidence}\n")

                body_parts.append("")  # Empty line between findings

        # Add footer
        body_parts.append("\n---")
        body_parts.append("*Automated security review by Auto-Claude*")

        return "\n".join(body_parts)

    async def post_review_to_github(
        self,
        pr_number: int,
        findings: list[PRReviewFinding],
        repo: str | None = None,
    ) -> int:
        """
        Post review findings to GitHub PR via gh_client.

        Args:
            pr_number: PR number to post review to
            findings: List of PR review findings
            repo: Optional repository in 'owner/repo' format

        Returns:
            Review ID (currently 0, as gh CLI doesn't return ID)

        Raises:
            GHCommandError: If posting review fails
        """
        self._report_progress(
            "post_review",
            10,
            f"Posting review to PR #{pr_number}...",
            pr_number=pr_number,
        )

        safe_print(f"[CodeReview] Posting review to PR #{pr_number}...", flush=True)

        # Initialize GH client
        gh_client = GHClient(
            project_dir=self.project_dir,
            repo=repo,
        )

        # Format review body
        review_body = self._format_review_body(findings)

        # Determine review event based on findings
        event = "comment"
        if self.should_block_merge(findings):
            event = "request-changes"
            safe_print(
                f"[CodeReview] Requesting changes due to {sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL)} critical issues",
                flush=True,
            )
        elif not findings:
            event = "approve"
            safe_print("[CodeReview] Approving PR - no issues found", flush=True)
        else:
            safe_print(
                "[CodeReview] Posting comment review with non-critical findings",
                flush=True,
            )

        # Post review using gh_client
        review_id = await gh_client.pr_review(
            pr_number=pr_number,
            body=review_body,
            event=event,
        )

        self._report_progress(
            "post_review",
            100,
            f"Review posted to PR #{pr_number}",
            pr_number=pr_number,
            extra={
                "review_id": review_id,
                "event": event,
                "findings_count": len(findings),
            },
        )

        safe_print(
            f"[CodeReview] Review posted successfully (event: {event})", flush=True
        )

        return review_id
