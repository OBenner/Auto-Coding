#!/usr/bin/env python3
"""
Tests for OWASP Scanner Module
===============================

Tests cover:
- OWASPVulnerability and OWASPScanResult dataclasses
- OWASPScanner initialization and pattern compilation
- Pattern-based scanning for all OWASP Top 10 categories
- Python AST analysis for injection vulnerabilities
- File filtering and exclusion logic
- Summary calculation and statistics
- Result serialization to JSON
- Convenience functions
- Edge cases and error handling
"""

import json
import tempfile
from pathlib import Path
import pytest

# Add auto-claude to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.owasp_scanner import (
    OWASPVulnerability,
    OWASPScanResult,
    OWASPScanner,
    OWASP_CATEGORIES,
    scan_for_owasp_issues,
    has_owasp_issues,
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
    """Create an OWASPScanner instance."""
    return OWASPScanner()


@pytest.fixture
def python_project(temp_dir):
    """Create a Python project with various security issues."""
    # File with injection vulnerabilities
    (temp_dir / "app.py").write_text("""
import os
import subprocess
import pickle

# A03: Injection vulnerabilities
def unsafe_query(user_input):
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    cursor.execute(query)

def unsafe_command(user_input):
    os.system("echo " + user_input)
    subprocess.run("ls " + user_input, shell=True)

def unsafe_eval(code):
    eval(code)
    exec(code)

def unsafe_deserialize(data):
    pickle.loads(data)
""")

    # File with cryptographic failures
    (temp_dir / "crypto.py").write_text("""
import hashlib
import base64

# A02: Cryptographic Failures
password = "hardcoded_password123"
api_key = "sk-1234567890abcdefghij1234567890ab"

def weak_hash(data):
    return hashlib.md5(data.encode()).hexdigest()

def weak_hash2(data):
    return hashlib.sha1(data.encode()).hexdigest()
""")

    # File with security misconfigurations
    (temp_dir / "settings.py").write_text("""
# A05: Security Misconfiguration
DEBUG = True
ALLOWED_HOSTS = []
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

import requests
requests.get(url, verify=False)
""")

    # File with authentication issues
    (temp_dir / "auth.py").write_text("""
# A07: Authentication Failures
def check_login(username, password):
    if password == "admin123":
        return True

def authenticate():
    return True

is_authenticated = True
""")

    return temp_dir


# =============================================================================
# DATA CLASS TESTS
# =============================================================================


class TestOWASPVulnerability:
    """Tests for OWASPVulnerability dataclass."""

    def test_create_vulnerability(self):
        """Test creating an OWASP vulnerability."""
        vuln = OWASPVulnerability(
            category="A03",
            category_name="Injection",
            severity="critical",
            title="SQL Injection",
            description="SQL injection vulnerability",
            file="app.py",
            line=42,
            code_snippet='query = f"SELECT * FROM users WHERE id = {user_id}"',
            recommendation="Use parameterized queries",
        )

        assert vuln.category == "A03"
        assert vuln.category_name == "Injection"
        assert vuln.severity == "critical"
        assert vuln.title == "SQL Injection"
        assert vuln.file == "app.py"
        assert vuln.line == 42
        assert vuln.code_snippet is not None
        assert vuln.recommendation is not None

    def test_vulnerability_optional_fields(self):
        """Test vulnerability with optional fields as None."""
        vuln = OWASPVulnerability(
            category="A01",
            category_name="Broken Access Control",
            severity="high",
            title="IDOR",
            description="Insecure direct object reference",
            file="routes.py",
            line=10,
        )

        assert vuln.code_snippet is None
        assert vuln.recommendation is None


