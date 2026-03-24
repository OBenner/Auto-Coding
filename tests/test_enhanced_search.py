#!/usr/bin/env python3
"""
Unit tests for EnhancedCodeSearch class.

Tests the enhanced code search that combines:
- CodeSearcher: Keyword and semantic file search
- GraphitiSearch: Semantic search in knowledge graph
- CodeRelationshipQueries: Code relationships and purpose search
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add apps/backend to path for imports (idempotent guard)
sys_path = Path(__file__).parent.parent / "apps" / "backend"
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from context.enhanced_search import EnhancedCodeSearch
from context.models import FileMatch

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory."""
    project = tmp_path / "test_project"
    project.mkdir()
    # Create a few test files
    (project / "auth.py").write_text("def authenticate(): pass\n")
    (project / "api.py").write_text("from auth import authenticate\n")
    return project


@pytest.fixture
def mock_graphiti_memory():
    """Create a mock GraphitiMemory instance."""
    memory = MagicMock()
    memory.is_initialized = True
    memory.code_relationships = MagicMock()
    memory._search = MagicMock()
    return memory


@pytest.fixture
def mock_code_searcher():
    """Create a mock CodeSearcher instance."""
    searcher = MagicMock()
    searcher.search_service = MagicMock(return_value=[])
    searcher.search_with_semantics = AsyncMock(return_value=[])
    searcher.use_semantic_search = True
    return searcher


@pytest.fixture
def enhanced_search(project_dir, mock_graphiti_memory):
    """Create an EnhancedCodeSearch instance with Graphiti."""
    # Mock the CodeSearcher creation
    with patch("context.enhanced_search.CodeSearcher") as mock_searcher_class:
        mock_searcher_class.return_value = MagicMock(
            search_service=MagicMock(return_value=[]),
            search_with_semantics=AsyncMock(return_value=[]),
            use_semantic_search=True,
        )
        return EnhancedCodeSearch(project_dir, graphiti_memory=mock_graphiti_memory)


@pytest.fixture
def enhanced_search_no_graphiti(project_dir):
    """Create an EnhancedCodeSearch instance without Graphiti."""
    with patch("context.enhanced_search.CodeSearcher") as mock_searcher_class:
        mock_searcher_class.return_value = MagicMock(
            search_service=MagicMock(return_value=[]),
            search_with_semantics=AsyncMock(return_value=[]),
            use_semantic_search=True,
        )
        return EnhancedCodeSearch(project_dir, graphiti_memory=None)


# =============================================================================
# MOCK RESULT FACTORIES
# =============================================================================


def _create_file_match(
    path: str = "test.py",
    service: str = "backend",
    score: float = 0.8,
) -> FileMatch:
    """Create a FileMatch object for testing."""
    return FileMatch(
        path=path,
        service=service,
        reason=f"Match found with score {score}",
        relevance_score=score,
        matching_lines=[(1, "test line")],
    )


def _create_purpose_result(
    entity_name: str = "test_function",
    entity_type: str = "function",
    score: float = 0.9,
) -> dict:
    """Create a purpose search result."""
    return {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "purpose": f"Test purpose for {entity_name}",
        "file_path": "test.py",
        "lineno": 42,
        "docstring": "Test docstring",
        "tags": ["test"],
        "score": score,
    }


def _create_pattern_result(
    content: str = "Test pattern",
    score: float = 0.85,
    pattern_type: str = "pattern",
) -> dict:
    """Create a pattern/gotcha search result."""
    return {
        "content": content,
        "score": score,
        "type": pattern_type,
        "category": "test",
        "confidence": 0.9,
    }


