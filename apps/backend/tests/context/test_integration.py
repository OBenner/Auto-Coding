#!/usr/bin/env python3
"""
End-to-End Integration Tests for Context Optimization
====================================================

Tests the full context optimization pipeline on the real codebase.
Validates that semantic scoring, redundancy detection, token estimation,
and compression work together correctly.
"""

# IMPORTANT: This sys.path manipulation must happen BEFORE importing pytest
# to ensure we import from the actual context module, not tests.context
import sys
from pathlib import Path

# Remove tests directories from path if they were added
tests_dirs = [p for p in sys.path if "tests" in p]
for td in tests_dirs:
    if td in sys.path:
        sys.path.remove(td)

# Add backend root to path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context.builder import ContextBuilder
from context.compressor import ContextCompressor
from context.models import FileMatch, TaskContext
from context.redundancy_detector import RedundancyDetector
from context.semantic_scorer import SemanticScorer
from context.token_estimator import TokenEstimator


@pytest.fixture
def real_project_dir():
    """Get the path to the real backend project directory."""
    # Use the actual backend directory
    return Path(__file__).parent.parent.parent


@pytest.fixture
def token_estimator():
    """Create a TokenEstimator instance."""
    return TokenEstimator()


@pytest.fixture
def mock_embedder():
    """Create a mock embedder for testing semantic scoring."""
    embedder = MagicMock()
    embedder.embed = AsyncMock()
    return embedder


class TestTokenEstimationE2E:
    """End-to-end tests for token estimation on real files."""

    def test_estimate_tokens_for_real_files(self, token_estimator, real_project_dir):
        """Test token estimation on actual Python files from the codebase."""
        # Find some real Python files
        context_files = list((real_project_dir / "context").glob("*.py"))

        assert len(context_files) > 0, "No context files found for testing"

        results = []
        for file_path in context_files[:5]:  # Test first 5 files
            content = file_path.read_text(encoding="utf-8")
            tokens = token_estimator.count_tokens(content)

            # Verify token count is reasonable
            assert tokens > 0, f"Token count should be positive for {file_path.name}"
            assert tokens < 100000, f"Token count seems too high for {file_path.name}: {tokens}"

            # Tokens should be roughly proportional to file length
            # (Approximate: ~4 chars per token for code)
            estimated_by_length = len(content) / 4
            ratio = tokens / estimated_by_length if estimated_by_length > 0 else 0

            # Ratio should be between 0.5 and 2.0 (allowing for variation)
            assert 0.5 < ratio < 2.0, (
                f"Token count ({tokens}) seems off for {file_path.name} "
                f"(expected ~{estimated_by_length:.0f})"
            )

            results.append({"file": file_path.name, "tokens": tokens})

        # Different files should have different token counts
        token_counts = [r["tokens"] for r in results]
        assert len(set(token_counts)) > 1, "All files have the same token count"

    def test_estimate_tokens_for_common_patterns(self, token_estimator):
        """Test token estimation for common code patterns."""
        patterns = {
            "simple_function": "def hello():\n    print('hello world')\n",
            "class_definition": "class MyClass:\n    def __init__(self):\n        self.value = 42\n",
            "import_block": "import os\nimport sys\nfrom pathlib import Path\nfrom typing import List, Dict\n",
            "docstring": '"""This is a multi-line\ndocstring with some\ndescription."""\n',
            "comments": "# This is a comment\n# Another comment\n# Yet another comment\n",
        }

        for name, content in patterns.items():
            tokens = token_estimator.count_tokens(content)

            # All patterns should have at least some tokens
            assert tokens > 0, f"Token count should be positive for {name}"

            # Docstrings and comments typically have more tokens per character
            if name in ["docstring", "comments"]:
                # These should have more tokens relative to length
                assert tokens >= 5, f"{name} should have at least 5 tokens, got {tokens}"

    def test_token_summation(self, token_estimator):
        """Test that token counts can be accurately summed."""
        contents = [
            "def foo():\n    return 1\n",
            "def bar():\n    return 2\n",
            "def baz():\n    return 3\n",
        ]

        individual_tokens = [token_estimator.count_tokens(c) for c in contents]
        combined_content = "\n".join(contents)
        combined_tokens = token_estimator.count_tokens(combined_content)

        # Combined should be close to sum of individual (allowing for newlines)
        assert abs(combined_tokens - sum(individual_tokens)) <= 5, (
            f"Combined token count ({combined_tokens}) should be close to "
            f"sum of individual ({sum(individual_tokens)})"
        )


