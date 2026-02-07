"""
Tests for impact analysis and dependency traversal operations.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .impact_analyzer import ImpactAnalyzer


@pytest.fixture
def mock_client():
    """Create a mock Graphiti client."""
    client = MagicMock()
    client.graphiti = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_calculate_impact(mock_client):
    """Test calculating impact of changing a function."""
    # Mock the code_relationships query methods
    mock_code_relationships = AsyncMock()

    # Nested callers (functions that call the callers)
    async def mock_find_callers_nested(function_name):
        if function_name == "target_function":
            return [
                {
                    "caller": "function_a",
                    "file_path": "module_a.py",
                    "lineno": 10,
                },
                {
                    "caller": "function_b",
                    "file_path": "module_b.py",
                    "lineno": 20,
                },
            ]
        elif function_name == "function_a":
            return [
                {
                    "caller": "main",
                    "file_path": "main.py",
                    "lineno": 5,
                }
            ]
        elif function_name == "function_b":
            return []
        return []

    mock_code_relationships.find_callers = mock_find_callers_nested

    # Set up the mock client with code_relationships
    mock_client.code_relationships = mock_code_relationships

    # Create impact analyzer with properly mocked client
    with tempfile.TemporaryDirectory() as tmpdir:
        impact_analyzer = ImpactAnalyzer(
            client=mock_client,
            group_id="test-group",
            spec_context_id="test-spec",
            project_dir=Path(tmpdir),
        )

        # Calculate impact of changing "target_function"
        impact = await impact_analyzer.calculate_impact(
            entity_name="target_function",
            entity_type="function",
            max_depth=2,
        )

        # Verify impact results
        assert impact is not None
        assert "affected_entities" in impact
        assert "impact_score" in impact
        assert "depth_analysis" in impact

        # Should find at least the direct callers
        affected = impact["affected_entities"]
        assert len(affected) >= 2

        # Check that we have the expected functions
        affected_names = [e["name"] for e in affected]
        assert "function_a" in affected_names
        assert "function_b" in affected_names

        # Verify impact score is calculated
        assert isinstance(impact["impact_score"], (int, float))
        assert impact["impact_score"] >= 0


@pytest.mark.asyncio
async def test_calculate_impact_with_depth(mock_client):
    """Test impact calculation respects max_depth parameter."""
    mock_code_relationships = AsyncMock()

    # Create a chain: main -> func_a -> func_b -> target_function
    async def mock_find_callers(function_name):
        if function_name == "target_function":
            return [{"caller": "func_b", "file_path": "b.py", "lineno": 1}]
        elif function_name == "func_b":
            return [{"caller": "func_a", "file_path": "a.py", "lineno": 1}]
        elif function_name == "func_a":
            return [{"caller": "main", "file_path": "main.py", "lineno": 1}]
        return []

    mock_code_relationships.find_callers = mock_find_callers
    mock_client.code_relationships = mock_code_relationships

    with tempfile.TemporaryDirectory() as tmpdir:
        impact_analyzer = ImpactAnalyzer(
            client=mock_client,
            group_id="test-group",
            spec_context_id="test-spec",
            project_dir=Path(tmpdir),
        )

        # With depth=1, should only find func_b
        impact1 = await impact_analyzer.calculate_impact(
            entity_name="target_function",
            entity_type="function",
            max_depth=1,
        )

        affected_names1 = [e["name"] for e in impact1["affected_entities"]]
        assert "func_b" in affected_names1
        assert "func_a" not in affected_names1

        # With depth=2, should find func_b and func_a
        impact2 = await impact_analyzer.calculate_impact(
            entity_name="target_function",
            entity_type="function",
            max_depth=2,
        )

        affected_names2 = [e["name"] for e in impact2["affected_entities"]]
        assert "func_b" in affected_names2
        assert "func_a" in affected_names2


@pytest.mark.asyncio
async def test_calculate_impact_no_callers(mock_client):
    """Test impact calculation when function has no callers."""
    mock_code_relationships = AsyncMock()
    mock_code_relationships.find_callers = AsyncMock(return_value=[])
    mock_client.code_relationships = mock_code_relationships

    with tempfile.TemporaryDirectory() as tmpdir:
        impact_analyzer = ImpactAnalyzer(
            client=mock_client,
            group_id="test-group",
            spec_context_id="test-spec",
            project_dir=Path(tmpdir),
        )

        impact = await impact_analyzer.calculate_impact(
            entity_name="unused_function",
            entity_type="function",
            max_depth=2,
        )

        assert impact is not None
        assert len(impact["affected_entities"]) == 0
        assert impact["impact_score"] == 0


@pytest.mark.asyncio
async def test_calculate_impact_error_handling(mock_client):
    """Test impact calculation handles errors gracefully."""
    mock_code_relationships = AsyncMock()
    mock_code_relationships.find_callers = AsyncMock(
        side_effect=Exception("Database error")
    )
    mock_client.code_relationships = mock_code_relationships

    with tempfile.TemporaryDirectory() as tmpdir:
        impact_analyzer = ImpactAnalyzer(
            client=mock_client,
            group_id="test-group",
            spec_context_id="test-spec",
            project_dir=Path(tmpdir),
        )

        impact = await impact_analyzer.calculate_impact(
            entity_name="target_function",
            entity_type="function",
            max_depth=2,
        )

        # Should return empty results on error, not crash
        assert impact is not None
        assert len(impact["affected_entities"]) == 0
        assert impact["impact_score"] == 0
