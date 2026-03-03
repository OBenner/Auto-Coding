#!/usr/bin/env python3
"""
Tests for the SecurityAuditAgent module.

Tests cover:
- SecurityFinding and SecurityReport dataclasses
- SecurityAuditAgent functionality
- OWASP scanning integration
- Dependency and secrets scanning
- Authentication flow analysis
- Report generation and serialization
- Remediation guidance generation
"""

import json

# Add auto-claude to path for imports
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from agents.security_auditor import (
    SecurityAuditAgent,
    SecurityFinding,
    SecurityReport,
    has_critical_security_issues,
    run_security_audit,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def agent():
    """Create a SecurityAuditAgent instance."""
    return SecurityAuditAgent()


@pytest.fixture
def sample_finding():
    """Create a sample security finding."""
    return SecurityFinding(
        category="auth",
        owasp_category="A07_2021",
        severity="high",
        title="Hardcoded password",
        description="Password found in code",
        file="app.py",
        line=42,
        code_snippet="password = 'secret123'",
        remediation="Use environment variables",
        cwe="CWE-798",
        references=["https://owasp.org/"],
    )


@pytest.fixture
def sample_report(temp_dir):
    """Create a sample security report."""
    return SecurityReport(
        project_dir=str(temp_dir),
        timestamp=datetime.now().isoformat(),
    )


@pytest.fixture
def python_project(temp_dir):
    """Create a simple Python project with test files."""
    # Create a Python file with hardcoded credentials
    app_file = temp_dir / "app.py"
    app_file.write_text("""
import os

# Test file with security issues
password = "hardcoded123"
api_key = "PLACEHOLDER_TEST_KEY_000000"

def login(username, password):
    if password == "admin123":
        return True
    return False
""")

    # Create requirements.txt
    requirements = temp_dir / "requirements.txt"
    requirements.write_text("flask==2.0.0\nrequests==2.25.0\n")

    return temp_dir


# =============================================================================
# SECURITY FINDING TESTS
# =============================================================================


class TestSecurityFinding:
    """Tests for SecurityFinding dataclass."""

    def test_create_finding(self):
        """Test creating a security finding."""
        finding = SecurityFinding(
            category="secret",
            severity="critical",
            title="API key exposed",
            description="Found API key in code",
            file="config.py",
            line=10,
        )

        assert finding.category == "secret"
        assert finding.severity == "critical"
        assert finding.title == "API key exposed"
        assert finding.file == "config.py"
        assert finding.line == 10

    def test_finding_optional_fields(self):
        """Test finding with optional fields."""
        finding = SecurityFinding(
            category="auth",
            title="Test finding",
            description="Test description",
        )

        assert finding.owasp_category is None
        assert finding.file is None
        assert finding.line is None
        assert finding.code_snippet is None
        assert finding.cwe is None
        assert finding.references == []

    def test_finding_to_dict(self, sample_finding):
        """Test converting finding to dictionary."""
        finding_dict = sample_finding.to_dict()

        assert isinstance(finding_dict, dict)
        assert finding_dict["category"] == "auth"
        assert finding_dict["owasp_category"] == "A07_2021"
        assert finding_dict["severity"] == "high"
        assert finding_dict["title"] == "Hardcoded password"
        assert finding_dict["file"] == "app.py"
        assert finding_dict["line"] == 42
        assert finding_dict["cwe"] == "CWE-798"
        assert len(finding_dict["references"]) == 1


# =============================================================================
# SECURITY REPORT TESTS
# =============================================================================


class TestSecurityReport:
    """Tests for SecurityReport dataclass."""

    def test_create_report(self, temp_dir):
        """Test creating a security report."""
        report = SecurityReport(
            project_dir=str(temp_dir),
            timestamp=datetime.now().isoformat(),
        )

        assert report.project_dir == str(temp_dir)
        assert report.findings == []
        assert report.summary_counts == {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
            "total": 0,
        }

    def test_add_finding(self, sample_report, sample_finding):
        """Test adding a finding to report."""
        sample_report.add_finding(sample_finding)

        assert len(sample_report.findings) == 1
        assert sample_report.summary_counts["high"] == 1
        assert sample_report.summary_counts["total"] == 1

    def test_add_multiple_findings(self, sample_report):
        """Test adding multiple findings."""
        findings = [
            SecurityFinding(
                category="auth",
                severity="critical",
                title="Critical issue",
                description="Test",
            ),
            SecurityFinding(
                category="auth", severity="high", title="High issue", description="Test"
            ),
            SecurityFinding(
                category="auth",
                severity="medium",
                title="Medium issue",
                description="Test",
            ),
        ]

        for finding in findings:
            sample_report.add_finding(finding)

        assert len(sample_report.findings) == 3
        assert sample_report.summary_counts["critical"] == 1
        assert sample_report.summary_counts["high"] == 1
        assert sample_report.summary_counts["medium"] == 1
        assert sample_report.summary_counts["total"] == 3

    def test_get_critical_findings(self, sample_report):
        """Test getting critical and high severity findings."""
        findings = [
            SecurityFinding(
                category="auth",
                severity="critical",
                title="Critical",
                description="Test",
            ),
            SecurityFinding(
                category="auth", severity="high", title="High", description="Test"
            ),
            SecurityFinding(
                category="auth", severity="medium", title="Medium", description="Test"
            ),
        ]

        for finding in findings:
            sample_report.add_finding(finding)

        critical_findings = sample_report.get_critical_findings()

        assert len(critical_findings) == 2
        assert all(f.severity in ("critical", "high") for f in critical_findings)

    def test_has_blocking_issues(self, sample_report):
        """Test checking for blocking issues."""
        # No issues initially
        assert sample_report.has_blocking_issues() is False

        # Add medium severity - should not block
        sample_report.add_finding(
            SecurityFinding(
                category="auth", severity="medium", title="Test", description="Test"
            )
        )
        assert sample_report.has_blocking_issues() is False

        # Add critical severity - should block
        sample_report.add_finding(
            SecurityFinding(
                category="auth", severity="critical", title="Test", description="Test"
            )
        )
        assert sample_report.has_blocking_issues() is True

    def test_to_dict(self, sample_report, sample_finding):
        """Test converting report to dictionary."""
        sample_report.add_finding(sample_finding)

        report_dict = sample_report.to_dict()

        assert isinstance(report_dict, dict)
        assert "project_dir" in report_dict
        assert "timestamp" in report_dict
        assert "findings" in report_dict
        assert "summary_counts" in report_dict
        assert len(report_dict["findings"]) == 1

    def test_to_json(self, sample_report, sample_finding):
        """Test converting report to JSON."""
        sample_report.add_finding(sample_finding)

        json_str = sample_report.to_json()

        assert isinstance(json_str, str)
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert "findings" in parsed
        assert len(parsed["findings"]) == 1

    def test_to_markdown(self, sample_report, sample_finding):
        """Test converting report to Markdown."""
        sample_report.add_finding(sample_finding)
        sample_report.executive_summary = "Test summary"
        sample_report.recommendations = ["Fix all critical issues"]

        markdown = sample_report.to_markdown()

        assert isinstance(markdown, str)
        assert "# Security Audit Report" in markdown
        assert "## Executive Summary" in markdown
        assert "Test summary" in markdown
        assert "## Recommendations" in markdown
        assert "## High Severity Findings" in markdown
        assert "Hardcoded password" in markdown

    def test_to_json_file(self, sample_report, sample_finding, temp_dir):
        """Test saving report to JSON file."""
        sample_report.add_finding(sample_finding)
        output_file = temp_dir / "report.json"

        sample_report.to_json_file(output_file)

        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
            assert "findings" in data
            assert len(data["findings"]) == 1

    def test_to_markdown_file(self, sample_report, sample_finding, temp_dir):
        """Test saving report to Markdown file."""
        sample_report.add_finding(sample_finding)
        output_file = temp_dir / "report.md"

        sample_report.to_markdown_file(output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "# Security Audit Report" in content

    def test_to_security_scan_results_dict(self, sample_report):
        """Test converting to security_scan_results.json format."""
        # Add a secret finding
        sample_report.add_finding(
            SecurityFinding(
                category="secret",
                severity="critical",
                title="Potential secret: api_key",
                description="Found API key",
                file="config.py",
                line=10,
            )
        )

        # Add an auth finding
        sample_report.add_finding(
            SecurityFinding(
                category="auth",
                severity="high",
                title="Weak password",
                description="Password policy issue",
                file="auth.py",
                line=20,
            )
        )

        scan_results = sample_report.to_security_scan_results_dict()

        assert isinstance(scan_results, dict)
        assert "detections" in scan_results
        assert "vulnerabilities" in scan_results
        assert "summary" in scan_results
        assert len(scan_results["detections"]) == 1
        assert len(scan_results["vulnerabilities"]) == 2
        assert scan_results["has_critical_issues"] is True
        assert scan_results["should_block_qa"] is True


# =============================================================================
# SECURITY AUDIT AGENT TESTS
# =============================================================================


class TestSecurityAuditAgent:
    """Tests for SecurityAuditAgent class."""

    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent is not None
        assert agent._security_scanner is None

    def test_security_scanner_property(self, agent):
        """Test lazy initialization of security scanner."""
        scanner = agent.security_scanner

        assert scanner is not None
        assert agent._security_scanner is not None

    def test_to_dict(self, agent):
        """Test converting agent to dictionary."""
        agent_dict = agent.to_dict()

        assert isinstance(agent_dict, dict)
        assert agent_dict["agent_type"] == "SecurityAuditAgent"
        assert "capabilities" in agent_dict
        assert "owasp_top_10_scanning" in agent_dict["capabilities"]
        assert "dependency_vulnerability_checking" in agent_dict["capabilities"]
        assert "authentication_flow_analysis" in agent_dict["capabilities"]

    @patch("agents.security_auditor.SecurityScanner")
    def test_run_full_audit_basic(self, mock_scanner_class, agent, temp_dir):
        """Test running a full security audit."""
        # Mock the scanner
        mock_scanner = MagicMock()
        mock_scan_result = MagicMock()
        mock_scan_result.secrets = []
        mock_scan_result.vulnerabilities = []
        mock_scanner.scan.return_value = mock_scan_result
        mock_scanner_class.return_value = mock_scanner
        agent._security_scanner = mock_scanner

        report = agent.run_full_audit(temp_dir)

        assert isinstance(report, SecurityReport)
        assert report.project_dir == str(temp_dir)
        assert report.timestamp is not None

    @patch("agents.security_auditor.SecurityScanner")
    def test_scan_secrets(self, mock_scanner_class, agent, temp_dir):
        """Test secret detection integration."""
        # Mock the scanner with credential findings
        mock_scanner = MagicMock()
        mock_scan_result = MagicMock()
        mock_scan_result.has_critical_issues = True
        mock_scan_result.vulnerabilities = []
        mock_scanner.scan.return_value = mock_scan_result
        agent._security_scanner = mock_scanner

        report = SecurityReport(
            project_dir=str(temp_dir), timestamp=datetime.now().isoformat()
        )
        agent._scan_secrets(temp_dir, report)

        assert len(report.findings) == 1
        assert report.findings[0].category == "secret"
        assert report.findings[0].severity == "critical"
        assert report.detection_scan["issues_found"] == 1

    @patch("agents.security_auditor.SecurityScanner")
    def test_scan_dependencies(self, mock_scanner_class, agent, temp_dir):
        """Test dependency vulnerability scanning."""
        from analysis.security_scanner import SecurityVulnerability

        # Mock the scanner with dependency vulnerabilities
        mock_scanner = MagicMock()
        mock_scan_result = MagicMock()
        mock_scan_result.secrets = []
        mock_scan_result.vulnerabilities = [
            SecurityVulnerability(
                severity="high",
                source="npm_audit",
                title="Vulnerable package",
                description="Package has known CVE",
                file="package.json",
            )
        ]
        mock_scanner.scan.return_value = mock_scan_result
        agent._security_scanner = mock_scanner

        report = SecurityReport(
            project_dir=str(temp_dir), timestamp=datetime.now().isoformat()
        )
        agent._scan_dependencies(temp_dir, report)

        assert len(report.findings) == 1
        assert report.findings[0].category == "dependency"
        assert report.dependency_audit["vulnerabilities_found"] == 1

    def test_analyze_authentication(self, agent, python_project):
        """Test authentication flow analysis."""
        result = agent.analyze_authentication(python_project)

        assert isinstance(result, dict)
        assert "findings" in result
        assert "auth_mechanisms" in result
        assert "checks_performed" in result
        assert "summary" in result
        assert isinstance(result["findings"], list)

    def test_scan_auth_patterns(self, agent, python_project):
        """Test scanning for authentication security patterns."""
        findings = agent._scan_auth_patterns(python_project)

        assert isinstance(findings, list)
        # Should find hardcoded credentials in our test file
        assert len(findings) > 0
        assert any(f.category == "auth" for f in findings)

    def test_detect_auth_mechanisms(self, agent, python_project):
        """Test detecting authentication mechanisms."""
        mechanisms = agent._detect_auth_mechanisms(python_project)

        assert isinstance(mechanisms, list)
        assert len(mechanisms) > 0

    def test_check_password_policies(self, agent, python_project):
        """Test checking password policies."""
        findings = agent._check_password_policies(python_project)

        assert isinstance(findings, list)

    def test_check_session_management(self, agent, temp_dir):
        """Test checking session management security."""
        # Create a file with insecure session config
        app_file = temp_dir / "app.py"
        app_file.write_text("""
from flask import session
# Configure session with insecure settings
session.cookie_httponly = False
session.cookie_secure = False
""")

        findings = agent._check_session_management(temp_dir)

        assert isinstance(findings, list)
        # Should find both HTTPOnly and Secure issues
        assert len(findings) == 2

    def test_check_token_handling(self, agent, temp_dir):
        """Test checking JWT/OAuth token handling."""
        # Create a file with insecure JWT usage
        app_file = temp_dir / "auth.py"
        app_file.write_text("""
import jwt

def verify_token(token):
    return jwt.decode(token, verify=False)
""")

        findings = agent._check_token_handling(temp_dir)

        assert isinstance(findings, list)
        # Should find JWT signature verification disabled
        assert len(findings) > 0
        assert any("JWT" in f.title for f in findings)

    def test_check_rate_limiting(self, agent, temp_dir):
        """Test checking rate limiting on auth endpoints."""
        # Create a file with login endpoint but no rate limiting
        app_file = temp_dir / "routes.py"
        app_file.write_text("""
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    return authenticate(username, password)
""")

        findings = agent._check_rate_limiting(temp_dir)

        assert isinstance(findings, list)
        # Should find missing rate limiting
        assert len(findings) > 0

    def test_generate_remediation_secret(self, agent):
        """Test generating remediation for secret findings."""
        finding = SecurityFinding(
            category="secret",
            severity="critical",
            title="API key exposed",
            description="Found hardcoded API key",
            remediation="Remove from code",
        )

        remediation = agent.generate_remediation(finding)

        assert isinstance(remediation, str)
        assert "CRITICAL" in remediation
        assert "environment variable" in remediation.lower()
        assert "rotate" in remediation.lower()

    def test_generate_remediation_auth(self, agent):
        """Test generating remediation for auth findings."""
        finding = SecurityFinding(
            category="auth",
            severity="high",
            title="Weak password hashing",
            description="Using MD5 for passwords",
            remediation="Use bcrypt",
        )

        remediation = agent.generate_remediation(finding)

        assert isinstance(remediation, str)
        assert "bcrypt" in remediation.lower()
        assert "password" in remediation.lower()

    def test_generate_remediation_dependency(self, agent):
        """Test generating remediation for dependency findings."""
        finding = SecurityFinding(
            category="dependency",
            severity="high",
            title="Vulnerable package",
            description="Package has CVE",
            remediation="Update package",
        )

        remediation = agent.generate_remediation(finding)

        assert isinstance(remediation, str)
        assert "update" in remediation.lower()
        assert "npm" in remediation.lower() or "pip" in remediation.lower()

    def test_generate_remediation_owasp(self, agent):
        """Test generating remediation for OWASP findings."""
        finding = SecurityFinding(
            category="owasp",
            owasp_category="A03_2021",
            severity="high",
            title="SQL Injection",
            description="Injection vulnerability",
            remediation="Use parameterized queries",
        )

        remediation = agent.generate_remediation(finding)

        assert isinstance(remediation, str)
        assert "A03_2021" in remediation

    def test_generate_report(self, agent, temp_dir):
        """Test generating a security report."""
        findings = [
            SecurityFinding(
                category="auth", severity="critical", title="Test", description="Test"
            ),
            SecurityFinding(
                category="secret", severity="high", title="Test", description="Test"
            ),
        ]

        report = agent.generate_report(findings=findings, project_dir=temp_dir)

        assert isinstance(report, SecurityReport)
        assert len(report.findings) == 2
        assert report.summary_counts["total"] == 2
        assert report.executive_summary != ""

    def test_export_report_to_scan_results_format(self, agent, sample_report, temp_dir):
        """Test exporting report in scan results format."""
        sample_report.add_finding(
            SecurityFinding(
                category="secret",
                severity="critical",
                title="Potential secret: api_key",
                description="Test",
                file="config.py",
                line=10,
            )
        )

        output_file = temp_dir / "scan_results.json"
        agent.export_report_to_scan_results_format(sample_report, output_file)

        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
            assert "detections" in data
            assert "vulnerabilities" in data
            assert "summary" in data


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestSecurityAuditIntegration:
    """Integration tests for full security audit workflow."""

    @patch("agents.security_auditor.SecurityScanner")
    def test_full_audit_with_all_scans(self, mock_scanner_class, agent, temp_dir):
        """Test running full audit with all scan types."""
        # Mock the scanner
        mock_scanner = MagicMock()
        mock_scan_result = MagicMock()
        mock_scan_result.secrets = []
        mock_scan_result.vulnerabilities = []
        mock_scanner.scan.return_value = mock_scan_result
        agent._security_scanner = mock_scanner

        report = agent.run_full_audit(
            temp_dir,
            scan_dependencies=True,
            scan_secrets=True,
            analyze_auth=True,
            scan_owasp=True,
        )

        assert isinstance(report, SecurityReport)
        assert report.summary_counts is not None

    @patch("agents.security_auditor.SecurityScanner")
    def test_full_audit_saves_to_spec_dir(self, mock_scanner_class, agent, temp_dir):
        """Test that audit saves report to spec directory."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        # Mock the scanner
        mock_scanner = MagicMock()
        mock_scan_result = MagicMock()
        mock_scan_result.secrets = []
        mock_scan_result.vulnerabilities = []
        mock_scanner.scan.return_value = mock_scan_result
        agent._security_scanner = mock_scanner

        agent.run_full_audit(temp_dir, spec_dir=spec_dir)

        # Check that reports were saved
        assert (spec_dir / "security_report.json").exists()
        assert (spec_dir / "security_report.md").exists()

    @patch("agents.security_auditor.SecurityScanner")
    def test_full_audit_selective_scans(self, mock_scanner_class, agent, temp_dir):
        """Test running audit with selective scan types."""
        # Mock the scanner
        mock_scanner = MagicMock()
        mock_scan_result = MagicMock()
        mock_scan_result.secrets = []
        mock_scan_result.vulnerabilities = []
        mock_scanner.scan.return_value = mock_scan_result
        agent._security_scanner = mock_scanner

        # Only scan secrets
        report = agent.run_full_audit(
            temp_dir,
            scan_secrets=True,
            scan_dependencies=False,
            analyze_auth=False,
            scan_owasp=False,
        )

        assert isinstance(report, SecurityReport)


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch("agents.security_auditor.SecurityAuditAgent.run_full_audit")
    def test_run_security_audit(self, mock_run_full_audit, temp_dir):
        """Test run_security_audit convenience function."""
        mock_report = SecurityReport(
            project_dir=str(temp_dir), timestamp=datetime.now().isoformat()
        )
        mock_run_full_audit.return_value = mock_report

        report = run_security_audit(temp_dir)

        assert isinstance(report, SecurityReport)
        mock_run_full_audit.assert_called_once()

    @patch("agents.security_auditor.SecurityAuditAgent.run_full_audit")
    def test_has_critical_security_issues_true(self, mock_run_full_audit, temp_dir):
        """Test has_critical_security_issues when issues exist."""
        mock_report = SecurityReport(
            project_dir=str(temp_dir), timestamp=datetime.now().isoformat()
        )
        mock_report.add_finding(
            SecurityFinding(
                category="auth", severity="critical", title="Test", description="Test"
            )
        )
        mock_run_full_audit.return_value = mock_report

        has_issues = has_critical_security_issues(temp_dir)

        assert has_issues is True

    @patch("agents.security_auditor.SecurityAuditAgent.run_full_audit")
    def test_has_critical_security_issues_false(self, mock_run_full_audit, temp_dir):
        """Test has_critical_security_issues when no issues exist."""
        mock_report = SecurityReport(
            project_dir=str(temp_dir), timestamp=datetime.now().isoformat()
        )
        mock_run_full_audit.return_value = mock_report

        has_issues = has_critical_security_issues(temp_dir)

        assert has_issues is False


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_project_scan(self, agent, temp_dir):
        """Test scanning an empty project directory."""
        findings = agent._scan_auth_patterns(temp_dir)

        assert isinstance(findings, list)
        assert len(findings) == 0

    def test_nonexistent_directory(self, agent):
        """Test handling non-existent directory."""
        fake_dir = Path("/nonexistent/path")

        findings = agent._scan_auth_patterns(fake_dir)

        assert isinstance(findings, list)
        assert len(findings) == 0

    def test_report_with_no_findings(self, temp_dir):
        """Test report generation with no findings."""
        report = SecurityReport(
            project_dir=str(temp_dir), timestamp=datetime.now().isoformat()
        )

        assert report.has_blocking_issues() is False
        assert len(report.get_critical_findings()) == 0
        assert report.summary_counts["total"] == 0

    def test_report_markdown_with_empty_recommendations(self, temp_dir):
        """Test markdown generation with no recommendations."""
        report = SecurityReport(
            project_dir=str(temp_dir), timestamp=datetime.now().isoformat()
        )

        markdown = report.to_markdown()

        assert isinstance(markdown, str)
        assert "# Security Audit Report" in markdown

    def test_file_with_unicode_errors(self, agent, temp_dir):
        """Test handling files with unicode decode errors."""
        # Create a binary file that can't be decoded as text
        binary_file = temp_dir / "binary.py"
        binary_file.write_bytes(b"\x80\x81\x82\x83")

        # Should not crash
        findings = agent._scan_auth_patterns(temp_dir)
        assert isinstance(findings, list)

    def test_detect_auth_mechanisms_no_files(self, agent, temp_dir):
        """Test auth mechanism detection with no relevant files."""
        mechanisms = agent._detect_auth_mechanisms(temp_dir)

        assert isinstance(mechanisms, list)
        assert "No auth mechanisms detected" in mechanisms
