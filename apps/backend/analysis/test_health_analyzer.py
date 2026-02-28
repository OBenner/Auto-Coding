"""
Unit tests for health_analyzer module.

Tests cover:
- Test coverage calculation with various formats
- Health score aggregation
- Edge cases (missing files, invalid data)
- Summary generation
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from analysis.health_analyzer import (
    _calculate_agent_activity,
    _calculate_code_quality,
    _calculate_dependency_health,
    _calculate_overall_score,
    _calculate_security_score,
    _calculate_test_coverage,
    _count_test_files,
    _get_health_status,
    _load_implementation_plan,
    _load_package_json,
    _load_requirements_txt,
    _parse_cobertura_coverage,
    _parse_jest_coverage,
    _parse_python_coverage_json,
    calculate_test_coverage,
    get_health_summary,
    get_project_health,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def temp_spec_dir(tmp_path: Path) -> Path:
    """Create a temporary spec directory."""
    spec_dir = tmp_path / ".auto-claude" / "specs" / "test-spec"
    spec_dir.mkdir(parents=True)
    return spec_dir


@pytest.fixture
def sample_implementation_plan() -> dict:
    """Sample implementation plan for testing."""
    return {
        "qa_iteration_history": [
            {"iteration": 1, "status": "approved", "timestamp": "2026-02-09T10:00:00Z"},
            {"iteration": 2, "status": "approved", "timestamp": "2026-02-09T11:00:00Z"},
            {"iteration": 3, "status": "error", "timestamp": "2026-02-09T12:00:00Z"},
        ]
    }


@pytest.fixture
def sample_package_json() -> dict:
    """Sample package.json for testing."""
    return {
        "dependencies": {
            "react": "^18.0.0",
            "typescript": "^5.0.0",
        },
        "devDependencies": {
            "jest": "^29.0.0",
            "@types/react": "^18.0.0",
        },
    }


# =============================================================================
# TEST FILE LOADING
# =============================================================================


class TestLoadImplementationPlan:
    """Tests for _load_implementation_plan function."""

    def test_load_valid_plan(
        self, temp_spec_dir: Path, sample_implementation_plan: dict
    ):
        """Test loading a valid implementation plan."""
        plan_file = temp_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_implementation_plan))

        result = _load_implementation_plan(temp_spec_dir)

        assert result is not None
        assert (
            result["qa_iteration_history"]
            == sample_implementation_plan["qa_iteration_history"]
        )

    def test_load_missing_plan(self, temp_spec_dir: Path):
        """Test loading when implementation_plan.json doesn't exist."""
        result = _load_implementation_plan(temp_spec_dir)
        assert result is None

    def test_load_invalid_json(self, temp_spec_dir: Path):
        """Test loading with invalid JSON."""
        plan_file = temp_spec_dir / "implementation_plan.json"
        plan_file.write_text("{ invalid json }")

        result = _load_implementation_plan(temp_spec_dir)
        assert result is None


class TestLoadPackageJson:
    """Tests for _load_package_json function."""

    def test_load_valid_package_json(
        self, temp_project_dir: Path, sample_package_json: dict
    ):
        """Test loading a valid package.json."""
        package_file = temp_project_dir / "package.json"
        package_file.write_text(json.dumps(sample_package_json))

        result = _load_package_json(temp_project_dir)

        assert result is not None
        assert result["dependencies"]["react"] == "^18.0.0"
        assert len(result["devDependencies"]) == 2

    def test_load_missing_package_json(self, temp_project_dir: Path):
        """Test loading when package.json doesn't exist."""
        result = _load_package_json(temp_project_dir)
        assert result is None

    def test_load_invalid_json(self, temp_project_dir: Path):
        """Test loading with invalid JSON."""
        package_file = temp_project_dir / "package.json"
        package_file.write_text("{ invalid }")

        result = _load_package_json(temp_project_dir)
        assert result is None


