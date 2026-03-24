#!/usr/bin/env python3
"""
Unit tests for SavedSearches class.

Tests the saved searches management that handles:
- Saving and loading searches from JSON
- CRUD operations on saved searches
- Export and import functionality
- Filtering and sorting searches
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Add apps/backend to path for imports (idempotent guard)
sys_path = Path(__file__).parent.parent / "apps" / "backend"
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from context.saved_searches import SavedSearch, SavedSearches

# =============================================================================
# HELPER FACTORIES
# =============================================================================


def _make_search_data(
    name: str = "test-search",
    query: str = "test query",
    search_type: str = "semantic",
    **overrides,
) -> dict:
    """Create a SavedSearch data dict with defaults."""
    data = {
        "name": name,
        "query": query,
        "search_type": search_type,
        "filters": {},
        "created_at": datetime.now(UTC).isoformat(),
        "last_used": None,
        "description": None,
        "tags": [],
    }
    data.update(overrides)
    return data


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def tmp_storage_path(tmp_path):
    """Create a temporary storage path for saved searches."""
    return tmp_path / "saved_searches.json"


@pytest.fixture
def saved_searches(tmp_storage_path):
    """Create a SavedSearches instance with temporary storage."""
    return SavedSearches(storage_path=tmp_storage_path)


@pytest.fixture
def sample_search():
    """Create a sample SavedSearch object."""
    return SavedSearch(
        name="auth_search",
        query="authentication login",
        search_type="semantic",
        filters={"service": "backend", "file_types": ["py"]},
        description="Find authentication code",
        tags=["auth", "security"],
    )


# =============================================================================
# SavedSearch DATACLASS TESTS
# =============================================================================


class TestSavedSearchDataclass:
    """Test SavedSearch dataclass functionality."""

    def test_saved_search_creation(self):
        """Test creating a SavedSearch object."""
        search = SavedSearch(
            name="test_search",
            query="test query",
            search_type="keyword",
        )

        assert search.name == "test_search"
        assert search.query == "test query"
        assert search.search_type == "keyword"
        assert search.filters == {}
        assert search.description is None
        assert search.tags == []
        assert isinstance(search.created_at, str)
        assert search.last_used is None

    def test_saved_search_with_all_fields(self):
        """Test creating a SavedSearch with all fields."""
        created_at = "2024-01-01T00:00:00+00:00"
        last_used = "2024-01-02T00:00:00+00:00"

        search = SavedSearch(
            name="full_search",
            query="complex query",
            search_type="hybrid",
            filters={"service": "backend"},
            created_at=created_at,
            last_used=last_used,
            description="Full description",
            tags=["tag1", "tag2"],
        )

        assert search.name == "full_search"
        assert search.query == "complex query"
        assert search.search_type == "hybrid"
        assert search.filters == {"service": "backend"}
        assert search.created_at == created_at
        assert search.last_used == last_used
        assert search.description == "Full description"
        assert search.tags == ["tag1", "tag2"]

    def test_to_dict(self):
        """Test converting SavedSearch to dictionary."""
        search = SavedSearch(
            name="test",
            query="query",
            search_type="semantic",
            tags=["test"],
        )

        result = search.to_dict()

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["query"] == "query"
        assert result["search_type"] == "semantic"
        assert result["tags"] == ["test"]
        assert "created_at" in result

    def test_from_dict(self):
        """Test creating SavedSearch from dictionary."""
        data = {
            "name": "test",
            "query": "query",
            "search_type": "keyword",
            "filters": {"service": "backend"},
            "created_at": "2024-01-01T00:00:00+00:00",
            "last_used": "2024-01-02T00:00:00+00:00",
            "description": "Test search",
            "tags": ["test"],
        }

        search = SavedSearch.from_dict(data)

        assert search.name == "test"
        assert search.query == "query"
        assert search.search_type == "keyword"
        assert search.filters == {"service": "backend"}
        assert search.created_at == "2024-01-01T00:00:00+00:00"
        assert search.last_used == "2024-01-02T00:00:00+00:00"
        assert search.description == "Test search"
        assert search.tags == ["test"]

    def test_roundtrip_dict_conversion(self):
        """Test that to_dict and from_dict are inverses."""
        original = SavedSearch(
            name="test",
            query="query",
            search_type="hybrid",
            filters={"key": "value"},
            description="desc",
            tags=["a", "b"],
        )

        # Convert to dict and back
        dict_data = original.to_dict()
        restored = SavedSearch.from_dict(dict_data)

        assert restored.name == original.name
        assert restored.query == original.query
        assert restored.search_type == original.search_type
        assert restored.filters == original.filters
        assert restored.description == original.description
        assert restored.tags == original.tags


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestSavedSearchesInit:
    """Test SavedSearches initialization."""

    def test_init_with_custom_storage_path(self, tmp_storage_path):
        """Test initialization with custom storage path."""
        searches = SavedSearches(storage_path=tmp_storage_path)

        assert searches.storage_path == tmp_storage_path
        assert searches.count == 0

    def test_init_with_default_storage_path(self, tmp_path):
        """Test initialization with default storage path."""
        # Change to temp directory to test default path
        original_cwd = Path.cwd()
        try:
            # Mock Path.cwd() to return temp directory
            with patch.object(Path, "cwd", return_value=tmp_path):
                searches = SavedSearches()

                expected_path = tmp_path / ".auto-claude" / "saved_searches.json"
                assert searches.storage_path == expected_path
        finally:
            # Restore original cwd
            import os

            os.chdir(original_cwd)

    def test_init_loads_existing_searches(self, tmp_storage_path):
        """Test that initialization loads existing searches from file."""
        # Create a pre-existing searches file
        existing_data = {
            "saved_at": datetime.now(UTC).isoformat(),
            "count": 1,
            "searches": [_make_search_data(name="existing_search")],
        }
        tmp_storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_storage_path.write_text(json.dumps(existing_data), encoding="utf-8")

        # Initialize - should load existing search
        searches = SavedSearches(storage_path=tmp_storage_path)

        assert searches.count == 1
        assert searches.get_search("existing_search") is not None

    def test_init_handles_missing_file(self, tmp_storage_path):
        """Test that initialization handles missing storage file gracefully."""
        # Don't create the file
        searches = SavedSearches(storage_path=tmp_storage_path)

        assert searches.count == 0
        assert not tmp_storage_path.exists()

    def test_init_handles_invalid_json(self, tmp_storage_path):
        """Test that initialization handles invalid JSON gracefully."""
        # Create invalid JSON file
        tmp_storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_storage_path.write_text("invalid json content", encoding="utf-8")

        # Should not raise exception, just log warning
        searches = SavedSearches(storage_path=tmp_storage_path)

        assert searches.count == 0


# =============================================================================
# save_search TESTS
# =============================================================================


class TestSaveSearch:
    """Test save_search method."""

    def test_save_new_search(self, saved_searches):
        """Test saving a new search."""
        search = saved_searches.save_search(
            name="new_search",
            query="test query",
            search_type="semantic",
            description="Test description",
            tags=["test"],
        )

        assert search.name == "new_search"
        assert search.query == "test query"
        assert search.search_type == "semantic"
        assert search.description == "Test description"
        assert search.tags == ["test"]
        assert saved_searches.count == 1

    def test_save_search_with_default_params(self, saved_searches):
        """Test saving a search with default parameters."""
        search = saved_searches.save_search(
            name="minimal_search",
            query="query",
        )

        assert search.name == "minimal_search"
        assert search.query == "query"
        assert search.search_type == "semantic"  # default
        assert search.filters == {}
        assert search.description is None
        assert search.tags == []

    def test_save_search_updates_existing(self, saved_searches):
        """Test that saving with same name updates existing search."""
        # Create initial search
        original = saved_searches.save_search(
            name="update_test",
            query="original query",
            search_type="keyword",
            description="Original description",
        )
        original_created_at = original.created_at

        # Update with new data
        updated = saved_searches.save_search(
            name="update_test",
            query="updated query",
            search_type="semantic",
            description="Updated description",
        )

        # Should preserve created_at
        assert updated.created_at == original_created_at
        # But update other fields
        assert updated.query == "updated query"
        assert updated.search_type == "semantic"
        assert updated.description == "Updated description"
        assert updated.last_used is not None
        # Should still be only 1 search
        assert saved_searches.count == 1

    def test_save_search_empty_name_raises_error(self, saved_searches):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Search name cannot be empty"):
            saved_searches.save_search(
                name="",
                query="test",
            )

    def test_save_search_whitespace_name_raises_error(self, saved_searches):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="Search name cannot be empty"):
            saved_searches.save_search(
                name="   ",
                query="test",
            )

    def test_save_search_invalid_type_raises_error(self, saved_searches):
        """Test that invalid search_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid search_type: invalid"):
            saved_searches.save_search(
                name="test",
                query="query",
                search_type="invalid",
            )

    def test_save_search_persists_to_file(self, saved_searches, tmp_storage_path):
        """Test that saving persists to storage file."""
        saved_searches.save_search(
            name="persistent_search",
            query="query",
        )

        # Verify file exists and contains data
        assert tmp_storage_path.exists()
        content = tmp_storage_path.read_text(encoding="utf-8")
        data = json.loads(content)

        assert data["count"] == 1
        assert len(data["searches"]) == 1
        assert data["searches"][0]["name"] == "persistent_search"

    def test_save_search_with_filters(self, saved_searches):
        """Test saving a search with filters."""
        filters = {
            "service": "backend",
            "file_types": ["py", "js"],
            "exclude_paths": ["tests/"],
        }

        search = saved_searches.save_search(
            name="filtered_search",
            query="query",
            filters=filters,
        )

        assert search.filters == filters


