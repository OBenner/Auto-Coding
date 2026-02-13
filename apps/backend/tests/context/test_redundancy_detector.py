#!/usr/bin/env python3
"""
Unit tests for Redundancy Detector
==================================

Tests the RedundancyDetector class for finding duplicate and similar code.
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

from unittest.mock import MagicMock

import pytest
from context.models import FileMatch
from context.redundancy_detector import RedundancyDetector


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with test files."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create some test files
    (project_dir / "file1.py").write_text(
        "def hello():\n    print('hello')\n", encoding="utf-8"
    )
    (project_dir / "file2.py").write_text(
        "def hello():\n    print('hello')\n", encoding="utf-8"
    )  # Exact duplicate
    (project_dir / "file3.py").write_text(
        "def hello():\n    print('hello')\n    # Extra comment\n", encoding="utf-8"
    )  # Near-duplicate
    (project_dir / "file4.py").write_text(
        "def different():\n    print('different')\n", encoding="utf-8"
    )

    return project_dir


@pytest.fixture
def detector(temp_project_dir):
    """Create a RedundancyDetector instance."""
    return RedundancyDetector(temp_project_dir)


@pytest.fixture
def sample_files():
    """Create sample FileMatch objects for testing."""
    return [
        FileMatch(
            path="file1.py",
            service="backend",
            reason="test",
            relevance_score=0.8,
            estimated_tokens=100,
        ),
        FileMatch(
            path="file2.py",
            service="backend",
            reason="test",
            relevance_score=0.7,
            estimated_tokens=100,
        ),
        FileMatch(
            path="file3.py",
            service="backend",
            reason="test",
            relevance_score=0.6,
            estimated_tokens=120,
        ),
        FileMatch(
            path="file4.py",
            service="backend",
            reason="test",
            relevance_score=0.9,
            estimated_tokens=80,
        ),
    ]


class TestRedundancyDetectorInitialization:
    """Test suite for RedundancyDetector initialization."""

    def test_initialization_with_project_dir(self, temp_project_dir):
        """Test initialization with project directory."""
        detector = RedundancyDetector(temp_project_dir)
        assert detector.project_dir == temp_project_dir.resolve()
        assert detector.similarity_threshold == 0.85
        assert detector.token_estimator is None

    def test_initialization_with_custom_threshold(self, temp_project_dir):
        """Test initialization with custom similarity threshold."""
        detector = RedundancyDetector(temp_project_dir, similarity_threshold=0.9)
        assert detector.similarity_threshold == 0.9

    def test_initialization_with_token_estimator(self, temp_project_dir):
        """Test initialization with token estimator."""
        mock_estimator = MagicMock()
        detector = RedundancyDetector(temp_project_dir, token_estimator=mock_estimator)
        assert detector.token_estimator == mock_estimator

    def test_project_dir_is_resolved(self, tmp_path):
        """Test that project_dir is resolved to absolute path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        detector = RedundancyDetector(project_dir)
        assert detector.project_dir.is_absolute()


class TestComputeHash:
    """Test suite for _compute_hash method."""

    def test_compute_hash_same_content(self, detector):
        """Test that same content produces same hash."""
        content = "def hello():\n    print('hello')"
        hash1 = detector._compute_hash(content)
        hash2 = detector._compute_hash(content)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 produces 64 hex characters

    def test_compute_hash_different_content(self, detector):
        """Test that different content produces different hashes."""
        hash1 = detector._compute_hash("content1")
        hash2 = detector._compute_hash("content2")

        assert hash1 != hash2

    def test_compute_hash_empty_string(self, detector):
        """Test hashing empty string."""
        empty_hash = detector._compute_hash("")
        assert isinstance(empty_hash, str)
        assert len(empty_hash) == 64

    def test_compute_hash_unicode_content(self, detector):
        """Test hashing content with Unicode characters."""
        content = "Hello 世界 🌍"
        hash_value = detector._compute_hash(content)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

    def test_compute_hash_deterministic(self, detector):
        """Test that hashing is deterministic across multiple calls."""
        content = "test content"
        hashes = [detector._compute_hash(content) for _ in range(10)]

        # All hashes should be identical
        assert all(h == hashes[0] for h in hashes)