class TestLoadRequirementsTxt:
    """Tests for _load_requirements_txt function."""

    def test_load_valid_requirements(self, temp_project_dir: Path):
        """Test loading a valid requirements.txt."""
        req_file = temp_project_dir / "requirements.txt"
        req_file.write_text("pytest==7.0.0\n# This is a comment\nrequests>=2.28.0\n")

        result = _load_requirements_txt(temp_project_dir)

        assert len(result) == 2
        assert "pytest==7.0.0" in result
        assert "requests>=2.28.0" in result

    def test_load_missing_requirements(self, temp_project_dir: Path):
        """Test loading when requirements.txt doesn't exist."""
        result = _load_requirements_txt(temp_project_dir)
        assert result == []

    def test_load_empty_requirements(self, temp_project_dir: Path):
        """Test loading an empty requirements.txt."""
        req_file = temp_project_dir / "requirements.txt"
        req_file.write_text("# Only comments\n\n")

        result = _load_requirements_txt(temp_project_dir)
        assert result == []


# =============================================================================
# TEST COVERAGE CALCULATION
# =============================================================================


class TestCountTestFiles:
    """Tests for _count_test_files function."""

    def test_count_python_test_files(self, temp_project_dir: Path):
        """Test counting Python test files."""
        (temp_project_dir / "test_module.py").touch()
        (temp_project_dir / "module_test.py").touch()
        (temp_project_dir / "regular.py").touch()

        count = _count_test_files(temp_project_dir)
        assert count == 2

    def test_count_javascript_test_files(self, temp_project_dir: Path):
        """Test counting JavaScript test files."""
        (temp_project_dir / "component.test.js").touch()
        (temp_project_dir / "utils.spec.ts").touch()
        (temp_project_dir / "app.test.tsx").touch()
        (temp_project_dir / "regular.js").touch()

        count = _count_test_files(temp_project_dir)
        assert count == 3

    def test_count_nested_test_files(self, temp_project_dir: Path):
        """Test counting test files in nested directories."""
        tests_dir = temp_project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_feature.py").touch()

        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        (src_dir / "utils.test.ts").touch()

        count = _count_test_files(temp_project_dir)
        assert count == 2


class TestParseJestCoverage:
    """Tests for _parse_jest_coverage function."""

    def test_parse_valid_jest_coverage(self, temp_project_dir: Path):
        """Test parsing valid Jest/Vitest coverage JSON."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_data = {
            "file1.js": {"lines": {"total": 100, "covered": 75}},
            "file2.js": {"lines": {"total": 50, "covered": 50}},
        }
        coverage_file.write_text(json.dumps(coverage_data))

        result = _parse_jest_coverage(coverage_file)

        assert result is not None
        assert result["percentage"] == pytest.approx(83.33)
        assert result["covered_lines"] == 125
        assert result["total_lines"] == 150

    def test_parse_jest_coverage_no_files(self, temp_project_dir: Path):
        """Test parsing coverage with no files."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_file.write_text(json.dumps({}))

        result = _parse_jest_coverage(coverage_file)
        assert result is None

    def test_parse_jest_coverage_invalid_json(self, temp_project_dir: Path):
        """Test parsing invalid JSON."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_file.write_text("{ invalid }")

        result = _parse_jest_coverage(coverage_file)
        assert result is None


class TestParsePythonCoverageJson:
    """Tests for _parse_python_coverage_json function."""

    def test_parse_valid_python_coverage(self, temp_project_dir: Path):
        """Test parsing valid Python coverage.py JSON."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_data = {
            "totals": {
                "covered_lines": 450,
                "num_statements": 500,
                "percent_covered": 90.0,
            }
        }
        coverage_file.write_text(json.dumps(coverage_data))

        result = _parse_python_coverage_json(coverage_file)

        assert result is not None
        assert result["percentage"] == pytest.approx(90.0)
        assert result["covered_lines"] == 450
        assert result["total_lines"] == 500

    def test_parse_python_coverage_no_totals(self, temp_project_dir: Path):
        """Test parsing coverage without totals section."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_file.write_text(json.dumps({}))

        result = _parse_python_coverage_json(coverage_file)
        assert result is None

    def test_parse_python_coverage_invalid_json(self, temp_project_dir: Path):
        """Test parsing invalid JSON."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_file.write_text("{ invalid }")

        result = _parse_python_coverage_json(coverage_file)
        assert result is None


