"""
Integration tests for enhanced code search functionality.

Tests the integration between EnhancedCodeSearch, SavedSearches, and
Graphiti memory for semantic code discovery.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend to path (idempotent)
REPO_ROOT = Path(__file__).resolve().parent.parent
_backend_path = str(REPO_ROOT / "apps" / "backend")
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from context.enhanced_search import EnhancedCodeSearch
from context.models import FileMatch
from context.saved_searches import SavedSearch, SavedSearches

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create test service structure
        service_dir = project_dir / "apps" / "backend" / "services"
        service_dir.mkdir(parents=True)

        # Create test Python files
        (service_dir / "auth.py").write_text(
            """
def authenticate_user(username, password):
    '''Authenticate user credentials.'''
    pass

def validate_token(token):
    '''Validate JWT token.'''
    pass
""",
            encoding="utf-8",
        )

        (service_dir / "database.py").write_text(
            """
def connect_database():
    '''Connect to database.'''
    pass

def query_data(sql):
    '''Execute SQL query.'''
    pass
""",
            encoding="utf-8",
        )

        yield project_dir


@pytest.fixture
def mock_graphiti_memory():
    """Create a mock Graphiti memory instance."""
    memory = MagicMock()

    # Mock code relationships
    memory.code_relationships = AsyncMock()
    memory.code_relationships.search_by_purpose = AsyncMock(
        return_value=[
            {
                "entity_name": "authenticate_user",
                "entity_type": "function",
                "purpose": "Authenticates user credentials",
                "file_path": "apps/backend/services/auth.py",
                "lineno": 2,
                "docstring": "Authenticate user credentials.",
                "tags": ["authentication", "security"],
                "score": 0.95,
            }
        ]
    )
    memory.code_relationships.find_callers = AsyncMock(
        return_value=[
            {
                "caller": "process_request",
                "file_path": "apps/backend/api.py",
                "lineno": 123,
                "call_type": "function",
                "module": None,
            }
        ]
    )
    memory.code_relationships.find_callees = AsyncMock(
        return_value=[
            {
                "callee": "validate_token",
                "file_path": "apps/backend/services/auth.py",
                "lineno": 8,
                "call_type": "function",
                "module": "auth",
            }
        ]
    )

    # Mock graphiti search
    memory._search = AsyncMock()
    memory._search.get_patterns_and_gotchas = AsyncMock(
        return_value=(
            [
                {
                    "content": "Always validate input before processing",
                    "score": 0.92,
                    "category": "security",
                    "confidence": 0.95,
                }
            ],
            [
                {
                    "content": "Don't forget to handle database connection errors",
                    "score": 0.88,
                }
            ],
        )
    )

    # Mock initialization status
    memory.is_initialized = True

    return memory


@pytest.fixture
def searcher_no_graphiti(temp_project_dir):
    """Create an EnhancedCodeSearch instance without Graphiti."""
    return EnhancedCodeSearch(project_dir=temp_project_dir, graphiti_memory=None)


@pytest.fixture
def searcher_with_graphiti(temp_project_dir, mock_graphiti_memory):
    """Create an EnhancedCodeSearch instance with mock Graphiti."""
    return EnhancedCodeSearch(
        project_dir=temp_project_dir, graphiti_memory=mock_graphiti_memory
    )


@pytest.fixture
def temp_searches_file():
    """Create a temporary saved searches file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        searches_file = Path(tmpdir) / "saved_searches.json"
        yield searches_file


# =============================================================================
# ENHANCED CODE SEARCH TESTS
# =============================================================================


class TestEnhancedCodeSearchInit:
    """Tests for EnhancedCodeSearch initialization."""

    def test_init_without_graphiti(self, temp_project_dir):
        """Test initialization without Graphiti memory."""
        searcher = EnhancedCodeSearch(
            project_dir=temp_project_dir, graphiti_memory=None
        )

        assert searcher.project_dir == temp_project_dir.resolve()
        assert searcher.graphiti_memory is None
        assert searcher._code_relationships is None
        assert searcher._graphiti_search is None

    def test_init_with_graphiti(self, temp_project_dir, mock_graphiti_memory):
        """Test initialization with Graphiti memory."""
        searcher = EnhancedCodeSearch(
            project_dir=temp_project_dir, graphiti_memory=mock_graphiti_memory
        )

        assert searcher.graphiti_memory == mock_graphiti_memory
        assert searcher._code_relationships is not None
        assert searcher._graphiti_search is not None

    def test_init_with_semantic_search_disabled(self, temp_project_dir):
        """Test initialization with semantic search disabled."""
        searcher = EnhancedCodeSearch(
            project_dir=temp_project_dir,
            graphiti_memory=None,
            use_semantic_search=False,
        )

        assert searcher._code_searcher.use_semantic_search is False


