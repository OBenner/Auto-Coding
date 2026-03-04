"""
Knowledge Base Integration Configuration
=========================================

Constants, provider mappings, and configuration helpers for knowledge base integration.
Supports Notion, Confluence, GitHub Wiki, and GitBook.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Knowledge Base Providers
PROVIDER_NOTION = "notion"
PROVIDER_CONFLUENCE = "confluence"
PROVIDER_GITHUB_WIKI = "github_wiki"
PROVIDER_GITBOOK = "gitbook"

# Sync status constants
SYNC_STATUS_IDLE = "idle"
SYNC_STATUS_RUNNING = "running"
SYNC_STATUS_SUCCESS = "success"
SYNC_STATUS_FAILED = "failed"
SYNC_STATUS_PARTIAL = "partial"  # Some docs synced, some failed

# Document status
STATUS_INDEXED = "indexed"
STATUS_PENDING = "pending"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

# Knowledge base marker file (stores sync state)
KB_MARKER = ".knowledge_base.json"

# Default sync intervals (in seconds)
DEFAULT_SYNC_INTERVAL = 3600  # 1 hour
MIN_SYNC_INTERVAL = 300  # 5 minutes


@dataclass
class KnowledgeBaseConfig:
    """Configuration for knowledge base integration."""

    provider: str  # notion, confluence, github_wiki, gitbook
    api_key: str = ""
    api_url: str = ""  # For Confluence (self-hosted) or GitBook
    space_key: str = ""  # For Confluence
    workspace_id: str = ""  # For Notion
    repository: str = ""  # For GitHub Wiki (owner/repo)
    enabled: bool = True
    sync_interval: int = DEFAULT_SYNC_INTERVAL
    max_docs: int = 1000  # Maximum docs to index

    @classmethod
    def from_env(cls, provider: str) -> "KnowledgeBaseConfig":
        """
        Create config from environment variables for a specific provider.

        Args:
            provider: Provider name (notion, confluence, github_wiki, gitbook)

        Returns:
            KnowledgeBaseConfig instance
        """
        provider_upper = provider.upper()
        api_key = os.environ.get(f"KNOWLEDGE_BASE_{provider_upper}_API_KEY", "")

        # Provider-specific config
        config = cls(
            provider=provider,
            api_key=api_key,
            api_url=os.environ.get(f"KNOWLEDGE_BASE_{provider_upper}_API_URL", ""),
            space_key=os.environ.get(f"KNOWLEDGE_BASE_{provider_upper}_SPACE_KEY", ""),
            workspace_id=os.environ.get(
                f"KNOWLEDGE_BASE_{provider_upper}_WORKSPACE_ID", ""
            ),
            repository=os.environ.get(
                f"KNOWLEDGE_BASE_{provider_upper}_REPOSITORY", ""
            ),
            enabled=bool(api_key),
        )

        # Optional settings
        if sync_interval_str := os.environ.get("KNOWLEDGE_BASE_SYNC_INTERVAL"):
            try:
                config.sync_interval = max(int(sync_interval_str), MIN_SYNC_INTERVAL)
            except ValueError:
                pass

        if max_docs_str := os.environ.get("KNOWLEDGE_BASE_MAX_DOCS"):
            try:
                config.max_docs = int(max_docs_str)
            except ValueError:
                pass

        return config

    def is_valid(self) -> bool:
        """Check if config has minimum required values for the provider."""
        if not self.api_key:
            return False

        # Provider-specific validation
        if self.provider == PROVIDER_NOTION:
            return bool(self.workspace_id)
        elif self.provider == PROVIDER_CONFLUENCE:
            return bool(self.space_key)
        elif self.provider == PROVIDER_GITHUB_WIKI:
            return bool(self.repository)
        elif self.provider == PROVIDER_GITBOOK:
            return bool(self.api_url)

        return False


@dataclass
class KnowledgeBaseState:
    """State of a knowledge base sync for an auto-claude spec."""

    initialized: bool = False
    provider: str = ""
    last_sync: str | None = None
    sync_status: str = SYNC_STATUS_IDLE
    total_docs: int = 0
    indexed_docs: int = 0
    failed_docs: int = 0
    error_message: str = ""
    created_at: str | None = None
    doc_mapping: dict = None  # doc_id -> doc metadata mapping

    def __post_init__(self):
        if self.doc_mapping is None:
            self.doc_mapping = {}

    def to_dict(self) -> dict:
        return {
            "initialized": self.initialized,
            "provider": self.provider,
            "last_sync": self.last_sync,
            "sync_status": self.sync_status,
            "total_docs": self.total_docs,
            "indexed_docs": self.indexed_docs,
            "failed_docs": self.failed_docs,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "doc_mapping": self.doc_mapping,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeBaseState":
        return cls(
            initialized=data.get("initialized", False),
            provider=data.get("provider", ""),
            last_sync=data.get("last_sync"),
            sync_status=data.get("sync_status", SYNC_STATUS_IDLE),
            total_docs=data.get("total_docs", 0),
            indexed_docs=data.get("indexed_docs", 0),
            failed_docs=data.get("failed_docs", 0),
            error_message=data.get("error_message", ""),
            created_at=data.get("created_at"),
            doc_mapping=data.get("doc_mapping", {}),
        )

    def save(self, spec_dir: Path) -> None:
        """Save state to the spec directory."""
        marker_file = spec_dir / KB_MARKER
        with open(marker_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, spec_dir: Path) -> "KnowledgeBaseState | None":
        """Load state from the spec directory."""
        marker_file = spec_dir / KB_MARKER
        if not marker_file.exists():
            return None

        try:
            with open(marker_file, encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def should_sync(self, interval_seconds: int) -> bool:
        """
        Check if sync should run based on interval.

        Args:
            interval_seconds: Sync interval in seconds

        Returns:
            True if sync should run
        """
        if not self.last_sync:
            return True

        if self.sync_status == SYNC_STATUS_RUNNING:
            return False

        try:
            last_sync_time = datetime.fromisoformat(self.last_sync)
            elapsed = (datetime.now() - last_sync_time).total_seconds()
            return elapsed >= interval_seconds
        except (ValueError, OSError):
            return True


def get_provider_display_name(provider: str) -> str:
    """
    Get display name for a provider.

    Args:
        provider: Provider identifier

    Returns:
        Display name
    """
    names = {
        PROVIDER_NOTION: "Notion",
        PROVIDER_CONFLUENCE: "Confluence",
        PROVIDER_GITHUB_WIKI: "GitHub Wiki",
        PROVIDER_GITBOOK: "GitBook",
    }
    return names.get(provider, provider)


def format_kb_summary(state: KnowledgeBaseState) -> str:
    """
    Format knowledge base state as a summary string.

    Args:
        state: KnowledgeBaseState instance

    Returns:
        Formatted summary
    """
    if not state.initialized:
        return "Knowledge base: Not initialized"

    provider_name = get_provider_display_name(state.provider)
    status_emoji = {
        SYNC_STATUS_IDLE: "💤",
        SYNC_STATUS_RUNNING: "🔄",
        SYNC_STATUS_SUCCESS: "✅",
        SYNC_STATUS_FAILED: "❌",
        SYNC_STATUS_PARTIAL: "⚠️",
    }.get(state.sync_status, "❓")

    parts = [
        f"Knowledge base: {provider_name} {status_emoji}",
    ]

    if state.last_sync:
        parts.append(f"Last sync: {state.last_sync}")

    if state.indexed_docs > 0:
        parts.append(f"Indexed: {state.indexed_docs}/{state.total_docs} docs")

    if state.failed_docs > 0:
        parts.append(f"Failed: {state.failed_docs} docs")

    if state.error_message:
        parts.append(f"Error: {state.error_message[:100]}")

    return " | ".join(parts)


def format_doc_reference(doc_id: str, doc_metadata: dict) -> str:
    """
    Format a document reference for agent context.

    Args:
        doc_id: Document identifier
        doc_metadata: Document metadata from state

    Returns:
        Formatted reference string
    """
    title = doc_metadata.get("title", doc_id)
    url = doc_metadata.get("url", "")
    source = doc_metadata.get("source", "Unknown")

    if url:
        return f"- [{title}]({url}) (from {source})"
    return f"- {title} (from {source})"