# =============================================================================
# get_search TESTS
# =============================================================================


class TestGetSearch:
    """Test get_search method."""

    def test_get_existing_search(self, saved_searches):
        """Test retrieving an existing search."""
        saved_searches.save_search(
            name="test_search",
            query="query",
        )

        search = saved_searches.get_search("test_search")

        assert search is not None
        assert search.name == "test_search"
        assert search.query == "query"

    def test_get_nonexistent_search(self, saved_searches):
        """Test retrieving a non-existent search returns None."""
        search = saved_searches.get_search("nonexistent")

        assert search is None

    def test_get_search_updates_last_used(self, saved_searches):
        """Test that getting a search updates last_used timestamp."""
        saved_searches.save_search(name="test", query="query")
        original_search = saved_searches.get_search("test")
        original_last_used = original_search.last_used

        # Wait a tiny bit and get again
        import time

        time.sleep(0.01)

        updated_search = saved_searches.get_search("test")

        # last_used should be updated
        assert updated_search.last_used != original_last_used
        assert updated_search.last_used is not None

    def test_get_search_persists_last_used(self, saved_searches, tmp_storage_path):
        """Test that last_used update is persisted to file."""
        saved_searches.save_search(name="test", query="query")
        saved_searches.get_search("test")

        # Reload from file
        searches_reloaded = SavedSearches(storage_path=tmp_storage_path)
        search = searches_reloaded.get_search("test")

        assert search.last_used is not None


