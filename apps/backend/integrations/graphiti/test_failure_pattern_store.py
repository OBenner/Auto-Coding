#!/usr/bin/env python3
"""
Test FailurePatternStore
========================

Pytest-compatible tests for the failure pattern storage layer.

Tests cover:
- Storing failure patterns with metadata
- Retrieving patterns by type, category, or similarity
- Querying for historical patterns
- Tracking pattern occurrences across specs and subtasks
- Updating pattern frequency and confidence
- Getting recovery recommendations
- Pattern statistics

Usage:
    # Run with pytest:
    pytest integrations/graphiti/test_failure_pattern_store.py -v

    # Run specific test class:
    pytest integrations/graphiti/test_failure_pattern_store.py::TestStorePattern -v

    # Run with coverage:
    pytest integrations/graphiti/test_failure_pattern_store.py --cov=FailurePatternStore
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Mock graphiti_core before importing FailurePatternStore
sys.modules["graphiti_core"] = MagicMock()
sys.modules["graphiti_core.nodes"] = MagicMock()

from integrations.graphiti.failure_pattern_store import FailurePatternStore
from integrations.graphiti.queries_pkg.schema import GroupIdMode


@pytest.fixture
def mock_client():
    """Create a mock GraphitiClient."""
    client = MagicMock()
    client.graphiti = AsyncMock()
    return client


@pytest.fixture
def failure_pattern_store(mock_client):
    """Create a FailurePatternStore instance with mock client."""
    return FailurePatternStore(
        client=mock_client,
        group_id="test_group_123",
        spec_context_id="test_spec_001",
        group_id_mode=GroupIdMode.SPEC,
        project_dir=None,
    )


class TestStorePattern:
    """Test storing failure patterns."""

    @pytest.mark.asyncio
    async def test_store_single_pattern(self, failure_pattern_store, mock_client):
        """Test storing a single failure pattern."""
        # Mock the add_episode method
        mock_client.graphiti.add_episode = AsyncMock()

        # Store the pattern
        result = await failure_pattern_store.store_failure_pattern(
            pattern_type="recurring_error",
            description="ImportError occurs when module path is incorrect",
            frequency=3,
            confidence=0.85,
            affected_subtasks=["subtask-1", "subtask-2"],
            recovery_recommendations=[
                "Check import paths match directory structure",
                "Verify __init__.py files exist in packages",
            ],
        )

        # Verify success
        assert result is True

        # Verify add_episode was called
        assert mock_client.graphiti.add_episode.called
        call_args = mock_client.graphiti.add_episode.call_args
        assert "name" in call_args.kwargs
        assert "episode_body" in call_args.kwargs
        assert "group_id" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_store_pattern_with_metadata(
        self, failure_pattern_store, mock_client
    ):
        """Test storing a pattern with custom metadata."""
        mock_client.graphiti.add_episode = AsyncMock()

        result = await failure_pattern_store.store_failure_pattern(
            pattern_type="syntax_error",
            description="Syntax error in configuration file",
            frequency=1,
            confidence=0.7,
            metadata={
                "error_examples": ["SyntaxError: invalid syntax"],
                "error_category": "syntax_error",
            },
        )

        assert result is True
        assert mock_client.graphiti.add_episode.called

    @pytest.mark.asyncio
    async def test_store_pattern_normalizes_confidence(
        self, failure_pattern_store, mock_client
    ):
        """Test that confidence is normalized to 0.0-1.0 range."""
        mock_client.graphiti.add_episode = AsyncMock()

        # Test with confidence > 1.0
        result = await failure_pattern_store.store_failure_pattern(
            pattern_type="test",
            description="Test pattern",
            confidence=1.5,
        )

        assert result is True
        call_args = mock_client.graphiti.add_episode.call_args
        import json

        episode_body = json.loads(call_args.kwargs["episode_body"])
        assert episode_body["confidence"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_store_batch_patterns(self, failure_pattern_store, mock_client):
        """Test storing multiple patterns in batch."""
        mock_client.graphiti.add_episode = AsyncMock()

        patterns = [
            {
                "pattern_type": "circular_fix",
                "description": "Fix oscillates between two solutions",
                "frequency": 2,
                "confidence": 0.75,
            },
            {
                "pattern_type": "escalating_complexity",
                "description": "Fix becomes more complex than original code",
                "frequency": 1,
                "confidence": 0.6,
            },
        ]

        stored_count = await failure_pattern_store.store_failure_patterns_batch(
            patterns
        )

        assert stored_count == 2
        assert mock_client.graphiti.add_episode.call_count == 2


class TestQueryPatterns:
    """Test querying failure patterns."""

    @pytest.mark.asyncio
    async def test_query_patterns_basic(self, failure_pattern_store, mock_client):
        """Test basic pattern query."""
        # Mock search results
        mock_result = MagicMock()
        mock_result.content = '{"type": "failure_pattern", "pattern_type": "recurring_error", "description": "Test error", "frequency": 3, "confidence": 0.8, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": ["subtask-1"], "recovery_recommendations": ["Fix it"], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        mock_result.score = 0.9

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.query_failure_patterns(
            query="recurring error",
            num_results=10,
        )

        assert len(patterns) == 1
        assert patterns[0]["pattern_type"] == "recurring_error"
        assert patterns[0]["description"] == "Test error"

    @pytest.mark.asyncio
    async def test_query_with_type_filter(self, failure_pattern_store, mock_client):
        """Test querying with pattern type filter."""
        mock_result = MagicMock()
        mock_result.content = '{"type": "failure_pattern", "pattern_type": "test_failure", "description": "Test fails", "frequency": 5, "confidence": 0.9, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        mock_result.score = 0.85

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.query_failure_patterns(
            query="test",
            pattern_type="test_failure",
            num_results=10,
        )

        assert len(patterns) == 1
        assert patterns[0]["pattern_type"] == "test_failure"

    @pytest.mark.asyncio
    async def test_query_with_confidence_filter(
        self, failure_pattern_store, mock_client
    ):
        """Test querying with minimum confidence filter."""
        # Create two mock results with different confidence levels
        high_conf_result = MagicMock()
        high_conf_result.content = '{"type": "failure_pattern", "pattern_type": "error", "description": "High confidence", "frequency": 1, "confidence": 0.9, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        high_conf_result.score = 0.9

        low_conf_result = MagicMock()
        low_conf_result.content = '{"type": "failure_pattern", "pattern_type": "error", "description": "Low confidence", "frequency": 1, "confidence": 0.5, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        low_conf_result.score = 0.5

        mock_client.graphiti.search = AsyncMock(
            return_value=[high_conf_result, low_conf_result]
        )

        patterns = await failure_pattern_store.query_failure_patterns(
            query="error",
            min_confidence=0.7,
            num_results=10,
        )

        # Should only return high confidence pattern
        assert len(patterns) == 1
        assert patterns[0]["confidence"] == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_query_with_frequency_filter(
        self, failure_pattern_store, mock_client
    ):
        """Test querying with minimum frequency filter."""
        mock_result = MagicMock()
        mock_result.content = '{"type": "failure_pattern", "pattern_type": "recurring", "description": "Frequent error", "frequency": 5, "confidence": 0.8, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        mock_result.score = 0.8

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.query_failure_patterns(
            query="error",
            min_frequency=3,
            num_results=10,
        )

        assert len(patterns) == 1
        assert patterns[0]["frequency"] == 5

    @pytest.mark.asyncio
    async def test_get_patterns_by_type(self, failure_pattern_store, mock_client):
        """Test getting patterns by specific type."""
        mock_result = MagicMock()
        mock_result.content = '{"type": "failure_pattern", "pattern_type": "import_error", "description": "Import failed", "frequency": 2, "confidence": 0.75, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        mock_result.score = 0.75

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.get_patterns_by_type(
            pattern_type="import_error",
            num_results=10,
        )

        assert len(patterns) == 1
        assert patterns[0]["pattern_type"] == "import_error"

    @pytest.mark.asyncio
    async def test_get_patterns_for_subtask(self, failure_pattern_store, mock_client):
        """Test getting patterns affecting a specific subtask."""
        mock_result = MagicMock()
        mock_result.content = '{"type": "failure_pattern", "pattern_type": "error", "description": "Error in subtask-1", "frequency": 1, "confidence": 0.7, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": ["subtask-1", "subtask-2"], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        mock_result.score = 0.7

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.get_patterns_for_subtask(
            subtask_id="subtask-1",
            num_results=10,
        )

        assert len(patterns) == 1
        assert "subtask-1" in patterns[0]["affected_subtasks"]


class TestUpdatePatterns:
    """Test updating failure patterns."""

    @pytest.mark.asyncio
    async def test_update_pattern_frequency(self, failure_pattern_store, mock_client):
        """Test updating pattern frequency."""
        # Mock search for existing pattern
        existing_result = MagicMock()
        existing_result.content = '{"type": "failure_pattern", "pattern_type": "syntax_error", "description": "Syntax error in config", "frequency": 2, "confidence": 0.7, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        existing_result.score = 0.7

        mock_client.graphiti.search = AsyncMock(return_value=[existing_result])
        mock_client.graphiti.add_episode = AsyncMock()

        success = await failure_pattern_store.update_pattern_frequency(
            pattern_type="syntax_error",
            description="Syntax error in config",
            increment=2,
            new_confidence=0.85,
        )

        assert success is True
        assert mock_client.graphiti.search.called
        assert mock_client.graphiti.add_episode.called

    @pytest.mark.asyncio
    async def test_update_creates_new_pattern_if_not_exists(
        self, failure_pattern_store, mock_client
    ):
        """Test that update creates a new pattern if it doesn't exist."""
        mock_client.graphiti.search = AsyncMock(return_value=[])
        mock_client.graphiti.add_episode = AsyncMock()

        success = await failure_pattern_store.update_pattern_frequency(
            pattern_type="new_pattern",
            description="New pattern description",
            increment=1,
        )

        assert success is True
        assert mock_client.graphiti.search.called
        assert mock_client.graphiti.add_episode.called


