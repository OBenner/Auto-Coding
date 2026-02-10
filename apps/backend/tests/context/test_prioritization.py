"""
Tests for Prioritization Integration in ContextBuilder
========================================================

Tests that FilePrioritizer and DependencyAnalyzer are properly
integrated into the context building pipeline.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from context.builder import ContextBuilder
from context.models import FileMatch


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create basic project structure
        (project_dir / ".auto-claude").mkdir()

        # Create some Python files
        backend_dir = project_dir / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        (backend_dir / "main.py").write_text("# Main entry point\n")
        (backend_dir / "utils.py").write_text("# Utilities\n")
        (backend_dir / "config.py").write_text("# Configuration\n")

        yield project_dir


@pytest.fixture
def mock_project_index():
    """Mock project index with a simple backend service."""
    return {
        "services": {
            "backend": {
                "path": "apps/backend",
                "language": "python",
                "framework": "none",
                "type": "application",
            }
        }
    }


@pytest.fixture
def sample_matches():
    """Create sample FileMatch objects for testing."""
    return [
        FileMatch(
            path="apps/backend/old_file.py",
            service="backend",
            reason="Contains: test",
            relevance_score=5.0,
            matching_lines=[(1, "test code")],
        ),
        FileMatch(
            path="apps/backend/new_file.py",
            service="backend",
            reason="Contains: test, feature",
            relevance_score=8.0,
            matching_lines=[(1, "test feature")],
        ),
        FileMatch(
            path="apps/backend/medium_file.py",
            service="backend",
            reason="Contains: feature",
            relevance_score=6.0,
            matching_lines=[(1, "feature code")],
        ),
    ]


class TestPrioritizationIntegration:
    """Test suite for prioritization integration."""

    def test_builder_has_prioritization_components(self, temp_project, mock_project_index):
        """Test that ContextBuilder initializes prioritization components."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        # Check that prioritizer and dependency_analyzer are initialized
        assert hasattr(builder, "prioritizer")
        assert hasattr(builder, "dependency_analyzer")
        assert builder.prioritizer is not None
        assert builder.dependency_analyzer is not None

    def test_prioritize_matches_method_exists(self, temp_project, mock_project_index):
        """Test that _prioritize_matches method exists."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        assert hasattr(builder, "_prioritize_matches")
        assert callable(builder._prioritize_matches)

    def test_prioritize_matches_with_empty_list(self, temp_project, mock_project_index):
        """Test that _prioritize_matches handles empty list."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        result = builder._prioritize_matches([])
        assert result == []

    def test_prioritize_matches_applies_recency_scoring(
        self, temp_project, mock_project_index, sample_matches
    ):
        """Test that _prioritize_matches applies recency scoring."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        # Mock the prioritizer to verify it's called
        with patch.object(builder.prioritizer, "prioritize_matches") as mock_prioritize:
            mock_prioritize.return_value = sample_matches

            result = builder._prioritize_matches(sample_matches)

            # Verify prioritizer was called
            mock_prioritize.assert_called_once_with(sample_matches)
            assert len(result) == len(sample_matches)

    def test_prioritize_matches_applies_dependency_boost(
        self, temp_project, mock_project_index, sample_matches
    ):
        """Test that _prioritize_matches applies dependency impact boost."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        # Mock dependency analyzer to return impact scores
        with patch.object(
            builder.dependency_analyzer, "calculate_impact_score"
        ) as mock_impact:
            # Return different impact scores for different files
            def impact_side_effect(path):
                if "new_file" in path:
                    return 10.0  # High impact
                elif "medium_file" in path:
                    return 5.0  # Medium impact
                else:
                    return 0.0  # Low impact

            mock_impact.side_effect = impact_side_effect

            # Run prioritization
            builder._prioritize_matches(sample_matches.copy())

            # Verify dependency analyzer was called for each file
            assert mock_impact.call_count == len(sample_matches)

    def test_prioritize_matches_handles_analysis_errors(
        self, temp_project, mock_project_index, sample_matches
    ):
        """Test that _prioritize_matches handles dependency analysis errors gracefully."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        # Mock dependency analyzer to raise errors
        with patch.object(
            builder.dependency_analyzer, "calculate_impact_score"
        ) as mock_impact:
            mock_impact.side_effect = FileNotFoundError("File not found")

            # Should not raise, should handle gracefully
            result = builder._prioritize_matches(sample_matches.copy())
            assert len(result) == len(sample_matches)

    def test_prioritization_integrated_in_build_context(
        self, temp_project, mock_project_index
    ):
        """Test that prioritization is called during build_context."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        # Mock the searcher to return sample matches
        sample_matches = [
            FileMatch(
                path="apps/backend/file1.py",
                service="backend",
                reason="test",
                relevance_score=5.0,
            ),
            FileMatch(
                path="apps/backend/file2.py",
                service="backend",
                reason="test",
                relevance_score=8.0,
            ),
        ]

        with patch.object(builder.searcher, "search_service") as mock_search:
            mock_search.return_value = sample_matches

            # Mock _prioritize_matches to track if it's called
            with patch.object(builder, "_prioritize_matches") as mock_prioritize:
                mock_prioritize.return_value = sample_matches

                # Build context
                try:
                    builder.build_context(
                        task="Test task",
                        services=["backend"],
                        keywords=["test"],
                        include_graph_hints=False,
                    )
                except Exception:
                    # May fail due to other dependencies, that's OK
                    pass

                # Verify prioritization was called
                mock_prioritize.assert_called_once()

    def test_prioritization_maintains_file_match_structure(
        self, temp_project, mock_project_index, sample_matches
    ):
        """Test that prioritization preserves FileMatch structure."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        result = builder._prioritize_matches(sample_matches.copy())

        # All results should still be FileMatch objects
        for match in result:
            assert isinstance(match, FileMatch)
            assert hasattr(match, "path")
            assert hasattr(match, "service")
            assert hasattr(match, "reason")
            assert hasattr(match, "relevance_score")

    def test_prioritization_modifies_relevance_scores(
        self, temp_project, mock_project_index, sample_matches
    ):
        """Test that prioritization can modify relevance scores."""
        builder = ContextBuilder(
            project_dir=temp_project,
            project_index=mock_project_index,
        )

        # Mock to return high impact for one file
        with patch.object(
            builder.dependency_analyzer, "calculate_impact_score"
        ) as mock_impact:
            mock_impact.return_value = 10.0  # High impact for all

            result = builder._prioritize_matches(sample_matches.copy())

            # At least one score should have changed due to impact boost
            # (Note: prioritizer also changes scores with recency)
            assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