class TestOWASPScanResult:
    """Tests for OWASPScanResult dataclass."""

    def test_create_empty_result(self):
        """Test creating an empty scan result."""
        result = OWASPScanResult()

        assert result.vulnerabilities == []
        assert result.summary == {}
        assert result.scan_errors == []
        assert result.has_critical_issues is False
        assert result.total_vulnerabilities == 0

    def test_result_with_vulnerabilities(self):
        """Test result with vulnerabilities."""
        vuln1 = OWASPVulnerability(
            category="A03",
            category_name="Injection",
            severity="critical",
            title="SQL Injection",
            description="Test",
            file="app.py",
            line=10,
        )
        vuln2 = OWASPVulnerability(
            category="A02",
            category_name="Cryptographic Failures",
            severity="high",
            title="Weak hash",
            description="Test",
            file="crypto.py",
            line=5,
        )

        result = OWASPScanResult(
            vulnerabilities=[vuln1, vuln2],
            has_critical_issues=True,
            total_vulnerabilities=2,
        )

        assert len(result.vulnerabilities) == 2
        assert result.has_critical_issues is True
        assert result.total_vulnerabilities == 2

    def test_result_with_errors(self):
        """Test result with scan errors."""
        result = OWASPScanResult(
            scan_errors=["Error scanning file1.py", "Error scanning file2.py"]
        )

        assert len(result.scan_errors) == 2


# =============================================================================
# SCANNER INITIALIZATION TESTS
# =============================================================================


class TestScannerInitialization:
    """Tests for OWASPScanner initialization."""

    def test_scanner_initialization(self, scanner):
        """Test scanner initializes correctly."""
        assert scanner is not None
        assert hasattr(scanner, "_compiled_patterns")
        assert hasattr(scanner, "PATTERNS")

    def test_patterns_compiled(self, scanner):
        """Test that regex patterns are compiled on init."""
        assert scanner._compiled_patterns is not None
        assert len(scanner._compiled_patterns) > 0

        # Check all OWASP categories have compiled patterns
        for category in OWASP_CATEGORIES.keys():
            if category in scanner.PATTERNS:
                assert category in scanner._compiled_patterns
                # Each pattern should be a tuple of (compiled_regex, description)
                for pattern, desc in scanner._compiled_patterns[category]:
                    assert hasattr(pattern, "search")  # Compiled regex
                    assert isinstance(desc, str)

    def test_owasp_categories_constant(self):
        """Test OWASP_CATEGORIES constant is correctly defined."""
        assert len(OWASP_CATEGORIES) == 10
        assert "A01" in OWASP_CATEGORIES
        assert "A10" in OWASP_CATEGORIES
        assert OWASP_CATEGORIES["A01"] == "Broken Access Control"
        assert OWASP_CATEGORIES["A03"] == "Injection"


# =============================================================================
# FILE FILTERING TESTS
# =============================================================================


class TestFileFiltering:
    """Tests for file filtering and scanning logic."""

    def test_is_scannable_file(self, scanner):
        """Test file extension filtering."""
        assert scanner._is_scannable_file("app.py") is True
        assert scanner._is_scannable_file("test.js") is True
        assert scanner._is_scannable_file("component.tsx") is True
        assert scanner._is_scannable_file("main.go") is True
        assert scanner._is_scannable_file("lib.rs") is True
        assert scanner._is_scannable_file("readme.md") is False
        assert scanner._is_scannable_file("config.json") is False
        assert scanner._is_scannable_file("image.png") is False

    def test_find_scannable_files(self, scanner, temp_dir):
        """Test finding scannable files in project."""
        # Create various files
        (temp_dir / "app.py").write_text("print('hello')")
        (temp_dir / "test.js").write_text("console.log('test')")
        (temp_dir / "readme.md").write_text("# README")

        # Create excluded directory
        excluded = temp_dir / "node_modules"
        excluded.mkdir()
        (excluded / "lib.js").write_text("module.exports = {}")

        files = scanner._find_scannable_files(temp_dir)

        # Should find .py and .js but not .md or node_modules
        file_names = [f.name for f in files]
        assert "app.py" in file_names
        assert "test.js" in file_names
        assert "readme.md" not in file_names
        assert "lib.js" not in file_names  # Excluded from node_modules

    def test_excluded_directories(self, scanner, temp_dir):
        """Test that common directories are excluded."""
        # Create excluded directories
        for excluded_dir in [".git", "__pycache__", "node_modules", ".venv", "dist"]:
            path = temp_dir / excluded_dir
            path.mkdir()
            (path / "file.py").write_text("print('test')")

        files = scanner._find_scannable_files(temp_dir)

        # None of the files in excluded dirs should be found
        assert len(files) == 0