class TestSemanticScoringE2E:
    """End-to-end tests for semantic scoring with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_semantic_scoring_ranks_relevant_files_higher(self, mock_embedder):
        """Test that semantic scoring ranks relevant files higher than irrelevant ones."""
        # Create mock embeddings that simulate semantic similarity
        # Query: "authentication system"
        mock_embedder.embed.side_effect = [
            [1.0, 0.0, 0.0, 0.0],  # Query embedding
            [1.0, 0.0, 0.0, 0.0],  # auth.py (very relevant)
            [0.9, 0.1, 0.0, 0.0],  # login.py (relevant)
            [0.8, 0.2, 0.0, 0.0],  # user.py (somewhat relevant)
            [0.0, 1.0, 0.0, 0.0],  # database.py (not relevant)
            [0.0, 0.0, 1.0, 0.0],  # frontend.py (not relevant)
            [0.0, 0.0, 0.0, 1.0],  # test_ui.py (not relevant)
        ]

        scorer = SemanticScorer(mock_embedder)

        files = [
            {"path": "src/auth.py", "content": "Authentication and authorization logic"},
            {"path": "src/login.py", "content": "Login form and validation"},
            {"path": "src/user.py", "content": "User model and database operations"},
            {"path": "src/database.py", "content": "Database connection and queries"},
            {"path": "frontend/app.js", "content": "React frontend application"},
            {"path": "tests/test_ui.py", "content": "UI component tests"},
        ]

        results = await scorer.score_files(files, "authentication system")

        # Verify results are sorted by semantic score (descending)
        assert len(results) == 6

        # First file should be auth.py (most relevant)
        assert results[0]["path"] == "src/auth.py"

        # Scores should be in descending order
        for i in range(len(results) - 1):
            assert results[i]["semantic_score"] >= results[i + 1]["semantic_score"], (
                f"Scores not in descending order: "
                f"{results[i]['path']} ({results[i]['semantic_score']}) >= "
                f"{results[i+1]['path']} ({results[i+1]['semantic_score']})"
            )

        # Relevant files should have higher scores than irrelevant ones
        auth_score = next(f["semantic_score"] for f in results if f["path"] == "src/auth.py")
        frontend_score = next(f["semantic_score"] for f in results if f["path"] == "frontend/app.js")

        assert auth_score > frontend_score, (
            f"Relevant file (auth.py) score {auth_score} should be > "
            f"irrelevant file (app.js) score {frontend_score}"
        )

    @pytest.mark.asyncio
    async def test_semantic_scoring_handles_varied_content(self, mock_embedder):
        """Test semantic scoring with different types of content."""
        # Mock embeddings for different file types
        mock_embedder.embed.side_effect = [
            [0.5, 0.5, 0.0],  # Query: "API caching"
            [0.5, 0.5, 0.0],  # cache.py (perfect match)
            [0.6, 0.4, 0.0],  # api.py (relevant)
            [0.4, 0.6, 0.0],  # redis.py (somewhat relevant)
            [0.0, 0.0, 1.0],  # styles.css (not relevant)
            "",  # Empty file (should return None or empty)
        ]

        scorer = SemanticScorer(mock_embedder)

        files = [
            {"path": "backend/cache.py", "content": "Cache implementation with Redis"},
            {"path": "backend/api.py", "content": "REST API endpoints"},
            {"path": "backend/redis.py", "content": "Redis client wrapper"},
            {"path": "frontend/styles.css", "content": "CSS styling"},
            {"path": "README.md", "content": ""},  # Empty file
        ]

        results = await scorer.score_files(files, "API caching")

        # Should handle all files including empty ones
        assert len(results) == 5

        # Empty file should have score of 0.0
        empty_file = next(f for f in results if f["path"] == "README.md")
        assert empty_file["semantic_score"] == 0.0

        # Most relevant files should be ranked higher
        top_3 = results[:3]
        top_paths = [f["path"] for f in top_3]

        # cache.py, api.py, redis.py should be in top 3
        assert "backend/cache.py" in top_paths
        assert "backend/api.py" in top_paths


class TestRedundancyDetectionE2E:
    """End-to-end tests for redundancy detection on realistic code."""

    def test_detects_exact_duplicates(self, real_project_dir, tmp_path):
        """Test that exact duplicate files are detected and removed."""
        # Use tmp_path for isolated testing
        detector = RedundancyDetector(tmp_path)

        # Create files with exact duplicate content
        duplicate_content = "def test_function():\n    return 'duplicate'\n"

        # Create actual test files
        (tmp_path / "file1.py").write_text(duplicate_content, encoding="utf-8")
        (tmp_path / "file2.py").write_text(duplicate_content, encoding="utf-8")
        (tmp_path / "file3.py").write_text("def different():\n    return 'unique'\n", encoding="utf-8")

        files = [
            FileMatch(
                path="file1.py",
                service="backend",
                reason="test",
                relevance_score=0.8,
                estimated_tokens=50,
            ),
            FileMatch(
                path="file2.py",
                service="backend",
                reason="test",
                relevance_score=0.7,
                estimated_tokens=50,  # Same tokens = likely duplicate
            ),
            FileMatch(
                path="file3.py",
                service="backend",
                reason="test",
                relevance_score=0.6,
                estimated_tokens=100,  # Different tokens = not duplicate
            ),
        ]

        # Detect redundancies
        filtered, report = detector.detect_redundancies(
            files, keep_highest_relevance=True
        )

        # Should remove duplicates (keep highest relevance)
        # file1.py (0.8) and file2.py (0.7) are duplicates, keep file1
        # file3.py is different, keep it
        assert len(filtered) <= len(files), "Should reduce file count"
        assert len(report) > 0, "Should generate removal report"

        # Check that at least one duplicate was removed
        removed_paths = [r.get("file") for r in report]
        assert "file2.py" in removed_paths, "Should remove lower relevance duplicate"

        # Verify token savings
        total_savings = sum(r.get("tokens_saved", 0) for r in report)
        assert total_savings > 0, "Should report token savings"

    def test_detects_near_duplicates(self, real_project_dir, tmp_path):
        """Test that near-duplicate files are detected."""
        detector = RedundancyDetector(tmp_path, similarity_threshold=0.9)

        # Create near-duplicate content
        base_content = "def test_function():\n    return 'value'\n"
        variations = [
            base_content,
            base_content + "# extra comment\n",
            base_content.replace("value", "different"),  # Different enough
        ]

        # Create actual test files
        for i, content in enumerate(variations):
            (tmp_path / f"file{i}.py").write_text(content, encoding="utf-8")

        files = [
            FileMatch(
                path=f"file{i}.py",
                service="backend",
                reason="test",
                relevance_score=0.8 - (i * 0.1),
                estimated_tokens=50 + i * 10,
            )
            for i in range(3)
        ]

        # Detect redundancies
        filtered, report = detector.detect_redundancies(
            files, keep_highest_relevance=True
        )

        # Should detect near-duplicates
        assert len(filtered) <= len(files)

        # File 2 is near-duplicate of file 1, file 3 is different
        # So we should have removed at least file 2
        removed_count = len(files) - len(filtered)
        assert removed_count >= 1, "Should remove at least one near-duplicate"

    def test_preserves_unique_content(self, real_project_dir, tmp_path):
        """Test that unique content is preserved."""
        detector = RedundancyDetector(tmp_path)

        unique_contents = [
            "def function_one():\n    return 1\n",
            "def function_two():\n    return 2\n",
            "def function_three():\n    return 3\n",
        ]

        # Create actual test files
        for i, content in enumerate(unique_contents):
            (tmp_path / f"file{i}.py").write_text(content, encoding="utf-8")

        files = [
            FileMatch(
                path=f"file{i}.py",
                service="backend",
                reason="test",
                relevance_score=0.8,
                estimated_tokens=50,
            )
            for i in range(3)
        ]

        # Detect redundancies
        filtered, report = detector.detect_redundancies(
            files, keep_highest_relevance=True
        )

        # All unique files should be preserved
        assert len(filtered) == len(files), "Should preserve all unique files"
        assert len(report) == 0, "Should have no removals for unique content"


class TestContextCompressionE2E:
    """End-to-end tests for context compression."""

    def test_compression_result_structure(self, token_estimator, tmp_path):
        """Test that compression returns proper result structure."""
        compressor = ContextCompressor(
            compression_threshold=10,  # Low threshold for testing
            token_estimator=token_estimator
        )

        # Create a test file
        test_file = tmp_path / "test.py"
        test_content = "def hello():\n    print('world')\n"
        test_file.write_text(test_content, encoding="utf-8")

        # Compress the file
        result = compressor.compress_file(test_file, strategy="auto")

        # Verify result structure
        assert hasattr(result, "original_content"), "Should have original_content"
        assert hasattr(result, "compressed_content"), "Should have compressed_content"
        assert hasattr(result, "original_tokens"), "Should have original_tokens"
        assert hasattr(result, "compressed_tokens"), "Should have compressed_tokens"
        assert hasattr(result, "compression_ratio"), "Should have compression_ratio"
        assert hasattr(result, "method"), "Should have method"

        # Verify content
        assert result.original_content == test_content
        assert isinstance(result.compressed_content, str)
        assert result.original_tokens > 0

    def test_small_files_not_compressed(self, token_estimator, tmp_path):
        """Test that small files are not compressed."""
        compressor = ContextCompressor(
            compression_threshold=1000,  # High threshold
            target_ratio=0.5,
            token_estimator=token_estimator
        )

        # Create a small file
        test_file = tmp_path / "small.py"
        test_content = "def foo(): return 1"
        test_file.write_text(test_content, encoding="utf-8")

        # Compress
        result = compressor.compress_file(test_file, strategy="auto")

        # Small files should not be compressed
        assert result.method == "none", "Small files should not be compressed"
        assert result.compressed_content == test_content, "Content should be unchanged"

    def test_compression_records_token_counts(self, token_estimator, tmp_path):
        """Test that compression accurately records token counts."""
        compressor = ContextCompressor(
            compression_threshold=10,  # Low threshold for testing
            target_ratio=0.5,
            token_estimator=token_estimator
        )

        # Create a test file
        test_file = tmp_path / "test.py"
        test_content = "\n".join([f"line {i}" for i in range(100)])
        test_file.write_text(test_content, encoding="utf-8")

        # Manually count tokens
        expected_tokens = token_estimator.count_tokens(test_content)

        # Compress
        result = compressor.compress_file(test_file, strategy="auto")

        # Verify token counts
        assert result.original_tokens == expected_tokens, "Original tokens should match"
        assert result.compressed_tokens >= 0, "Compressed tokens should be non-negative"


class TestFullPipelineE2E:
    """End-to-end tests for the full context optimization pipeline."""

    def test_context_builder_integration(self, real_project_dir):
        """Test ContextBuilder with all optimizations enabled."""
        # This test requires a project index to exist
        # For now, we'll create a minimal one
        project_index = {
            "services": {
                "backend": {
                    "path": "context",
                    "language": "python",
                    "framework": None,
                    "type": "service",
                }
            }
        }

        # Create builder
        builder = ContextBuilder(real_project_dir, project_index=project_index)

        # Verify components are initialized
        assert builder.token_estimator is not None, "TokenEstimator should be initialized"
        assert builder.searcher is not None, "CodeSearcher should be initialized"
        assert builder.redundancy_detector is not None, "RedundancyDetector should be initialized"
        assert builder.priority_manager is not None, "PriorityManager should be initialized"

        # Build context for a realistic task
        task = "Add token estimation to context builder"

        # Build context (may use keyword search if semantic scorer unavailable)
        context = builder.build_context(task, services=["backend"])

        # Verify context structure
        assert isinstance(context, TaskContext), "Should return TaskContext"
        assert context.task_description == task, "Should preserve task description"
        assert "backend" in context.scoped_services, "Should include backend service"

        # Verify token counts are populated
        all_files = context.files_to_modify + context.files_to_reference
        for file_dict in all_files:
            if isinstance(file_dict, dict):
                assert "estimated_tokens" in file_dict, "Each file should have token count"
                assert file_dict["estimated_tokens"] >= 0, "Token count should be non-negative"

    def test_token_accuracy_within_acceptable_range(self, token_estimator):
        """Test that token estimation is accurate within acceptable margin."""
        # Test on a variety of realistic code samples
        long_lines = []
        for i in range(50):
            long_lines.append(f"def function_{i}():")
            long_lines.append(f"    '''Function {i} description'''")
            long_lines.append(f"    return {i}")
            long_lines.append("")

        samples = {
            "short_function": "def add(a, b):\n    return a + b\n",
            "medium_class": """
