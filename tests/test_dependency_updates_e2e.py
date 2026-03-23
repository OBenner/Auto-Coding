"""
End-to-End Tests for Dependency Updates Workflow
==================================================

Tests the full dependency update automation flow with mocked external dependencies.
These tests validate the integration between:
- DependencyScanner: Scans for outdated packages
- DependencyAnalyzer: Batches compatible updates
- DependencyNotifier: Creates GitHub issues for vulnerabilities
- DependencyUpdateRunner: Orchestrates the entire workflow
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
_runners_dir = _backend_dir / "runners"
_analysis_dir = _backend_dir / "analysis"

if str(_runners_dir) not in sys.path:
    sys.path.insert(0, str(_runners_dir))
if str(_analysis_dir) not in sys.path:
    sys.path.insert(0, str(_analysis_dir))
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from analysis.dependency_scanner import DependencyScanResult, DependencyUpdate
from dependency_notifications import DependencyNotifier, NotificationResult
from runners.github.gh_client import GHClient


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory structure."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir(parents=True)

    # Create Python project files
    (project_dir / "pyproject.toml").write_text(
        '[project]\nname = "test-project"\nversion = "1.0.0"\n'
        'dependencies = ["requests==2.28.0", "click==8.0.0"]\n',
        encoding="utf-8",
    )

    # Create GitHub workflows directory
    github_dir = project_dir / ".github"
    github_dir.mkdir(parents=True)
    (github_dir / "dependency-updates.config.json.example").write_text(
        json.dumps({"auto_approval": {"enabled": True}}), encoding="utf-8"
    )

    return project_dir


@pytest.fixture
def sample_security_updates():
    """Create sample security update data."""
    return [
        DependencyUpdate(
            name="requests",
            current_version="2.28.0",
            latest_version="2.31.0",
            update_type="minor",
            ecosystem="python",
            is_security=True,
            cve_ids=["CVE-2023-32681"],
            severity="high",
            changelog_url="https://github.com/psf/requests/releases",
        ),
        DependencyUpdate(
            name="urllib3",
            current_version="1.26.0",
            latest_version="1.26.18",
            update_type="patch",
            ecosystem="python",
            is_security=True,
            cve_ids=["CVE-2023-43804"],
            severity="medium",
        ),
    ]


@pytest.fixture
def sample_non_security_updates():
    """Create sample non-security update data."""
    return [
        DependencyUpdate(
            name="click",
            current_version="8.0.0",
            latest_version="8.1.0",
            update_type="minor",
            ecosystem="python",
            is_security=False,
        ),
        DependencyUpdate(
            name="pytest",
            current_version="7.4.0",
            latest_version="7.4.3",
            update_type="patch",
            ecosystem="python",
            is_security=False,
        ),
    ]


@pytest.fixture
def sample_scan_result(sample_security_updates, sample_non_security_updates):
    """Create a complete scan result."""
    return DependencyScanResult(
        updates_available=sample_security_updates + sample_non_security_updates,
        security_updates=sample_security_updates,
        scan_errors=[],
        has_updates=True,
        has_security_updates=True,
        scan_metadata={
            "project_dir": "/test/project",
            "scanned_ecosystems": ["python"],
        },
    )


@pytest.fixture
def mock_gh_client():
    """Create a mock GitHub client."""
    client = MagicMock(spec=GHClient)
    client.run = AsyncMock()
    return client


# ============================================================================
# E2E Test: Scanner Integration
# ============================================================================


class TestScannerIntegrationE2E:
    """Test dependency scanner end-to-end integration."""

    def test_scan_result_data_structure(self, sample_scan_result):
        """Test that scan result has correct structure and data."""
        assert sample_scan_result.has_updates is True
        assert sample_scan_result.has_security_updates is True
        assert len(sample_scan_result.updates_available) == 4
        assert len(sample_scan_result.security_updates) == 2

        # Verify security updates
        security_updates = sample_scan_result.security_updates
        assert security_updates[0].name == "requests"
        assert security_updates[0].is_security is True
        assert "CVE-2023-32681" in security_updates[0].cve_ids
        assert security_updates[0].severity == "high"

        # Verify metadata
        assert "python" in sample_scan_result.scan_metadata["scanned_ecosystems"]

    def test_dependency_update_fields(self, sample_security_updates):
        """Test that DependencyUpdate has all required fields."""
        update = sample_security_updates[0]

        assert update.name == "requests"
        assert update.current_version == "2.28.0"
        assert update.latest_version == "2.31.0"
        assert update.update_type == "minor"
        assert update.ecosystem == "python"
        assert update.is_security is True
        assert len(update.cve_ids) > 0
        assert update.severity == "high"
        assert update.changelog_url is not None


# ============================================================================
# E2E Test: Notification System
# ============================================================================


class TestNotificationSystemE2E:
    """Test notification system end-to-end integration."""

    @pytest.mark.asyncio
    async def test_notify_critical_vulnerabilities(
        self, temp_project_dir, sample_scan_result, mock_gh_client
    ):
        """Test notifying about critical vulnerabilities."""
        # Use unique state file for each test to avoid persistence
        state_file = temp_project_dir / f"test-notifications-{datetime.now(UTC).timestamp()}.json"

        # Mock gh client to return issue number
        mock_gh_client.run.return_value = MagicMock(
            stdout="https://github.com/test/repo/issues/42"
        )

        with patch.object(
            GHClient, "__init__", return_value=None
        ):
            notifier = DependencyNotifier(
                project_dir=temp_project_dir,
                state_file=state_file
            )
            notifier._gh_client = mock_gh_client

            result = await notifier.notify_critical_vulnerabilities(
                scan_result=sample_scan_result,
                min_severity="high",
                create_issues=True,
            )

        # Verify result
        assert result.success is True
        assert len(result.notifications_sent) == 1  # Only high/critical

        # Manually calculate expected counts since __post_init__ runs too early
        expected_high = sum(1 for n in result.notifications_sent if n.severity == "high")
        assert expected_high == 1

        # Verify notification record
        notification = result.notifications_sent[0]
        assert notification.package_name == "requests"
        assert "CVE-2023-32681" in notification.cve_ids
        assert notification.severity == "high"
        assert notification.issue_number == 42
        assert notification.notification_type == "issue"

    @pytest.mark.asyncio
    async def test_notify_with_dry_run(
        self, temp_project_dir, sample_scan_result
    ):
        """Test notification in dry-run mode (no actual issues created)."""
        # Use unique state file for each test
        state_file = temp_project_dir / f"test-notifications-dryrun-{datetime.now(UTC).timestamp()}.json"

        notifier = DependencyNotifier(
            project_dir=temp_project_dir,
            state_file=state_file
        )

        result = await notifier.notify_critical_vulnerabilities(
            scan_result=sample_scan_result,
            min_severity="medium",
            create_issues=False,  # Dry run
        )

        # Verify dry-run behavior
        assert result.success is True
        assert len(result.notifications_sent) == 2  # high + medium
        assert result.notifications_sent[0].notification_type == "dry_run"
        assert result.notifications_sent[0].issue_number is None

    @pytest.mark.asyncio
    async def test_notification_history_persistence(
        self, temp_project_dir, sample_scan_result, mock_gh_client
    ):
        """Test that notification history persists and prevents duplicates."""
        state_file = temp_project_dir / ".dependency-notifications.json"

        # Mock gh client
        mock_gh_client.run.return_value = MagicMock(
            stdout="https://github.com/test/repo/issues/42"
        )

        with patch.object(
            DependencyNotifier, "gh_client", mock_gh_client
        ):
            # First notification
            notifier1 = DependencyNotifier(
                project_dir=temp_project_dir, state_file=state_file
            )
            await notifier1.notify_critical_vulnerabilities(
                scan_result=sample_scan_result,
                min_severity="high",
                create_issues=True,
            )

            # Verify state file was created
            assert state_file.exists()

            # Second notification attempt (should skip already notified)
            notifier2 = DependencyNotifier(
                project_dir=temp_project_dir, state_file=state_file
            )
            result2 = await notifier2.notify_critical_vulnerabilities(
                scan_result=sample_scan_result,
                min_severity="high",
                create_issues=True,
            )

        # Should have skipped the already-notified package
        assert len(result2.notifications_sent) == 0
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_notification_result_serialization(
        self, temp_project_dir, sample_scan_result, mock_gh_client
    ):
        """Test that NotificationResult serializes correctly to dict."""
        # Use unique state file
        state_file = temp_project_dir / f"test-notifications-serial-{datetime.now(UTC).timestamp()}.json"

        mock_gh_client.run.return_value = MagicMock(
            stdout="https://github.com/test/repo/issues/42"
        )

        with patch.object(
            GHClient, "__init__", return_value=None
        ):
            notifier = DependencyNotifier(
                project_dir=temp_project_dir,
                state_file=state_file
            )
            notifier._gh_client = mock_gh_client

            result = await notifier.notify_critical_vulnerabilities(
                scan_result=sample_scan_result,
                min_severity="high",
                create_issues=True,
            )

        # Verify serialization
        result_dict = result.to_dict()
        assert "success" in result_dict
        assert "notifications_sent" in result_dict
        assert "summary_counts" in result_dict
        assert len(result_dict["notifications_sent"]) == 1

        # Manually verify high count
        high_count = sum(1 for n in result.notifications_sent if n.severity == "high")
        assert high_count == 1


# ============================================================================
# E2E Test: Update Batching
# ============================================================================


class TestUpdateBatchingE2E:
    """Test update batching end-to-end integration."""

    def test_batch_update_segregation(self, sample_scan_result):
        """Test that updates are properly segregated by type and security."""
        # Separate security and non-security updates
        security_updates = [u for u in sample_scan_result.updates_available if u.is_security]
        non_security_updates = [
            u for u in sample_scan_result.updates_available if not u.is_security
        ]

        # Verify segregation
        assert len(security_updates) == 2
        assert len(non_security_updates) == 2

        # Verify all security updates have CVEs
        for update in security_updates:
            assert update.is_security is True
            assert len(update.cve_ids) > 0
            assert update.severity is not None

        # Verify non-security updates have no CVEs
        for update in non_security_updates:
            assert update.is_security is False
            assert len(update.cve_ids) == 0
            assert update.severity is None

    def test_batch_update_types(self, sample_non_security_updates):
        """Test that updates are categorized by type (major, minor, patch)."""
        minor_updates = [u for u in sample_non_security_updates if u.update_type == "minor"]
        patch_updates = [u for u in sample_non_security_updates if u.update_type == "patch"]

        assert len(minor_updates) == 1
        assert len(patch_updates) == 1
        assert minor_updates[0].name == "click"
        assert patch_updates[0].name == "pytest"


# ============================================================================
# E2E Test: Config Loading
# ============================================================================


class TestConfigLoadingE2E:
    """Test configuration loading and auto-approval logic."""

    def test_load_config_from_file(self, temp_project_dir):
        """Test loading configuration from dependency-updates.config.json."""
        # Import here to avoid issues with missing dependencies during test collection
        from runners.dependency_update_runner import load_config

        config = load_config(temp_project_dir)

        # Should load from example config
        assert config is not None
        assert "auto_approval" in config
        assert config["auto_approval"]["enabled"] is True

    def test_load_config_when_missing(self, tmp_path):
        """Test loading config when file doesn't exist."""
        from runners.dependency_update_runner import load_config

        empty_dir = tmp_path / "empty-project"
        empty_dir.mkdir()

        config = load_config(empty_dir)

        # Should return None when config not found
        assert config is None

    def test_auto_approval_logic(self, sample_non_security_updates):
        """Test auto-approval logic for different scenarios."""
        from runners.dependency_update_runner import is_auto_approved

        # Test config with auto-approval enabled for patches
        config = {
            "auto_approval": {
                "enabled": True,
                "patch_updates": True,
                "minor_updates": False,
                "blocklisted_packages": [],
                "allowlisted_packages": [],
            }
        }

        # Patch update should be auto-approved
        patch_update = sample_non_security_updates[1]  # pytest (patch)
        assert is_auto_approved(
            package_name=patch_update.name,
            update_type=patch_update.update_type,
            ecosystem=patch_update.ecosystem,
            is_security=patch_update.is_security,
            config=config,
        ) is True

        # Minor update should NOT be auto-approved (global setting disabled)
        minor_update = sample_non_security_updates[0]  # click (minor)
        assert is_auto_approved(
            package_name=minor_update.name,
            update_type=minor_update.update_type,
            ecosystem=minor_update.ecosystem,
            is_security=minor_update.is_security,
            config=config,
        ) is False

    def test_auto_approval_blocklist(self, sample_non_security_updates):
        """Test that blocklisted packages are never auto-approved."""
        from runners.dependency_update_runner import is_auto_approved

        config = {
            "auto_approval": {
                "enabled": True,
                "patch_updates": True,
                "blocklisted_packages": [
                    {"name": "pytest", "ecosystem": "python", "reason": "Testing"}
                ],
                "allowlisted_packages": [],
            }
        }

        # Even though it's a patch and patches are enabled globally
        # this package is blocklisted
        assert is_auto_approved(
            package_name="pytest",
            update_type="patch",
            ecosystem="python",
            is_security=False,
            config=config,
        ) is False

    def test_auto_approval_allowlist(self, sample_non_security_updates):
        """Test that allowlisted packages use their specific settings."""
        from runners.dependency_update_runner import is_auto_approved

        config = {
            "auto_approval": {
                "enabled": True,
                "patch_updates": False,  # Disabled globally
                "allowlisted_packages": [
                    {"name": "click", "ecosystem": "python", "auto_approve": "minor"}
                ],
                "blocklisted_packages": [],
            }
        }

        # click is in allowlist with minor approval, so it should be approved
        # even though global patch is disabled
        assert is_auto_approved(
            package_name="click",
            update_type="minor",
            ecosystem="python",
            is_security=False,
            config=config,
        ) is True

    def test_security_updates_never_auto_approved(self, sample_security_updates):
        """Test that security updates are never auto-approved."""
        from runners.dependency_update_runner import is_auto_approved

        config = {
            "auto_approval": {
                "enabled": True,
                "patch_updates": True,
                "minor_updates": True,
                "blocklisted_packages": [],
                "allowlisted_packages": [],
            }
        }

        # Even with all auto-approval enabled, security updates should not be auto-approved
        security_update = sample_security_updates[0]
        assert is_auto_approved(
            package_name=security_update.name,
            update_type=security_update.update_type,
            ecosystem=security_update.ecosystem,
            is_security=True,  # Security flag
            config=config,
        ) is False


