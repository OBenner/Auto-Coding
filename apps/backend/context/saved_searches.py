"""
Saved Searches Management
=========================

Manages saved code searches for quick reuse and sharing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SavedSearch:
    """A saved code search with metadata."""

    name: str
    query: str
    search_type: str  # 'unified', 'purpose', 'patterns', 'callers', 'callees', 'semantic', 'keyword', 'hybrid'
    filters: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_used: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SavedSearch:
        """Create SavedSearch from dictionary."""
        known_fields = {
            "name",
            "query",
            "search_type",
            "filters",
            "created_at",
            "last_used",
            "description",
            "tags",
        }
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


class SavedSearches:
    """Manages saved searches with JSON persistence."""

    def __init__(self, storage_path: Path | None = None):
        """
        Initialize saved searches manager.

        Args:
            storage_path: Path to JSON file storing searches. Defaults to
                         .auto-claude/saved_searches.json in project root.
        """
        if storage_path is None:
            # Default to .auto-claude directory
            self._storage_path = Path.cwd() / ".auto-claude" / "saved_searches.json"
        else:
            self._storage_path = Path(storage_path)

        self._searches: dict[str, SavedSearch] = {}
        self._load_searches()

    def save_search(
        self,
        name: str,
        query: str,
        search_type: str = "semantic",
        filters: dict[str, Any] | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> SavedSearch:
        """
        Save a new search or update existing one.

        Args:
            name: Unique name for the search
            query: Search query string
            search_type: Type of search ('semantic', 'keyword', 'hybrid')
            filters: Optional filters (file types, services, etc.)
            description: Optional description of the search
            tags: Optional tags for categorization

        Returns:
            The saved SavedSearch object

        Raises:
            ValueError: If name is empty or search_type is invalid
        """
        if not name or not name.strip():
            raise ValueError("Search name cannot be empty")

        valid_types = (
            "unified",
            "purpose",
            "patterns",
            "callers",
            "callees",
            "semantic",
            "keyword",
            "hybrid",
        )
        if search_type not in valid_types:
            raise ValueError(
                f"Invalid search_type: {search_type}. "
                f"Must be one of: {', '.join(repr(t) for t in valid_types)}"
            )

        # Create or update search
        if name in self._searches:
            # Update existing search, preserve created_at
            existing = self._searches[name]
            search = SavedSearch(
                name=name,
                query=query,
                search_type=search_type,
                filters=filters or {},
                created_at=existing.created_at,
                last_used=datetime.now(UTC).isoformat(),
                description=description,
                tags=tags or [],
            )
        else:
            # Create new search
            search = SavedSearch(
                name=name,
                query=query,
                search_type=search_type,
                filters=filters or {},
                description=description,
                tags=tags or [],
            )

        self._searches[name] = search
        self._save_searches()
        logger.info(f"Saved search: {name}")
        return search

    def get_search(self, name: str) -> SavedSearch | None:
        """
        Get a saved search by name.

        Args:
            name: Name of the search to retrieve

        Returns:
            SavedSearch object or None if not found
        """
        search = self._searches.get(name)
        if search:
            # Update last_used timestamp
            search.last_used = datetime.now(UTC).isoformat()
            self._save_searches()
        return search

    def list_searches(
        self,
        search_type: str | None = None,
        tags: list[str] | None = None,
    ) -> list[SavedSearch]:
        """
        List all saved searches, optionally filtered.

        Args:
            search_type: Optional filter by search type
            tags: Optional filter by tags (must match all tags)

        Returns:
            List of SavedSearch objects, sorted by last_used (most recent first)
        """
        searches = list(self._searches.values())

        # Filter by search_type
        if search_type:
            searches = [s for s in searches if s.search_type == search_type]

        # Filter by tags (must match all provided tags)
        if tags:
            searches = [s for s in searches if all(tag in s.tags for tag in tags)]

        # Sort by last_used (most recent first), then created_at
        searches.sort(
            key=lambda s: (
                s.last_used or "1970-01-01T00:00:00+00:00",
                s.created_at,
            ),
            reverse=True,
        )

        return searches

    def delete_search(self, name: str) -> bool:
        """
        Delete a saved search.

        Args:
            name: Name of the search to delete

        Returns:
            True if deleted, False if not found
        """
        if name in self._searches:
            del self._searches[name]
            self._save_searches()
            logger.info(f"Deleted search: {name}")
            return True
        return False

    def update_search(
        self,
        name: str,
        query: str | None = None,
        search_type: str | None = None,
        filters: dict[str, Any] | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> SavedSearch | None:
        """
        Update an existing saved search.

        Args:
            name: Name of the search to update
            query: New query string (optional)
            search_type: New search type (optional)
            filters: New filters (optional)
            description: New description (optional)
            tags: New tags (optional)

        Returns:
            Updated SavedSearch object or None if not found

        Raises:
            ValueError: If search_type is invalid
        """
        if name not in self._searches:
            return None

        existing = self._searches[name]

        # Validate search_type if provided
        valid_types = (
            "unified",
            "purpose",
            "patterns",
            "callers",
            "callees",
            "semantic",
            "keyword",
            "hybrid",
        )
        if search_type and search_type not in valid_types:
            raise ValueError(
                f"Invalid search_type: {search_type}. "
                f"Must be one of: {', '.join(repr(t) for t in valid_types)}"
            )

        # Update fields
        updated = SavedSearch(
            name=name,
            query=query if query is not None else existing.query,
            search_type=search_type
            if search_type is not None
            else existing.search_type,
            filters=filters if filters is not None else existing.filters,
            created_at=existing.created_at,
            last_used=datetime.now(UTC).isoformat(),
            description=description
            if description is not None
            else existing.description,
            tags=tags if tags is not None else existing.tags,
        )

        self._searches[name] = updated
        self._save_searches()
        logger.info(f"Updated search: {name}")
        return updated

    def export_searches(
        self,
        output_path: Path | None = None,
        search_type: str | None = None,
        tags: list[str] | None = None,
    ) -> Path:
        """
        Export saved searches to JSON file.

        Args:
            output_path: Path to export to. Defaults to saved_searches_export.json
            search_type: Optional filter by search type
            tags: Optional filter by tags

        Returns:
            Path to exported file

        Raises:
            OSError: If export fails
        """
        if output_path is None:
            output_path = Path.cwd() / "saved_searches_export.json"

        searches = self.list_searches(search_type=search_type, tags=tags)
        data = {
            "exported_at": datetime.now(UTC).isoformat(),
            "count": len(searches),
            "searches": [s.to_dict() for s in searches],
        }

        try:
            output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info(f"Exported {len(searches)} searches to {output_path}")
            return output_path
        except OSError as e:
            logger.error(f"Failed to export searches: {e}")
            raise

    def import_searches(
        self,
        input_path: Path,
        merge_strategy: str = "error",
    ) -> int:
        """
        Import saved searches from JSON file.

        Args:
            input_path: Path to JSON file to import
            merge_strategy: How to handle name conflicts:
                           - 'error': Raise ValueError on conflict (default)
                           - 'skip': Skip conflicting searches
                           - 'overwrite': Overwrite existing searches

        Returns:
            Number of searches imported

        Raises:
            ValueError: If merge_strategy is invalid or conflict occurs
            OSError: If import fails
        """
        if merge_strategy not in ("error", "skip", "overwrite"):
            raise ValueError(
                f"Invalid merge_strategy: {merge_strategy}. "
                "Must be 'error', 'skip', or 'overwrite'"
            )

        try:
            content = input_path.read_text(encoding="utf-8")
            data = json.loads(content)

            if "searches" not in data:
                raise ValueError("Invalid import file: missing 'searches' key")

            valid_types = (
                "unified",
                "purpose",
                "patterns",
                "callers",
                "callees",
                "semantic",
                "keyword",
                "hybrid",
            )

            imported_count = 0
            for search_data in data["searches"]:
                search = SavedSearch.from_dict(search_data)
                name = search.name

                if search.search_type not in valid_types:
                    logger.warning(
                        f"Skipping search '{search.name}' with invalid type: {search.search_type}"
                    )
                    continue

                # Handle name conflicts
                if name in self._searches:
                    if merge_strategy == "error":
                        raise ValueError(
                            f"Search '{name}' already exists. "
                            "Use merge_strategy='skip' or 'overwrite'"
                        )
                    elif merge_strategy == "skip":
                        continue
                    # 'overwrite': proceed with import

                self._searches[name] = search
                imported_count += 1

            self._save_searches()
            logger.info(f"Imported {imported_count} searches from {input_path}")
            return imported_count

        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to import searches: {e}")
            raise

    def _load_searches(self) -> None:
        """Load searches from storage file."""
        if not self._storage_path.exists():
            logger.debug(f"No saved searches file at {self._storage_path}")
            return

        try:
            content = self._storage_path.read_text(encoding="utf-8")
            data = json.loads(content)

            for search_data in data.get("searches", []):
                try:
                    search = SavedSearch.from_dict(search_data)
                    self._searches[search.name] = search
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to load search {search_data.get('name', 'unknown')}: {e}"
                    )

            logger.debug(f"Loaded {len(self._searches)} saved searches")

        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load saved searches: {e}")

    def _save_searches(self) -> None:
        """Save searches to storage file."""
        try:
            # Ensure parent directory exists
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "saved_at": datetime.now(UTC).isoformat(),
                "count": len(self._searches),
                "searches": [s.to_dict() for s in self._searches.values()],
            }

            self._storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        except OSError as e:
            logger.error(f"Failed to save searches: {e}")
            raise

    @property
    def storage_path(self) -> Path:
        """Get the storage file path."""
        return self._storage_path

    @property
    def count(self) -> int:
        """Get the number of saved searches."""
        return len(self._searches)