def _create_caller_result(
    caller: str = "test_caller",
    file_path: str = "test.py",
) -> dict:
    """Create a caller search result."""
    return {
        "caller": caller,
        "file_path": file_path,
        "lineno": 123,
        "call_type": "function",
        "module": None,
    }


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestEnhancedCodeSearchInit:
    """Test EnhancedCodeSearch initialization."""

    def test_init_with_graphiti(self, project_dir, mock_graphiti_memory):
        """Test initialization with Graphiti memory."""
        with patch("context.enhanced_search.CodeSearcher") as mock_searcher_class:
            mock_searcher_class.return_value = MagicMock(
                use_semantic_search=True,
            )

            searcher = EnhancedCodeSearch(
                project_dir, graphiti_memory=mock_graphiti_memory
            )

            assert searcher.project_dir == project_dir.resolve()
            assert searcher.graphiti_memory == mock_graphiti_memory
            assert (
                searcher._code_relationships == mock_graphiti_memory.code_relationships
            )
            assert searcher._graphiti_search == mock_graphiti_memory._search

    def test_init_without_graphiti(self, project_dir):
        """Test initialization without Graphiti memory."""
        with patch("context.enhanced_search.CodeSearcher") as mock_searcher_class:
            mock_searcher_class.return_value = MagicMock(
                use_semantic_search=True,
            )

            searcher = EnhancedCodeSearch(project_dir, graphiti_memory=None)

            assert searcher.project_dir == project_dir.resolve()
            assert searcher.graphiti_memory is None
            assert searcher._code_relationships is None
            assert searcher._graphiti_search is None

    def test_init_with_semantic_search_disabled(self, project_dir):
        """Test initialization with semantic search disabled."""
        with patch("context.enhanced_search.CodeSearcher") as mock_searcher_class:
            mock_searcher_class.return_value = MagicMock(
                use_semantic_search=False,
            )

            searcher = EnhancedCodeSearch(project_dir, use_semantic_search=False)

            assert searcher._code_searcher.use_semantic_search is False


# =============================================================================
# search_service TESTS
# =============================================================================


class TestSearchService:
    """Test search_service method."""

    def test_search_service_delegates_to_code_searcher(
        self, enhanced_search, project_dir
    ):
        """Test that search_service delegates to CodeSearcher."""
        expected_matches = [
            _create_file_match("auth.py", "backend", 0.9),
            _create_file_match("api.py", "backend", 0.7),
        ]
        enhanced_search._code_searcher.search_service.return_value = expected_matches

        service_path = project_dir / "backend"
        result = enhanced_search.search_service(
            service_path, "backend", ["auth", "login"]
        )

        assert len(result) == 2
        assert result == expected_matches
        enhanced_search._code_searcher.search_service.assert_called_once_with(
            service_path, "backend", ["auth", "login"]
        )

    def test_search_service_empty_results(self, enhanced_search, project_dir):
        """Test search_service with no results."""
        enhanced_search._code_searcher.search_service.return_value = []

        result = enhanced_search.search_service(project_dir, "backend", ["nonexistent"])

        assert result == []


# =============================================================================
# search_with_semantics TESTS
# =============================================================================


class TestSearchWithSemantics:
    """Test search_with_semantics method."""

    @pytest.mark.asyncio
    async def test_search_with_semantics_delegates_to_code_searcher(
        self, enhanced_search, project_dir
    ):
        """Test that search_with_semantics delegates to CodeSearcher."""
        expected_matches = [
            _create_file_match("auth.py", "backend", 0.95),
        ]
        enhanced_search._code_searcher.search_with_semantics = AsyncMock(
            return_value=expected_matches
        )

        service_path = project_dir / "backend"
        result = await enhanced_search.search_with_semantics(
            service_path, "backend", ["auth"], "user authentication"
        )

        assert len(result) == 1
        assert result == expected_matches
        enhanced_search._code_searcher.search_with_semantics.assert_called_once_with(
            service_path, "backend", ["auth"], "user authentication"
        )

    @pytest.mark.asyncio
    async def test_search_with_semantics_empty_results(
        self, enhanced_search, project_dir
    ):
        """Test search_with_semantics with no results."""
        enhanced_search._code_searcher.search_with_semantics = AsyncMock(
            return_value=[]
        )

        result = await enhanced_search.search_with_semantics(
            project_path := project_dir,
            "backend",
            ["nonexistent"],
            "nonexistent query",
        )

        assert result == []


# =============================================================================
# search_by_purpose TESTS
# =============================================================================