# =============================================================================
# list_searches TESTS
# =============================================================================


class TestListSearches:
    """Test list_searches method."""

    def test_list_all_searches(self, saved_searches):
        """Test listing all searches."""
        saved_searches.save_search(name="search1", query="query1")
        saved_searches.save_search(name="search2", query="query2")
        saved_searches.save_search(name="search3", query="query3")

        searches = saved_searches.list_searches()

        assert len(searches) == 3
        names = [s.name for s in searches]
        assert "search1" in names
        assert "search2" in names
        assert "search3" in names

    def test_list_searches_empty(self, saved_searches):
        """Test listing searches when none exist."""
        searches = saved_searches.list_searches()

        assert searches == []

    def test_list_searches_filtered_by_type(self, saved_searches):
        """Test listing searches filtered by search_type."""
        saved_searches.save_search(name="s1", query="q1", search_type="semantic")
        saved_searches.save_search(name="k1", query="q2", search_type="keyword")
        saved_searches.save_search(name="h1", query="q3", search_type="hybrid")
        saved_searches.save_search(name="s2", query="q4", search_type="semantic")

        semantic_searches = saved_searches.list_searches(search_type="semantic")

        assert len(semantic_searches) == 2
        names = [s.name for s in semantic_searches]
        assert set(names) == {"s1", "s2"}

    def test_list_searches_filtered_by_tags(self, saved_searches):
        """Test listing searches filtered by tags."""
        saved_searches.save_search(name="auth1", query="q1", tags=["auth", "security"])
        saved_searches.save_search(name="auth2", query="q2", tags=["auth", "api"])
        saved_searches.save_search(name="ui", query="q3", tags=["ui", "frontend"])

        # Single tag filter
        auth_searches = saved_searches.list_searches(tags=["auth"])
        assert len(auth_searches) == 2

        # Multiple tags (must match all)
        auth_api_searches = saved_searches.list_searches(tags=["auth", "api"])
        assert len(auth_api_searches) == 1
        assert auth_api_searches[0].name == "auth2"

    def test_list_searches_sorted_by_last_used(self, saved_searches):
        """Test that searches are sorted by last_used (most recent first)."""
        # Create searches in order
        saved_searches.save_search(name="old", query="q1")
        import time

        time.sleep(0.01)

        saved_searches.save_search(name="middle", query="q2")
        time.sleep(0.01)

        saved_searches.save_search(name="new", query="q3")

        # Access to update last_used timestamps
        saved_searches.get_search("old")
        time.sleep(0.01)
        saved_searches.get_search("middle")
        time.sleep(0.01)
        saved_searches.get_search("new")

        searches = saved_searches.list_searches()

        # Most recently used should be first
        assert searches[0].name == "new"
        assert searches[1].name == "middle"
        assert searches[2].name == "old"

    def test_list_searches_with_no_last_used(self, saved_searches):
        """Test sorting when some searches have no last_used."""
        saved_searches.save_search(name="no_last_used", query="q1")
        saved_searches.save_search(name="has_last_used", query="q2")
        saved_searches.get_search("has_last_used")  # Update last_used

        searches = saved_searches.list_searches()

        # Search with last_used should come first
        assert searches[0].name == "has_last_used"
        assert searches[1].name == "no_last_used"