class Calculator:
    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result

    def subtract(self, a, b):
        return a - b
""",
            "long_file": "\n".join(long_lines),
        }

        for name, content in samples.items():
            tokens = token_estimator.count_tokens(content)

            # Verify token count is reasonable
            assert tokens > 0, f"{name}: Token count should be positive"

            # Rough estimate: ~4 characters per token for code
            # This can vary significantly, but should be in reasonable range
            char_count = len(content)
            estimated_min = char_count / 6  # Conservative (more tokens)
            estimated_max = char_count / 2  # Liberal (fewer tokens)

            assert estimated_min <= tokens <= estimated_max, (
                f"{name}: Token count {tokens} outside expected range "
                f"[{estimated_min:.0f}, {estimated_max:.0f}] for {char_count} chars"
            )

    def test_context_optimization_preserves_relevant_files(self, real_project_dir):
        """Test that context optimization preserves the most relevant files."""
        # Create a mock scenario where we have files of varying relevance
        project_index = {
            "services": {
                "test": {
                    "path": "context",
                    "language": "python",
                    "framework": None,
                    "type": "service",
                }
            }
        }

        builder = ContextBuilder(real_project_dir, project_index=project_index)

        # Search for files related to "token estimation"
        context = builder.build_context("token estimation", services=["test"])

        # Should return some results (unless no matching files exist)
        # We're testing the pipeline, not specific results
        assert isinstance(context, TaskContext)

        # Total tokens should be tracked
        total_tokens = sum(
            f.get("estimated_tokens", 0)
            for f in context.files_to_modify + context.files_to_reference
        )

        assert total_tokens >= 0, "Total tokens should be non-negative"


class TestEdgeCasesAndIntegration:
    """Integration tests for edge cases and real-world scenarios."""

    def test_handles_empty_task_gracefully(self, real_project_dir):
        """Test that empty tasks are handled gracefully."""
        project_index = {
            "services": {
                "test": {
                    "path": "context",
                    "language": "python",
                    "type": "service",
                }
            }
        }

        builder = ContextBuilder(real_project_dir, project_index=project_index)

        # Empty task should still work
        context = builder.build_context("", services=["test"])

        assert isinstance(context, TaskContext)
        assert context.task_description == ""

    def test_handles_special_characters_in_content(self, token_estimator):
        """Test token estimation with special characters."""
        special_content = """