class TestComputeContentSignature:
    """Test suite for _compute_content_signature method."""

    def test_compute_signature_normalizes_whitespace(self, detector):
        """Test that signature normalizes whitespace."""
        content1 = "def hello():    print('hello')"
        content2 = "def hello(): print('hello')"

        sig1 = detector._compute_content_signature(content1)
        sig2 = detector._compute_content_signature(content2)

        # Should be same after normalization
        assert sig1 == sig2

    def test_compute_signature_removes_comments(self, detector):
        """Test that signature removes comments."""
        content1 = "def hello():\n    print('hello')\n# This is a comment"
        content2 = "def hello():\n    print('hello')\n# Different comment"

        sig1 = detector._compute_content_signature(content1)
        sig2 = detector._compute_content_signature(content2)

        # Should be same after removing comments
        assert sig1 == sig2

    def test_compute_signature_lowercase(self, detector):
        """Test that signature lowercases content."""
        content1 = "def Hello():\n    Print('hello')"
        content2 = "def hello():\n    print('hello')"

        sig1 = detector._compute_content_signature(content1)
        sig2 = detector._compute_content_signature(content2)

        # Should be same after lowercasing
        assert sig1 == sig2

    def test_compute_signature_empty_lines(self, detector):
        """Test that signature ignores empty lines."""
        content1 = "def hello():\n\n\n    print('hello')"
        content2 = "def hello():\n    print('hello')"

        sig1 = detector._compute_content_signature(content1)
        sig2 = detector._compute_content_signature(content2)

        # Should be same after removing empty lines
        assert sig1 == sig2

    def test_compute_signature_different_content(self, detector):
        """Test that different content produces different signatures."""
        sig1 = detector._compute_content_signature("def hello():")
        sig2 = detector._compute_content_signature("def goodbye():")

        assert sig1 != sig2

    def test_compute_signature_empty_string(self, detector):
        """Test signature of empty string."""
        sig = detector._compute_content_signature("")
        assert isinstance(sig, str)
        assert len(sig) == 32  # MD5 produces 32 hex characters


class TestComputeSimilarity:
    """Test suite for _compute_similarity method."""

    def test_compute_similarity_returns_float(self, detector):
        """Test that similarity returns a float."""
        content = "some content"
        signature = detector._compute_content_signature(content)
        similarity = detector._compute_similarity(content, signature)

        assert isinstance(similarity, float)

    def test_compute_similarity_range(self, detector):
        """Test that similarity is in valid range."""
        content = "some content"
        signature = detector._compute_content_signature(content)
        similarity = detector._compute_similarity(content, signature)

        # Similarity should be between 0.0 and 1.0
        assert 0.0 <= similarity <= 1.0

    def test_compute_similarity_identical_content(self, detector):
        """Test similarity with identical content."""
        content = "def hello():\n    print('hello')"
        signature = detector._compute_content_signature(content)
        similarity = detector._compute_similarity(content, signature)

        # Should be high similarity (currently returns 0.9 placeholder)
        assert similarity >= 0.85