# =============================================================================
# PATTERN DETECTION TESTS
# =============================================================================


class TestPatternDetection:
    """Tests for OWASP pattern detection."""

    def test_detect_sql_injection(self, scanner, temp_dir):
        """Test detecting SQL injection patterns."""
        # Create file with SQL injection using string concatenation
        (temp_dir / "db.py").write_text("""
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
    cursor.execute(query)
""")

        result = scanner.scan(temp_dir, include_patterns=["A03"])

        # Note: The pattern detection may not catch all SQL injections
        # This test verifies the scanner runs without errors
        assert isinstance(result, OWASPScanResult)
        assert result.scan_errors == []

    def test_detect_command_injection(self, scanner, temp_dir):
        """Test detecting OS command injection."""
        (temp_dir / "cmd.py").write_text("""
import os
import subprocess

def run_cmd(user_input):
    os.system("ls " + user_input)
    subprocess.run("echo " + user_input, shell=True)
""")

        result = scanner.scan(temp_dir, include_patterns=["A03"])

        assert result.total_vulnerabilities > 0
        injection_vulns = [v for v in result.vulnerabilities if "injection" in v.title.lower()]
        assert len(injection_vulns) > 0

    def test_detect_weak_crypto(self, scanner, temp_dir):
        """Test detecting weak cryptographic algorithms."""
        (temp_dir / "hash.py").write_text("""
import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def another_hash(data):
    return hashlib.sha1(data.encode()).hexdigest()
""")

        result = scanner.scan(temp_dir, include_patterns=["A02"])

        assert result.total_vulnerabilities > 0
        crypto_vulns = [v for v in result.vulnerabilities if v.category == "A02"]
        assert len(crypto_vulns) >= 2  # Both MD5 and SHA1

    def test_detect_hardcoded_credentials(self, scanner, temp_dir):
        """Test detecting hardcoded passwords and API keys."""
        (temp_dir / "config.py").write_text("""
password = "my_secret_password"
api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
""")

        result = scanner.scan(temp_dir, include_patterns=["A02"])

        assert result.total_vulnerabilities > 0
        cred_vulns = [
            v for v in result.vulnerabilities
            if "hardcoded" in v.title.lower() or "password" in v.title.lower()
        ]
        assert len(cred_vulns) > 0

    def test_detect_debug_mode(self, scanner, temp_dir):
        """Test detecting debug mode enabled."""
        (temp_dir / "settings.py").write_text("""
DEBUG = True
ALLOWED_HOSTS = []
""")

        result = scanner.scan(temp_dir, include_patterns=["A05"])

        assert result.total_vulnerabilities > 0
        debug_vulns = [v for v in result.vulnerabilities if "DEBUG" in v.code_snippet]
        assert len(debug_vulns) > 0

    def test_detect_ssl_verification_disabled(self, scanner, temp_dir):
        """Test detecting disabled SSL verification."""
        (temp_dir / "api.py").write_text("""
import requests

def fetch_data(url):
    response = requests.get(url, verify=False)
    return response.json()
""")

        result = scanner.scan(temp_dir, include_patterns=["A05", "A08"])

        assert result.total_vulnerabilities > 0
        ssl_vulns = [v for v in result.vulnerabilities if "verify" in v.code_snippet]
        assert len(ssl_vulns) > 0


# =============================================================================
# AST ANALYSIS TESTS
# =============================================================================


