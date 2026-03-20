"""
Dependency Notification Module
==============================

Sends notifications for dependency vulnerability alerts.

This module integrates with the GitHub CLI to:
- Create GitHub issues for critical CVEs
- Post notifications with vulnerability details
- Track notified vulnerabilities to avoid duplicates

Usage:
    from runners.dependency_notifications import DependencyNotifier

    notifier = DependencyNotifier(project_dir=Path("/path/to/project"))
    await notifier.notify_critical_vulnerabilities(scan_result)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .github.gh_client import GHClient, GHCommandError
except ImportError:
    from runners.github.gh_client import GHClient, GHCommandError

from analysis.dependency_scanner import DependencyScanResult, DependencyUpdate

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class NotificationRecord:
    """
    Record of a sent notification.

    Attributes:
        package_name: Name of the vulnerable package
        cve_ids: List of CVE IDs notified about
        severity: Severity level
        notified_at: When the notification was sent
        issue_number: GitHub issue number (if created)
        notification_type: Type of notification (issue, comment, etc.)
    """

    package_name: str
    cve_ids: list[str]
    severity: str
    notified_at: str
    issue_number: int | None = None
    notification_type: str = "issue"  # issue, comment, summary

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "package_name": self.package_name,
            "cve_ids": self.cve_ids,
            "severity": self.severity,
            "notified_at": self.notified_at,
            "issue_number": self.issue_number,
            "notification_type": self.notification_type,
        }


@dataclass
class NotificationResult:
    """
    Result of a notification operation.

    Attributes:
        success: Whether the notification was sent successfully
        notifications_sent: List of notification records
        errors: List of errors that occurred
        summary_counts: Count of notifications by severity
    """

    success: bool = False
    notifications_sent: list[NotificationRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    summary_counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate summary counts after initialization."""
        if not self.summary_counts:
            self._calculate_summary_counts()

    def _calculate_summary_counts(self) -> None:
        """Calculate notification counts by severity."""
        self.summary_counts = {
            "critical": sum(
                1
                for n in self.notifications_sent
                if n.severity == "critical"
            ),
            "high": sum(1 for n in self.notifications_sent if n.severity == "high"),
            "medium": sum(
                1 for n in self.notifications_sent if n.severity == "medium"
            ),
            "low": sum(1 for n in self.notifications_sent if n.severity == "low"),
            "total": len(self.notifications_sent),
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "notifications_sent": [n.to_dict() for n in self.notifications_sent],
            "errors": self.errors,
            "summary_counts": self.summary_counts,
        }


# =============================================================================
# NOTIFICATION MANAGER
# =============================================================================