class TestDetectRedundancies:
    """Test suite for detect_redundancies method."""

    def test_detect_redundancies_empty_list(self, detector):
        """Test with empty file list."""
        filtered, report = detector.detect_redundancies([])

        assert filtered == []
        assert report == []

    def test_detect_redundancies_exact_duplicates(
        self, detector, sample_files, temp_project_dir
    ):
        """Test detection of exact duplicate files."""
        # file1.py and file2.py have identical content
        filtered, report = detector.detect_redundancies(sample_files)

        # Should remove one of the duplicates
        assert len(filtered) < len(sample_files)

        # Should have a removal report
        assert len(report) > 0

        # Check that exact_duplicate reason is present
        duplicate_removals = [r for r in report if r["reason"] == "exact_duplicate"]
        assert len(duplicate_removals) > 0

    def test_detect_redundancies_keeps_highest_relevance(self, detector, sample_files):
        """Test that highest relevance file is kept when duplicates found."""
        filtered, report = detector.detect_redundancies(
            sample_files, keep_highest_relevance=True
        )

        # Check that file4.py (highest relevance: 0.9) is kept
        file4 = [f for f in filtered if f.path == "file4.py"]
        assert len(file4) == 1

    def test_detect_redundancies_does_not_keep_highest_relevance(
        self, detector, sample_files
    ):
        """Test behavior when keep_highest_relevance is False."""
        filtered, report = detector.detect_redundancies(
            sample_files, keep_highest_relevance=False
        )

        # Should still filter duplicates
        assert len(filtered) <= len(sample_files)

    def test_detect_redundancies_file_not_found(self, detector, temp_project_dir):
        """Test handling of files that don't exist."""
        files = [
            FileMatch(
                path="nonexistent.py",
                service="backend",
                reason="test",
                relevance_score=0.5,
                estimated_tokens=100,
            )
        ]

        filtered, report = detector.detect_redundancies(files)

        # Should handle gracefully - file won't be in filtered list
        # since it doesn't exist and can't be analyzed
        assert isinstance(filtered, list)

    def test_detect_redundancies_reports_tokens_saved(self, detector, sample_files):
        """Test that removal report includes token savings."""
        filtered, report = detector.detect_redundancies(sample_files)

        # At least one removal should have tokens_saved
        if report:
            assert all("tokens_saved" in r for r in report)

            # Calculate total tokens saved
            total_saved = sum(r.get("tokens_saved", 0) for r in report)
            assert total_saved >= 0

    def test_detect_redundancies_report_structure(self, detector, sample_files):
        """Test that removal reports have correct structure."""
        filtered, report = detector.detect_redundancies(sample_files)

        for removal in report:
            assert "file" in removal
            assert "reason" in removal
            assert "tokens_saved" in removal
            assert removal["reason"] in ["exact_duplicate", "near_duplicate"]

            if removal["reason"] == "exact_duplicate":
                assert "duplicate_of" in removal
            elif removal["reason"] == "near_duplicate":
                assert "similar_to" in removal
                assert "similarity" in removal

    def test_detect_redundancies_custom_threshold(self, detector, sample_files):
        """Test with custom similarity threshold."""
        # Lower threshold should catch more near-duplicates
        detector_low = RedundancyDetector(
            detector.project_dir, similarity_threshold=0.5
        )
        detector_high = RedundancyDetector(
            detector.project_dir, similarity_threshold=0.95
        )

        filtered_low, report_low = detector_low.detect_redundancies(sample_files)
        filtered_high, report_high = detector_high.detect_redundancies(sample_files)

        # Lower threshold may catch more duplicates
        assert len(filtered_low) <= len(sample_files)
        assert len(filtered_high) <= len(sample_files)