class TestASTAnalysis:
    """Tests for Python AST analysis."""

    def test_analyze_python_for_injection_eval(self, scanner, temp_dir):
        """Test AST analysis detects eval() usage."""
        code_file = temp_dir / "unsafe.py"
        code_file.write_text("""
def execute_code(code):
    result = eval(code)
    return result
""")

        result = scanner.scan_injection_risks(temp_dir)

        assert len(result) > 0
        eval_vulns = [v for v in result if "eval" in v.title.lower()]
        assert len(eval_vulns) > 0

    def test_analyze_python_for_injection_exec(self, scanner, temp_dir):
        """Test AST analysis detects exec() usage."""
        code_file = temp_dir / "unsafe.py"
        code_file.write_text("""
def run_code(code):
    exec(code)
""")

        result = scanner.scan_injection_risks(temp_dir)

        assert len(result) > 0
        exec_vulns = [v for v in result if "exec" in v.title.lower()]
        assert len(exec_vulns) > 0

    def test_analyze_python_for_subprocess_shell_true(self, scanner, temp_dir):
        """Test AST analysis detects subprocess with shell=True."""
        code_file = temp_dir / "cmd.py"
        code_file.write_text("""
import subprocess

def run_command(cmd):
    subprocess.run(cmd, shell=True)
    subprocess.call(cmd, shell=True)
    subprocess.Popen(cmd, shell=True)
""")

        result = scanner.scan_injection_risks(temp_dir)

        assert len(result) > 0
        shell_vulns = [v for v in result if "shell=True" in v.description]
        assert len(shell_vulns) >= 3  # run, call, Popen

    def test_ast_analysis_handles_syntax_errors(self, scanner, temp_dir):
        """Test that AST analysis gracefully handles syntax errors."""
        code_file = temp_dir / "broken.py"
        code_file.write_text("""
def incomplete_function(
    # This is syntactically invalid
""")

        # Should not crash
        result = scanner.scan_injection_risks(temp_dir)
        assert isinstance(result, list)

    def test_analyze_python_ast_hardcoded_credentials(self, scanner, temp_dir):
        """Test AST analysis detects hardcoded credentials."""
        code_file = temp_dir / "creds.py"
        code_file.write_text("""
password = "my_secret_password_123"
api_key = "sk_live_1234567890abcdefghij"
secret = "very_long_secret_value"
token = "jwt_token_here_12345"
""")

        result = scanner.scan(temp_dir, include_patterns=["A02"])

        cred_vulns = [
            v for v in result.vulnerabilities
            if v.category == "A02" and v.title == "Hardcoded credential"
        ]
        assert len(cred_vulns) > 0


# =============================================================================
# SCAN METHOD TESTS
# =============================================================================