class TestParseCoberturaCoverage:
    """Tests for _parse_cobertura_coverage function."""

    def test_parse_valid_cobertura_xml(self, temp_project_dir: Path):
        """Test parsing valid Cobertura XML coverage."""
        coverage_file = temp_project_dir / "coverage.xml"
        xml_content = """<?xml version="1.0" ?>
<coverage line-rate="0.85">
    <packages>
        <package name="test">
            <classes>
                <class name="TestClass">
                    <lines>
                        <line number="1" hits="1"/>
                        <line number="2" hits="1"/>
                        <line number="3" hits="0"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>
"""
        coverage_file.write_text(xml_content)

        result = _parse_cobertura_coverage(coverage_file)

        assert result is not None
        assert result["percentage"] == pytest.approx(85.0)
        assert result["covered_lines"] == 2
        assert result["total_lines"] == 3

    def test_parse_cobertura_invalid_xml(self, temp_project_dir: Path):
        """Test parsing invalid XML."""
        coverage_file = temp_project_dir / "coverage.xml"
        coverage_file.write_text("<invalid>xml")

        result = _parse_cobertura_coverage(coverage_file)
        assert result is None


class TestCalculateTestCoverage:
    """Tests for calculate_test_coverage function."""

    def test_no_coverage_files(self, temp_project_dir: Path):
        """Test when no coverage files exist."""
        result = calculate_test_coverage(temp_project_dir)

        assert result["percentage"] == pytest.approx(0.0)
        assert result["test_count"] == 0
        assert result["trend"] == "unknown"

    def test_jest_coverage_priority(self, temp_project_dir: Path):
        """Test that Jest coverage is parsed correctly."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_data = {"file1.js": {"lines": {"total": 100, "covered": 80}}}
        coverage_file.write_text(json.dumps(coverage_data))

        (temp_project_dir / "test_file.py").touch()

        result = calculate_test_coverage(temp_project_dir)

        assert result["percentage"] == pytest.approx(80.0)
        assert result["test_count"] == 1

    def test_cobertura_coverage(self, temp_project_dir: Path):
        """Test Cobertura XML coverage parsing."""
        coverage_file = temp_project_dir / "coverage.xml"
        xml_content = """<?xml version="1.0" ?>
<coverage line-rate="0.90">
    <packages>
        <package name="test">
            <classes>
                <class name="TestClass">
                    <lines>
                        <line number="1" hits="1"/>
                        <line number="2" hits="1"/>
                        <line number="3" hits="1"/>
                        <line number="4" hits="0"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>