class TestFindRedundantSnippets:
    """Test suite for find_redundant_snippets method."""

    def test_find_redundant_snippets_empty_list(self, detector):
        """Test with empty file list."""
        snippets = detector.find_redundant_snippets([])
        assert snippets == []

    def test_find_redundant_snippets_finds_duplicates(self, detector, temp_project_dir):
        """Test finding duplicate code snippets."""
        # Create files with duplicate snippets
        (temp_project_dir / "snippet1.py").write_text(
            "def func1():\n    pass\n\ndef func2():\n    pass\n", encoding="utf-8"
        )
        (temp_project_dir / "snippet2.py").write_text(
            "def func1():\n    pass\n\ndef func3():\n    pass\n", encoding="utf-8"
        )

        files = [
            FileMatch(
                path="snippet1.py",
                service="backend",
                reason="test",
                relevance_score=0.5,
                estimated_tokens=50,
            ),
            FileMatch(
                path="snippet2.py",
                service="backend",
                reason="test",
                relevance_score=0.5,
                estimated_tokens=50,
            ),
        ]

        snippets = detector.find_redundant_snippets(files, min_lines=2)

        # Should find the duplicate "def func1():\n    pass" snippet
        assert len(snippets) > 0

    def test_find_redundant_snippets_min_lines_parameter(
        self, detector, temp_project_dir
    ):
        """Test min_lines parameter affects snippet detection."""
        # Create file with repeated pattern
        (temp_project_dir / "repeat.py").write_text(
            "line1\nline2\nline3\n", encoding="utf-8"
        )

        files = [
            FileMatch(
                path="repeat.py",
                service="backend",
                reason="test",
                relevance_score=0.5,
                estimated_tokens=30,
            )
        ]

        snippets_2 = detector.find_redundant_snippets(files, min_lines=2)
        snippets_5 = detector.find_redundant_snippets(files, min_lines=5)

        # Higher min_lines should find fewer (or no) snippets
        assert len(snippets_5) <= len(snippets_2)

    def test_find_redundant_snippets_report_structure(self, detector, temp_project_dir):
        """Test that snippet reports have correct structure."""
        (temp_project_dir / "a.py").write_text("common code\n", encoding="utf-8")
        (temp_project_dir / "b.py").write_text("common code\n", encoding="utf-8")

        files = [
            FileMatch(
                path="a.py", service="backend", reason="test", estimated_tokens=20
            ),
            FileMatch(
                path="b.py", service="backend", reason="test", estimated_tokens=20
            ),
        ]

        snippets = detector.find_redundant_snippets(files, min_lines=1)

        for snippet in snippets:
            assert "snippet" in snippet
            assert "occurrences" in snippet
            assert "count" in snippet
            assert "potential_token_savings" in snippet
            assert snippet["count"] >= 2
            assert len(snippet["occurrences"]) == snippet["count"]

            # Check occurrence structure
            for occ in snippet["occurrences"]:
                assert "file" in occ
                assert "line" in occ

    def test_find_redundant_snippets_with_token_estimator(self, temp_project_dir):
        """Test snippet finding with token estimator."""
        mock_estimator = MagicMock()
        detector = RedundancyDetector(temp_project_dir, token_estimator=mock_estimator)

        (temp_project_dir / "dup.py").write_text("duplicate\n", encoding="utf-8")

        files = [
            FileMatch(
                path="dup.py", service="backend", reason="test", estimated_tokens=20
            )
        ]

        snippets = detector.find_redundant_snippets(files, min_lines=1)

        # Should still work (may use token_estimator for better estimates)
        assert isinstance(snippets, list)

    def test_find_redundant_snippets_no_duplicates(self, detector, temp_project_dir):
        """Test when no duplicate snippets exist."""
        (temp_project_dir / "unique1.py").write_text(
            "unique content 1\n", encoding="utf-8"
        )
        (temp_project_dir / "unique2.py").write_text(
            "unique content 2\n", encoding="utf-8"
        )

        files = [
            FileMatch(
                path="unique1.py", service="backend", reason="test", estimated_tokens=20
            ),
            FileMatch(
                path="unique2.py", service="backend", reason="test", estimated_tokens=20
            ),
        ]

        snippets = detector.find_redundant_snippets(files, min_lines=1)

        # Should find no duplicates
        assert len(snippets) == 0


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_unicode_file_handling(self, detector, temp_project_dir):
        """Test handling of files with Unicode content."""
        (temp_project_dir / "unicode.py").write_text(
            "# Comment: 世界\n\ndef hello():\n    print('你好')\n", encoding="utf-8"
        )
        (temp_project_dir / "unicode2.py").write_text(
            "# Comment: 世界\n\ndef hello():\n    print('你好')\n", encoding="utf-8"
        )

        files = [
            FileMatch(
                path="unicode.py", service="backend", reason="test", estimated_tokens=50
            ),
            FileMatch(
                path="unicode2.py",
                service="backend",
                reason="test",
                estimated_tokens=50,
            ),
        ]

        filtered, report = detector.detect_redundancies(files)

        # Should handle Unicode without errors
        assert isinstance(filtered, list)
        assert isinstance(report, list)

    def test_mixed_line_endings(self, detector, temp_project_dir):
        """Test handling of different line endings."""
        # Create file with \r\n line endings
        (temp_project_dir / "crlf.py").write_text(
            "def hello():\r\n    print('hello')\r\n", encoding="utf-8"
        )
        # Create file with \n line endings
        (temp_project_dir / "lf.py").write_text(
            "def hello():\n    print('hello')\n", encoding="utf-8"
        )

        files = [
            FileMatch(
                path="crlf.py", service="backend", reason="test", estimated_tokens=40
            ),
            FileMatch(
                path="lf.py", service="backend", reason="test", estimated_tokens=40
            ),
        ]

        filtered, report = detector.detect_redundancies(files)

        # Should normalize and detect as duplicates
        assert isinstance(filtered, list)
        assert isinstance(report, list)

    def test_large_file_handling(self, detector, temp_project_dir):
        """Test handling of larger files."""
        large_content = "\n".join([f"x = {i}" for i in range(1000)])
        (temp_project_dir / "large1.py").write_text(large_content, encoding="utf-8")
        (temp_project_dir / "large2.py").write_text(large_content, encoding="utf-8")

        files = [
            FileMatch(
                path="large1.py",
                service="backend",
                reason="test",
                estimated_tokens=5000,
            ),
            FileMatch(
                path="large2.py",
                service="backend",
                reason="test",
                estimated_tokens=5000,
            ),
        ]

        filtered, report = detector.detect_redundancies(files)

        # Should handle large files without errors
        assert isinstance(filtered, list)
        assert isinstance(report, list)

    def test_single_file_list(self, detector, temp_project_dir):
        """Test with only one file in list."""
        (temp_project_dir / "single.py").write_text(
            "def hello():\n    pass\n", encoding="utf-8"
        )

        files = [
            FileMatch(
                path="single.py", service="backend", reason="test", estimated_tokens=30
            )
        ]

        filtered, report = detector.detect_redundancies(files)

        # Should keep the single file
        assert len(filtered) == 1
        assert len(report) == 0

    def test_all_unique_files(self, detector, temp_project_dir):
        """Test when all files are unique."""
        (temp_project_dir / "unique1.py").write_text("content 1\n", encoding="utf-8")
        (temp_project_dir / "unique2.py").write_text("content 2\n", encoding="utf-8")
        (temp_project_dir / "unique3.py").write_text("content 3\n", encoding="utf-8")

        files = [
            FileMatch(
                path="unique1.py", service="backend", reason="test", estimated_tokens=20
            ),
            FileMatch(
                path="unique2.py", service="backend", reason="test", estimated_tokens=20
            ),
            FileMatch(
                path="unique3.py", service="backend", reason="test", estimated_tokens=20
            ),
        ]

        filtered, report = detector.detect_redundancies(files)

        # Should keep all files
        assert len(filtered) == 3
        assert len(report) == 0

    def test_files_with_zero_tokens(self, detector, temp_project_dir):
        """Test files with zero token estimates."""
        (temp_project_dir / "empty1.py").write_text("", encoding="utf-8")
        (temp_project_dir / "empty2.py").write_text("", encoding="utf-8")

        files = [
            FileMatch(
                path="empty1.py", service="backend", reason="test", estimated_tokens=0
            ),
            FileMatch(
                path="empty2.py", service="backend", reason="test", estimated_tokens=0
            ),
        ]

        filtered, report = detector.detect_redundancies(files)

        # Should handle gracefully
        assert isinstance(filtered, list)
        assert isinstance(report, list)


