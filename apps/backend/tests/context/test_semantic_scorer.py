#!/usr/bin/env python3
"""
Unit tests for Semantic Scorer
==============================

Tests the SemanticScorer class for computing semantic relevance scores
using embeddings and cosine similarity.
"""

# IMPORTANT: This sys.path manipulation must happen BEFORE importing pytest
# to ensure we import from the actual context module, not tests.context
import sys
from pathlib import Path


def _configure_sys_path() -> None:
    """Configure sys.path to import from the actual context module."""
    for td in [p for p in sys.path if "tests" in p]:
        if td in sys.path:
            sys.path.remove(td)
    backend_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_root))


_configure_sys_path()

from unittest.mock import AsyncMock, MagicMock

import pytest
from context.semantic_scorer import SemanticScorer


@pytest.fixture
def mock_embedder():
    """Create a mock embedder for testing."""
    embedder = MagicMock()
    embedder.embed = AsyncMock()
    return embedder


@pytest.fixture
def scorer(mock_embedder):
    """Create a SemanticScorer instance with mock embedder."""
    return SemanticScorer(mock_embedder)


class TestSemanticScorerInitialization:
    """Test suite for SemanticScorer initialization."""

    def test_initialization_with_embedder(self, mock_embedder):
        """Test SemanticScorer initialization with embedder."""
        scorer = SemanticScorer(mock_embedder)
        assert scorer.embedder == mock_embedder

    def test_initialization_with_none_embedder(self):
        """Test SemanticScorer initialization with None embedder."""
        scorer = SemanticScorer(None)
        assert scorer.embedder is None