class TestRecommendations:
    """Test recovery recommendations."""

    @pytest.mark.asyncio
    async def test_get_recovery_recommendations(
        self, failure_pattern_store, mock_client
    ):
        """Test getting recovery recommendations."""
        # Mock patterns with recommendations
        mock_result = MagicMock()
        mock_result.content = '{"type": "failure_pattern", "pattern_type": "import_error", "description": "Module import fails", "frequency": 3, "confidence": 0.8, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": ["Install missing dependencies", "Check requirements.txt"], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        mock_result.score = 0.8

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        recommendations = await failure_pattern_store.get_recovery_recommendations(
            failure_context="Module import fails due to missing dependencies",
            pattern_type="import_error",
            num_recommendations=5,
        )

        assert len(recommendations) > 0
        assert "recommendation" in recommendations[0]
        assert "pattern_type" in recommendations[0]
        assert "confidence" in recommendations[0]
        assert "frequency" in recommendations[0]


class TestStatistics:
    """Test pattern statistics."""

    @pytest.mark.asyncio
    async def test_get_pattern_statistics(self, failure_pattern_store, mock_client):
        """Test getting pattern statistics."""
        # Mock multiple patterns
        mock_results = [
            MagicMock(
                content='{"type": "failure_pattern", "pattern_type": "type_error", "description": "Type error 1", "frequency": 5, "confidence": 0.9, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}',
                score=0.9,
            ),
            MagicMock(
                content='{"type": "failure_pattern", "pattern_type": "type_error", "description": "Type error 2", "frequency": 3, "confidence": 0.75, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}',
                score=0.75,
            ),
            MagicMock(
                content='{"type": "failure_pattern", "pattern_type": "import_error", "description": "Import error 1", "frequency": 2, "confidence": 0.6, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}',
                score=0.6,
            ),
        ]

        mock_client.graphiti.search = AsyncMock(return_value=mock_results)

        stats = await failure_pattern_store.get_pattern_statistics()

        assert stats["total_patterns"] == 3
        assert "type_error" in stats["patterns_by_type"]
        assert "import_error" in stats["patterns_by_type"]
        assert stats["patterns_by_type"]["type_error"] == 2
        assert stats["patterns_by_type"]["import_error"] == 1
        assert len(stats["most_common_patterns"]) > 0
        assert stats["high_frequency_patterns"] == 2  # Patterns with frequency >= 3
        assert stats["average_confidence"] > 0

    @pytest.mark.asyncio
    async def test_get_pattern_statistics_empty(
        self, failure_pattern_store, mock_client
    ):
        """Test statistics with no patterns."""
        mock_client.graphiti.search = AsyncMock(return_value=[])

        stats = await failure_pattern_store.get_pattern_statistics()

        assert stats["total_patterns"] == 0
        assert stats["patterns_by_type"] == {}
        assert stats["most_common_patterns"] == []
        assert stats["high_frequency_patterns"] == 0
        assert stats["average_confidence"] == pytest.approx(0.0)


