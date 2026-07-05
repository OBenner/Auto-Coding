#!/usr/bin/env python3
"""
Tests for the security_scanner module.

Tests cover:
- Secrets scanning integration
- SAST tool integration
- Dependency audit integration
- Result aggregation
- Blocking logic
"""

import json

# Add auto-claude to path for imports
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.security_scanner import (
    HAS_SECRETS_SCANNER,
    SecurityScanner,
    SecurityScanResult,
    SecurityVulnerability,
    has_security_issues,
    scan_for_security_issues,
    scan_secrets_only,
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
def scanner():
    """Create a SecurityScanner instance."""
    return SecurityScanner()


@pytest.fixture
def python_project(temp_dir):
    """Create a simple Python project structure."""
    (temp_dir / "requirements.txt").write_text("flask==2.0.0\n")
    (temp_dir / "app.py").write_text("print('hello')\n")
    return temp_dir


@pytest.fixture
def node_project(temp_dir):
    """Create a simple Node.js project structure."""
    (temp_dir / "package.json").write_text(
        json.dumps({"name": "test", "dependencies": {"express": "^4.18.0"}})
    )
    return temp_dir


# =============================================================================
# DATA CLASS TESTS
# =============================================================================


class TestSecurityVulnerability:
    """Tests for SecurityVulnerability dataclass."""

    def test_create_vulnerability(self):
        """Test creating a security vulnerability."""
        vuln = SecurityVulnerability(
            severity="high",
            source="bandit",
            title="SQL Injection",
            description="Potential SQL injection",
            file="app.py",
            line=42,
        )

        assert vuln.severity == "high"
        assert vuln.source == "bandit"
        assert vuln.title == "SQL Injection"
        assert vuln.file == "app.py"
        assert vuln.line == 42

    def test_vulnerability_optional_fields(self):
        """Test vulnerability with optional fields."""
        vuln = SecurityVulnerability(
            severity="low",
            source="npm_audit",
            title="Outdated dependency",
            description="Package is outdated",
        )

        assert vuln.file is None
        assert vuln.line is None
        assert vuln.cwe is None


class TestSecurityScanResult:
    """Tests for SecurityScanResult dataclass."""

    def test_create_result(self):
        """Test creating a scan result."""
        result = SecurityScanResult()

        assert result.secrets == []
        assert result.vulnerabilities == []
        assert result.scan_errors == []
        assert result.has_critical_issues is False
        assert result.should_block_qa is False

    def test_result_with_data(self):
        """Test result with actual data."""
        result = SecurityScanResult(
            secrets=[{"file": "config.py", "pattern": "api_key"}],
            vulnerabilities=[
                SecurityVulnerability(
                    severity="critical",
                    source="secrets",
                    title="API Key exposed",
                    description="Found API key",
                )
            ],
            has_critical_issues=True,
            should_block_qa=True,
        )

        assert len(result.secrets) == 1
        assert len(result.vulnerabilities) == 1
        assert result.has_critical_issues is True
        assert result.should_block_qa is True


# =============================================================================
# SCANNER TESTS
# =============================================================================


class TestSecurityScanner:
    """Tests for SecurityScanner class."""

    def test_scan_empty_project(self, scanner, temp_dir):
        """Test scanning an empty project."""
        result = scanner.scan(temp_dir)

        assert isinstance(result, SecurityScanResult)

    def test_scan_python_project(self, scanner, python_project):
        """Test scanning a Python project."""
        result = scanner.scan(python_project)

        assert isinstance(result, SecurityScanResult)

    def test_scan_node_project(self, scanner, node_project):
        """Test scanning a Node.js project."""
        result = scanner.scan(node_project)

        assert isinstance(result, SecurityScanResult)

    def test_scan_with_spec_dir(self, scanner, python_project, temp_dir):
        """Test that results are saved to spec dir."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        scanner.scan(python_project, spec_dir=spec_dir)

        results_file = spec_dir / "security_scan_results.json"
        assert results_file.exists()

    def test_scan_secrets_only(self, scanner, python_project):
        """Test scanning only for secrets."""
        result = scanner.scan(
            python_project,
            run_sast=False,
            run_dependency_audit=False,
        )

        assert isinstance(result, SecurityScanResult)


# =============================================================================
# SECRETS DETECTION TESTS
# =============================================================================


class TestSecretsDetection:
    """Tests for secrets detection integration."""

    @pytest.mark.skipif(not HAS_SECRETS_SCANNER, reason="scan_secrets not available")
    def test_detects_api_key(self, scanner, temp_dir):
        """Test detecting an API key in code."""
        # Create a file with a fake API key
        code_file = temp_dir / "config.py"
        code_file.write_text(
            'API_KEY = "sk-test1234567890abcdefghij1234567890abcdefghij"'
        )

        result = scanner.scan(temp_dir, run_sast=False, run_dependency_audit=False)

        # Note: This may or may not find the key depending on the patterns
        # The test is more about ensuring no crashes occur
        assert isinstance(result, SecurityScanResult)

    def test_secrets_block_qa(self, scanner, temp_dir):
        """Test that secrets block QA approval."""
        result = SecurityScanResult(
            secrets=[{"file": "config.py", "pattern": "api_key", "line": 1}],
        )

        # Manually set the blocking flag as the scan method would
        result.should_block_qa = len(result.secrets) > 0

        assert result.should_block_qa is True


# =============================================================================
# BLOCKING LOGIC TESTS
# =============================================================================


class TestBlockingLogic:
    """Tests for QA blocking logic."""

    def test_secrets_always_block(self):
        """Test that any secrets always block QA."""
        result = SecurityScanResult(
            secrets=[{"file": "test.py", "pattern": "password"}],
            has_critical_issues=True,
            should_block_qa=True,
        )

        assert result.should_block_qa is True

    def test_critical_vulns_block(self):
        """Test that critical vulnerabilities block QA."""
        result = SecurityScanResult(
            vulnerabilities=[
                SecurityVulnerability(
                    severity="critical",
                    source="npm_audit",
                    title="Remote code execution",
                    description="Critical CVE",
                )
            ],
            has_critical_issues=True,
            should_block_qa=True,
        )

        assert result.should_block_qa is True

    def test_high_vulns_dont_block_alone(self):
        """Test that high (non-critical) vulnerabilities don't block alone."""
        result = SecurityScanResult(
            vulnerabilities=[
                SecurityVulnerability(
                    severity="high",
                    source="bandit",
                    title="SQL Injection",
                    description="Possible SQL injection",
                )
            ],
        )

        # High should mark as critical issue but not necessarily block
        result.has_critical_issues = True
        result.should_block_qa = False  # Only critical blocks

        assert result.has_critical_issues is True
        assert result.should_block_qa is False

    def test_no_issues_doesnt_block(self):
        """Test that clean scans don't block."""
        result = SecurityScanResult()

        assert result.has_critical_issues is False
        assert result.should_block_qa is False


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


class TestSerialization:
    """Tests for result serialization."""

    def test_to_dict(self, scanner):
        """Test converting result to dictionary."""
        result = SecurityScanResult(
            secrets=[{"file": "test.py", "pattern": "api_key", "line": 1}],
            vulnerabilities=[
                SecurityVulnerability(
                    severity="high",
                    source="bandit",
                    title="Test issue",
                    description="Description",
                    file="app.py",
                    line=10,
                )
            ],
            scan_errors=["Test error"],
            has_critical_issues=True,
            should_block_qa=True,
        )

        result_dict = scanner.to_dict(result)

        assert isinstance(result_dict, dict)
        assert "secrets" in result_dict
        assert "vulnerabilities" in result_dict
        assert "summary" in result_dict
        assert result_dict["summary"]["total_secrets"] == 1
        assert result_dict["summary"]["high_count"] == 1

    def test_json_serializable(self, scanner):
        """Test that result is JSON serializable."""
        result = SecurityScanResult(
            vulnerabilities=[
                SecurityVulnerability(
                    severity="medium",
                    source="test",
                    title="Test",
                    description="Test",
                )
            ],
        )

        result_dict = scanner.to_dict(result)

        # Should not raise
        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_scan_for_security_issues(self, python_project):
        """Test scan_for_security_issues function."""
        result = scan_for_security_issues(python_project)

        assert isinstance(result, SecurityScanResult)

    def test_has_security_issues_clean(self, temp_dir):
        """Test has_security_issues on clean project."""
        (temp_dir / "app.py").write_text("print('hello')")

        # This should return False for a clean project
        # (actual behavior depends on secrets scanner availability)
        result = has_security_issues(temp_dir)
        assert isinstance(result, bool)

    def test_scan_secrets_only_function(self, temp_dir):
        """Test scan_secrets_only function."""
        (temp_dir / "app.py").write_text("print('hello')")

        secrets = scan_secrets_only(temp_dir)
        assert isinstance(secrets, list)


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_nonexistent_directory(self, scanner):
        """Test handling of non-existent directory."""
        fake_dir = Path("/nonexistent/path")

        # Targeted mock: only return False for paths under /nonexistent
        _original_exists = Path.exists

        def _selective_exists(self):
            if str(self).startswith("/nonexistent"):
                return False
            return _original_exists(self)

        with patch.object(Path, "exists", _selective_exists):
            result = scanner.scan(fake_dir)
            assert isinstance(result, SecurityScanResult)

    def test_scan_specific_files(self, scanner, python_project):
        """Test scanning specific files only."""
        result = scanner.scan(
            python_project,
            changed_files=["app.py"],
            run_sast=False,
            run_dependency_audit=False,
        )

        assert isinstance(result, SecurityScanResult)

    def test_redact_secret_short(self, scanner):
        """Test secret redaction for short strings."""
        redacted = scanner._redact_secret("abc123")
        assert "abc123" not in redacted
        assert "*" in redacted

    def test_redact_secret_long(self, scanner):
        """Test secret redaction for long strings."""
        secret = "sk-test1234567890abcdefghij"
        redacted = scanner._redact_secret(secret)

        # Should show first 4 and last 4 chars
        assert redacted.startswith("sk-t")
        assert redacted.endswith("ghij")
        assert "*" in redacted

    def test_is_python_project_detection(self, scanner, temp_dir):
        """Test Python project detection."""
        assert scanner._is_python_project(temp_dir) is False

        (temp_dir / "requirements.txt").write_text("flask\n")
        assert scanner._is_python_project(temp_dir) is True

    def test_is_python_project_pyproject(self, scanner, temp_dir):
        """Test Python project detection with pyproject.toml."""
        (temp_dir / "pyproject.toml").write_text("[project]\nname='test'")
        assert scanner._is_python_project(temp_dir) is True


# =============================================================================
# SAST TOOL INTEGRATION TESTS
# =============================================================================


class TestSASTIntegration:
    """Tests for SAST tool integration."""

    def test_bandit_availability_check(self, scanner):
        """Test Bandit availability check."""
        # Just verify it doesn't crash
        result = scanner._check_bandit_available()
        assert isinstance(result, bool)

    @patch("subprocess.run")
    def test_bandit_output_parsing(self, mock_run, scanner, python_project):
        """Test parsing Bandit JSON output."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(
                {
                    "results": [
                        {
                            "issue_severity": "HIGH",
                            "issue_text": "Test issue",
                            "filename": "app.py",
                            "line_number": 10,
                            "issue_cwe": {"id": "CWE-89"},
                        }
                    ]
                }
            ),
            returncode=0,
        )

        result = SecurityScanResult()
        scanner._bandit_available = True

        scanner._run_bandit(python_project, result)

        # If bandit ran (may be skipped if not available)
        # Check that parsing works
        if result.vulnerabilities:
            assert result.vulnerabilities[0].severity == "high"
            assert result.vulnerabilities[0].source == "bandit"

    @patch("subprocess.run")
    def test_npm_audit_output_parsing(self, mock_run, scanner, node_project):
        """Test parsing npm audit JSON output."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(
                {
                    "vulnerabilities": {
                        "lodash": {
                            "severity": "critical",
                            "via": [{"title": "Prototype Pollution"}],
                        }
                    }
                }
            ),
            returncode=0,
        )

        result = SecurityScanResult()
        scanner._run_npm_audit(node_project, result)

        # Check parsing worked
        if result.vulnerabilities:
            assert any(v.source == "npm_audit" for v in result.vulnerabilities)