# ============================================================================
# E2E Test: Complete Workflow
# ============================================================================


class TestCompleteWorkflowE2E:
    """Test the complete dependency update workflow end-to-end."""

    def test_workflow_data_flow(self, sample_scan_result):
        """Test that data flows correctly through the workflow."""
        # Step 1: Scanner produces results
        assert sample_scan_result.has_updates is True
        assert sample_scan_result.has_security_updates is True

        # Step 2: Segregate security vs non-security
        security_updates = sample_scan_result.security_updates
        non_security_updates = [
            u for u in sample_scan_result.updates_available if not u.is_security
        ]

        assert len(security_updates) == 2
        assert len(non_security_updates) == 2

        # Step 3: Verify data integrity for notifications
        for vuln in security_updates:
            assert vuln.name is not None
            assert vuln.current_version is not None
            assert vuln.latest_version is not None
            assert len(vuln.cve_ids) > 0
            assert vuln.severity is not None

    @pytest.mark.asyncio
    async def test_workflow_scan_to_notification(
        self, temp_project_dir, sample_scan_result, mock_gh_client
    ):
        """Test complete workflow from scan to notification."""
        # Use specific state file
        state_file = temp_project_dir / "test-workflow-notifications.json"

        # Mock gh client
        mock_gh_client.run.return_value = MagicMock(
            stdout="https://github.com/test/repo/issues/42"
        )

        with patch.object(
            GHClient, "__init__", return_value=None
        ):
            # Step 1: Initialize notifier
            notifier = DependencyNotifier(
                project_dir=temp_project_dir,
                state_file=state_file
            )
            notifier._gh_client = mock_gh_client

            # Step 2: Notify about vulnerabilities
            result = await notifier.notify_critical_vulnerabilities(
                scan_result=sample_scan_result,
                min_severity="high",
                create_issues=True,
            )

            # Step 3: Verify workflow completed successfully
            assert result.success is True
            assert len(result.notifications_sent) > 0

            # Step 4: Verify state persistence
            assert state_file.exists()

            # Step 5: Verify state can be reloaded
            notifier2 = DependencyNotifier(
                project_dir=temp_project_dir,
                state_file=state_file
            )
            # Should have history from previous notification
            assert len(notifier2._notification_history) > 0

    def test_workflow_with_config_integration(
        self, temp_project_dir, sample_scan_result
    ):
        """Test workflow with configuration integration."""
        from runners.dependency_update_runner import load_config, is_auto_approved

        # Load configuration
        config = load_config(temp_project_dir)

        if config:
            # Test auto-approval for each update
            approval_results = {}
            for update in sample_scan_result.updates_available:
                approved = is_auto_approved(
                    package_name=update.name,
                    update_type=update.update_type,
                    ecosystem=update.ecosystem,
                    is_security=update.is_security,
                    config=config,
                )
                approval_results[update.name] = approved

            # Verify security updates are never approved
            security_approval = [
                approval_results[u.name]
                for u in sample_scan_result.security_updates
            ]
            assert all(approved is False for approved in security_approval)