"""
        coverage_file.write_text(xml_content)

        result = calculate_test_coverage(temp_project_dir)

        assert result["percentage"] == pytest.approx(90.0)
        assert result["trend"] == "unknown"


# =============================================================================
# CODE QUALITY METRICS
# =============================================================================


class TestCalculateCodeQuality:
    """Tests for _calculate_code_quality function."""

    def test_calculate_code_quality(self, temp_project_dir: Path):
        """Test code quality calculation."""
        result = _calculate_code_quality(temp_project_dir)

        assert "complexity_score" in result
        assert "duplication_percentage" in result
        assert "maintainability_index" in result
        assert "issues_count" in result
        assert result["maintainability_index"] == pytest.approx(100.0)


# =============================================================================
# SECURITY METRICS
# =============================================================================


class TestCalculateSecurityScore:
    """Tests for _calculate_security_score function."""

    def test_calculate_security_score(self, temp_project_dir: Path):
        """Test security score calculation."""
        result = _calculate_security_score(temp_project_dir)

        assert "vulnerability_count" in result
        assert "critical_count" in result
        assert "high_count" in result
        assert "medium_count" in result
        assert "low_count" in result
        assert "scan_date" in result
        assert result["vulnerability_count"] == 0


# =============================================================================
# DEPENDENCY METRICS
# =============================================================================


class TestCalculateDependencyHealth:
    """Tests for _calculate_dependency_health function."""

    def test_calculate_with_package_json(
        self, temp_project_dir: Path, sample_package_json: dict
    ):
        """Test dependency calculation with package.json."""
        package_file = temp_project_dir / "package.json"
        package_file.write_text(json.dumps(sample_package_json))

        result = _calculate_dependency_health(temp_project_dir)

        assert result["total_dependencies"] == 4  # 2 deps + 2 devDeps
        assert result["freshness_score"] == pytest.approx(100.0)

    def test_calculate_with_requirements_txt(self, temp_project_dir: Path):
        """Test dependency calculation with requirements.txt."""
        req_file = temp_project_dir / "requirements.txt"
        req_file.write_text("pytest==7.0.0\nrequests>=2.28.0\n")

        result = _calculate_dependency_health(temp_project_dir)

        assert result["total_dependencies"] == 2
        assert result["freshness_score"] == pytest.approx(100.0)

    def test_calculate_with_both(
        self, temp_project_dir: Path, sample_package_json: dict
    ):
        """Test dependency calculation with both package types."""
        package_file = temp_project_dir / "package.json"
        package_file.write_text(json.dumps(sample_package_json))

        req_file = temp_project_dir / "requirements.txt"
        req_file.write_text("pytest==7.0.0\n")

        result = _calculate_dependency_health(temp_project_dir)

        assert result["total_dependencies"] == 5  # 4 npm + 1 python


# =============================================================================
# AGENT ACTIVITY METRICS
# =============================================================================


class TestCalculateAgentActivity:
    """Tests for _calculate_agent_activity function."""

    def test_calculate_with_valid_plan(
        self, temp_spec_dir: Path, sample_implementation_plan: dict
    ):
        """Test activity calculation with valid plan."""
        plan_file = temp_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_implementation_plan))

        result = _calculate_agent_activity(temp_spec_dir)

        assert result["total_iterations"] == 3
        assert result["success_rate"] == pytest.approx(66.7)  # 2 out of 3 approved
        assert len(result["recent_activity"]) == 3

    def test_calculate_without_plan(self, temp_spec_dir: Path):
        """Test activity calculation without plan."""
        result = _calculate_agent_activity(temp_spec_dir)

        assert result["total_iterations"] == 0
        assert result["success_rate"] == pytest.approx(0.0)
        assert result["recent_activity"] == []

    def test_calculate_truncates_recent_activity(self, temp_spec_dir: Path):
        """Test that recent activity is limited to last 5 iterations."""
        history = [
            {
                "iteration": i,
                "status": "approved",
                "timestamp": f"2026-02-09T{i:02d}:00:00Z",
            }
            for i in range(1, 11)
        ]
        plan_data = {"qa_iteration_history": history}
        plan_file = temp_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan_data))

        result = _calculate_agent_activity(temp_spec_dir)

        assert len(result["recent_activity"]) == 5


# =============================================================================
# HEALTH SCORE CALCULATION
# =============================================================================


class TestCalculateOverallScore:
    """Tests for _calculate_overall_score function."""

    def test_calculate_default_weights(self):
        """Test score calculation with default weights."""
        metrics = {
            "test_coverage": {"percentage": 80.0},
            "code_quality": {"maintainability_index": 90.0},
            "security": {"vulnerability_count": 1},
            "dependencies": {"freshness_score": 95.0},
            "agent_activity": {"success_rate": 85.0},
        }

        result = _calculate_overall_score(metrics)

        # Expected calculation:
        # test: 80.0 * 0.25 = 20.0
        # quality: 90.0 * 0.20 = 18.0
        # security: 90.0 * 0.25 = 22.5 (100 - 1*10 = 90)
        # deps: 95.0 * 0.15 = 14.25
        # activity: 85.0 * 0.15 = 12.75
        # Total: 87.5
        assert result == pytest.approx(87.5)

    def test_calculate_custom_weights(self):
        """Test score calculation with custom weights."""
        metrics = {
            "test_coverage": {"percentage": 80.0},
            "code_quality": {"maintainability_index": 90.0},
            "security": {"vulnerability_count": 0},
            "dependencies": {"freshness_score": 95.0},
            "agent_activity": {"success_rate": 85.0},
        }

        custom_weights = {
            "test_coverage": 0.5,
            "code_quality": 0.2,
            "security": 0.1,
            "dependencies": 0.1,
            "agent_activity": 0.1,
        }

        result = _calculate_overall_score(metrics, custom_weights)

        # test: 80.0 * 0.5 = 40.0
        # quality: 90.0 * 0.2 = 18.0
        # security: 100.0 * 0.1 = 10.0
        # deps: 95.0 * 0.1 = 9.5
        # activity: 85.0 * 0.1 = 8.5
        # Total: 86.0
        assert result == pytest.approx(86.0)

    def test_security_score_clamping(self):
        """Test that security score is clamped between 0 and 100."""
        metrics = {
            "test_coverage": {"percentage": 100.0},
            "code_quality": {"maintainability_index": 100.0},
            "security": {"vulnerability_count": 20},  # Would be -100
            "dependencies": {"freshness_score": 100.0},
            "agent_activity": {"success_rate": 100.0},
        }

        result = _calculate_overall_score(metrics)

        # Security should be clamped to 0.0
        assert 0.0 <= result <= 100.0


class TestGetHealthStatus:
    """Tests for _get_health_status function."""

    def test_excellent_status(self):
        """Test excellent status threshold."""
        assert _get_health_status(95.0) == "excellent"
        assert _get_health_status(90.0) == "excellent"

    def test_good_status(self):
        """Test good status threshold."""
        assert _get_health_status(85.0) == "good"
        assert _get_health_status(75.0) == "good"

    def test_fair_status(self):
        """Test fair status threshold."""
        assert _get_health_status(70.0) == "fair"
        assert _get_health_status(60.0) == "fair"

    def test_poor_status(self):
        """Test poor status threshold."""
        assert _get_health_status(50.0) == "poor"
        assert _get_health_status(0.0) == "poor"


# =============================================================================
# PUBLIC API
# =============================================================================


class TestGetProjectHealth:
    """Tests for get_project_health function."""

    def test_get_health_basic(self, temp_project_dir: Path):
        """Test basic project health retrieval."""
        health = get_project_health(temp_project_dir)

        assert "overall_score" in health
        assert "status" in health
        assert "test_coverage" in health
        assert "code_quality" in health
        assert "security" in health
        assert "dependencies" in health
        assert "agent_activity" in health
        assert "generated_at" in health

    def test_get_health_with_spec_dir(
        self, temp_project_dir: Path, temp_spec_dir: Path
    ):
        """Test project health with spec directory."""
        health = get_project_health(temp_project_dir, temp_spec_dir)

        assert health["agent_activity"]["total_iterations"] == 0
        assert health["agent_activity"]["success_rate"] == pytest.approx(0.0)

    def test_get_health_with_package_json(
        self, temp_project_dir: Path, sample_package_json: dict
    ):
        """Test health calculation with package.json."""
        package_file = temp_project_dir / "package.json"
        package_file.write_text(json.dumps(sample_package_json))

        health = get_project_health(temp_project_dir)

        assert health["dependencies"]["total_dependencies"] == 4

    def test_get_health_with_coverage(self, temp_project_dir: Path):
        """Test health calculation with coverage file."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_data = {"file1.js": {"lines": {"total": 100, "covered": 85}}}
        coverage_file.write_text(json.dumps(coverage_data))

        health = get_project_health(temp_project_dir)

        assert health["test_coverage"]["percentage"] == pytest.approx(85.0)

    def test_get_health_custom_weights(self, temp_project_dir: Path):
        """Test health calculation with custom weights."""
        custom_weights = {
            "test_coverage": 0.5,
            "code_quality": 0.5,
            "security": 0.0,
            "dependencies": 0.0,
            "agent_activity": 0.0,
        }

        health = get_project_health(temp_project_dir, weights=custom_weights)

        # Should use custom weights
        assert 0.0 <= health["overall_score"] <= 100.0