class TestEnhancedCodeSearchFileSearch:
    """Tests for file-based search methods."""

    def test_search_service(self, temp_project_dir):
        """Test searching a service for files."""
        searcher = EnhancedCodeSearch(
            project_dir=temp_project_dir, graphiti_memory=None
        )

        service_path = temp_project_dir / "apps" / "backend" / "services"
        results = searcher.search_service(
            service_path=service_path,
            service_name="services",
            keywords=["authenticate"],
        )

        assert isinstance(results, list)
        # Should find auth.py with "authenticate" keyword
        assert len(results) > 0
        assert any("auth.py" in str(r.path) for r in results)

    @pytest.mark.asyncio
    async def test_search_with_semantics(self, temp_project_dir):
        """Test semantic search with task context."""
        searcher = EnhancedCodeSearch(
            project_dir=temp_project_dir, graphiti_memory=None
        )

        service_path = temp_project_dir / "apps" / "backend" / "services"
        results = await searcher.search_with_semantics(
            service_path=service_path,
            service_name="services",
            keywords=["authenticate", "user"],
            task_query="Find user authentication functions",
        )

        assert isinstance(results, list)
        # Results should be sorted by relevance
        if results:
            assert isinstance(results[0], FileMatch)


class TestEnhancedCodeSearchGraphitiMethods:
    """Tests for Graphiti-dependent search methods."""

    @pytest.mark.asyncio
    async def test_search_by_purpose(self, searcher_with_graphiti):
        """Test searching code by purpose using Graphiti."""
        results = await searcher_with_graphiti.search_by_purpose("user authentication")

        assert len(results) == 1
        assert results[0]["entity_name"] == "authenticate_user"
        assert results[0]["entity_type"] == "function"
        assert results[0]["score"] == pytest.approx(0.95)

    @pytest.mark.asyncio
    async def test_search_by_purpose_without_graphiti(self, searcher_no_graphiti):
        """Test search_by_purpose returns empty without Graphiti."""
        results = await searcher_no_graphiti.search_by_purpose("user authentication")

        assert results == []

    @pytest.mark.asyncio
    async def test_find_similar_patterns(self, searcher_with_graphiti):
        """Test finding similar code patterns."""
        results = await searcher_with_graphiti.find_similar_patterns(
            "security patterns"
        )

        assert len(results) == 2  # 1 pattern + 1 gotcha
        # Results should be sorted by score
        assert results[0]["score"] >= results[1]["score"]

        # Check pattern structure
        pattern = results[0]
        assert "content" in pattern
        assert "score" in pattern
        assert "type" in pattern

    @pytest.mark.asyncio
    async def test_find_similar_patterns_without_graphiti(self, searcher_no_graphiti):
        """Test find_similar_patterns returns empty without Graphiti."""
        results = await searcher_no_graphiti.find_similar_patterns("security patterns")

        assert results == []

    @pytest.mark.asyncio
    async def test_find_callers(self, searcher_with_graphiti):
        """Test finding function callers."""
        callers = await searcher_with_graphiti.find_callers("authenticate_user")

        assert len(callers) == 1
        assert callers[0]["caller"] == "process_request"
        assert callers[0]["file_path"] == "apps/backend/api.py"

    @pytest.mark.asyncio
    async def test_find_callees(self, searcher_with_graphiti):
        """Test finding function callees."""
        callees = await searcher_with_graphiti.find_callees("authenticate_user")

        assert len(callees) == 1
        assert callees[0]["callee"] == "validate_token"
        assert callees[0]["file_path"] == "apps/backend/services/auth.py"

    @pytest.mark.asyncio
    async def test_search_unified(self, searcher_with_graphiti):
        """Test unified search across all methods."""
        results = await searcher_with_graphiti.search_unified(
            "authentication", limit=10
        )

        assert "files" in results
        assert "purpose" in results
        assert "patterns" in results
        assert "total" in results

        # Total should be sum of all result types
        expected_total = (
            len(results["files"]) + len(results["purpose"]) + len(results["patterns"])
        )
        assert results["total"] == expected_total