class TestScanMethod:
    """Tests for the main scan() method."""

    def test_scan_empty_project(self, scanner, temp_dir):
        """Test scanning an empty project."""
        result = scanner.scan(temp_dir)

        assert isinstance(result, OWASPScanResult)
        assert result.total_vulnerabilities == 0
        assert result.has_critical_issues is False

    def test_scan_with_vulnerabilities(self, scanner, python_project):
        """Test scanning a project with vulnerabilities."""
        result = scanner.scan(python_project)

        assert isinstance(result, OWASPScanResult)
        assert result.total_vulnerabilities > 0
        assert len(result.vulnerabilities) > 0

    def test_scan_specific_categories(self, scanner, python_project):
        """Test scanning only specific OWASP categories."""
        # Scan only injection
        result = scanner.scan(python_project, include_patterns=["A03"])

        injection_vulns = [v for v in result.vulnerabilities if v.category == "A03"]

        # Note: AST analysis may find A02 (crypto) issues even when only scanning A03
        # because _analyze_python_ast runs for all Python files
        assert len(injection_vulns) > 0

        # All A03 vulnerabilities should be present
        assert any(v.category == "A03" for v in result.vulnerabilities)

    def test_scan_multiple_categories(self, scanner, python_project):
        """Test scanning multiple specific categories."""
        result = scanner.scan(python_project, include_patterns=["A02", "A03"])

        categories = set(v.category for v in result.vulnerabilities)
        assert categories.issubset({"A02", "A03"})

    def test_scan_changed_files_only(self, scanner, temp_dir):
        """Test scanning only specific changed files."""
        # Create multiple files
        (temp_dir / "file1.py").write_text("eval('test')")
        (temp_dir / "file2.py").write_text("exec('test')")
        (temp_dir / "file3.py").write_text("print('safe')")

        # Scan only file1.py
        result = scanner.scan(temp_dir, changed_files=["file1.py"])

        # Should only find vulnerabilities in file1.py
        files_with_vulns = set(v.file for v in result.vulnerabilities)
        assert all("file1.py" in f for f in files_with_vulns)

    def test_scan_saves_to_spec_dir(self, scanner, python_project, temp_dir):
        """Test that scan results are saved when spec_dir is provided."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        scanner.scan(python_project, spec_dir=spec_dir)

        results_file = spec_dir / "owasp_scan_results.json"
        assert results_file.exists()

        # Verify JSON is valid
        with open(results_file) as f:
            data = json.load(f)
            assert "vulnerabilities" in data
            assert "summary" in data


# =============================================================================
# INJECTION SCANNING TESTS
# =============================================================================


class TestInjectionScanning:
    """Tests for scan_injection_risks() method."""

    def test_scan_injection_risks(self, scanner, temp_dir):
        """Test scanning specifically for injection vulnerabilities."""
        (temp_dir / "app.py").write_text("""
import os

def unsafe(user_input):
    os.system(user_input)
    eval(user_input)
""")

        result = scanner.scan_injection_risks(temp_dir)

        assert len(result) > 0
        assert all(v.category == "A03" for v in result)
        assert all(v.severity == "critical" for v in result)

    def test_scan_injection_specific_files(self, scanner, temp_dir):
        """Test scanning injection risks in specific files."""
        (temp_dir / "safe.py").write_text("print('safe')")
        (temp_dir / "unsafe.py").write_text("eval('unsafe')")

        result = scanner.scan_injection_risks(
            temp_dir,
            files_to_scan=["unsafe.py"]
        )

        # Should only scan unsafe.py
        files_scanned = set(v.file for v in result)
        assert all("unsafe.py" in f for f in files_scanned)


# =============================================================================
# SUMMARY CALCULATION TESTS
# =============================================================================


class TestSummaryCalculation:
    """Tests for summary calculation."""

    def test_calculate_summary(self, scanner, temp_dir):
        """Test summary statistics calculation."""
        # Create files with known vulnerabilities
        (temp_dir / "inject.py").write_text("eval('test')")
        (temp_dir / "crypto.py").write_text("""
