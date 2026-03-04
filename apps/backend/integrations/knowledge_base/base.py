"""
Knowledge Base Connector Interface
===================================

Abstract base class for knowledge base connectors.
All connectors (Notion, Confluence, GitHub Wiki, GitBook) must inherit from this.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .config import KnowledgeBaseConfig, KnowledgeBaseState


class BaseConnector(ABC):
    """
    Abstract base class for knowledge base connectors.

    Defines the interface that all knowledge base connectors must implement.
    Each connector handles authentication, document fetching, and synchronization
    for a specific documentation platform (Notion, Confluence, GitHub Wiki, GitBook).

    Subclasses must implement:
    - connect(): Establish connection and authenticate
    - fetch_documents(): Retrieve all documents
    - incremental_sync(): Perform incremental sync since last update
    """

    def __init__(self, config: KnowledgeBaseConfig, spec_dir: Path):
        """
        Initialize the connector with configuration.

        Args:
            config: KnowledgeBaseConfig instance with provider settings
            spec_dir: Spec directory for storing state and cache

        Raises:
            ValueError: If config is invalid for the provider
        """
        self.config = config
        self.spec_dir = spec_dir
        self.state: KnowledgeBaseState | None = None
        self._connected = False

        # Validate config
        if not config.is_valid():
            raise ValueError(f"Invalid config for provider '{config.provider}'")

        # Load existing state if available
        self._load_state()

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the knowledge base platform.

        Should authenticate using the API key/tokens and verify access.
        Set self._connected = True on success.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def fetch_documents(self) -> list[dict[str, Any]]:
        """
        Fetch all documents from the knowledge base.

        Returns a list of document dictionaries, each containing:
        - id: Unique document identifier (provider-specific)
        - title: Document title
        - content: Document text content (markdown/plain text)
        - url: Link to the original document
        - metadata: Optional dict with author, updated_at, tags, etc.

        Returns:
            List of document dictionaries

        Raises:
            ConnectionError: If not connected
        """
        pass

    @abstractmethod
    def incremental_sync(self) -> dict[str, Any]:
        """
        Perform incremental sync since last successful update.

        Fetches only documents that have been created or modified since
        the last sync (stored in self.state.last_sync).

        Updates self.state with:
        - last_sync: Current timestamp
        - sync_status: success, failed, or partial
        - total_docs: Total document count
        - indexed_docs: Number successfully indexed
        - failed_docs: Number that failed
        - error_message: Error details if failed
        - doc_mapping: Updated doc_id -> metadata mapping

        Returns:
            Dict with sync results:
            - success: bool
            - added: int (new documents)
            - updated: int (modified documents)
            - failed: int
            - errors: list of error messages
        """
        pass

    def is_connected(self) -> bool:
        """
        Check if connector is connected and authenticated.

        Returns:
            True if connected
        """
        return self._connected

    def get_provider_name(self) -> str:
        """
        Get the provider name for this connector.

        Returns:
            Provider identifier (notion, confluence, github_wiki, gitbook)
        """
        return self.config.provider

    def _load_state(self) -> None:
        """Load knowledge base state from spec directory."""
        self.state = KnowledgeBaseState.load(self.spec_dir)

    def _save_state(self) -> None:
        """Save knowledge base state to spec directory."""
        if self.state:
            self.state.save(self.spec_dir)

    def _initialize_state(self) -> None:
        """Initialize a new knowledge base state for this spec."""
        from datetime import datetime

        self.state = KnowledgeBaseState(
            initialized=True,
            provider=self.config.provider,
            created_at=datetime.now().isoformat(),
        )
        self._save_state()

    def get_sync_summary(self) -> dict[str, Any]:
        """
        Get a summary of the current sync status.

        Returns:
            Dict with sync status information
        """
        if not self.state:
            return {
                "provider": self.config.provider,
                "initialized": False,
                "connected": self._connected,
            }

        return {
            "provider": self.config.provider,
            "initialized": self.state.initialized,
            "connected": self._connected,
            "last_sync": self.state.last_sync,
            "sync_status": self.state.sync_status,
            "total_docs": self.state.total_docs,
            "indexed_docs": self.state.indexed_docs,
            "failed_docs": self.state.failed_docs,
            "error_message": self.state.error_message,
        }

    def disconnect(self) -> None:
        """
        Close connection and release resources.

        Subclasses can override to perform cleanup (close HTTP sessions, etc.)
        """
        self._connected = False

    def __enter__(self):
        """
        Context manager entry.

        Returns:
            Self
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.

        Ensures disconnect is called.
        """
        self.disconnect()
        return False