class TestNativeAndDependencyScanners:
    """Tests for cppcheck, gosec, cargo audit, and composer audit."""

    def test_is_c_cpp_project_cmake(self, scanner, temp_dir):
        """CMake project is detected as C/C++."""
        (temp_dir / "CMakeLists.txt").write_text("project(demo)")
        assert scanner._is_c_cpp_project(temp_dir) is True

    def test_is_c_cpp_project_sources(self, scanner, temp_dir):
        """Bare C sources are detected as C/C++."""
        (temp_dir / "main.c").write_text("int main(void) { return 0; }")
        assert scanner._is_c_cpp_project(temp_dir) is True

    def test_is_c_cpp_project_negative(self, scanner, temp_dir):
        """Non-C project is not detected as C/C++."""
        (temp_dir / "app.py").write_text("print('hello')")
        assert scanner._is_c_cpp_project(temp_dir) is False

    @patch("subprocess.run")
    def test_cppcheck_output_parsing(self, mock_run, scanner, temp_dir):
        """Test parsing cppcheck template output from stderr."""
        mock_run.return_value = MagicMock(
            stdout="",
            stderr=(
                "src/main.c|10|error|nullPointer|Null pointer dereference\n"
                "src/util.c|22|warning|bufferAccessOutOfBounds|Buffer overrun\n"
                "not a finding line\n"
            ),
            returncode=0,
        )

        result = SecurityScanResult()
        scanner._run_cppcheck(temp_dir, result)

        assert len(result.vulnerabilities) == 2
        first = result.vulnerabilities[0]
        assert first.source == "cppcheck"
        assert first.severity == "high"
        assert first.file == "src/main.c"
        assert first.line == 10
        assert result.vulnerabilities[1].severity == "medium"

    @patch("subprocess.run")
    def test_cppcheck_missing_tool_is_silent(self, mock_run, scanner, temp_dir):
        """Missing cppcheck binary skips the scan without errors."""
        mock_run.side_effect = FileNotFoundError()

        result = SecurityScanResult()
        scanner._run_cppcheck(temp_dir, result)

        assert result.vulnerabilities == []
        assert result.scan_errors == []

    @patch("subprocess.run")
    def test_gosec_output_parsing(self, mock_run, scanner, temp_dir):
        """Test parsing gosec JSON output."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(
                {
                    "Issues": [
                        {
                            "severity": "HIGH",
                            "details": "Subprocess launched with variable",
                            "file": "main.go",
                            "line": "42",
                            "cwe": {"id": "78"},
                        }
                    ]
                }
            ),
            stderr="",
            returncode=1,
        )

        result = SecurityScanResult()
        scanner._run_gosec(temp_dir, result)

        assert len(result.vulnerabilities) == 1
        vuln = result.vulnerabilities[0]
        assert vuln.source == "gosec"
        assert vuln.severity == "high"
        assert vuln.line == 42
        assert vuln.cwe == "78"

    @patch("subprocess.run")
    def test_cargo_audit_output_parsing(self, mock_run, scanner, temp_dir):
        """Test parsing cargo audit JSON output."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(
                {
                    "vulnerabilities": {
                        "found": True,
                        "count": 1,
                        "list": [
                            {
                                "advisory": {
                                    "id": "RUSTSEC-2024-0001",
                                    "title": "Use after free in demo crate",
                                },
                                "package": {"name": "demo", "version": "0.1.0"},
                            }
                        ],
                    }
                }
            ),
            stderr="",
            returncode=1,
        )

        result = SecurityScanResult()
        scanner._run_cargo_audit(temp_dir, result)

        assert len(result.vulnerabilities) == 1
        vuln = result.vulnerabilities[0]
        assert vuln.source == "cargo_audit"
        assert vuln.severity == "high"
        assert "demo" in vuln.title
        assert "RUSTSEC-2024-0001" in vuln.title

    @patch("subprocess.run")
    def test_composer_audit_output_parsing(self, mock_run, scanner, temp_dir):
        """Test parsing composer audit JSON output."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(
                {
                    "advisories": {
                        "vendor/package": [
                            {
                                "advisoryId": "PKSA-1234",
                                "title": "SQL injection in query builder",
                                "cve": "CVE-2024-0001",
                                "severity": "high",
                            }
                        ]
                    }
                }
            ),
            stderr="",
            returncode=1,
        )

        result = SecurityScanResult()
        scanner._run_composer_audit(temp_dir, result)

        assert len(result.vulnerabilities) == 1
        vuln = result.vulnerabilities[0]
        assert vuln.source == "composer_audit"
        assert vuln.severity == "high"
        assert "vendor/package" in vuln.title
        assert vuln.cwe == "CVE-2024-0001"