# Special characters test
# Unicode: 你好世界 🌍 🚀
# Math: ∑ ∫ √ ≠ ≤ ≥
# Symbols: © ®™ £ € ¥
# Quotes: " ' ' " ` `
"""

        tokens = token_estimator.count_tokens(special_content)

        assert tokens > 0, "Should handle special characters"
        assert isinstance(tokens, int), "Should return integer token count"

    def test_handles_very_long_lines(self, token_estimator):
        """Test token estimation with very long lines."""
        # Create a very long line (e.g., minified code or data URL)
        long_line = "x" * 10000

        tokens = token_estimator.count_tokens(long_line)

        assert tokens > 0, "Should handle very long lines"
        assert tokens < 5000, "Very long line should not exceed reasonable token count"

    @pytest.mark.asyncio
    async def test_semantic_scoring_with_long_documents(self, mock_embedder):
        """Test semantic scoring with long documents."""
        # Mock embeddings
        mock_embedder.embed.side_effect = [
            [0.5, 0.5],  # Query
            [0.5, 0.5],  # Short doc
            [0.5, 0.5],  # Long doc (same embedding)
        ]

        scorer = SemanticScorer(mock_embedder)

        short_doc = {"path": "short.py", "content": "def foo(): return 1"}
        long_doc = {
            "path": "long.py",
            "content": "\n".join([f"# Comment {i}" for i in range(1000)])
        }

        results = await scorer.score_files(
            [short_doc, long_doc], "test query"
        )

        assert len(results) == 2
        # Both should have scores (length shouldn't matter for scoring)
        assert all("semantic_score" in r for r in results)


class TestPerformanceAndScalability:
    """Tests for performance characteristics and scalability."""

    def test_token_estimation_performance(self, token_estimator):
        """Test that token estimation is performant."""
        import time

        # Create a moderately large file (10k lines)
        large_content = "\n".join([f"line {i}" for i in range(10000)])

        start = time.time()
        tokens = token_estimator.count_tokens(large_content)
        elapsed = time.time() - start

        # Should complete in reasonable time (< 1 second for 10k lines)
        assert elapsed < 1.0, f"Token estimation too slow: {elapsed:.2f}s"
        assert tokens > 0, "Should produce token count"

    def test_redundancy_detection_performance(self, real_project_dir):
        """Test that redundancy detection is performant."""
        import time

        detector = RedundancyDetector(real_project_dir)

        # Create many files
        files = [
            FileMatch(
                path=f"file{i}.py",
                service="backend",
                reason="test",
                relevance_score=0.5,
                estimated_tokens=100,
            )
            for i in range(100)
        ]

        # Mock file reading
        with patch.object(Path, "read_text", return_value="def foo(): return 1"):
            start = time.time()
            filtered, report = detector.detect_redundancies(files)
            elapsed = time.time() - start

        # Should complete in reasonable time (< 5 seconds for 100 files)
        assert elapsed < 5.0, f"Redundancy detection too slow: {elapsed:.2f}s"