class TestSearchByPurpose:
    """Test search_by_purpose method."""

    @pytest.mark.asyncio
    async def test_search_by_purpose_with_graphiti(self, enhanced_search):
        """Test search_by_purpose with Graphiti enabled."""
        expected_results = [
            _create_purpose_result("authenticate_user", "function", 0.95),
            _create_purpose_result("validate_token", "function", 0.85),
        ]
        enhanced_search._code_relationships.search_by_purpose = AsyncMock(
            return_value=expected_results
        )

        result = await enhanced_search.search_by_purpose("authentication functions")

        assert len(result) == 2
        assert result[0]["entity_name"] == "authenticate_user"
        assert result[1]["entity_name"] == "validate_token"
        enhanced_search._code_relationships.search_by_purpose.assert_called_once_with(
            query="authentication functions",
            limit=20,
            entity_type=None,
        )

    @pytest.mark.asyncio
    async def test_search_by_purpose_with_entity_type_filter(self, enhanced_search):
        """Test search_by_purpose with entity type filter."""
        expected_results = [
            _create_purpose_result("UserAuth", "class", 0.9),
        ]
        enhanced_search._code_relationships.search_by_purpose = AsyncMock(
            return_value=expected_results
        )

        result = await enhanced_search.search_by_purpose(
            "authentication", entity_type="class"
        )

        assert len(result) == 1
        assert result[0]["entity_type"] == "class"
        enhanced_search._code_relationships.search_by_purpose.assert_called_once_with(
            query="authentication",
            limit=20,
            entity_type="class",
        )

    @pytest.mark.asyncio
    async def test_search_by_purpose_without_graphiti(
        self, enhanced_search_no_graphiti
    ):
        """Test search_by_purpose without Graphiti returns empty."""
        result = await enhanced_search_no_graphiti.search_by_purpose("authentication")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_by_purpose_handles_exception(self, enhanced_search):
        """Test search_by_purpose handles exceptions gracefully."""
        enhanced_search._code_relationships.search_by_purpose = AsyncMock(
            side_effect=Exception("Graphiti error")
        )

        result = await enhanced_search.search_by_purpose("authentication")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_by_purpose_custom_limit(self, enhanced_search):
        """Test search_by_purpose with custom limit."""
        expected_results = [
            _create_purpose_result(f"func_{i}", "function", 0.9 - i * 0.1)
            for i in range(5)
        ]
        enhanced_search._code_relationships.search_by_purpose = AsyncMock(
            return_value=expected_results
        )

        result = await enhanced_search.search_by_purpose("test", limit=5)

        assert len(result) == 5
        enhanced_search._code_relationships.search_by_purpose.assert_called_once_with(
            query="test",
            limit=5,
            entity_type=None,
        )


# =============================================================================
# find_similar_patterns TESTS
# =============================================================================