class TestHighFrequencyPatterns:
    """Test high-frequency pattern queries."""

    @pytest.mark.asyncio
    async def test_get_high_frequency_patterns(
        self, failure_pattern_store, mock_client
    ):
        """Test getting high-frequency patterns."""
        mock_result = MagicMock()
        mock_result.content = '{"type": "failure_pattern", "pattern_type": "recurring_error", "description": "Frequent error", "frequency": 5, "confidence": 0.8, "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-05T00:00:00Z", "affected_subtasks": [], "recovery_recommendations": [], "timestamp": "2024-01-01T00:00:00Z", "spec_id": "test"}'
        mock_result.score = 0.8

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.get_high_frequency_patterns(
            min_frequency=3,
            min_confidence=0.7,
            num_results=10,
        )

        assert len(patterns) == 1
        assert patterns[0]["frequency"] >= 3


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_query_filters_non_pattern_results(
        self, failure_pattern_store, mock_client
    ):
        """Test that non-failure-pattern results are filtered out."""
        # Mock result with wrong type
        mock_result = MagicMock()
        mock_result.content = (
            '{"type": "other_type", "description": "Not a failure pattern"}'
        )
        mock_result.score = 0.5

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.query_failure_patterns(
            query="test",
            num_results=10,
        )

        # Should return empty list (non-pattern filtered out)
        assert len(patterns) == 0

    @pytest.mark.asyncio
    async def test_query_handles_invalid_json(self, failure_pattern_store, mock_client):
        """Test that invalid JSON is handled gracefully."""
        mock_result = MagicMock()
        mock_result.content = "invalid json {{{"
        mock_result.score = 0.5

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.query_failure_patterns(
            query="test",
            num_results=10,
        )

        # Should skip invalid results
        assert len(patterns) == 0

    @pytest.mark.asyncio
    async def test_query_handles_empty_content(
        self, failure_pattern_store, mock_client
    ):
        """Test that empty content is handled gracefully."""
        mock_result = MagicMock()
        mock_result.content = None
        mock_result.fact = None
        mock_result.score = 0.5

        mock_client.graphiti.search = AsyncMock(return_value=[mock_result])

        patterns = await failure_pattern_store.query_failure_patterns(
            query="test",
            num_results=10,
        )

        # Should skip empty results
        assert len(patterns) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