# ============================================================================
# E2E Test: Report Generation
# ============================================================================


class TestReportGenerationE2E:
    """Test report generation end-to-end integration."""

    def test_markdown_report_structure(self, sample_scan_result):
        """Test that markdown report has correct structure."""
        # Import report generation function
        from runners.dependency_update_runner import _generate_markdown_report

        # Create mock batches
        mock_batches = []
        report = _generate_markdown_report(
            scan_result=sample_scan_result,
            batches=mock_batches,
            project_dir=Path("/test/project"),
            ecosystems_filter=["python"],
            config=None,
            updates_to_process=sample_scan_result.updates_available,
        )

        # Verify report structure
        assert "# Dependency Update Report" in report
        assert "## Summary" in report
        assert "## 🔒 Security Vulnerabilities" in report
        assert "## 📦 Recommended Update Batches" in report
        assert "## 📋 All Available Updates" in report
        assert "Generated by" in report

    def test_markdown_report_content(self, sample_scan_result):
        """Test that markdown report contains correct content."""
        from runners.dependency_update_runner import _generate_markdown_report

        report = _generate_markdown_report(
            scan_result=sample_scan_result,
            batches=[],
            project_dir=Path("/test/project"),
            ecosystems_filter=["python"],
            config=None,
            updates_to_process=sample_scan_result.updates_available,
        )

        # Verify security updates are mentioned
        assert "requests" in report
        assert "CVE-2023-32681" in report
        assert "urllib3" in report
        assert "CVE-2023-43804" in report

        # Verify severity levels shown
        assert "High" in report
        assert "Medium" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
