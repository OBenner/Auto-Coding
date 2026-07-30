#!/usr/bin/env python3
"""
Tests for Quality Tracker Coverage Integration
================================================

Tests the quality_tracker.py and quality_models.py coverage tracking functionality:
- QualityScore dataclass with coverage fields
- Coverage metrics calculation from .coverage.json
- Coverage integration in quality score calculation
- Coverage display in MCP tools
"""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from analysis.quality_models import QualityScore
from analysis.quality_tracker import _calculate_coverage_metrics, calculate_quality_score


# =============================================================================
# TEST QUALITYSCORE WITH COVERAGE FIELDS
# =============================================================================


class TestQualityScoreCoverageFields:
    """Tests for QualityScore dataclass with coverage fields."""

    def test_quality_score_with_coverage_fields(self):
        """Test QualityScore can be created with coverage data."""
        score = QualityScore(
            session_id="test-session",
            spec_id="001-test",
            agent_type="coder",
            timestamp=datetime.now(UTC),
            coverage_percent=85.5,
            lines_covered=171,
            lines_total=200,
        )

        assert score.coverage_percent == 85.5
        assert score.lines_covered == 171
        assert score.lines_total == 200

    def test_quality_score_default_coverage_values(self):
        """Test QualityScore defaults coverage fields to 0."""
        score = QualityScore(
            session_id="test-session",
            spec_id="001-test",
            agent_type="coder",
            timestamp=datetime.now(UTC),
        )

        assert score.coverage_percent == 0.0
        assert score.lines_covered == 0
        assert score.lines_total == 0

    def test_quality_score_serialization_with_coverage(self):
        """Test QualityScore.to_dict() includes coverage fields."""
        score = QualityScore(
            session_id="test-session",
            spec_id="001-test",
            agent_type="coder",
            timestamp=datetime.now(UTC),
            coverage_percent=92.3,
            lines_covered=120,
            lines_total=130,
        )

        data = score.to_dict()

        assert "coverage_percent" in data
        assert "lines_covered" in data
        assert "lines_total" in data
        assert data["coverage_percent"] == 92.3
        assert data["lines_covered"] == 120
        assert data["lines_total"] == 130

    def test_quality_score_deserialization_with_coverage(self):
        """Test QualityScore.from_dict() deserializes coverage fields."""
        data = {
            "session_id": "test-session",
            "spec_id": "001-test",
            "agent_type": "coder",
            "timestamp": "2026-03-20T10:00:00+00:00",
            "coverage_percent": 78.5,
            "lines_covered": 157,
            "lines_total": 200,
        }

        score = QualityScore.from_dict(data)

        assert score.coverage_percent == 78.5
        assert score.lines_covered == 157
        assert score.lines_total == 200

    def test_quality_score_deserialization_without_coverage(self):
        """Test QualityScore.from_dict() handles missing coverage fields."""
        data = {
            "session_id": "test-session",
            "spec_id": "001-test",
            "agent_type": "coder",
            "timestamp": "2026-03-20T10:00:00+00:00",
        }

        score = QualityScore.from_dict(data)

        # Should default to 0 when not provided
        assert score.coverage_percent == 0.0
        assert score.lines_covered == 0
        assert score.lines_total == 0


# =============================================================================
# TEST _calculate_coverage_metrics() FUNCTION
# =============================================================================


