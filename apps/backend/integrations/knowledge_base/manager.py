"""
Knowledge Base Manager
======================

Main orchestrator for knowledge base connectors.

Provides a high-level interface that:
- Instantiates the appropriate connector based on configuration
- Manages sync operations and state tracking
- Provides unified search across all connected knowledge bases
- Handles error recovery and graceful degradation
"""

import logging
from pathlib import Path
from typing import Any

from core.sentry import capture_exception
from integrations.knowledge_base.base import BaseConnector
from integrations.knowledge_base.config import (
    SYNC_STATUS_FAILED,
    SYNC_STATUS_PARTIAL,
    SYNC_STATUS_RUNNING,
    SYNC_STATUS_SUCCESS,
    KnowledgeBaseConfig,
    KnowledgeBaseState,
    format_kb_summary,
)
from integrations.knowledge_base.connectors import (
    ConfluenceConnector,
    GitBookConnector,
    GitHubWikiConnector,
    NotionConnector,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    Manages knowledge base connectors for team documentation.

    This class provides a high-level interface for:
    - Initializing the appropriate connector (Notion, Confluence, GitHub Wiki, GitBook)
    - Performing full and incremental sync operations
    - Searching across all indexed documentation
    - Tracking sync state and providing status summaries

    The integration is OPTIONAL - if no valid configuration is found,
    operations gracefully no-op or return empty results.

    All sync operations include error handling with fallback behavior.
    """

    # Provider class mapping
    _CONNECTOR_CLASSES = {
        "notion": NotionConnector,
        "confluence": ConfluenceConnector,
        "github_wiki": GitHubWikiConnector,
        "gitbook": GitBookConnector,
    }

    def __init__(self, spec_dir: Path, project_dir: Path):
        """
        Initialize knowledge base manager.

        Args:
            spec_dir: Spec directory for storing state and cache
            project_dir: Project root directory
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.config: KnowledgeBaseConfig | None = None
        self.state: KnowledgeBaseState | None = None
        self._connector: BaseConnector | None = None
        self._available = False

        # Try to load configuration from environment
        self._load_configuration()

    @property
    def is_enabled(self) -> bool:
        """Check if knowledge base integration is enabled and configured."""
        return self._available

    @property
    def is_connected(self) -> bool:
        """Check if connector is connected and ready."""
        return self._connector is not None and self._connector.is_connected()

    @property
    def is_initialized(self) -> bool:
        """Check if knowledge base has been initialized for this spec."""
        return self._available and self.state is not None and self.state.initialized

    async def initialize(self) -> bool:
        """
        Initialize the knowledge base connector.

        Returns:
            True if initialization succeeded
        """
        if self.is_initialized and self.is_connected:
            return True

        if not self._available:
            logger.info("Knowledge base not available - skipping initialization")
            return False

        try:
            # Get connector class for the provider
            connector_class = self._CONNECTOR_CLASSES.get(self.config.provider)
            if not connector_class:
                logger.error(f"Unknown provider: {self.config.provider}")
                self._available = False
                return False

            # Instantiate connector
            self._connector = connector_class(self.config, self.spec_dir)

            # Connect to the knowledge base
            if not self._connector.connect():
                logger.error(f"Failed to connect to {self.config.provider}")
                return False

            # Initialize state if needed
            if not self.state:
                self._initialize_state()

            logger.info(
                f"Knowledge base initialized: {self.config.provider} "
                f"for {self.spec_dir.name}"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize knowledge base: {e}")
            self._record_error(f"Initialization failed: {e}")
            capture_exception(
                e,
                component="knowledge_base",
                operation="initialize",
                provider=self.config.provider if self.config else None,
                spec_dir=str(self.spec_dir),
            )
            return False

    async def close(self) -> None:
        """
        Close the connector and clean up connections.
        """
        if self._connector:
            self._connector.disconnect()
            self._connector = None

    async def sync(self, force: bool = False) -> dict[str, Any]:
        """
        Perform a sync operation.

        If force=False and the state exists, performs incremental sync.
        If force=True or no state exists, performs full sync.

        Args:
            force: Force a full sync regardless of state

        Returns:
            Dict with sync results:
            - success: bool
            - added: int (new documents)
            - updated: int (modified documents)
            - failed: int
            - errors: list of error messages
        """
        if not await self._ensure_initialized():
            return {
                "success": False,
                "added": 0,
                "updated": 0,
                "failed": 0,
                "errors": ["Knowledge base not initialized"],
            }

        # Check if sync should run (unless forced)
        if not force and self.state:
            if not self.state.should_sync(self.config.sync_interval):
                logger.info("Knowledge base sync not needed (interval not elapsed)")
                return {
                    "success": True,
                    "added": 0,
                    "updated": 0,
                    "failed": 0,
                    "errors": [],
                    "skipped": True,
                    "reason": "Sync interval not elapsed",
                }

        try:
            # Update state to running
            if self.state:
                self.state.sync_status = SYNC_STATUS_RUNNING
                self.state.save(self.spec_dir)

            # Perform sync (full if forced or no prior sync)
            if force or not self.state or not self.state.last_sync:
                documents = self._connector.fetch_documents()
                result = {
                    "success": True,
                    "added": len(documents),
                    "updated": 0,
                    "failed": 0,
                    "errors": [],
                }
            else:
                result = self._connector.incremental_sync()

            # Update state
            if self.state:
                if result.get("success"):
                    self.state.sync_status = (
                        SYNC_STATUS_SUCCESS
                        if result.get("failed", 0) == 0
                        else SYNC_STATUS_PARTIAL
                    )
                else:
                    self.state.sync_status = SYNC_STATUS_FAILED
                self.state.save(self.spec_dir)

            logger.info(
                f"Knowledge base sync completed: "
                f"added={result.get('added', 0)}, "
                f"updated={result.get('updated', 0)}, "
                f"failed={result.get('failed', 0)}"
            )

            return result

        except Exception as e:
            logger.warning(f"Failed to sync knowledge base: {e}")
            self._record_error(f"Sync failed: {e}")
            capture_exception(
                e,
                component="knowledge_base",
                operation="sync",
                provider=self.config.provider if self.config else None,
                force=force,
            )

            # Update state to failed
            if self.state:
                self.state.sync_status = SYNC_STATUS_FAILED
                self.state.error_message = str(e)
                self.state.save(self.spec_dir)

            return {
                "success": False,
                "added": 0,
                "updated": 0,
                "failed": 0,
                "errors": [str(e)],
            }

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search the knowledge base for relevant documents.

        Args:
            query: Search query
            limit: Maximum number of results
            filters: Optional filters (e.g., tags, date range)

        Returns:
            List of matching documents with metadata
        """
        if not await self._ensure_initialized():
            return []

        try:
            from integrations.knowledge_base.indexer import DocumentationIndexer

            logger.info(f"Searching knowledge base for: {query}")

            indexer = DocumentationIndexer(self.spec_dir, self.project_dir, self.state)
            results = await indexer.search(query=query, limit=limit)
            return results

        except Exception as e:
            logger.warning(f"Failed to search knowledge base: {e}")
            self._record_error(f"Search failed: {e}")
            capture_exception(
                e,
                component="knowledge_base",
                operation="search",
                query=query,
                limit=limit,
            )
            return []

    async def get_documents(
        self,
        limit: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all or filtered documents from the knowledge base.

        Args:
            limit: Maximum number of documents to return
            filters: Optional filters (tags, date range, etc.)

        Returns:
            List of documents with metadata
        """
        if not await self._ensure_initialized():
            return []

        try:
            # Fetch documents from connector
            documents = self._connector.fetch_documents()

            # Apply limit
            if limit and len(documents) > limit:
                documents = documents[:limit]

            # Apply filters if provided
            if filters:
                documents = self._apply_filters(documents, filters)

            return documents

        except Exception as e:
            logger.warning(f"Failed to get documents: {e}")
            self._record_error(f"Get documents failed: {e}")
            capture_exception(
                e,
                component="knowledge_base",
                operation="get_documents",
                limit=limit,
            )
            return []

    def get_status_summary(self) -> dict[str, Any]:
        """
        Get a summary of knowledge base status.

        Returns:
            Dict with status information
        """
        if not self._available:
            return {
                "enabled": False,
                "provider": None,
                "initialized": False,
                "connected": False,
            }

        return {
            "enabled": True,
            "provider": self.config.provider if self.config else None,
            "initialized": self.is_initialized,
            "connected": self.is_connected,
            "sync_summary": self._connector.get_sync_summary()
            if self._connector
            else None,
        }

    def get_status_string(self) -> str:
        """
        Get a formatted status string for logging.

        Returns:
            Formatted status summary
        """
        if not self.state:
            return "Knowledge base: Not configured"

        return format_kb_summary(self.state)

    # Private helper methods

    def _load_configuration(self) -> None:
        """
        Load configuration from environment.

        Tries each provider in order and uses the first one with valid config.
        """
        providers = ["notion", "confluence", "github_wiki", "gitbook"]

        for provider in providers:
            config = KnowledgeBaseConfig.from_env(provider)
            if config.is_valid():
                self.config = config
                self._available = True

                # Load existing state
                self.state = KnowledgeBaseState.load(self.spec_dir)

                logger.info(
                    f"Knowledge base configured with provider: {provider} "
                    f"(sync_interval: {config.sync_interval}s)"
                )
                return

        logger.info("No valid knowledge base configuration found")
        self._available = False

    def _initialize_state(self) -> None:
        """Initialize a new knowledge base state."""
        from datetime import datetime

        self.state = KnowledgeBaseState(
            initialized=True,
            provider=self.config.provider,
            created_at=datetime.now().isoformat(),
        )
        self.state.save(self.spec_dir)

    async def _ensure_initialized(self) -> bool:
        """
        Ensure knowledge base is initialized, attempting initialization if needed.

        Returns:
            True if initialized and ready
        """
        if self.is_initialized and self.is_connected:
            return True

        if not self._available:
            return False

        return await self.initialize()

    def _record_error(self, error_msg: str) -> None:
        """Record an error in the state."""
        if not self.state:
            self.state = KnowledgeBaseState()

        self.state.error_message = error_msg
        self.state.sync_status = SYNC_STATUS_FAILED
        self.state.save(self.spec_dir)

    @staticmethod
    def _apply_filters(
        documents: list[dict[str, Any]], filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Apply filters to a list of documents.

        Args:
            documents: List of document dictionaries
            filters: Filter criteria

        Returns:
            Filtered list of documents
        """
        filtered = documents

        # Filter by tag
        if "tags" in filters:
            tags = filters["tags"]
            filtered = [
                doc
                for doc in filtered
                if set(tags).intersection(set(doc.get("metadata", {}).get("tags", [])))
            ]

        # Filter by date range
        if "updated_after" in filters:
            from datetime import datetime

            try:
                cutoff = datetime.fromisoformat(filters["updated_after"])
            except (ValueError, TypeError):
                return filtered
            date_filtered = []
            for doc in filtered:
                updated_at = doc.get("metadata", {}).get("updated_at", "")
                if not updated_at:
                    continue
                try:
                    if datetime.fromisoformat(updated_at) >= cutoff:
                        date_filtered.append(doc)
                except (ValueError, TypeError):
                    # Include docs with malformed timestamps
                    date_filtered.append(doc)
            filtered = date_filtered

        return filtered