class DependencyNotifier:
    """
    Manages notifications for dependency vulnerability alerts.

    This class handles sending notifications about security vulnerabilities
    in dependencies, including creating GitHub issues for critical CVEs.

    Example:
        notifier = DependencyNotifier(project_dir=Path("/path/to/project"))

        # Notify about critical vulnerabilities
        result = await notifier.notify_critical_vulnerabilities(scan_result)

        if result.success:
            print(f"Sent {result.summary_counts['total']} notifications")
    """

    def __init__(
        self,
        project_dir: Path,
        state_file: str | Path = ".dependency-notifications.json",
        repo: str | None = None,
    ):
        """
        Initialize the dependency notifier.

        Args:
            project_dir: Path to the project directory
            state_file: Path to state file for tracking sent notifications
            repo: Repository in 'owner/repo' format for GitHub operations
        """
        self.project_dir = Path(project_dir)
        self.state_file = Path(state_file)
        self.repo = repo

        # Initialize GitHub client
        self._gh_client: GHClient | None = None

        # Load notification history
        self._notification_history: dict[str, NotificationRecord] = {}
        self._load_notification_history()

    @property
    def gh_client(self) -> GHClient:
        """Get or create the GitHub client instance."""
        if self._gh_client is None:
            self._gh_client = GHClient(
                project_dir=self.project_dir,
                repo=self.repo,
                enable_rate_limiting=True,
            )
        return self._gh_client

    def _load_notification_history(self) -> None:
        """Load notification history from state file."""
        if not self.state_file.exists():
            logger.debug("No notification history file found")
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for package_name, record_data in data.items():
                self._notification_history[package_name] = NotificationRecord(
                    package_name=record_data["package_name"],
                    cve_ids=record_data["cve_ids"],
                    severity=record_data["severity"],
                    notified_at=record_data["notified_at"],
                    issue_number=record_data.get("issue_number"),
                    notification_type=record_data.get("notification_type", "issue"),
                )

            logger.info(
                f"Loaded {len(self._notification_history)} notification records"
            )

        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Failed to load notification history: {e}")
            self._notification_history = {}

    def _save_notification_history(self) -> None:
        """Save notification history to state file."""
        try:
            data = {
                pkg: record.to_dict()
                for pkg, record in self._notification_history.items()
            }

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._notification_history)} notification records")

        except OSError as e:
            logger.error(f"Failed to save notification history: {e}")

    def _was_already_notified(
        self, package_name: str, cve_ids: list[str]
    ) -> bool:
        """
        Check if a vulnerability was already notified.

        Args:
            package_name: Package name to check
            cve_ids: List of CVE IDs to check

        Returns:
            True if this vulnerability was already notified
        """
        if package_name not in self._notification_history:
            return False

        previous_record = self._notification_history[package_name]

        # Check if any of the current CVEs were already notified
        for cve in cve_ids:
            if cve in previous_record.cve_ids:
                return True

        return False

    async def notify_critical_vulnerabilities(
        self,
        scan_result: DependencyScanResult,
        min_severity: str = "high",
        create_issues: bool = True,
    ) -> NotificationResult:
        """
        Send notifications for critical vulnerabilities.

        This method creates GitHub issues for vulnerabilities that meet
        the severity threshold and haven't been previously notified.

        Args:
            scan_result: Result from dependency scan
            min_severity: Minimum severity level to notify (critical, high, medium, low)
            create_issues: Whether to create GitHub issues

        Returns:
            NotificationResult with details of sent notifications
        """
        result = NotificationResult(success=True)

        # Filter security updates by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        min_severity_level = severity_order.get(min_severity.lower(), 1)

        vulnerabilities_to_notify = [
            vuln
            for vuln in scan_result.security_updates
            if vuln.severity
            and severity_order.get(vuln.severity.lower(), 999) <= min_severity_level
            and vuln.cve_ids  # Only notify if we have CVE IDs
        ]

        if not vulnerabilities_to_notify:
            logger.info(f"No vulnerabilities matching severity >= {min_severity}")
            return result

        logger.info(
            f"Found {len(vulnerabilities_to_notify)} vulnerabilities "
            f"with severity >= {min_severity}"
        )

        # Create issues for each vulnerability
        for vuln in vulnerabilities_to_notify:
            # Skip if already notified
            if self._was_already_notified(vuln.name, vuln.cve_ids):
                logger.debug(f"Skipping {vuln.name} - already notified")
                continue

            try:
                if create_issues:
                    # Create GitHub issue
                    issue_number = await self._create_vulnerability_issue(vuln)

                    # Record notification
                    record = NotificationRecord(
                        package_name=vuln.name,
                        cve_ids=vuln.cve_ids,
                        severity=vuln.severity or "unknown",
                        notified_at=datetime.now(UTC).isoformat(),
                        issue_number=issue_number,
                        notification_type="issue",
                    )

                    result.notifications_sent.append(record)

                    # Update history
                    self._notification_history[vuln.name] = record

                    logger.info(
                        f"Created issue #{issue_number} for {vuln.name} "
                        f"(CVEs: {', '.join(vuln.cve_ids)})"
                    )

                else:
                    # Just record without creating issue (dry run)
                    record = NotificationRecord(
                        package_name=vuln.name,
                        cve_ids=vuln.cve_ids,
                        severity=vuln.severity or "unknown",
                        notified_at=datetime.now(UTC).isoformat(),
                        issue_number=None,
                        notification_type="dry_run",
                    )

                    result.notifications_sent.append(record)
                    logger.info(
                        f"[DRY RUN] Would notify about {vuln.name} "
                        f"(CVEs: {', '.join(vuln.cve_ids)})"
                    )

            except (GHCommandError, Exception) as e:
                error_msg = f"Failed to notify about {vuln.name}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                result.success = False

        # Save notification history
        if result.notifications_sent:
            self._save_notification_history()

        return result

    async def _create_vulnerability_issue(
        self, vuln: DependencyUpdate
    ) -> int:
        """
        Create a GitHub issue for a vulnerability.

        Args:
            vuln: DependencyUpdate with vulnerability details

        Returns:
            Created issue number

        Raises:
            GHCommandError: If issue creation fails
        """
        # Build issue title
        cve_str = ", ".join(vuln.cve_ids)
        title = f"Security: {vuln.name} vulnerability ({cve_str})"

        # Build issue body
        body = self._generate_issue_body(vuln)

        # Create issue using gh CLI
        # Note: gh issue create returns JSON with the issue number
        args = [
            "issue",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--label",
            "security,vulnerability,dependencies",
        ]

        result = await self.gh_client.run(args)

        # Parse issue number from output
        # gh outputs: "https://github.com/owner/repo/issues/123"
        output = result.stdout.strip()
        try:
            issue_number = int(output.split("/")[-1])
            return issue_number
        except (ValueError, IndexError):
            # If parsing fails, return 0 (error indicator)
            logger.warning(f"Could not parse issue number from gh output: {output}")
            return 0

    def _generate_issue_body(self, vuln: DependencyUpdate) -> str:
        """
        Generate GitHub issue body for a vulnerability.

        Args:
            vuln: DependencyUpdate with vulnerability details

        Returns:
            Formatted issue body in markdown
        """
        lines = [
            f"## 🔒 Security Vulnerability in `{vuln.name}`",
            "",
            f"**Severity**: {vuln.severity.upper() if vuln.severity else 'UNKNOWN'}",
            f"**Current Version**: `{vuln.current_version}`",
            f"**Fixed Version**: `{vuln.latest_version}`",
            f"**Ecosystem**: {vuln.ecosystem}",
            "",
            "### CVE IDs",
            "",
        ]

        # Add CVE IDs with links
        for cve_id in vuln.cve_ids:
            lines.append(f"- [{cve_id}](https://nvd.nist.gov/vuln/detail/{cve_id})")

        lines.extend([
            "",
            "### Description",
            "",
            f"This package has a **{vuln.severity.upper() if vuln.severity else 'UNKNOWN'}** severity "
            "vulnerability that should be addressed promptly.",
            "",
            "### Remediation",
            "",
            f"Update `{vuln.name}` to version `{vuln.latest_version}` or later.",
            "",
        ])

        # Add ecosystem-specific update commands
        if vuln.ecosystem == "python":
            lines.extend([
                "```bash",
                f"pip install --upgrade {vuln.name}",
                "```",
                "",
            ])
        elif vuln.ecosystem == "npm":
            lines.extend([
                "```bash",
                f"npm update {vuln.name}",
                "# or",
                "npm audit fix",
                "```",
                "",
            ])

        lines.extend([
            "### References",
            "",
            "- [NVD National Vulnerability Database](https://nvd.nist.gov/)",
            "- [GitHub Advisory Database](https://github.com/advisories)",
            "",
            "---",
            "",
            f"*This issue was automatically created by the dependency update system on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}.*",
        ])

        if vuln.changelog_url:
            lines.insert(
                len(lines) - 3,  # Before the separator line
                f"- [Changelog/Release Notes]({vuln.changelog_url})"
            )

        return "\n".join(lines)

    async def create_summary_issue(
        self,
        scan_result: DependencyScanResult,
        batches: list[Any] | None = None,
    ) -> int | None:
        """
        Create a summary issue with all available updates.

        Args:
            scan_result: Result from dependency scan
            batches: Optional list of update batches

        Returns:
            Created issue number, or None if creation failed
        """
        if not scan_result.has_updates:
            logger.info("No updates available, skipping summary issue")
            return None

        try:
            # Build issue title
            title = (
                f"Dependency Updates Available ({len(scan_result.updates_available)} packages)"
            )

            # Build issue body
            body = self._generate_summary_body(scan_result, batches)

            # Create issue
            args = [
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--label",
                "dependencies,maintenance",
            ]

            result = await self.gh_client.run(args)

            # Parse issue number
            output = result.stdout.strip()
            try:
                issue_number = int(output.split("/")[-1])
                logger.info(f"Created summary issue #{issue_number}")
                return issue_number
            except (ValueError, IndexError):
                logger.warning(f"Could not parse issue number from: {output}")
                return None

        except (GHCommandError, Exception) as e:
            logger.error(f"Failed to create summary issue: {e}")
            return None

    def _generate_summary_body(
        self,
        scan_result: DependencyScanResult,
        batches: list[Any] | None = None,
    ) -> str:
        """
        Generate summary issue body for all available updates.

        Args:
            scan_result: Result from dependency scan
            batches: Optional list of update batches

        Returns:
            Formatted issue body in markdown
        """
        lines = [
            "## 📦 Dependency Updates Summary",
            "",
            f"**Total Updates Available**: {len(scan_result.updates_available)}",
            f"**Security Updates**: {len(scan_result.security_updates)}",
            "",
        ]

        # Security updates section
        if scan_result.security_updates:
            lines.extend([
                "### 🔒 Security Updates (Priority)",
                "",
                "The following packages have security vulnerabilities:",
                "",
            ])

            for vuln in scan_result.security_updates:
                cve_str = ", ".join(vuln.cve_ids) if vuln.cve_ids else "None"
                lines.append(
                    f"- **{vuln.name}** `{vuln.current_version}` → `{vuln.latest_version}` "
                    f"({vuln.severity or 'UNKNOWN'}) - CVEs: {cve_str}"
                )

            lines.append("")

        # Non-security updates section
        non_security = [
            u
            for u in scan_result.updates_available
            if not u.is_security
        ]

        if non_security:
            lines.extend([
                "### 🔄 Non-Security Updates",
                "",
                "The following packages have updates available:",
                "",
            ])

            # Group by update type
            for update_type in ["major", "minor", "patch"]:
                updates = [u for u in non_security if u.update_type == update_type]
                if updates:
                    lines.append(f"#### {update_type.capitalize()} Updates")
                    lines.append("")
                    for update in updates[:10]:  # Limit to 10 per type
                        lines.append(
                            f"- **{update.name}** `{update.current_version}` → "
                            f"`{update.latest_version}`"
                        )
                    if len(updates) > 10:
                        lines.append(f"- ... and {len(updates) - 10} more {update_type} updates")
                    lines.append("")

        # Update batches section
        if batches:
            lines.extend([
                "### 📋 Update Batches",
                "",
                "Updates are organized into the following batches to minimize conflicts:",
                "",
            ])
            for i, batch in enumerate(batches, 1):
                lines.append(
                    f"**Batch {i}**: {batch.batch_id} ({batch.risk_level} risk) - "
                    f"{len(batch.packages)} packages"
                )

            lines.append("")

        # Next steps section
        lines.extend([
            "### 🚀 Next Steps",
            "",
            "1. Review and test security updates first",
            "2. Apply updates in batch order to minimize conflicts",
            "3. Run full test suite after each batch",
            "4. Monitor for any breaking changes",
            "",
            "---",
            "",
            f"*This issue was automatically generated on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}.*",
        ])

        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def notify_vulnerabilities(
    scan_result: DependencyScanResult,
    project_dir: Path,
    min_severity: str = "high",
    repo: str | None = None,
) -> NotificationResult:
    """
    Convenience function to send vulnerability notifications.

    Args:
        scan_result: Result from dependency scan
        project_dir: Path to the project directory
        min_severity: Minimum severity to notify (critical, high, medium, low)
        repo: Repository in 'owner/repo' format

    Returns:
        NotificationResult with details of sent notifications
    """
    notifier = DependencyNotifier(project_dir=project_dir, repo=repo)
    return await notifier.notify_critical_vulnerabilities(
        scan_result,
        min_severity=min_severity,
        create_issues=True,
    )