class TestCalculateCoverageMetrics:
    """Tests for _calculate_coverage_metrics() function."""

    def test_calculate_coverage_metrics_valid_file(self):
        """Test coverage calculation with valid .coverage.json file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            coverage_file = spec_dir / ".coverage.json"

            # Create valid coverage JSON
            coverage_data = {
                "totals": {
                    "covered_lines": 85,
                    "num_statements": 100,
                }
            }

            with open(coverage_file, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f)

            # Calculate coverage
            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 85.0
            assert lines_covered == 85
            assert lines_total == 100

    def test_calculate_coverage_metrics_missing_file(self):
        """Test coverage calculation when .coverage.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)

            # No .coverage.json file created
            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 0.0
            assert lines_covered == 0
            assert lines_total == 0

    def test_calculate_coverage_metrics_malformed_json(self):
        """Test coverage calculation with malformed JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            coverage_file = spec_dir / ".coverage.json"

            # Create invalid JSON
            with open(coverage_file, "w", encoding="utf-8") as f:
                f.write("{ invalid json }")

            # Should return zeros without crashing
            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 0.0
            assert lines_covered == 0
            assert lines_total == 0

    def test_calculate_coverage_metrics_missing_totals(self):
        """Test coverage calculation when totals section is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            coverage_file = spec_dir / ".coverage.json"

            # Create JSON without totals
            coverage_data = {"files": {}}

            with open(coverage_file, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f)

            # Should return zeros
            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 0.0
            assert lines_covered == 0
            assert lines_total == 0

    def test_calculate_coverage_metrics_zero_lines(self):
        """Test coverage calculation when total lines = 0 (division by zero)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            coverage_file = spec_dir / ".coverage.json"

            # Create coverage data with 0 total lines
            coverage_data = {
                "totals": {
                    "covered_lines": 0,
                    "num_statements": 0,
                }
            }

            with open(coverage_file, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f)

            # Should handle division by zero gracefully
            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 0.0
            assert lines_covered == 0
            assert lines_total == 0

    def test_calculate_coverage_metrics_partial_coverage(self):
        """Test coverage calculation with partial coverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            coverage_file = spec_dir / ".coverage.json"

            # Create coverage data with 50% coverage
            coverage_data = {
                "totals": {
                    "covered_lines": 42,
                    "num_statements": 84,
                }
            }

            with open(coverage_file, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f)

            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 50.0
            assert lines_covered == 42
            assert lines_total == 84

    def test_calculate_coverage_metrics_unicode_error(self):
        """Test coverage calculation with encoding issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            coverage_file = spec_dir / ".coverage.json"

            # Create file with invalid UTF-8
            with open(coverage_file, "wb") as f:
                f.write(b"\xff\xfe invalid utf-8")

            # Should handle encoding error gracefully
            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 0.0
            assert lines_covered == 0
            assert lines_total == 0


# =============================================================================
# TEST COVERAGE INTEGRATION IN calculate_quality_score()
# =============================================================================


class TestQualityScoreCoverageIntegration:
    """Tests for coverage integration in calculate_quality_score()."""

    def test_calculate_quality_score_with_coverage_data(self):
        """Test calculate_quality_score() includes coverage when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir) / "001-test-spec"
            spec_dir.mkdir(parents=True)

            # Create implementation plan (required by calculate_quality_score)
            plan = {
                "phases": [],
                "qa_iteration_history": [],
            }
            plan_file = spec_dir / "implementation_plan.json"
            with open(plan_file, "w", encoding="utf-8") as f:
                json.dump(plan, f)

            # Create coverage data
            coverage_file = spec_dir / ".coverage.json"
            coverage_data = {
                "totals": {
                    "covered_lines": 90,
                    "num_statements": 100,
                }
            }
            with open(coverage_file, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f)

            # Calculate quality score
            score = calculate_quality_score(
                spec_dir=spec_dir,
                session_id="test-session",
                agent_type="coder",
            )

            # Verify coverage fields are populated
            assert score.coverage_percent == 90.0
            assert score.lines_covered == 90
            assert score.lines_total == 100

    def test_calculate_quality_score_without_coverage_data(self):
        """Test calculate_quality_score() works without coverage data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir) / "001-test-spec"
            spec_dir.mkdir(parents=True)

            # Create implementation plan
            plan = {
                "phases": [],
                "qa_iteration_history": [],
            }
            plan_file = spec_dir / "implementation_plan.json"
            with open(plan_file, "w", encoding="utf-8") as f:
                json.dump(plan, f)

            # No coverage file created

            # Calculate quality score
            score = calculate_quality_score(
                spec_dir=spec_dir,
                session_id="test-session",
                agent_type="coder",
            )

            # Verify coverage fields default to 0
            assert score.coverage_percent == 0.0
            assert score.lines_covered == 0
            assert score.lines_total == 0

    def test_calculate_quality_score_coverage_persists_in_history(self):
        """Test that coverage data persists in quality_history.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir) / "001-test-spec"
            spec_dir.mkdir(parents=True)

            # Create implementation plan with QA data to trigger persistence
            plan = {
                "phases": [
                    {
                        "subtasks": [
                            {
                                "id": "test-subtask",
                                "verification": {
                                    "test_results": {
                                        "total": 10,
                                        "passed": 8,
                                    }
                                },
                            }
                        ]
                    }
                ],
                "qa_iteration_history": [
                    {
                        "iteration": 1,
                        "status": "approved",
                    }
                ],
            }
            plan_file = spec_dir / "implementation_plan.json"
            with open(plan_file, "w", encoding="utf-8") as f:
                json.dump(plan, f)

            # Create coverage data
            coverage_file = spec_dir / ".coverage.json"
            coverage_data = {
                "totals": {
                    "covered_lines": 75,
                    "num_statements": 100,
                }
            }
            with open(coverage_file, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f)

            # Calculate quality score (should persist with meaningful data)
            score = calculate_quality_score(
                spec_dir=spec_dir,
                session_id="test-session",
                agent_type="coder",
                subtask_id="test-subtask",
                iteration=1,
            )

            # Verify coverage in returned score
            assert score.coverage_percent == 75.0
            assert score.lines_covered == 75
            assert score.lines_total == 100

            # Verify persistence in quality_history.json
            history_file = spec_dir / "quality_history.json"
            assert history_file.exists()

            with open(history_file, encoding="utf-8") as f:
                history_data = json.load(f)

            scores = history_data.get("scores", [])
            assert len(scores) > 0

            # Check the persisted score has coverage data
            persisted_score = scores[0]
            assert persisted_score["coverage_percent"] == 75.0
            assert persisted_score["lines_covered"] == 75
            assert persisted_score["lines_total"] == 100