# =============================================================================
# delete_search TESTS
# =============================================================================


class TestDeleteSearch:
    """Test delete_search method."""

    def test_delete_existing_search(self, saved_searches):
        """Test deleting an existing search."""
        saved_searches.save_search(name="to_delete", query="query")
        assert saved_searches.count == 1

        result = saved_searches.delete_search("to_delete")

        assert result is True
        assert saved_searches.count == 0

    def test_delete_nonexistent_search(self, saved_searches):
        """Test deleting a non-existent search."""
        result = saved_searches.delete_search("nonexistent")

        assert result is False

    def test_delete_search_persists_to_file(self, saved_searches, tmp_storage_path):
        """Test that deletion is persisted to file."""
        saved_searches.save_search(name="test", query="query")
        saved_searches.delete_search("test")

        # Reload from file
        searches_reloaded = SavedSearches(storage_path=tmp_storage_path)

        assert searches_reloaded.count == 0


# =============================================================================
# update_search TESTS
# =============================================================================


class TestUpdateSearch:
    """Test update_search method."""

    def test_update_search_query(self, saved_searches):
        """Test updating search query."""
        saved_searches.save_search(name="test", query="original")

        updated = saved_searches.update_search(name="test", query="updated")

        assert updated is not None
        assert updated.query == "updated"
        assert saved_searches.get_search("test").query == "updated"

    def test_update_search_all_fields(self, saved_searches):
        """Test updating all search fields."""
        saved_searches.save_search(
            name="test",
            query="original",
            search_type="keyword",
        )

        updated = saved_searches.update_search(
            name="test",
            query="new query",
            search_type="semantic",
            filters={"service": "backend"},
            description="New description",
            tags=["updated"],
        )

        assert updated.query == "new query"
        assert updated.search_type == "semantic"
        assert updated.filters == {"service": "backend"}
        assert updated.description == "New description"
        assert updated.tags == ["updated"]

    def test_update_nonexistent_search(self, saved_searches):
        """Test updating a non-existent search returns None."""
        result = saved_searches.update_search(name="nonexistent", query="query")

        assert result is None

    def test_update_search_invalid_type_raises_error(self, saved_searches):
        """Test that invalid search_type raises ValueError."""
        saved_searches.save_search(name="test", query="query")

        with pytest.raises(ValueError, match="Invalid search_type"):
            saved_searches.update_search(name="test", search_type="invalid")

    def test_update_search_preserves_created_at(self, saved_searches):
        """Test that update preserves created_at timestamp."""
        original = saved_searches.save_search(name="test", query="original")
        original_created_at = original.created_at

        updated = saved_searches.update_search(name="test", query="updated")

        assert updated.created_at == original_created_at

    def test_update_search_updates_last_used(self, saved_searches):
        """Test that update sets last_used timestamp."""
        saved_searches.save_search(name="test", query="original")

        updated = saved_searches.update_search(name="test", query="updated")

        assert updated.last_used is not None