class TestEnhancedCodeSearchStatusAndExport:
    """Tests for status and export functionality."""

    def test_get_status_with_graphiti(self, searcher_with_graphiti):
        """Test getting status with Graphiti enabled."""
        status = searcher_with_graphiti.get_status()

        assert "project_dir" in status
        assert "graphiti_enabled" in status
        assert status["graphiti_enabled"] is True
        assert status["graphiti_initialized"] is True
        assert status["code_relationships_available"] is True
        assert status["graphiti_search_available"] is True

    def test_get_status_without_graphiti(self, searcher_no_graphiti):
        """Test getting status without Graphiti."""
        status = searcher_no_graphiti.get_status()

        assert status["graphiti_enabled"] is False
        assert status["graphiti_initialized"] is False
        assert status["code_relationships_available"] is False
        assert status["graphiti_search_available"] is False

    def test_export_search_results_json(self, searcher_no_graphiti):
        """Test exporting search results to JSON."""
        results = [
            {
                "entity_name": "test_func",
                "entity_type": "function",
                "purpose": "Test function",
            }
        ]

        output_path = _create_temp_json_path()

        try:
            exported_path = searcher_no_graphiti.export_search_results(
                results=results, output_path=output_path, format="json"
            )

            assert exported_path == output_path
            assert output_path.exists()

            # Verify JSON content
            with open(output_path, encoding="utf-8") as f:
                exported_data = json.load(f)
            assert exported_data == results
        finally:
            output_path.unlink(missing_ok=True)

    def test_export_json_with_filematch_objects(self, searcher_no_graphiti):
        """Test JSON export correctly serializes FileMatch objects
        without mutating the original results dict."""
        fm = FileMatch(
            path=Path("apps/backend/auth.py"),
            service="search",
            reason="keyword match",
            relevance_score=0.85,
            matching_lines=[(10, "def login")],
        )
        results = {
            "files": [fm],
            "purpose": [
                {
                    "entity_name": "login",
                    "entity_type": "function",
                    "score": 0.9,
                }
            ],
            "patterns": [],
            "total": 2,
        }

        output_path = _create_temp_json_path()

        try:
            searcher_no_graphiti.export_search_results(
                results=results, output_path=output_path, format="json"
            )

            # Original dict must still contain the FileMatch object
            assert isinstance(results["files"][0], FileMatch)

            # Exported JSON should have a plain dict for the file entry
            with open(output_path, encoding="utf-8") as f:
                exported_data = json.load(f)

            assert exported_data["files"][0]["path"] == "apps/backend/auth.py"
            assert exported_data["files"][0]["relevance_score"] == 0.85
            assert exported_data["purpose"][0]["entity_name"] == "login"
        finally:
            output_path.unlink(missing_ok=True)

    def test_export_search_results_csv(self, searcher_no_graphiti):
        """Test exporting search results to CSV."""
        results = [
            {
                "entity_name": "test_func",
                "entity_type": "function",
                "purpose": "Test function",
            },
            {
                "entity_name": "another_func",
                "entity_type": "function",
                "purpose": "Another test function",
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            exported_path = searcher_no_graphiti.export_search_results(
                results=results, output_path=output_path, format="csv"
            )

            assert exported_path == output_path
            assert output_path.exists()

            # Verify CSV content
            content = output_path.read_text(encoding="utf-8")
            assert "entity_name,entity_type,purpose" in content
            assert "test_func" in content
            assert "another_func" in content
        finally:
            output_path.unlink(missing_ok=True)

    def test_export_csv_key_union(self, searcher_no_graphiti):
        """Test CSV export uses the union of all row keys when rows
        have differing key sets."""
        results = [
            {"entity_name": "func_a", "purpose": "does A"},
            {"entity_name": "func_b", "module": "mod_b"},
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = Path(f.name)

        try:
            searcher_no_graphiti.export_search_results(
                results=results, output_path=output_path, format="csv"
            )

            content = output_path.read_text(encoding="utf-8")
            # Header must include all unique keys
            assert "entity_name" in content
            assert "purpose" in content
            assert "module" in content
            assert "func_a" in content
            assert "func_b" in content
        finally:
            output_path.unlink(missing_ok=True)

    def test_export_search_results_unsupported_format(self, searcher_no_graphiti):
        """Test export fails with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            searcher_no_graphiti.export_search_results(
                results=[{"test": "data"}], format="xml"
            )

    def test_export_search_results_empty_data(self, searcher_no_graphiti):
        """Test export fails with empty data."""
        with pytest.raises(ValueError, match="Cannot export empty"):
            searcher_no_graphiti.export_search_results(results=[])


# =============================================================================
# SAVED SEARCHES TESTS
# =============================================================================


class TestSavedSearch:
    """Tests for SavedSearch dataclass."""

    def test_saved_search_creation(self):
        """Test creating a SavedSearch."""
        search = SavedSearch(
            name="test_search",
            query="authentication",
            search_type="semantic",
            description="Find authentication code",
            tags=["security", "auth"],
        )

        assert search.name == "test_search"
        assert search.query == "authentication"
        assert search.search_type == "semantic"
        assert search.description == "Find authentication code"
        assert search.tags == ["security", "auth"]
        assert search.created_at is not None

    def test_saved_search_to_dict(self):
        """Test converting SavedSearch to dictionary."""
        search = SavedSearch(
            name="test_search", query="authentication", search_type="semantic"
        )

        data = search.to_dict()

        assert data["name"] == "test_search"
        assert data["query"] == "authentication"
        assert data["search_type"] == "semantic"

    def test_saved_search_from_dict(self):
        """Test creating SavedSearch from dictionary."""
        data = {
            "name": "test_search",
            "query": "authentication",
            "search_type": "semantic",
            "filters": {},
            "created_at": "2024-01-01T00:00:00+00:00",
            "last_used": None,
            "description": "Test search",
            "tags": ["test"],
        }

        search = SavedSearch.from_dict(data)

        assert search.name == "test_search"
        assert search.query == "authentication"
        assert search.search_type == "semantic"


class TestSavedSearchesInit:
    """Tests for SavedSearches initialization."""

    def test_init_default_path(self):
        """Test initialization with default path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                searches = SavedSearches()
                assert (
                    searches.storage_path
                    == Path(tmpdir) / ".auto-claude" / "saved_searches.json"
                )

    def test_init_custom_path(self, temp_searches_file):
        """Test initialization with custom path."""
        searches = SavedSearches(storage_path=temp_searches_file)
        assert searches.storage_path == temp_searches_file

    def test_init_loads_existing_searches(self, temp_searches_file):
        """Test initialization loads existing searches from file."""
        # Create saved searches file
        data = {
            "saved_at": "2024-01-01T00:00:00+00:00",
            "count": 1,
            "searches": [
                {
                    "name": "existing_search",
                    "query": "test",
                    "search_type": "semantic",
                    "filters": {},
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "last_used": None,
                    "description": None,
                    "tags": [],
                }
            ],
        }
        temp_searches_file.write_text(json.dumps(data), encoding="utf-8")

        searches = SavedSearches(storage_path=temp_searches_file)

        assert searches.count == 1
        existing = searches.get_search("existing_search")
        assert existing is not None
        assert existing.query == "test"


class TestSavedSearchesCRUD:
    """Tests for SavedSearches CRUD operations."""

    def test_save_search_new(self, temp_searches_file):
        """Test saving a new search."""
        searches = SavedSearches(storage_path=temp_searches_file)

        search = searches.save_search(
            name="auth_search",
            query="authentication",
            search_type="semantic",
            description="Find authentication code",
            tags=["security"],
        )

        assert search.name == "auth_search"
        assert search.query == "authentication"
        assert searches.count == 1

        # Verify file was created
        assert temp_searches_file.exists()

    def test_save_search_update(self, temp_searches_file):
        """Test updating an existing search."""
        searches = SavedSearches(storage_path=temp_searches_file)

        # Create initial search
        searches.save_search(
            name="auth_search",
            query="authentication",
            search_type="semantic",
        )

        # Update search
        updated = searches.save_search(
            name="auth_search",
            query="user authentication",  # Updated query
            search_type="semantic",
        )

        assert updated.query == "user authentication"
        assert updated.created_at  # Created date preserved
        assert updated.last_used is not None  # Last used updated
        assert searches.count == 1  # Still only one search

    def test_save_search_empty_name(self, temp_searches_file):
        """Test saving search with empty name raises error."""
        searches = SavedSearches(storage_path=temp_searches_file)

        with pytest.raises(ValueError, match="Search name cannot be empty"):
            searches.save_search(name="", query="test")

    def test_save_search_invalid_type(self, temp_searches_file):
        """Test saving search with invalid type raises error."""
        searches = SavedSearches(storage_path=temp_searches_file)

        with pytest.raises(ValueError, match="Invalid search_type"):
            searches.save_search(name="test", query="test", search_type="invalid")

    def test_get_search(self, temp_searches_file):
        """Test retrieving a saved search."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(name="test_search", query="test", search_type="semantic")

        retrieved = searches.get_search("test_search")

        assert retrieved is not None
        assert retrieved.name == "test_search"
        assert retrieved.last_used is not None  # Should update last_used

    def test_get_search_not_found(self, temp_searches_file):
        """Test retrieving non-existent search returns None."""
        searches = SavedSearches(storage_path=temp_searches_file)

        retrieved = searches.get_search("nonexistent")

        assert retrieved is None

    def test_list_searches_all(self, temp_searches_file):
        """Test listing all searches."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(name="search1", query="test1", search_type="semantic")
        searches.save_search(name="search2", query="test2", search_type="keyword")

        all_searches = searches.list_searches()

        assert len(all_searches) == 2

    def test_list_searches_filtered_by_type(self, temp_searches_file):
        """Test listing searches filtered by type."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(name="s1", query="test1", search_type="semantic")
        searches.save_search(name="k1", query="test2", search_type="keyword")
        searches.save_search(name="s2", query="test3", search_type="semantic")

        semantic_searches = searches.list_searches(search_type="semantic")

        assert len(semantic_searches) == 2
        assert all(s.search_type == "semantic" for s in semantic_searches)

    def test_list_searches_filtered_by_tags(self, temp_searches_file):
        """Test listing searches filtered by tags."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(
            name="s1", query="test1", search_type="semantic", tags=["security", "auth"]
        )
        searches.save_search(
            name="s2", query="test2", search_type="semantic", tags=["database"]
        )
        searches.save_search(
            name="s3", query="test3", search_type="semantic", tags=["security"]
        )

        security_searches = searches.list_searches(tags=["security"])

        assert len(security_searches) == 2

    def test_list_searches_sorting(self, temp_searches_file):
        """Test searches are sorted by last_used."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(name="s1", query="test1", search_type="semantic")
        searches.save_search(name="s2", query="test2", search_type="semantic")
        searches.save_search(name="s3", query="test3", search_type="semantic")

        # Access s2 to update last_used
        searches.get_search("s2")

        all_searches = searches.list_searches()

        # s2 should be first (most recently used)
        assert all_searches[0].name == "s2"

    def test_delete_search(self, temp_searches_file):
        """Test deleting a search."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(name="test", query="test", search_type="semantic")
        assert searches.count == 1

        deleted = searches.delete_search("test")

        assert deleted is True
        assert searches.count == 0

    def test_delete_search_not_found(self, temp_searches_file):
        """Test deleting non-existent search returns False."""
        searches = SavedSearches(storage_path=temp_searches_file)

        deleted = searches.delete_search("nonexistent")

        assert deleted is False

    def test_update_search(self, temp_searches_file):
        """Test updating search fields."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(name="test", query="old", search_type="semantic")

        updated = searches.update_search(
            name="test", query="new", description="Updated description"
        )

        assert updated is not None
        assert updated.query == "new"
        assert updated.description == "Updated description"
        assert updated.created_at  # Created date preserved

    def test_update_search_not_found(self, temp_searches_file):
        """Test updating non-existent search returns None."""
        searches = SavedSearches(storage_path=temp_searches_file)

        updated = searches.update_search(name="nonexistent", query="new")

        assert updated is None


def _make_search_entry(
    name: str,
    query: str,
    search_type: str = "semantic",
) -> dict:
    """Build a single saved-search dict suitable for import data."""
    return {
        "name": name,
        "query": query,
        "search_type": search_type,
        "filters": {},
        "created_at": "2024-01-01T00:00:00+00:00",
        "last_used": None,
        "description": None,
        "tags": [],
    }


def _make_import_data(searches: list[dict]) -> dict:
    """Build an import-file payload wrapping a list of search entries."""
    return {
        "exported_at": "2024-01-01T00:00:00+00:00",
        "count": len(searches),
        "searches": searches,
    }


def _write_import_file(data: dict) -> Path:
    """Write *data* as JSON to a temporary file and return its path.

    The caller is responsible for deleting the file when done (use
    ``path.unlink(missing_ok=True)`` in a ``finally`` block).
    """
    with tempfile.NamedTemporaryFile(
        suffix=".json", mode="w", delete=False, encoding="utf-8"
    ) as f:
        import_path = Path(f.name)
        json.dump(data, f)
    return import_path


def _create_temp_json_path() -> Path:
    """Create a temporary .json file path (empty) for export tests.

    The caller is responsible for deleting the file when done.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        return Path(f.name)


class TestSavedSearchesImportExport:
    """Tests for import/export functionality."""

    def test_export_searches(self, temp_searches_file):
        """Test exporting searches to JSON."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(name="s1", query="test1", search_type="semantic")
        searches.save_search(name="s2", query="test2", search_type="keyword")

        export_path = _create_temp_json_path()

        try:
            result_path = searches.export_searches(output_path=export_path)

            assert result_path == export_path
            assert export_path.exists()

            # Verify content
            data = json.loads(export_path.read_text(encoding="utf-8"))
            assert "exported_at" in data
            assert data["count"] == 2
            assert len(data["searches"]) == 2
        finally:
            export_path.unlink(missing_ok=True)

    def test_export_searches_with_filters(self, temp_searches_file):
        """Test exporting searches with filters."""
        searches = SavedSearches(storage_path=temp_searches_file)

        searches.save_search(
            name="s1", query="test1", search_type="semantic", tags=["security"]
        )
        searches.save_search(
            name="k1", query="test2", search_type="keyword", tags=["database"]
        )

        export_path = _create_temp_json_path()

        try:
            # Export only semantic searches
            searches.export_searches(output_path=export_path, search_type="semantic")

            data = json.loads(export_path.read_text(encoding="utf-8"))
            assert data["count"] == 1
            assert data["searches"][0]["name"] == "s1"
        finally:
            export_path.unlink(missing_ok=True)

    def test_import_searches(self, temp_searches_file):
        """Test importing searches from JSON."""
        import_data = _make_import_data(
            [
                _make_search_entry("imported1", "test1", "semantic"),
                _make_search_entry("imported2", "test2", "keyword"),
            ]
        )

        import_path = _write_import_file(import_data)

        try:
            searches = SavedSearches(storage_path=temp_searches_file)

            count = searches.import_searches(import_path)

            assert count == 2
            assert searches.count == 2

            s1 = searches.get_search("imported1")
            assert s1 is not None
            assert s1.query == "test1"
        finally:
            import_path.unlink(missing_ok=True)

    def test_import_searches_with_conflict_error(self, temp_searches_file):
        """Test import with name conflict raises error."""
        searches = SavedSearches(storage_path=temp_searches_file)
        searches.save_search(name="existing", query="old", search_type="semantic")

        import_data = _make_import_data(
            [
                _make_search_entry("existing", "new"),
            ]
        )
        import_path = _write_import_file(import_data)

        try:
            with pytest.raises(ValueError, match="already exists"):
                searches.import_searches(import_path, merge_strategy="error")
        finally:
            import_path.unlink(missing_ok=True)

    def test_import_searches_with_conflict_skip(self, temp_searches_file):
        """Test import with conflict skip strategy."""
        searches = SavedSearches(storage_path=temp_searches_file)
        searches.save_search(name="existing", query="old", search_type="semantic")

        import_data = _make_import_data(
            [
                _make_search_entry("existing", "new"),
            ]
        )
        import_path = _write_import_file(import_data)

        try:
            count = searches.import_searches(import_path, merge_strategy="skip")

            assert count == 0  # No imports due to conflict
            assert searches.get_search("existing").query == "old"  # Unchanged
        finally:
            import_path.unlink(missing_ok=True)

    def test_import_searches_with_conflict_overwrite(self, temp_searches_file):
        """Test import with conflict overwrite strategy."""
        searches = SavedSearches(storage_path=temp_searches_file)
        searches.save_search(name="existing", query="old", search_type="semantic")

        import_data = _make_import_data(
            [
                _make_search_entry("existing", "new"),
            ]
        )
        import_path = _write_import_file(import_data)

        try:
            count = searches.import_searches(import_path, merge_strategy="overwrite")

            assert count == 1  # Imported with overwrite
            assert searches.get_search("existing").query == "new"  # Overwritten
        finally:
            import_path.unlink(missing_ok=True)

    def test_import_searches_invalid_strategy(self, temp_searches_file):
        """Test import with invalid merge strategy raises error."""
        searches = SavedSearches(storage_path=temp_searches_file)

        import_path = _write_import_file(_make_import_data([]))

        try:
            with pytest.raises(ValueError, match="Invalid merge_strategy"):
                searches.import_searches(import_path, merge_strategy="invalid")
        finally:
            import_path.unlink(missing_ok=True)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestSearchIntegration:
    """Integration tests for EnhancedCodeSearch and SavedSearches."""

    @pytest.mark.asyncio
    async def test_save_and_reuse_search(self, temp_project_dir, mock_graphiti_memory):
        """Test saving a search and reusing it."""
        # Create searcher
        searcher = EnhancedCodeSearch(
            project_dir=temp_project_dir, graphiti_memory=mock_graphiti_memory
        )

        # Perform search
        await searcher.search_by_purpose("authentication")

        # Save search
        with tempfile.TemporaryDirectory() as tmpdir:
            searches_file = Path(tmpdir) / "searches.json"
            saved_searches = SavedSearches(storage_path=searches_file)

            saved_searches.save_search(
                name="auth_search",
                query="authentication",
                search_type="semantic",
                description="Find authentication code",
            )

            # Retrieve saved search
            retrieved = saved_searches.get_search("auth_search")

            assert retrieved is not None
            assert retrieved.query == "authentication"
            assert retrieved.description == "Find authentication code"

    @pytest.mark.asyncio
    async def test_export_and_import_search_workflow(self, temp_project_dir):
        """Test exporting search results and importing saved searches."""
        searcher = EnhancedCodeSearch(
            project_dir=temp_project_dir, graphiti_memory=None
        )

        # Perform search
        results = [
            {
                "entity_name": "authenticate_user",
                "entity_type": "function",
                "purpose": "Authentication",
            }
        ]

        # Export results
        results_path = temp_project_dir / "export_results.json"

        searcher.export_search_results(
            results=results, output_path=results_path, format="json"
        )

        # Verify export
        assert results_path.exists()
        exported_data = json.loads(results_path.read_text(encoding="utf-8"))
        assert exported_data == results

        # -- Also exercise the saved-searches import path --
        with tempfile.TemporaryDirectory() as tmpdir:
            searches_file = Path(tmpdir) / "searches.json"
            saved_searches = SavedSearches(storage_path=searches_file)

            # Save a search, export it, then import into a fresh instance
            saved_searches.save_search(
                name="auth_search",
                query="authentication",
                search_type="semantic",
            )

            export_path = Path(tmpdir) / "exported_searches.json"
            saved_searches.export_searches(output_path=export_path)

            # Import into a new instance
            new_file = Path(tmpdir) / "new_searches.json"
            new_searches = SavedSearches(storage_path=new_file)
            count = new_searches.import_searches(export_path)

            assert count == 1
            imported = new_searches.get_search("auth_search")
            assert imported is not None
            assert imported.query == "authentication"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