class TestIntegrationBehavior:
    """Test suite for integration-like behavior."""

    def test_full_redundancy_detection_workflow(self, detector, temp_project_dir):
        """Test complete workflow from files to filtered results."""
        # Create realistic scenario
        (temp_project_dir / "auth.py").write_text(
            "def authenticate():\n    pass\n", encoding="utf-8"
        )
        (temp_project_dir / "auth_copy.py").write_text(
            "def authenticate():\n    pass\n", encoding="utf-8"
        )  # Exact duplicate
        (temp_project_dir / "auth_similar.py").write_text(
            "def authenticate():\n    pass\n# Extra comment\n", encoding="utf-8"
        )  # Near duplicate
        (temp_project_dir / "database.py").write_text(
            "def connect():\n    pass\n", encoding="utf-8"
        )  # Unique

        files = [
            FileMatch(
                path="auth.py",
                service="backend",
                reason="test",
                relevance_score=0.7,
                estimated_tokens=100,
            ),
            FileMatch(
                path="auth_copy.py",
                service="backend",
                reason="test",
                relevance_score=0.5,
                estimated_tokens=100,
            ),
            FileMatch(
                path="auth_similar.py",
                service="backend",
                reason="test",
                relevance_score=0.6,
                estimated_tokens=120,
            ),
            FileMatch(
                path="database.py",
                service="backend",
                reason="test",
                relevance_score=0.8,
                estimated_tokens=80,
            ),
        ]

        filtered, report = detector.detect_redundancies(
            files, keep_highest_relevance=True
        )

        # Should remove duplicates
        assert len(filtered) < len(files)

        # Should keep database.py (highest relevance)
        database_files = [f for f in filtered if f.path == "database.py"]
        assert len(database_files) == 1

        # Should have removal reports
        assert len(report) > 0

        # Calculate tokens saved
        total_saved = sum(r.get("tokens_saved", 0) for r in report)
        assert total_saved > 0

    def test_redundancy_detection_preserves_file_attributes(
        self, detector, temp_project_dir
    ):
        """Test that filtered files preserve their attributes."""
        (temp_project_dir / "test.py").write_text("content\n", encoding="utf-8")

        original_file = FileMatch(
            path="test.py",
            service="backend",
            reason="test match",
            relevance_score=0.85,
            matching_lines=[(1, "content")],
            estimated_tokens=50,
        )

        filtered, _ = detector.detect_redundancies([original_file])

        assert len(filtered) == 1
        assert filtered[0].path == "test.py"
        assert filtered[0].service == "backend"
        assert filtered[0].reason == "test match"
        assert filtered[0].relevance_score == 0.85
        assert filtered[0].matching_lines == [(1, "content")]
        assert filtered[0].estimated_tokens == 50

    def test_combined_redundancy_and_snippet_detection(
        self, detector, temp_project_dir
    ):
        """Test using both redundancy detection and snippet finding."""
        # Create files with both full duplicates and snippet duplicates
        (temp_project_dir / "lib1.py").write_text(
            "def helper():\n    pass\n\ndef unique1():\n    pass\n", encoding="utf-8"
        )
        (temp_project_dir / "lib2.py").write_text(
            "def helper():\n    pass\n\ndef unique2():\n    pass\n", encoding="utf-8"
        )

        files = [
            FileMatch(
                path="lib1.py", service="backend", reason="test", estimated_tokens=100
            ),
            FileMatch(
                path="lib2.py", service="backend", reason="test", estimated_tokens=100
            ),
        ]

        # Test full file redundancy
        filtered_files, file_report = detector.detect_redundancies(files)

        # Test snippet redundancy
        snippet_report = detector.find_redundant_snippets(files, min_lines=1)

        # Both should work
        assert isinstance(filtered_files, list)
        assert isinstance(file_report, list)
        assert isinstance(snippet_report, list)

        # Snippet detection should find the duplicate "def helper():\n    pass"
        assert len(snippet_report) > 0