# =============================================================================
# export_searches TESTS
# =============================================================================


class TestExportSearches:
    """Test export_searches method."""

    def test_export_all_searches(self, saved_searches, tmp_path):
        """Test exporting all searches."""
        saved_searches.save_search(name="s1", query="q1", search_type="semantic")
        saved_searches.save_search(name="s2", query="q2", search_type="keyword")

        export_path = tmp_path / "export.json"
        result_path = saved_searches.export_searches(output_path=export_path)

        assert result_path == export_path
        assert export_path.exists()

        # Verify content
        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data["count"] == 2
        assert len(data["searches"]) == 2
        assert "exported_at" in data

    def test_export_with_default_path(self, saved_searches, tmp_path):
        """Test export with default output path."""
        saved_searches.save_search(name="test", query="query")

        # Change to temp directory for default path
        original_cwd = Path.cwd()
        try:
            with patch.object(Path, "cwd", return_value=tmp_path):
                result_path = saved_searches.export_searches()

                expected_path = tmp_path / "saved_searches_export.json"
                assert result_path == expected_path
                assert expected_path.exists()
        finally:
            import os

            os.chdir(original_cwd)

    def test_export_filtered_by_type(self, saved_searches, tmp_path):
        """Test exporting searches filtered by type."""
        saved_searches.save_search(name="s1", query="q1", search_type="semantic")
        saved_searches.save_search(name="k1", query="q2", search_type="keyword")

        export_path = tmp_path / "export.json"
        saved_searches.export_searches(output_path=export_path, search_type="semantic")

        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data["count"] == 1
        assert data["searches"][0]["name"] == "s1"

    def test_export_filtered_by_tags(self, saved_searches, tmp_path):
        """Test exporting searches filtered by tags."""
        saved_searches.save_search(name="auth1", query="q1", tags=["auth"])
        saved_searches.save_search(name="auth2", query="q2", tags=["auth", "api"])
        saved_searches.save_search(name="ui", query="q3", tags=["ui"])

        export_path = tmp_path / "export.json"
        saved_searches.export_searches(output_path=export_path, tags=["auth", "api"])

        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data["count"] == 1
        assert data["searches"][0]["name"] == "auth2"

    def test_export_empty_searches(self, saved_searches, tmp_path):
        """Test exporting when no searches exist."""
        export_path = tmp_path / "export.json"
        saved_searches.export_searches(output_path=export_path)

        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data["count"] == 0
        assert data["searches"] == []


# =============================================================================
# import_searches TESTS
# =============================================================================


