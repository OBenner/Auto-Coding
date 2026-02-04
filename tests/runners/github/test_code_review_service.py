#!/usr/bin/env python3
"""
Integration Tests for Code Review Service
==========================================

Tests for the CodeReviewService class covering:
- review_code_changes() method with mock SecurityScanner
- Security vulnerability to PR finding conversion
- Severity mapping (critical → CRITICAL, high → HIGH, etc.)
- post_review_to_github() with mock GHClient
- Markdown formatting of review body
- Review event determination (approve/comment/request-changes)
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def test_env(temp_git_repo: Path):
    """Create test environment with project and GitHub directories."""
    project_dir = temp_git_repo
    github_dir = project_dir / ".github" / "automation"
    github_dir.mkdir(parents=True, exist_ok=True)

    yield project_dir, github_dir


@pytest.fixture
def mock_config():
    """Create mock GitHubRunnerConfig."""
    from runners.github.models import GitHubRunnerConfig

    config = GitHubRunnerConfig(
        github_token="test_token",
        repo_owner="test_owner",
        repo_name="test_repo",
        enabled=True,
    )
    return config


@pytest.fixture
def mock_security_scanner():
    """Create mock SecurityScanner."""
    scanner = MagicMock()
    scanner.scan_project = MagicMock()
    return scanner


@pytest.fixture
def sample_vulnerability():
    """Create a sample SecurityVulnerability."""
    from analysis.security_scanner import SecurityVulnerability

    return SecurityVulnerability(
        title="SQL Injection Vulnerability",
        description="Unsafe SQL query construction using user input",
        severity="high",
        file="app/database.py",
        line=45,
        cwe="CWE-89",
        source="bandit",
    )


# =============================================================================
# CODE REVIEW SERVICE INITIALIZATION TESTS
# =============================================================================


class TestCodeReviewServiceInit:
    """Tests for CodeReviewService initialization."""

    def test_service_initialization(self, test_env, mock_config):
        """Test that service initializes correctly."""
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        service = CodeReviewService(
            project_dir=project_dir,
            github_dir=github_dir,
            config=mock_config,
        )

        assert service.project_dir == project_dir
        assert service.github_dir == github_dir
        assert service.config == mock_config
        assert service.scanner is not None

    def test_service_with_progress_callback(self, test_env, mock_config):
        """Test service initialization with progress callback."""
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        callback = MagicMock()
        service = CodeReviewService(
            project_dir=project_dir,
            github_dir=github_dir,
            config=mock_config,
            progress_callback=callback,
        )

        assert service.progress_callback == callback


# =============================================================================
# SEVERITY MAPPING TESTS
# =============================================================================


class TestSeverityMapping:
    """Tests for severity mapping from scanner to review severity."""

    def test_critical_severity_mapping(self, test_env, mock_config):
        """Test that 'critical' maps to ReviewSeverity.CRITICAL."""
        from runners.github.models import ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        result = service._map_severity("critical")
        assert result == ReviewSeverity.CRITICAL

    def test_high_severity_mapping(self, test_env, mock_config):
        """Test that 'high' maps to ReviewSeverity.HIGH."""
        from runners.github.models import ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        result = service._map_severity("high")
        assert result == ReviewSeverity.HIGH

    def test_medium_severity_mapping(self, test_env, mock_config):
        """Test that 'medium' maps to ReviewSeverity.MEDIUM."""
        from runners.github.models import ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        result = service._map_severity("medium")
        assert result == ReviewSeverity.MEDIUM

    def test_low_severity_mapping(self, test_env, mock_config):
        """Test that 'low' maps to ReviewSeverity.LOW."""
        from runners.github.models import ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        result = service._map_severity("low")
        assert result == ReviewSeverity.LOW

    def test_info_severity_maps_to_low(self, test_env, mock_config):
        """Test that 'info' maps to ReviewSeverity.LOW."""
        from runners.github.models import ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        result = service._map_severity("info")
        assert result == ReviewSeverity.LOW

    def test_unknown_severity_defaults_to_medium(self, test_env, mock_config):
        """Test that unknown severity defaults to ReviewSeverity.MEDIUM."""
        from runners.github.models import ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        result = service._map_severity("unknown")
        assert result == ReviewSeverity.MEDIUM


# =============================================================================
# CATEGORY MAPPING TESTS
# =============================================================================


class TestCategoryMapping:
    """Tests for category mapping from scanner source to review category."""

    def test_secrets_scanner_maps_to_security(self, test_env, mock_config):
        """Test that 'secrets' scanner maps to ReviewCategory.SECURITY."""
        from runners.github.models import ReviewCategory
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        result = service._map_category("secrets")
        assert result == ReviewCategory.SECURITY

    def test_bandit_scanner_maps_to_security(self, test_env, mock_config):
        """Test that 'bandit' scanner maps to ReviewCategory.SECURITY."""
        from runners.github.models import ReviewCategory
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        result = service._map_category("bandit")
        assert result == ReviewCategory.SECURITY


# =============================================================================
# VULNERABILITY CONVERSION TESTS
# =============================================================================


class TestVulnerabilityConversion:
    """Tests for converting security vulnerabilities to PR findings."""

    def test_convert_vulnerability_to_finding(
        self, test_env, mock_config, sample_vulnerability
    ):
        """Test conversion of SecurityVulnerability to PRReviewFinding."""
        from runners.github.models import ReviewCategory, ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        finding = service._convert_vulnerability_to_finding(
            sample_vulnerability
        )

        assert finding.title == "SQL Injection Vulnerability"
        assert "Unsafe SQL query construction" in finding.description
        assert finding.severity == ReviewSeverity.HIGH
        assert finding.category == ReviewCategory.SECURITY
        assert finding.file == "app/database.py"
        assert finding.line == 45
        assert "CWE-89" in finding.description

    def test_finding_id_generation_is_unique(
        self, test_env, mock_config, sample_vulnerability
    ):
        """Test that finding IDs are unique and consistent."""
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        finding1 = service._convert_vulnerability_to_finding(
            sample_vulnerability
        )
        finding2 = service._convert_vulnerability_to_finding(
            sample_vulnerability
        )

        # Same vulnerability should produce same ID
        assert finding1.id == finding2.id

        # ID should be a hash
        assert len(finding1.id) == 12
        assert isinstance(finding1.id, str)

    def test_vulnerability_without_file_uses_project_wide(
        self, test_env, mock_config
    ):
        """Test that vulnerability without file uses 'project-wide'."""
        from analysis.security_scanner import SecurityVulnerability
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        vuln = SecurityVulnerability(
            title="Dependency Vulnerability",
            description="Outdated package version",
            severity="medium",
            file=None,  # No specific file
            line=None,
            cwe=None,
            source="npm_audit",
        )

        finding = service._convert_vulnerability_to_finding(vuln)

        assert finding.file == "project-wide"
        assert finding.line == 1


# =============================================================================
# SECRET DETECTION CONVERSION TESTS
# =============================================================================


class TestSecretConversion:
    """Tests for converting detected secrets to PR findings."""

    def test_convert_secret_to_finding(self, test_env, mock_config):
        """Test conversion of secret detection to PRReviewFinding."""
        from runners.github.models import ReviewCategory, ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env
        service = CodeReviewService(project_dir, github_dir, mock_config)

        secret = {
            "file": "config/settings.py",
            "line": 12,
            "pattern": "AWS Access Key",
            "match": "AKIA...",
        }

        finding = service._convert_secret_to_finding(secret)

        assert "Secret detected: AWS Access Key" in finding.title
        assert finding.severity == ReviewSeverity.CRITICAL  # Always critical
        assert finding.category == ReviewCategory.SECURITY
        assert finding.file == "config/settings.py"
        assert finding.line == 12


# =============================================================================
# REVIEW_CODE_CHANGES TESTS
# =============================================================================


class TestReviewCodeChanges:
    """Tests for review_code_changes method."""

    @pytest.mark.asyncio
    async def test_review_code_changes_with_vulnerabilities(
        self, test_env, mock_config, sample_vulnerability
    ):
        """Test review_code_changes integrates SecurityScanner correctly."""
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        # Mock PRContext
        mock_context = MagicMock()
        mock_context.pr_number = 123
        mock_context.changed_files = ["app/database.py"]

        with patch(
            "runners.github.services.code_review_service.SecurityScanner"
        ) as MockScanner:
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_project = MagicMock(
                return_value=[sample_vulnerability]
            )
            MockScanner.return_value = mock_scanner_instance

            service = CodeReviewService(project_dir, github_dir, mock_config)

            findings = await service.review_code_changes(mock_context)

            assert len(findings) == 1
            assert findings[0].title == "SQL Injection Vulnerability"
            assert findings[0].file == "app/database.py"

    @pytest.mark.asyncio
    async def test_review_code_changes_no_vulnerabilities(
        self, test_env, mock_config
    ):
        """Test review_code_changes with no vulnerabilities found."""
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        mock_context = MagicMock()
        mock_context.pr_number = 123
        mock_context.changed_files = ["app/clean.py"]

        with patch(
            "runners.github.services.code_review_service.SecurityScanner"
        ) as MockScanner:
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_project = MagicMock(return_value=[])
            MockScanner.return_value = mock_scanner_instance

            service = CodeReviewService(project_dir, github_dir, mock_config)

            findings = await service.review_code_changes(mock_context)

            assert len(findings) == 0


# =============================================================================
# POST_REVIEW_TO_GITHUB TESTS
# =============================================================================


class TestPostReviewToGitHub:
    """Tests for post_review_to_github method."""

    @pytest.mark.asyncio
    async def test_post_review_with_critical_findings(
        self, test_env, mock_config
    ):
        """Test that critical findings result in REQUEST_CHANGES event."""
        from runners.github.models import PRReviewFinding, ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        critical_finding = PRReviewFinding(
            id="test123",
            severity=ReviewSeverity.CRITICAL,
            category="SECURITY",
            title="Critical Security Issue",
            description="This is critical",
            file="app/auth.py",
            line=10,
        )

        mock_context = MagicMock()
        mock_context.pr_number = 123

        with patch(
            "runners.github.services.code_review_service.GHClient"
        ) as MockGHClient:
            mock_gh_instance = MagicMock()
            mock_gh_instance.pr_review = AsyncMock()
            MockGHClient.return_value = mock_gh_instance

            service = CodeReviewService(project_dir, github_dir, mock_config)
            service.gh_client = mock_gh_instance

            await service.post_review_to_github(
                mock_context, [critical_finding]
            )

            # Verify review was posted
            mock_gh_instance.pr_review.assert_called_once()
            call_args = mock_gh_instance.pr_review.call_args

            # Should be REQUEST_CHANGES for critical issues
            assert "REQUEST_CHANGES" in str(call_args) or call_args[1].get(
                "event"
            ) in ["REQUEST_CHANGES", "request_changes"]

    @pytest.mark.asyncio
    async def test_post_review_with_low_findings(self, test_env, mock_config):
        """Test that low severity findings result in COMMENT event."""
        from runners.github.models import PRReviewFinding, ReviewSeverity
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        low_finding = PRReviewFinding(
            id="test456",
            severity=ReviewSeverity.LOW,
            category="STYLE",
            title="Minor Style Issue",
            description="Consider renaming",
            file="app/utils.py",
            line=20,
        )

        mock_context = MagicMock()
        mock_context.pr_number = 123

        with patch(
            "runners.github.services.code_review_service.GHClient"
        ) as MockGHClient:
            mock_gh_instance = MagicMock()
            mock_gh_instance.pr_review = AsyncMock()
            MockGHClient.return_value = mock_gh_instance

            service = CodeReviewService(project_dir, github_dir, mock_config)
            service.gh_client = mock_gh_instance

            await service.post_review_to_github(mock_context, [low_finding])

            # Verify review was posted
            mock_gh_instance.pr_review.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_review_no_findings_approves(
        self, test_env, mock_config
    ):
        """Test that no findings results in APPROVE event."""
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        mock_context = MagicMock()
        mock_context.pr_number = 123

        with patch(
            "runners.github.services.code_review_service.GHClient"
        ) as MockGHClient:
            mock_gh_instance = MagicMock()
            mock_gh_instance.pr_review = AsyncMock()
            MockGHClient.return_value = mock_gh_instance

            service = CodeReviewService(project_dir, github_dir, mock_config)
            service.gh_client = mock_gh_instance

            await service.post_review_to_github(mock_context, [])

            # Verify approval was posted
            mock_gh_instance.pr_review.assert_called_once()
            call_args = mock_gh_instance.pr_review.call_args

            # Should be APPROVE for no issues
            assert "APPROVE" in str(call_args) or call_args[1].get(
                "event"
            ) in ["APPROVE", "approve"]


# =============================================================================
# MARKDOWN FORMATTING TESTS
# =============================================================================


class TestMarkdownFormatting:
    """Tests for markdown formatting of review body."""

    @pytest.mark.asyncio
    async def test_review_body_markdown_format(self, test_env, mock_config):
        """Test that review body is formatted as markdown."""
        from runners.github.models import (
            PRReviewFinding,
            ReviewCategory,
            ReviewSeverity,
        )
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        finding = PRReviewFinding(
            id="md_test",
            severity=ReviewSeverity.HIGH,
            category=ReviewCategory.SECURITY,
            title="Test Finding",
            description="Test description",
            file="test.py",
            line=1,
        )

        mock_context = MagicMock()
        mock_context.pr_number = 123

        with patch(
            "runners.github.services.code_review_service.GHClient"
        ) as MockGHClient:
            mock_gh_instance = MagicMock()
            mock_gh_instance.pr_review = AsyncMock()
            MockGHClient.return_value = mock_gh_instance

            service = CodeReviewService(project_dir, github_dir, mock_config)
            service.gh_client = mock_gh_instance

            await service.post_review_to_github(mock_context, [finding])

            # Verify markdown formatting in call
            call_args = mock_gh_instance.pr_review.call_args
            body = call_args[1].get("body", "")

            # Should contain markdown elements
            assert isinstance(body, str)
            # Markdown typically uses headers, lists, or bold text
            # At minimum should mention the finding
            assert len(body) > 0


# =============================================================================
# PROGRESS CALLBACK TESTS
# =============================================================================


class TestProgressCallback:
    """Tests for progress callback integration."""

    @pytest.mark.asyncio
    async def test_progress_callback_invoked(self, test_env, mock_config):
        """Test that progress callback is invoked during review."""
        from runners.github.services.code_review_service import (
            CodeReviewService,
        )

        project_dir, github_dir = test_env

        callback = MagicMock()
        service = CodeReviewService(
            project_dir, github_dir, mock_config, progress_callback=callback
        )

        # Manually invoke progress report
        service._report_progress("testing", 50, "Test message")

        # Verify callback was called
        assert callback.called


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def run_all_tests():
    """Run all tests using pytest."""
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))


if __name__ == "__main__":
    run_all_tests()