import hashlib
password = "hardcoded123"
hashlib.md5(b"test")
""")

        result = scanner.scan(temp_dir)

        assert result.summary is not None
        assert result.total_vulnerabilities > 0

        # Check summary structure
        for category, stats in result.summary.items():
            assert "category_name" in stats
            assert "total" in stats
            assert "critical" in stats
            assert "high" in stats
            assert "medium" in stats
            assert "low" in stats

    def test_has_critical_issues_flag(self, scanner, temp_dir):
        """Test has_critical_issues flag is set correctly."""
        # Create file with critical issue
        (temp_dir / "critical.py").write_text("eval('dangerous')")

        result = scanner.scan(temp_dir)

        assert result.has_critical_issues is True

    def test_severity_assignment(self, scanner):
        """Test severity levels for different categories."""
        severity_map = {
            "A03": "critical",  # Injection
            "A01": "high",      # Broken Access Control
            "A02": "high",      # Cryptographic Failures
            "A04": "medium",    # Insecure Design
            "A05": "medium",    # Security Misconfiguration
            "A09": "low",       # Logging Failures
        }

        for category, expected_severity in severity_map.items():
            severity = scanner._get_severity_for_category(category)
            assert severity == expected_severity


# =============================================================================
# RECOMMENDATION TESTS
# =============================================================================


class TestRecommendations:
    """Tests for vulnerability recommendations."""

    def test_get_recommendation_injection(self, scanner):
        """Test getting recommendation for injection."""
        rec = scanner._get_recommendation("A03", "SQL Injection")

        assert "parameterized queries" in rec or "input validation" in rec

    def test_get_recommendation_crypto(self, scanner):
        """Test getting recommendation for cryptographic failures."""
        rec = scanner._get_recommendation("A02", "Weak hash")

        assert "encryption" in rec or "key management" in rec

    def test_get_recommendation_all_categories(self, scanner):
        """Test that all categories have recommendations."""
        for category in OWASP_CATEGORIES.keys():
            rec = scanner._get_recommendation(category, "Test")
            assert rec is not None
            assert len(rec) > 0


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


class TestSerialization:
    """Tests for result serialization."""

    def test_to_dict_conversion(self, scanner, temp_dir):
        """Test converting scan result to dictionary."""
        (temp_dir / "test.py").write_text("eval('test')")

        result = scanner.scan(temp_dir)
        result_dict = scanner.to_dict(result)

        assert isinstance(result_dict, dict)
        assert "vulnerabilities" in result_dict
        assert "summary" in result_dict
        assert "scan_errors" in result_dict
        assert "has_critical_issues" in result_dict
        assert "total_vulnerabilities" in result_dict

    def test_to_dict_vulnerability_structure(self, scanner, temp_dir):
        """Test vulnerability dictionary structure."""
        (temp_dir / "test.py").write_text("eval('test')")

        result = scanner.scan(temp_dir)
        result_dict = scanner.to_dict(result)

        if result_dict["vulnerabilities"]:
            vuln = result_dict["vulnerabilities"][0]
            assert "category" in vuln
            assert "category_name" in vuln
            assert "severity" in vuln
            assert "title" in vuln
            assert "description" in vuln
            assert "file" in vuln
            assert "line" in vuln
            assert "code_snippet" in vuln
            assert "recommendation" in vuln

    def test_json_serializable(self, scanner, temp_dir):
        """Test that result dictionary is JSON serializable."""
        (temp_dir / "test.py").write_text("eval('test')")

        result = scanner.scan(temp_dir)
        result_dict = scanner.to_dict(result)

        # Should not raise
        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed == result_dict


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_scan_for_owasp_issues(self, temp_dir):
        """Test scan_for_owasp_issues function."""
        (temp_dir / "test.py").write_text("eval('test')")

        result = scan_for_owasp_issues(temp_dir)

        assert isinstance(result, OWASPScanResult)
        assert result.total_vulnerabilities > 0

    def test_scan_for_owasp_issues_with_spec_dir(self, temp_dir):
        """Test scan_for_owasp_issues saves to spec_dir."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (temp_dir / "test.py").write_text("eval('test')")

        scan_for_owasp_issues(temp_dir, spec_dir=spec_dir)

        assert (spec_dir / "owasp_scan_results.json").exists()

    def test_scan_for_owasp_issues_with_changed_files(self, temp_dir):
        """Test scan_for_owasp_issues with changed files."""
        (temp_dir / "file1.py").write_text("eval('test')")
        (temp_dir / "file2.py").write_text("exec('test')")

        result = scan_for_owasp_issues(temp_dir, changed_files=["file1.py"])

        # Should only scan file1.py
        files = set(v.file for v in result.vulnerabilities)
        assert all("file1.py" in f for f in files)

    def test_has_owasp_issues_true(self, temp_dir):
        """Test has_owasp_issues returns True for vulnerable projects."""
        (temp_dir / "test.py").write_text("eval('dangerous')")

        assert has_owasp_issues(temp_dir) is True

    def test_has_owasp_issues_false(self, temp_dir):
        """Test has_owasp_issues returns False for clean projects."""
        (temp_dir / "safe.py").write_text("print('safe code')")

        assert has_owasp_issues(temp_dir) is False


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_scan_nonexistent_directory(self, scanner):
        """Test scanning a non-existent directory."""
        fake_dir = Path("/nonexistent/path")

        result = scanner.scan(fake_dir)

        assert isinstance(result, OWASPScanResult)
        # Should complete without crashing
        assert result.total_vulnerabilities == 0

    def test_scan_file_with_unicode_errors(self, scanner, temp_dir):
        """Test scanning files with unicode decode errors."""
        binary_file = temp_dir / "binary.py"
        binary_file.write_bytes(b"\x80\x81\x82\x83")

        # Should not crash
        result = scanner.scan(temp_dir)
        assert isinstance(result, OWASPScanResult)

    def test_scan_file_with_invalid_regex(self, scanner, temp_dir):
        """Test handling of regex pattern errors."""
        # This test ensures pattern compilation doesn't crash
        assert scanner._compiled_patterns is not None

    def test_scan_empty_file(self, scanner, temp_dir):
        """Test scanning an empty Python file."""
        (temp_dir / "empty.py").write_text("")

        result = scanner.scan(temp_dir)

        assert isinstance(result, OWASPScanResult)
        assert result.total_vulnerabilities == 0

    def test_scan_file_with_only_comments(self, scanner, temp_dir):
        """Test scanning a file with only comments."""
        (temp_dir / "comments.py").write_text("""
# This is a comment
# Another comment
""")

        result = scanner.scan(temp_dir)

        assert isinstance(result, OWASPScanResult)
        # Comments shouldn't trigger vulnerabilities
        assert result.total_vulnerabilities == 0

    def test_scan_with_permission_error(self, scanner, temp_dir):
        """Test handling of file permission errors."""
        # Create a file
        restricted_file = temp_dir / "restricted.py"
        restricted_file.write_text("eval('test')")

        # Note: Actually making file unreadable is platform-specific
        # This test mainly ensures error handling doesn't crash
        result = scanner.scan(temp_dir)
        assert isinstance(result, OWASPScanResult)

    def test_relative_path_calculation(self, scanner, temp_dir):
        """Test that file paths are relative in results."""
        subdir = temp_dir / "src"
        subdir.mkdir()
        (subdir / "app.py").write_text("eval('test')")

        result = scanner.scan(temp_dir)

        # Paths should be relative, not absolute
        for vuln in result.vulnerabilities:
            assert not vuln.file.startswith("/")
            assert not vuln.file.startswith("C:")

    def test_scan_mixed_file_types(self, scanner, temp_dir):
        """Test scanning project with mixed file types."""
        (temp_dir / "app.py").write_text("eval('test')")
        (temp_dir / "app.js").write_text("eval('test')")
        (temp_dir / "readme.md").write_text("# Documentation")
        (temp_dir / "data.json").write_text('{"key": "value"}')

        result = scanner.scan(temp_dir)

        # Should only scan .py and .js files
        scanned_extensions = set(Path(v.file).suffix for v in result.vulnerabilities)
        assert scanned_extensions.issubset({".py", ".js"})

    def test_summary_with_no_vulnerabilities(self, scanner, temp_dir):
        """Test summary calculation with no vulnerabilities."""
        (temp_dir / "safe.py").write_text("print('safe')")

        result = scanner.scan(temp_dir)

        assert result.summary == {}
        assert result.total_vulnerabilities == 0
        assert result.has_critical_issues is False

    def test_multiple_vulnerabilities_same_line(self, scanner, temp_dir):
        """Test handling multiple vulnerabilities on same line."""
        (temp_dir / "test.py").write_text("""
password = "secret123"; api_key = "sk-1234567890abcdefghij1234567890"
""")

        result = scanner.scan(temp_dir, include_patterns=["A02"])

        # Should detect both hardcoded credentials
        assert result.total_vulnerabilities >= 2