class TestImportSearches:
    """Test import_searches method."""

    def _create_import_file(self, path: Path, searches: list[dict]) -> None:
        """Helper to create an import file."""
        data = {
            "exported_at": datetime.now(UTC).isoformat(),
            "count": len(searches),
            "searches": searches,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def test_import_searches_success(self, saved_searches, tmp_path):
        """Test successfully importing searches."""
        import_path = tmp_path / "import.json"
        self._create_import_file(
            import_path,
            [
                _make_search_data(name="imported1", query="query1"),
                _make_search_data(
                    name="imported2", query="query2", search_type="keyword"
                ),
            ],
        )

        count = saved_searches.import_searches(import_path)

        assert count == 2
        assert saved_searches.count == 2
        assert saved_searches.get_search("imported1") is not None
        assert saved_searches.get_search("imported2") is not None

    def test_import_with_merge_strategy_error_on_conflict(
        self, saved_searches, tmp_path
    ):
        """Test import with error strategy on name conflict."""
        # Add existing search
        saved_searches.save_search(name="existing", query="old")

        import_path = tmp_path / "import.json"
        self._create_import_file(
            import_path,
            [_make_search_data(name="existing", query="new")],
        )

        # Should raise ValueError on conflict
        with pytest.raises(ValueError, match="already exists"):
            saved_searches.import_searches(import_path, merge_strategy="error")

    def test_import_with_merge_strategy_skip(self, saved_searches, tmp_path):
        """Test import with skip strategy on name conflict."""
        saved_searches.save_search(name="existing", query="old")

        import_path = tmp_path / "import.json"
        self._create_import_file(
            import_path,
            [
                _make_search_data(name="existing", query="new"),
                _make_search_data(name="new_search", query="query"),
            ],
        )

        count = saved_searches.import_searches(import_path, merge_strategy="skip")

        # Should skip conflicting search, import new one
        assert count == 1
        assert saved_searches.count == 2  # existing + new_search
        assert saved_searches.get_search("existing").query == "old"  # Unchanged

    def test_import_with_merge_strategy_overwrite(self, saved_searches, tmp_path):
        """Test import with overwrite strategy on name conflict."""
        saved_searches.save_search(name="existing", query="old")

        import_path = tmp_path / "import.json"
        self._create_import_file(
            import_path,
            [_make_search_data(name="existing", query="new")],
        )

        count = saved_searches.import_searches(import_path, merge_strategy="overwrite")

        # Should overwrite
        assert count == 1
        assert saved_searches.count == 1
        assert saved_searches.get_search("existing").query == "new"

    def test_import_invalid_merge_strategy(self, saved_searches, tmp_path):
        """Test that invalid merge_strategy raises ValueError."""
        import_path = tmp_path / "import.json"
        self._create_import_file(import_path, [])

        with pytest.raises(ValueError, match="Invalid merge_strategy"):
            saved_searches.import_searches(import_path, merge_strategy="invalid")

    def test_import_invalid_file_format(self, saved_searches, tmp_path):
        """Test that invalid file format raises ValueError."""
        import_path = tmp_path / "invalid.json"
        import_path.write_text('{"invalid": "format"}', encoding="utf-8")

        with pytest.raises(ValueError, match="missing 'searches' key"):
            saved_searches.import_searches(import_path)

    def test_import_invalid_json(self, saved_searches, tmp_path):
        """Test that invalid JSON raises error."""
        import_path = tmp_path / "invalid.json"
        import_path.write_text("not json", encoding="utf-8")

        with pytest.raises((OSError, json.JSONDecodeError)):
            saved_searches.import_searches(import_path)

    def test_import_persists_to_file(self, saved_searches, tmp_path, tmp_storage_path):
        """Test that imported searches are persisted."""
        import_path = tmp_path / "import.json"
        self._create_import_file(
            import_path,
            [_make_search_data(name="imported", query="query")],
        )

        saved_searches.import_searches(import_path)

        # Reload from file
        searches_reloaded = SavedSearches(storage_path=tmp_storage_path)

        assert searches_reloaded.count == 1
        assert searches_reloaded.get_search("imported") is not None


# =============================================================================
# PROPERTIES TESTS
# =============================================================================


class TestProperties:
    """Test SavedSearches properties."""

    def test_storage_path_property(self, saved_searches, tmp_storage_path):
        """Test storage_path property."""
        assert saved_searches.storage_path == tmp_storage_path

    def test_count_property(self, saved_searches):
        """Test count property."""
        assert saved_searches.count == 0

        saved_searches.save_search(name="s1", query="q1")
        assert saved_searches.count == 1

        saved_searches.save_search(name="s2", query="q2")
        assert saved_searches.count == 2

        saved_searches.delete_search("s1")
        assert saved_searches.count == 1


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestSavedSearchesIntegration:
    """Integration tests for SavedSearches."""

    def test_full_crud_workflow(self, saved_searches):
        """Test a full CRUD workflow."""
        # Create
        saved_searches.save_search(
            name="full_test",
            query="test query",
            search_type="semantic",
            tags=["test"],
        )
        assert saved_searches.count == 1

        # Read
        retrieved = saved_searches.get_search("full_test")
        assert retrieved is not None
        assert retrieved.query == "test query"

        # Update
        updated = saved_searches.update_search(name="full_test", query="updated query")
        assert updated.query == "updated query"

        # List
        searches = saved_searches.list_searches()
        assert len(searches) == 1

        # Delete
        deleted = saved_searches.delete_search("full_test")
        assert deleted is True
        assert saved_searches.count == 0

    def test_export_import_roundtrip(self, saved_searches, tmp_path):
        """Test that export and import are inverse operations."""
        # Create searches
        saved_searches.save_search(
            name="export_test1",
            query="query1",
            search_type="semantic",
            tags=["tag1"],
        )
        saved_searches.save_search(
            name="export_test2",
            query="query2",
            search_type="keyword",
            tags=["tag2"],
        )

        # Export
        export_path = tmp_path / "export.json"
        saved_searches.export_searches(output_path=export_path)

        # Import into new instance
        new_storage = tmp_path / "new_storage.json"
        new_searches = SavedSearches(storage_path=new_storage)

        count = new_searches.import_searches(export_path)

        assert count == 2
        assert new_searches.count == 2

        # Verify data integrity
        imported1 = new_searches.get_search("export_test1")
        assert imported1.query == "query1"
        assert imported1.search_type == "semantic"
        assert imported1.tags == ["tag1"]

    def test_filter_and_sort_workflow(self, saved_searches):
        """Test filtering and sorting workflow."""
        # Create searches with different attributes
        saved_searches.save_search(
            name="semantic_auth",
            query="auth",
            search_type="semantic",
            tags=["auth", "backend"],
        )
        saved_searches.save_search(
            name="keyword_auth",
            query="auth",
            search_type="keyword",
            tags=["auth"],
        )
        saved_searches.save_search(
            name="semantic_ui",
            query="ui",
            search_type="semantic",
            tags=["ui", "frontend"],
        )

        # Filter by type
        semantic = saved_searches.list_searches(search_type="semantic")
        assert len(semantic) == 2

        # Filter by tags
        auth = saved_searches.list_searches(tags=["auth"])
        assert len(auth) == 2

        # Combined filter
        semantic_auth = saved_searches.list_searches(
            search_type="semantic", tags=["auth"]
        )
        assert len(semantic_auth) == 1
        assert semantic_auth[0].name == "semantic_auth"

        # Update last_used to test sorting
        saved_searches.get_search("semantic_auth")
        import time

        time.sleep(0.01)
        saved_searches.get_search("keyword_auth")

        all_searches = saved_searches.list_searches()
        assert all_searches[0].name == "keyword_auth"  # Most recently used

    def test_persistence_across_instances(self, tmp_storage_path):
        """Test that data persists across SavedSearches instances."""
        # Create and save in first instance
        searches1 = SavedSearches(storage_path=tmp_storage_path)
        searches1.save_search(name="persistent", query="query")

        # Create new instance - should load data
        searches2 = SavedSearches(storage_path=tmp_storage_path)
        assert searches2.count == 1

        search = searches2.get_search("persistent")
        assert search is not None
        assert search.query == "query"

    def test_concurrent_access_handling(self, saved_searches):
        """Test handling of multiple accesses."""
        # Save multiple searches
        for i in range(5):
            saved_searches.save_search(
                name=f"search_{i}",
                query=f"query_{i}",
                tags=[f"tag_{i}"],
            )

        # Access multiple times
        for i in range(5):
            search = saved_searches.get_search(f"search_{i}")
            assert search is not None
            assert search.query == f"query_{i}"

        # Verify all are still there
        assert saved_searches.count == 5

    def test_error_recovery(self, saved_searches, tmp_storage_path):
        """Test recovery from errors."""
        # Save valid search
        saved_searches.save_search(name="valid", query="query")

        # Corrupt the storage file
        tmp_storage_path.write_text("corrupted data", encoding="utf-8")

        # Create new instance - should handle corruption gracefully
        new_searches = SavedSearches(storage_path=tmp_storage_path)
        # Should start fresh (corrupted file ignored)
        assert new_searches.count == 0

        # Should be able to save new searches
        new_searches.save_search(name="recovered", query="query")
        assert new_searches.count == 1