class TestCosineSimilarity:
    """Test suite for cosine similarity computation."""

    def test_cosine_similarity_identical_vectors(self, scorer):
        """Test cosine similarity of identical vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]

        score = scorer._cosine_similarity(vec1, vec2)

        # Identical vectors should have similarity of 1.0
        assert score == pytest.approx(1.0, rel=1e-5)

    def test_cosine_similarity_orthogonal_vectors(self, scorer):
        """Test cosine similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        score = scorer._cosine_similarity(vec1, vec2)

        # Orthogonal vectors should have similarity of 0.0
        assert score == pytest.approx(0.0, rel=1e-5)

    def test_cosine_similarity_opposite_vectors(self, scorer):
        """Test cosine similarity of opposite vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]

        score = scorer._cosine_similarity(vec1, vec2)

        # Opposite vectors should have similarity of -1.0, but clamped to 0.0
        assert score == 0.0

    def test_cosine_similarity_partial_similarity(self, scorer):
        """Test cosine similarity with partially similar vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [2.0, 4.0, 5.0]

        score = scorer._cosine_similarity(vec1, vec2)

        # Should be between 0 and 1
        assert 0.0 < score < 1.0

    def test_cosine_similarity_zero_vector(self, scorer):
        """Test cosine similarity with zero vector."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [0.0, 0.0, 0.0]

        score = scorer._cosine_similarity(vec1, vec2)

        # Zero vector should return 0.0
        assert score == 0.0

    def test_cosine_similarity_both_zero_vectors(self, scorer):
        """Test cosine similarity with both zero vectors."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [0.0, 0.0, 0.0]

        score = scorer._cosine_similarity(vec1, vec2)

        # Both zero vectors should return 0.0
        assert score == 0.0

    def test_cosine_similarity_negative_values(self, scorer):
        """Test cosine similarity with negative values."""
        vec1 = [1.0, -2.0, 3.0]
        vec2 = [-1.0, 2.0, -3.0]

        score = scorer._cosine_similarity(vec1, vec2)

        # Should handle negative values and clamp to [0, 1]
        assert 0.0 <= score <= 1.0

    def test_cosine_similarity_high_dimensional(self, scorer):
        """Test cosine similarity with high-dimensional vectors."""
        # Simulate embedding vectors (e.g., 1536 dimensions for OpenAI)
        vec1 = [float(i) for i in range(1536)]
        vec2 = [float(i) for i in range(1536)]

        score = scorer._cosine_similarity(vec1, vec2)

        # Identical high-dimensional vectors should have similarity of 1.0
        assert score == pytest.approx(1.0, rel=1e-5)

    def test_cosine_similarity_different_lengths_handled(self, scorer):
        """Test that different length vectors return a valid float without crashing."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]

        # numpy may broadcast or return a value; ensure we get a valid float
        score = scorer._cosine_similarity(vec1, vec2)
        assert isinstance(score, float)
        # Result should be clamped to [0, 1] regardless
        assert 0.0 <= score <= 1.0


class TestGetEmbedding:
    """Test suite for _get_embedding method."""

    @pytest.mark.asyncio
    async def test_get_embedding_with_dict_result(self, scorer, mock_embedder):
        """Test _get_embedding when embedder returns dict."""
        mock_embedder.embed.return_value = {"embedding": [0.1, 0.2, 0.3]}

        result = await scorer._get_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_embedder.embed.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_with_list_result(self, scorer, mock_embedder):
        """Test _get_embedding when embedder returns list."""
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

        result = await scorer._get_embedding("test text")

        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_get_embedding_with_object_result(self, scorer, mock_embedder):
        """Test _get_embedding when embedder returns object with embedding attribute."""
        mock_result = MagicMock()
        mock_result.embedding = [0.1, 0.2, 0.3]
        mock_embedder.embed.return_value = mock_result

        result = await scorer._get_embedding("test text")

        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_get_embedding_with_exception(self, scorer, mock_embedder):
        """Test _get_embedding when embedder raises exception."""
        mock_embedder.embed.side_effect = Exception("Embedding failed")

        result = await scorer._get_embedding("test text")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_embedding_no_embed_method(self):
        """Test _get_embedding when embedder has no embed method."""
        scorer = SemanticScorer(MagicMock(spec=[]))  # No embed method

        result = await scorer._get_embedding("test text")

        assert result is None


class TestScoreFiles:
    """Test suite for score_files method."""

    @pytest.mark.asyncio
    async def test_score_files_empty_list(self, scorer):
        """Test scoring empty file list."""
        result = await scorer.score_files([], "test query")

        assert result == []

    @pytest.mark.asyncio
    async def test_score_files_single_file(self, scorer, mock_embedder):
        """Test scoring a single file."""
        mock_embedder.embed.side_effect = [
            [0.1, 0.2, 0.3],  # Query embedding
            [0.1, 0.2, 0.3],  # File content embedding
        ]

        files = [{"path": "test.py", "content": "print('hello')"}]
        result = await scorer.score_files(files, "test query")

        assert len(result) == 1
        assert "semantic_score" in result[0]
        assert result[0]["path"] == "test.py"
        assert result[0]["semantic_score"] == pytest.approx(1.0, rel=1e-5)

    @pytest.mark.asyncio
    async def test_score_files_multiple_files(self, scorer, mock_embedder):
        """Test scoring multiple files."""
        # Query embedding
        # File 1 embedding (similar)
        # File 2 embedding (less similar)
        mock_embedder.embed.side_effect = [
            [1.0, 0.0, 0.0],  # Query
            [1.0, 0.0, 0.0],  # File 1 (identical to query)
            [0.0, 1.0, 0.0],  # File 2 (orthogonal to query)
        ]

        files = [
            {"path": "file1.py", "content": "matching content"},
            {"path": "file2.py", "content": "different content"},
        ]
        result = await scorer.score_files(files, "test query")

        assert len(result) == 2
        # First file should have higher score (sorted by score descending)
        assert result[0]["path"] == "file1.py"
        assert result[1]["path"] == "file2.py"
        assert result[0]["semantic_score"] > result[1]["semantic_score"]

    @pytest.mark.asyncio
    async def test_score_files_with_max_results(self, scorer, mock_embedder):
        """Test score_files with max_results limit."""
        mock_embedder.embed.side_effect = [
            [1.0, 0.0, 0.0],  # Query
            [1.0, 0.0, 0.0],  # File 1
            [0.9, 0.1, 0.0],  # File 2
            [0.8, 0.2, 0.0],  # File 3
        ]

        files = [{"path": f"file{i}.py", "content": f"content {i}"} for i in range(3)]
        result = await scorer.score_files(files, "test query", max_results=2)

        assert len(result) == 2
        assert result[0]["path"] == "file0.py"

    @pytest.mark.asyncio
    async def test_score_files_with_empty_content(self, scorer, mock_embedder):
        """Test scoring files with empty content."""
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

        files = [
            {"path": "empty.py", "content": ""},
            {"path": "valid.py", "content": "print('hello')"},
        ]
        result = await scorer.score_files(files, "test query")

        assert len(result) == 2
        # Empty content file should have score of 0.0
        empty_file = next(f for f in result if f["path"] == "empty.py")
        assert empty_file["semantic_score"] == 0.0

    @pytest.mark.asyncio
    async def test_score_files_query_embedding_fails(self, scorer, mock_embedder):
        """Test when query embedding fails."""
        mock_embedder.embed.return_value = None

        files = [{"path": "test.py", "content": "content"}]
        result = await scorer.score_files(files, "test query")

        assert len(result) == 1
        # All files should have score of 0.0
        assert result[0]["semantic_score"] == 0.0

    @pytest.mark.asyncio
    async def test_score_files_file_embedding_fails(self, scorer, mock_embedder):
        """Test when file embedding fails."""
        mock_embedder.embed.side_effect = [
            [0.1, 0.2, 0.3],  # Query embedding succeeds
            None,  # File embedding fails
        ]

        files = [{"path": "test.py", "content": "content"}]
        result = await scorer.score_files(files, "test query")

        assert len(result) == 1
        # File should have score of 0.0
        assert result[0]["semantic_score"] == 0.0

    @pytest.mark.asyncio
    async def test_score_files_preserves_original_fields(self, scorer, mock_embedder):
        """Test that scoring preserves original file dict fields."""
        mock_embedder.embed.side_effect = [
            [0.1, 0.2, 0.3],
            [0.1, 0.2, 0.3],
        ]

        files = [
            {
                "path": "test.py",
                "content": "print('hello')",
                "language": "python",
                "line_count": 42,
            }
        ]
        result = await scorer.score_files(files, "test query")

        assert len(result) == 1
        assert result[0]["path"] == "test.py"
        assert result[0]["language"] == "python"
        assert result[0]["line_count"] == 42
        assert "semantic_score" in result[0]

    @pytest.mark.asyncio
    async def test_score_files_handles_exception(self, scorer, mock_embedder):
        """Test that score_files handles exceptions gracefully."""
        mock_embedder.embed.side_effect = Exception("Embedding service down")

        files = [{"path": "test.py", "content": "content"}]
        result = await scorer.score_files(files, "test query")

        # Should return files with zero scores instead of crashing
        assert len(result) == 1
        assert result[0]["semantic_score"] == 0.0


class TestScoreQueryPairs:
    """Test suite for score_query_pairs method."""

    @pytest.mark.asyncio
    async def test_score_query_pairs_empty_lists(self, scorer):
        """Test scoring with empty query or document lists."""
        result1 = await scorer.score_query_pairs([], ["doc1"])
        assert result1 == []

        result2 = await scorer.score_query_pairs(["query1"], [])
        assert result2 == []

    @pytest.mark.asyncio
    async def test_score_query_pairs_single_query_single_doc(
        self, scorer, mock_embedder
    ):
        """Test scoring single query-document pair."""
        mock_embedder.embed.side_effect = [
            [1.0, 0.0],  # Query embedding
            [1.0, 0.0],  # Document embedding
        ]

        queries = ["test query"]
        documents = ["test document"]
        result = await scorer.score_query_pairs(queries, documents)

        assert len(result) == 1
        assert result[0][0] == "test query"
        assert result[0][1] == "test document"
        assert result[0][2] == pytest.approx(1.0, rel=1e-5)

    @pytest.mark.asyncio
    async def test_score_query_pairs_multiple_queries_multiple_docs(
        self, scorer, mock_embedder
    ):
        """Test scoring multiple query-document pairs."""
        mock_embedder.embed.side_effect = [
            [1.0, 0.0],  # Query 1
            [0.0, 1.0],  # Query 2
            [1.0, 0.0],  # Doc 1
            [0.0, 1.0],  # Doc 2
        ]

        queries = ["query 1", "query 2"]
        documents = ["doc 1", "doc 2"]
        result = await scorer.score_query_pairs(queries, documents)

        # Should have 2x2 = 4 pairs
        assert len(result) == 4

        # Check that we have all combinations
        query_doc_pairs = [(q, d) for q, d, _ in result]
        assert ("query 1", "doc 1") in query_doc_pairs
        assert ("query 1", "doc 2") in query_doc_pairs
        assert ("query 2", "doc 1") in query_doc_pairs
        assert ("query 2", "doc 2") in query_doc_pairs

    @pytest.mark.asyncio
    async def test_score_query_pairs_with_failed_embedding(self, scorer, mock_embedder):
        """Test when some embeddings fail."""
        mock_embedder.embed.side_effect = [
            [1.0, 0.0],  # Query 1 succeeds
            None,  # Query 2 fails
            [1.0, 0.0],  # Doc 1 succeeds
            None,  # Doc 2 fails
        ]

        queries = ["query 1", "query 2"]
        documents = ["doc 1", "doc 2"]
        result = await scorer.score_query_pairs(queries, documents)

        assert len(result) == 4

        # Pairs with successful embeddings should have scores
        q1_d1 = next(r for r in result if r[0] == "query 1" and r[1] == "doc 1")
        assert q1_d1[2] > 0

        # Pairs with failed embeddings should have 0.0 score
        q2_d1 = next(r for r in result if r[0] == "query 2" and r[1] == "doc 1")
        assert q2_d1[2] == 0.0

    @pytest.mark.asyncio
    async def test_score_query_pairs_handles_exception(self, scorer, mock_embedder):
        """Test that score_query_pairs handles exceptions gracefully."""
        mock_embedder.embed.side_effect = Exception("Service error")

        queries = ["query 1"]
        documents = ["doc 1"]
        result = await scorer.score_query_pairs(queries, documents)

        # Should return zero scores instead of crashing
        assert len(result) == 1
        assert result[0][2] == 0.0


class TestAddZeroScores:
    """Test suite for _add_zero_scores method."""

    def test_add_zero_scores_empty_list(self, scorer):
        """Test adding zero scores to empty list."""
        result = scorer._add_zero_scores([])
        assert result == []

    def test_add_zero_scores_single_file(self, scorer):
        """Test adding zero score to single file."""
        files = [{"path": "test.py", "content": "print('hello')"}]
        result = scorer._add_zero_scores(files)

        assert len(result) == 1
        assert result[0]["semantic_score"] == 0.0
        assert result[0]["path"] == "test.py"

    def test_add_zero_scores_multiple_files(self, scorer):
        """Test adding zero scores to multiple files."""
        files = [
            {"path": "file1.py", "content": "content1"},
            {"path": "file2.py", "content": "content2"},
        ]
        result = scorer._add_zero_scores(files)

        assert len(result) == 2
        assert all(f["semantic_score"] == 0.0 for f in result)

    def test_add_zero_scores_does_not_mutate_original(self, scorer):
        """Test that _add_zero_scores does not mutate original list."""
        files = [{"path": "test.py", "content": "content"}]

        result = scorer._add_zero_scores(files)

        # Original files should not have semantic_score
        assert "semantic_score" not in files[0]
        # But result should
        assert "semantic_score" in result[0]


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_score_files_with_none_embedder(self):
        """Test score_files when embedder is None."""
        scorer = SemanticScorer(None)
        files = [{"path": "test.py", "content": "content"}]

        result = await scorer.score_files(files, "test query")

        # Should return files with zero scores
        assert len(result) == 1
        assert result[0]["semantic_score"] == 0.0

    @pytest.mark.asyncio
    async def test_score_files_with_special_characters(self, scorer, mock_embedder):
        """Test scoring files with special characters in content."""
        mock_embedder.embed.side_effect = [
            [0.1, 0.2, 0.3],
            [0.1, 0.2, 0.3],
        ]

        files = [
            {
                "path": "special.txt",
                "content": "Hello 世界 🌍\n\t新 lines\nSpecial chars: ©®™",
            }
        ]
        result = await scorer.score_files(files, "test query")

        assert len(result) == 1
        assert "semantic_score" in result[0]

    @pytest.mark.asyncio
    async def test_score_files_very_long_query(self, scorer, mock_embedder):
        """Test scoring with very long query."""
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

        long_query = "test " * 10000  # Very long query
        files = [{"path": "test.py", "content": "content"}]

        result = await scorer.score_files(files, long_query)

        assert len(result) == 1
        assert "semantic_score" in result[0]

    @pytest.mark.asyncio
    async def test_cosine_similarity_with_floats(self, scorer):
        """Test cosine similarity with various float values."""
        vec1 = [0.123456789, 0.987654321, 0.555555555]
        vec2 = [0.987654321, 0.123456789, 0.555555555]

        score = scorer._cosine_similarity(vec1, vec2)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_cosine_similarity_with_nan_values(self, scorer):
        """Test cosine similarity handles NaN values gracefully."""
        vec1 = [float("nan"), 1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]

        score = scorer._cosine_similarity(vec1, vec2)

        # Should handle gracefully (return 0.0 or handle appropriately)
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_score_files_with_missing_content_key(self, scorer, mock_embedder):
        """Test scoring files without 'content' key."""
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

        files = [{"path": "test.py"}]  # No 'content' key
        result = await scorer.score_files(files, "test query")

        assert len(result) == 1
        # Should treat missing content as empty and give score of 0.0
        assert result[0]["semantic_score"] == 0.0


class TestIntegrationBehavior:
    """Test suite for integration-like behavior."""

    @pytest.mark.asyncio
    async def test_full_scoring_workflow(self, scorer, mock_embedder):
        """Test complete scoring workflow from files to ranked results."""
        # Setup: Create realistic embeddings
        mock_embedder.embed.side_effect = [
            [1.0, 0.0, 0.0, 0.0],  # Query: "authentication"
            [1.0, 0.0, 0.0, 0.0],  # auth.py (very relevant)
            [0.9, 0.1, 0.0, 0.0],  # login.py (relevant)
            [0.0, 1.0, 0.0, 0.0],  # database.py (somewhat relevant)
            [0.0, 0.0, 1.0, 0.0],  # ui.py (not relevant)
        ]

        files = [
            {"path": "src/auth.py", "content": "Authentication logic"},
            {"path": "src/login.py", "content": "Login handling"},
            {"path": "src/database.py", "content": "Database connection"},
            {"path": "src/ui.py", "content": "User interface"},
        ]

        result = await scorer.score_files(files, "authentication", max_results=3)

        # Verify results are sorted by relevance
        assert len(result) == 3
        assert result[0]["path"] == "src/auth.py"  # Most relevant
        assert result[0]["semantic_score"] > result[1]["semantic_score"]

    @pytest.mark.asyncio
    async def test_realistic_token_estimation_scenario(self, scorer, mock_embedder):
        """Test realistic scenario for context window optimization."""
        # Simulate a real task: "Add caching to API"
        mock_embedder.embed.side_effect = [
            [1.0, 0.5, 0.0],  # Query
            [1.0, 0.5, 0.0],  # cache.py (perfect match)
            [0.9, 0.4, 0.1],  # api.py (relevant)
            [0.5, 0.5, 0.0],  # redis.py (somewhat relevant)
            [0.0, 0.0, 1.0],  # frontend.py (not relevant)
            [0.0, 1.0, 0.0],  # test.py (not relevant)
        ]

        files = [
            {
                "path": "backend/cache.py",
                "content": "Cache implementation",
                "tokens": 500,
            },
            {"path": "backend/api.py", "content": "API endpoints", "tokens": 1000},
            {"path": "backend/redis.py", "content": "Redis client", "tokens": 300},
            {"path": "frontend/app.js", "content": "Frontend code", "tokens": 2000},
            {"path": "tests/api_test.py", "content": "API tests", "tokens": 400},
        ]

        result = await scorer.score_files(files, "Add caching to API")

        # Most relevant files should be ranked higher
        top_files = result[:3]
        paths = [f["path"] for f in top_files]

        assert "backend/cache.py" in paths
        assert "backend/api.py" in paths

        # Scores should be in descending order
        for i in range(len(result) - 1):
            assert result[i]["semantic_score"] >= result[i + 1]["semantic_score"]