class TestGetHealthSummary:
    """Tests for get_health_summary function."""

    def test_summary_basic(self, temp_project_dir: Path):
        """Test basic health summary."""
        summary = get_health_summary(temp_project_dir)

        assert "overall_score" in summary
        assert "status" in summary
        assert "critical_issues" in summary
        assert "recommendations" in summary
        assert isinstance(summary["critical_issues"], list)
        assert isinstance(summary["recommendations"], list)

    def test_summary_with_critical_vulnerabilities(self, temp_project_dir: Path):
        """Test summary identifies critical security issues."""
        # We need to mock get_project_health to return critical vulnerabilities
        with patch("analysis.health_analyzer.get_project_health") as mock_health:
            mock_health.return_value = {
                "overall_score": 50.0,
                "status": "fair",
                "test_coverage": {"percentage": 80.0},
                "security": {
                    "critical_count": 3,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0,
                },
                "dependencies": {"outdated_count": 5},
            }

            summary = get_health_summary(temp_project_dir)

            assert len(summary["critical_issues"]) > 0
            assert "critical security vulnerabilities" in summary["critical_issues"][0]
            assert len(summary["recommendations"]) > 0

    def test_summary_with_low_coverage(self, temp_project_dir: Path):
        """Test summary identifies low test coverage."""
        with patch("analysis.health_analyzer.get_project_health") as mock_health:
            mock_health.return_value = {
                "overall_score": 40.0,
                "status": "poor",
                "test_coverage": {"percentage": 30.0},
                "security": {
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0,
                },
                "dependencies": {"outdated_count": 5},
            }

            summary = get_health_summary(temp_project_dir)

            assert any(
                "Low test coverage" in issue for issue in summary["critical_issues"]
            )
            assert any(
                "Increase test coverage" in rec for rec in summary["recommendations"]
            )

    def test_summary_with_outdated_dependencies(self, temp_project_dir: Path):
        """Test summary identifies outdated dependencies."""
        with patch("analysis.health_analyzer.get_project_health") as mock_health:
            mock_health.return_value = {
                "overall_score": 60.0,
                "status": "fair",
                "test_coverage": {"percentage": 80.0},
                "security": {
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0,
                },
                "dependencies": {"outdated_count": 15},
            }

            summary = get_health_summary(temp_project_dir)

            assert any(
                "outdated dependencies" in issue for issue in summary["critical_issues"]
            )
            assert any(
                "Update dependencies" in rec for rec in summary["recommendations"]
            )


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_missing_project_directory(self):
        """Test handling of non-existent project directory."""
        # Path doesn't exist, but function should handle gracefully
        # The function uses Path() which doesn't raise until operations are performed
        health = get_project_health("/nonexistent/path/that/does/not/exist")
        # Should return a result with zeroed values rather than crashing
        assert health["test_coverage"]["percentage"] == pytest.approx(0.0)

    def test_empty_project_directory(self, tmp_path: Path):
        """Test handling of empty project directory."""
        health = get_project_health(tmp_path)
        assert health["overall_score"] >= 0.0
        assert health["test_coverage"]["percentage"] == pytest.approx(0.0)

    def test_invalid_coverage_json(self, temp_project_dir: Path):
        """Test handling of invalid coverage JSON."""
        coverage_file = temp_project_dir / "coverage.json"
        coverage_file.write_text("{ totally invalid json }")

        health = get_project_health(temp_project_dir)

        # Should gracefully handle invalid coverage
        assert health["test_coverage"]["percentage"] == pytest.approx(0.0)

    def test_corrupted_implementation_plan(self, temp_spec_dir: Path):
        """Test handling of corrupted implementation plan."""
        plan_file = temp_spec_dir / "implementation_plan.json"
        plan_file.write_text("{ corrupted }")

        health = get_project_health(temp_spec_dir.parent.parent, temp_spec_dir)

        # Should handle corrupted plan gracefully
        assert health["agent_activity"]["total_iterations"] == 0

    def test_path_as_string(self, temp_project_dir: Path):
        """Test that function accepts string paths."""
        health = get_project_health(str(temp_project_dir))
        assert health is not None

    def test_unicode_in_files(self, temp_project_dir: Path):
        """Test handling of unicode characters in files."""
        package_file = temp_project_dir / "package.json"
        package_data = {
            "name": "test-package",
            "version": "1.0.0",
            "description": "Test with unicode: ñ, é, 中文",
        }
        package_file.write_text(json.dumps(package_data), encoding="utf-8")

        health = get_project_health(temp_project_dir)
        assert health is not None