class TestFindSimilarPatterns:
    """Test find_similar_patterns method."""

    @pytest.mark.asyncio
    async def test_find_similar_patterns_with_graphiti(self, enhanced_search):
        """Test find_similar_patterns with Graphiti enabled."""
        mock_patterns = [
            _create_pattern_result("Use OAuth2", 0.92, "pattern"),
            _create_pattern_result("Validate tokens", 0.85, "pattern"),
        ]
        mock_gotchas = [
            _create_pattern_result("Token expires after 1 hour", 0.88, "gotcha"),
        ]
        enhanced_search._graphiti_search.get_patterns_and_gotchas = AsyncMock(
            return_value=(mock_patterns, mock_gotchas)
        )

        result = await enhanced_search.find_similar_patterns("authentication")

        # Should combine patterns and gotchas, sorted by score
        assert len(result) == 3
        assert result[0]["score"] == pytest.approx(0.92)  # OAuth2 pattern
        assert result[1]["score"] == pytest.approx(0.88)  # Token gotcha
        assert result[2]["score"] == pytest.approx(0.85)  # Validate pattern

    @pytest.mark.asyncio
    async def test_find_similar_patterns_without_graphiti(
        self, enhanced_search_no_graphiti
    ):
        """Test find_similar_patterns without Graphiti returns empty."""
        result = await enhanced_search_no_graphiti.find_similar_patterns(
            "authentication"
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_similar_patterns_handles_exception(self, enhanced_search):
        """Test find_similar_patterns handles exceptions gracefully."""
        enhanced_search._graphiti_search.get_patterns_and_gotchas = AsyncMock(
            side_effect=Exception("Graphiti error")
        )

        result = await enhanced_search.find_similar_patterns("authentication")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_similar_patterns_custom_params(self, enhanced_search):
        """Test find_similar_patterns with custom parameters."""
        mock_patterns = [_create_pattern_result("Test pattern", 0.7)]
        mock_gotchas = []
        enhanced_search._graphiti_search.get_patterns_and_gotchas = AsyncMock(
            return_value=(mock_patterns, mock_gotchas)
        )

        result = await enhanced_search.find_similar_patterns(
            "test", num_results=10, min_score=0.6
        )

        assert len(result) == 1
        enhanced_search._graphiti_search.get_patterns_and_gotchas.assert_called_once_with(
            query="test", num_results=10, min_score=0.6
        )

    @pytest.mark.asyncio
    async def test_find_similar_patterns_sorting(self, enhanced_search):
        """Test that results are sorted by score."""
        mock_patterns = [
            _create_pattern_result("Pattern C", 0.7, "pattern"),
            _create_pattern_result("Pattern A", 0.9, "pattern"),
            _create_pattern_result("Pattern B", 0.8, "pattern"),
        ]
        mock_gotchas = [
            _create_pattern_result("Gotcha A", 0.95, "gotcha"),
        ]
        enhanced_search._graphiti_search.get_patterns_and_gotchas = AsyncMock(
            return_value=(mock_patterns, mock_gotchas)
        )

        result = await enhanced_search.find_similar_patterns("test")

        # Verify sorted order (highest score first)
        assert result[0]["score"] == pytest.approx(0.95)  # Gotcha A
        assert result[1]["score"] == pytest.approx(0.9)  # Pattern A
        assert result[2]["score"] == pytest.approx(0.8)  # Pattern B
        assert result[3]["score"] == pytest.approx(0.7)  # Pattern C


# =============================================================================
# find_callers TESTS
# =============================================================================


class TestFindCallers:
    """Test find_callers method."""

    @pytest.mark.asyncio
    async def test_find_callers_with_graphiti(self, enhanced_search):
        """Test find_callers with Graphiti enabled."""
        expected_callers = [
            _create_caller_result("process_request", "api.py"),
            _create_caller_result("handle_login", "views.py"),
        ]
        enhanced_search._code_relationships.find_callers = AsyncMock(
            return_value=expected_callers
        )

        result = await enhanced_search.find_callers("authenticate_user")

        assert len(result) == 2
        assert result[0]["caller"] == "process_request"
        assert result[1]["caller"] == "handle_login"
        enhanced_search._code_relationships.find_callers.assert_called_once_with(
            function_name="authenticate_user", limit=50
        )

    @pytest.mark.asyncio
    async def test_find_callers_without_graphiti(self, enhanced_search_no_graphiti):
        """Test find_callers without Graphiti returns empty."""
        result = await enhanced_search_no_graphiti.find_callers("authenticate_user")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_callers_handles_exception(self, enhanced_search):
        """Test find_callers handles exceptions gracefully."""
        enhanced_search._code_relationships.find_callers = AsyncMock(
            side_effect=Exception("Graphiti error")
        )

        result = await enhanced_search.find_callers("test_function")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_callers_custom_limit(self, enhanced_search):
        """Test find_callers with custom limit."""
        expected_callers = [
            _create_caller_result(f"caller_{i}", f"file_{i}.py") for i in range(10)
        ]
        enhanced_search._code_relationships.find_callers = AsyncMock(
            return_value=expected_callers
        )

        result = await enhanced_search.find_callers("test_func", limit=10)

        assert len(result) == 10
        enhanced_search._code_relationships.find_callers.assert_called_once_with(
            function_name="test_func", limit=10
        )


# =============================================================================
# find_callees TESTS
# =============================================================================


class TestFindCallees:
    """Test find_callees method."""

    @pytest.mark.asyncio
    async def test_find_callees_with_graphiti(self, enhanced_search):
        """Test find_callees with Graphiti enabled."""
        expected_callees = [
            {
                "callee": "validate_token",
                "file_path": "auth.py",
                "lineno": 67,
                "call_type": "function",
                "module": "tokens",
            },
            {
                "callee": "check_password",
                "file_path": "auth.py",
                "lineno": 72,
                "call_type": "function",
                "module": None,
            },
        ]
        enhanced_search._code_relationships.find_callees = AsyncMock(
            return_value=expected_callees
        )

        result = await enhanced_search.find_callees("authenticate_user")

        assert len(result) == 2
        assert result[0]["callee"] == "validate_token"
        assert result[1]["callee"] == "check_password"
        enhanced_search._code_relationships.find_callees.assert_called_once_with(
            function_name="authenticate_user", limit=50
        )

    @pytest.mark.asyncio
    async def test_find_callees_without_graphiti(self, enhanced_search_no_graphiti):
        """Test find_callees without Graphiti returns empty."""
        result = await enhanced_search_no_graphiti.find_callees("authenticate_user")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_callees_handles_exception(self, enhanced_search):
        """Test find_callees handles exceptions gracefully."""
        enhanced_search._code_relationships.find_callees = AsyncMock(
            side_effect=Exception("Graphiti error")
        )

        result = await enhanced_search.find_callees("test_function")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_callees_custom_limit(self, enhanced_search):
        """Test find_callees with custom limit."""
        expected_callees = [
            {
                "callee": f"callee_{i}",
                "file_path": f"file_{i}.py",
                "lineno": i,
                "call_type": "function",
                "module": None,
            }
            for i in range(5)
        ]
        enhanced_search._code_relationships.find_callees = AsyncMock(
            return_value=expected_callees
        )

        result = await enhanced_search.find_callees("test_func", limit=5)

        assert len(result) == 5
        enhanced_search._code_relationships.find_callees.assert_called_once_with(
            function_name="test_func", limit=5
        )


# =============================================================================
# search_unified TESTS
# =============================================================================


class TestSearchUnified:
    """Test search_unified method."""

    @pytest.mark.asyncio
    async def test_search_unified_all_searches_enabled(self, enhanced_search):
        """Test search_unified with all search types enabled."""
        # Setup mocks
        file_matches = [_create_file_match("auth.py", "backend", 0.9)]
        purpose_results = [_create_purpose_result("authenticate", "function", 0.95)]
        pattern_results = [_create_pattern_result("Use OAuth", 0.88, "pattern")]

        enhanced_search._code_searcher.search_with_semantics = AsyncMock(
            return_value=file_matches
        )
        enhanced_search._code_relationships.search_by_purpose = AsyncMock(
            return_value=purpose_results
        )
        enhanced_search._code_relationships.find_callers = AsyncMock(return_value=[])
        enhanced_search._graphiti_search.get_patterns_and_gotchas = AsyncMock(
            return_value=(pattern_results, [])
        )

        result = await enhanced_search.search_unified("authentication")

        assert len(result["files"]) == 1
        assert len(result["purpose"]) == 1
        assert len(result["patterns"]) == 1
        assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_search_unified_selective_searches(self, enhanced_search):
        """Test search_unified with selective search types."""
        file_matches = [_create_file_match("auth.py", "backend", 0.9)]
        enhanced_search._code_searcher.search_with_semantics = AsyncMock(
            return_value=file_matches
        )

        result = await enhanced_search.search_unified(
            "authentication", search_purpose=False, search_patterns=False
        )

        assert len(result["files"]) == 1
        assert len(result["purpose"]) == 0
        assert len(result["patterns"]) == 0
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_unified_no_searches(self, enhanced_search):
        """Test search_unified with all searches disabled."""
        result = await enhanced_search.search_unified(
            "test", search_files=False, search_purpose=False, search_patterns=False
        )

        assert result["files"] == []
        assert result["purpose"] == []
        assert result["patterns"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_search_unified_handles_search_failures(self, enhanced_search):
        """Test search_unified handles individual search failures gracefully."""
        # File search succeeds
        file_matches = [_create_file_match("test.py", "backend", 0.8)]
        enhanced_search._code_searcher.search_with_semantics = AsyncMock(
            return_value=file_matches
        )

        # Purpose search fails
        enhanced_search._code_relationships.search_by_purpose = AsyncMock(
            side_effect=Exception("Purpose search failed")
        )

        # Pattern search fails
        enhanced_search._graphiti_search.get_patterns_and_gotchas = AsyncMock(
            side_effect=Exception("Pattern search failed")
        )

        result = await enhanced_search.search_unified("test")

        # Should still return file results
        assert len(result["files"]) == 1
        assert len(result["purpose"]) == 0
        assert len(result["patterns"]) == 0
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_unified_custom_limit(self, enhanced_search):
        """Test search_unified with custom limit."""
        file_matches = [
            _create_file_match(f"file_{i}.py", "backend", 0.9 - i * 0.1)
            for i in range(5)
        ]
        enhanced_search._code_searcher.search_with_semantics = AsyncMock(
            return_value=file_matches
        )
        enhanced_search._code_relationships.search_by_purpose = AsyncMock(
            return_value=[]
        )
        enhanced_search._graphiti_search.get_patterns_and_gotchas = AsyncMock(
            return_value=([], [])
        )

        result = await enhanced_search.search_unified("test", limit=3)

        # Should limit to 3 results
        assert len(result["files"]) == 3
        assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_search_unified_without_graphiti(self, enhanced_search_no_graphiti):
        """Test search_unified without Graphiti only does file search."""
        file_matches = [_create_file_match("auth.py", "backend", 0.9)]
        enhanced_search_no_graphiti._code_searcher.search_with_semantics = AsyncMock(
            return_value=file_matches
        )

        result = await enhanced_search_no_graphiti.search_unified("authentication")

        assert len(result["files"]) == 1
        assert len(result["purpose"]) == 0
        assert len(result["patterns"]) == 0
        assert result["total"] == 1


# =============================================================================
# get_status TESTS
# =============================================================================


class TestGetStatus:
    """Test get_status method."""

    def test_get_status_with_graphiti(self, enhanced_search, project_dir):
        """Test get_status with Graphiti enabled."""
        status = enhanced_search.get_status()

        assert status["project_dir"] == str(project_dir.resolve())
        assert status["graphiti_enabled"] is True
        assert status["graphiti_initialized"] is True
        assert status["code_relationships_available"] is True
        assert status["graphiti_search_available"] is True
        assert status["semantic_search_enabled"] is True

    def test_get_status_without_graphiti(
        self, enhanced_search_no_graphiti, project_dir
    ):
        """Test get_status without Graphiti."""
        status = enhanced_search_no_graphiti.get_status()

        assert status["project_dir"] == str(project_dir.resolve())
        assert status["graphiti_enabled"] is False
        assert status["graphiti_initialized"] is False
        assert status["code_relationships_available"] is False
        assert status["graphiti_search_available"] is False
        assert status["semantic_search_enabled"] is True

    def test_get_status_semantic_search_disabled(
        self, project_dir, mock_graphiti_memory
    ):
        """Test get_status with semantic search disabled."""
        with patch("context.enhanced_search.CodeSearcher") as mock_searcher_class:
            mock_searcher_class.return_value = MagicMock(
                use_semantic_search=False,
            )

            searcher = EnhancedCodeSearch(
                project_dir,
                graphiti_memory=mock_graphiti_memory,
                use_semantic_search=False,
            )

            status = searcher.get_status()

            assert status["semantic_search_enabled"] is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestEnhancedCodeSearchIntegration:
    """Integration tests for EnhancedCodeSearch."""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self, enhanced_search):
        """Test a full workflow combining multiple search methods."""
        # Setup all mocks
        file_matches = [
            _create_file_match("auth.py", "backend", 0.9),
            _create_file_match("api.py", "backend", 0.7),
        ]
        purpose_results = [
            _create_purpose_result("authenticate_user", "function", 0.95),
        ]
        pattern_results = [
            _create_pattern_result("Use OAuth2", 0.92, "pattern"),
        ]
        caller_results = [
            _create_caller_result("login_handler", "views.py"),
        ]

        enhanced_search._code_searcher.search_with_semantics = AsyncMock(
            return_value=file_matches
        )
        enhanced_search._code_relationships.search_by_purpose = AsyncMock(
            return_value=purpose_results
        )
        enhanced_search._graphiti_search.get_patterns_and_gotchas = AsyncMock(
            return_value=(pattern_results, [])
        )
        enhanced_search._code_relationships.find_callers = AsyncMock(
            return_value=caller_results
        )

        # Test unified search
        unified = await enhanced_search.search_unified("authentication")
        assert unified["total"] == 4  # 2 files + 1 purpose + 1 pattern

        # Test individual searches
        purpose = await enhanced_search.search_by_purpose("authentication")
        assert len(purpose) == 1

        patterns = await enhanced_search.find_similar_patterns("authentication")
        assert len(patterns) == 1

        callers = await enhanced_search.find_callers("authenticate_user")
        assert len(callers) == 1

        # Check status
        status = enhanced_search.get_status()
        assert status["graphiti_enabled"] is True