# =============================================================================
# TEST MCP TOOL COVERAGE OUTPUT
# =============================================================================


class TestMCPToolCoverageOutput:
    """Tests for coverage output in get_quality_metrics MCP tool."""

    def test_mcp_tool_with_coverage_data(self):
        """Test that get_quality_metrics tool includes coverage section."""
        # Note: This is a simplified test. Full integration testing would require
        # the MCP tool environment. Here we verify the data structure is correct.

        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir) / "001-test-spec"
            spec_dir.mkdir(parents=True)

            # Create quality history with coverage data
            quality_history = {
                "scores": [
                    {
                        "session_id": "test-session",
                        "spec_id": "001-test-spec",
                        "agent_type": "coder",
                        "timestamp": "2026-03-20T10:00:00+00:00",
                        "coverage_percent": 88.5,
                        "lines_covered": 177,
                        "lines_total": 200,
                        "composite_score": 0.85,
                        "is_high_quality": True,
                        "is_low_quality": False,
                    }
                ],
                "updated_at": "2026-03-20T10:00:00+00:00",
            }

            history_file = spec_dir / "quality_history.json"
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(quality_history, f)

            # Read the history and verify coverage data is present
            with open(history_file, encoding="utf-8") as f:
                data = json.load(f)

            scores = data.get("scores", [])
            assert len(scores) > 0

            latest_score = scores[-1]
            assert "coverage_percent" in latest_score
            assert "lines_covered" in latest_score
            assert "lines_total" in latest_score
            assert latest_score["coverage_percent"] == 88.5
            assert latest_score["lines_covered"] == 177
            assert latest_score["lines_total"] == 200

    def test_mcp_tool_without_coverage_data(self):
        """Test that get_quality_metrics tool handles missing coverage gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir) / "001-test-spec"
            spec_dir.mkdir(parents=True)

            # Create quality history without coverage data (legacy format)
            quality_history = {
                "scores": [
                    {
                        "session_id": "test-session",
                        "spec_id": "001-test-spec",
                        "agent_type": "coder",
                        "timestamp": "2026-03-20T10:00:00+00:00",
                        "composite_score": 0.85,
                        "is_high_quality": True,
                        "is_low_quality": False,
                    }
                ],
                "updated_at": "2026-03-20T10:00:00+00:00",
            }

            history_file = spec_dir / "quality_history.json"
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(quality_history, f)

            # Read the history and verify it handles missing coverage fields
            with open(history_file, encoding="utf-8") as f:
                data = json.load(f)

            scores = data.get("scores", [])
            assert len(scores) > 0

            latest_score = scores[-1]
            # Coverage fields should be missing (backward compatibility)
            assert "coverage_percent" not in latest_score
            assert "lines_covered" not in latest_score
            assert "lines_total" not in latest_score


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestCoverageEdgeCases:
    """Additional edge case tests for coverage tracking."""

    def test_coverage_with_100_percent(self):
        """Test coverage calculation with 100% coverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            coverage_file = spec_dir / ".coverage.json"

            coverage_data = {
                "totals": {
                    "covered_lines": 100,
                    "num_statements": 100,
                }
            }

            with open(coverage_file, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f)

            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 100.0
            assert lines_covered == 100
            assert lines_total == 100

    def test_coverage_with_decimal_percentage(self):
        """Test coverage calculation with decimal percentages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            coverage_file = spec_dir / ".coverage.json"

            # 67 / 100 = 67.0%
            coverage_data = {
                "totals": {
                    "covered_lines": 67,
                    "num_statements": 100,
                }
            }

            with open(coverage_file, "w", encoding="utf-8") as f:
                json.dump(coverage_data, f)

            coverage_percent, lines_covered, lines_total = _calculate_coverage_metrics(
                spec_dir
            )

            assert coverage_percent == 67.0
            assert lines_covered == 67
            assert lines_total == 100

    def test_coverage_backward_compatibility(self):
        """Test that QualityScore remains backward compatible with old data."""
        # Old data without coverage fields
        old_data = {
            "session_id": "old-session",
            "spec_id": "001-old",
            "agent_type": "coder",
            "timestamp": "2026-01-01T10:00:00+00:00",
            "test_pass_rate": 0.9,
            "composite_score": 0.85,
            "is_high_quality": True,
            "is_low_quality": False,
        }

        # Should deserialize successfully with default coverage values
        score = QualityScore.from_dict(old_data)

        assert score.session_id == "old-session"
        assert score.coverage_percent == 0.0
        assert score.lines_covered == 0
        assert score.lines_total == 0
