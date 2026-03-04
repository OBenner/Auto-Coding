"""
GitBook Knowledge Base Connector
=================================

Connects to GitBook spaces to fetch documentation pages.
Supports both full sync and incremental sync based on last modified time.

Environment Variables:
- KNOWLEDGE_BASE_GITBOOK_API_KEY: GitBook API token (required)
- KNOWLEDGE_BASE_GITBOOK_API_URL: GitBook API URL (default: https://api.gitbook.com)

GitBook API documentation: https://docs.gitbook.com/api

Key Features:
- Fetch all pages from a GitBook space
- Convert GitBook content to markdown
- Incremental sync based on last modified time
- Error handling and retry logic
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from ..base import BaseConnector
from ..config import (
    SYNC_STATUS_FAILED,
    SYNC_STATUS_PARTIAL,
    SYNC_STATUS_SUCCESS,
    KnowledgeBaseConfig,
)

logger = logging.getLogger(__name__)


class GitBookConnector(BaseConnector):
    """
    Connector for GitBook spaces.

    Fetches documentation pages from a GitBook space using the GitBook API.
    Converts GitBook content to markdown format for indexing in Graphiti.

    Attributes:
        config: KnowledgeBaseConfig instance
        spec_dir: Spec directory for state storage
        api_key: GitBook API token
        api_url: GitBook API base URL
        session: requests.Session for HTTP requests
    """

    API_BASE_URL = "https://api.gitbook.com"

    def __init__(self, config: KnowledgeBaseConfig, spec_dir: Path):
        """
        Initialize the GitBook connector.

        Args:
            config: KnowledgeBaseConfig with GitBook settings
            spec_dir: Spec directory for state storage

        Raises:
            ValueError: If config is invalid or missing API key
        """
        super().__init__(config, spec_dir)

        self.api_key = config.api_key
        self.api_url = config.api_url or self.API_BASE_URL
        self.session: requests.Session | None = None

        if not self.api_key:
            raise ValueError("GITBOOK_API_KEY is required for GitBook connector")

    def connect(self) -> bool:
        """
        Establish connection to GitBook API and verify authentication.

        Tests the API key by making a simple request to list spaces.
        Sets self._connected = True on success.

        Returns:
            True if connection successful, False otherwise
        """
        if self._connected:
            return True

        try:
            # Create HTTP session
            self.session = requests.Session()
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )

            # Test connection by fetching user info
            response = self._make_request("GET", "/v1/user")

            if response and response.status_code == 200:
                self._connected = True
                return True

            return False

        except (OSError, requests.RequestException):
            return False

    def fetch_documents(self) -> list[dict[str, Any]]:
        """
        Fetch all documents (pages) from accessible GitBook spaces.

        Performs a full sync, retrieving all accessible pages from all spaces.
        Converts GitBook content to markdown format.

        Returns:
            List of document dictionaries, each containing:
            - id: Page ID
            - title: Page title
            - content: Page content as markdown
            - url: Page URL
            - metadata: Dict with updated_at, created_at, etc.

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to GitBook API")

        documents = []
        errors = []

        try:
            # Fetch all spaces
            spaces = self._fetch_all_spaces()

            # Fetch pages from each space
            for space in spaces:
                try:
                    space_docs = self._fetch_space_documents(space)
                    documents.extend(space_docs)
                except Exception as e:
                    space_id = space.get("id", "unknown")
                    errors.append(f"Failed to fetch space {space_id}: {e}")

            # Update state
            if not self.state or not self.state.initialized:
                self._initialize_state()

            self.state.total_docs = len(documents)
            self.state.indexed_docs = len(documents)
            self.state.failed_docs = len(errors)
            self.state.last_sync = datetime.now().isoformat()
            self.state.sync_status = (
                SYNC_STATUS_SUCCESS if not errors else SYNC_STATUS_PARTIAL
            )
            self.state.error_message = "; ".join(errors[:5])  # First 5 errors
            self._save_state()

        except Exception as e:
            if self.state:
                self.state.sync_status = SYNC_STATUS_FAILED
                self.state.error_message = str(e)
                self._save_state()
            raise

        return documents

    def incremental_sync(self) -> dict[str, Any]:
        """
        Perform incremental sync since last successful update.

        Fetches only pages that have been created or modified since
        self.state.last_sync. Updates documents in the state's doc_mapping.

        Returns:
            Dict with sync results:
            - success: bool
            - added: int (new documents)
            - updated: int (modified documents)
            - failed: int
            - errors: list of error messages
        """
        if not self._connected:
            raise ConnectionError("Not connected to GitBook API")

        # Initialize state if needed
        if not self.state or not self.state.initialized:
            self._initialize_state()

        result = {
            "success": True,
            "added": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        try:
            # Get last sync time
            last_sync = self.state.last_sync

            # Fetch all spaces and their pages
            spaces = self._fetch_all_spaces()

            for space in spaces:
                try:
                    space_pages = self._fetch_space_pages(space)

                    # Filter pages modified since last sync
                    if last_sync is None:
                        updated_pages = space_pages
                    else:
                        updated_pages = []
                        for p in space_pages:
                            updated_at = p.get("updatedAt")
                            if not updated_at:
                                continue
                            try:
                                if datetime.fromisoformat(
                                    updated_at.replace("Z", "+00:00")
                                ) > datetime.fromisoformat(
                                    last_sync.replace("Z", "+00:00")
                                ):
                                    updated_pages.append(p)
                            except (ValueError, TypeError):
                                # Include page if we can't parse timestamps
                                updated_pages.append(p)

                    # Process each updated page
                    for page in updated_pages:
                        try:
                            doc = self._fetch_page_content(page, space)
                            if doc:
                                page_id = doc["id"]

                                # Check if this is a new or updated document
                                if page_id in self.state.doc_mapping:
                                    result["updated"] += 1
                                else:
                                    result["added"] += 1

                                # Update doc_mapping
                                self.state.doc_mapping[page_id] = {
                                    "title": doc["title"],
                                    "url": doc["url"],
                                    "updated_at": doc["metadata"]["updated_at"],
                                    "source": "GitBook",
                                }

                        except Exception as e:
                            page_id = page.get("id", "unknown")
                            result["failed"] += 1
                            result["errors"].append(
                                f"Failed to sync page {page_id}: {e}"
                            )

                except Exception as e:
                    space_id = space.get("id", "unknown")
                    result["failed"] += 1
                    result["success"] = False
                    result["errors"].append(f"Failed to sync space {space_id}: {e}")

            # Update state
            self.state.total_docs = len(self.state.doc_mapping)
            self.state.indexed_docs = len(self.state.doc_mapping)
            self.state.failed_docs = result["failed"]
            self.state.last_sync = datetime.now().isoformat()
            self.state.sync_status = (
                SYNC_STATUS_SUCCESS if not result["failed"] else SYNC_STATUS_PARTIAL
            )
            self.state.error_message = "; ".join(result["errors"][:5])
            self._save_state()

            result["success"] = result["failed"] == 0

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))

            if self.state:
                self.state.sync_status = SYNC_STATUS_FAILED
                self.state.error_message = str(e)
                self._save_state()

        return result

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        params: dict | None = None,
        retries: int = 3,
    ) -> requests.Response | None:
        """
        Make an HTTP request to the GitBook API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/v1/user")
            json_data: Request body for POST requests
            params: Query parameters
            retries: Number of retries on failure

        Returns:
            Response object or None if all retries fail
        """
        if not self.session:
            return None

        url = f"{self.api_url}{endpoint}"

        for attempt in range(retries):
            try:
                response = self.session.request(
                    method, url, json=json_data, params=params, timeout=30
                )

                # Rate limiting - wait and retry
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    time.sleep(retry_after)
                    continue

                # Success
                if response.status_code < 400:
                    return response

                # Client error - don't retry
                if response.status_code < 500:
                    return response

                # Server error - retry after delay
                time.sleep(2**attempt)

            except (OSError, requests.RequestException):
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                else:
                    return None

        return None

    def _fetch_all_spaces(self) -> list[dict[str, Any]]:
        """
        Fetch all accessible GitBook spaces.

        Returns:
            List of space objects with id, title, etc.
        """
        spaces = []

        try:
            response = self._make_request("GET", "/v1/spaces")

            if response and response.status_code == 200:
                data = response.json()
                spaces = data.get("items", [])

        except Exception:
            logger.debug("Failed to fetch GitBook spaces")

        return spaces

    def _fetch_space_documents(self, space: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Fetch all documents from a GitBook space.

        Args:
            space: Space object from GitBook API

        Returns:
            List of document dictionaries
        """
        documents = []
        pages = self._fetch_space_pages(space)

        for page in pages:
            try:
                doc = self._fetch_page_content(page, space)
                if doc:
                    documents.append(doc)
            except Exception:
                logger.debug(
                    "Failed to fetch page content from space %s", space.get("id")
                )
                continue

        return documents

    def _fetch_space_pages(self, space: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Fetch all pages from a GitBook space.

        Args:
            space: Space object from GitBook API

        Returns:
            List of page objects
        """
        space_id = space.get("id")
        if not space_id:
            return []

        pages = []

        try:
            # Fetch search results for all content in the space
            response = self._make_request(
                "GET",
                f"/v1/spaces/{space_id}/search",
                params={"query": "", "page": 1, "limit": 100},
            )

            if response and response.status_code == 200:
                data = response.json()
                pages = data.get("items", [])

                # Handle pagination if needed
                while data.get("hasMore"):
                    next_page = data.get("page", 1) + 1
                    response = self._make_request(
                        "GET",
                        f"/v1/spaces/{space_id}/search",
                        params={"query": "", "page": next_page, "limit": 100},
                    )

                    if not response or response.status_code != 200:
                        break

                    data = response.json()
                    pages.extend(data.get("items", []))

        except Exception:
            logger.debug("Failed to fetch pages for space %s", space.get("id"))

        return pages

    def _fetch_page_content(
        self, page: dict[str, Any], space: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Fetch the full content of a GitBook page.

        Args:
            page: Page object from GitBook API
            space: Space object for context

        Returns:
            Document dict with id, title, content, url, metadata
        """
        page_id = page.get("id")
        if not page_id:
            return None

        space_id = space.get("id", "")

        # Get page title and other metadata
        title = page.get("title", "Untitled")
        path = page.get("path", "")
        updated_at = page.get("updatedAt", "")
        created_at = page.get("createdAt", "")

        # Construct page URL
        space_url = space.get("url", "")
        url = f"{space_url}{path}" if space_url else ""

        # Fetch page content
        content = self._fetch_page_text(page_id, space_id)

        return {
            "id": page_id,
            "title": title,
            "content": content,
            "url": url,
            "metadata": {
                "created_at": created_at,
                "updated_at": updated_at,
                "source": "GitBook",
                "space_id": space_id,
            },
        }

    def _fetch_page_text(self, page_id: str, space_id: str) -> str:
        """
        Fetch the text content of a GitBook page.

        Args:
            page_id: Page ID
            space_id: Space ID

        Returns:
            Page content as markdown string
        """
        try:
            response = self._make_request(
                "GET", f"/v1/spaces/{space_id}/content/{page_id}"
            )

            if response and response.status_code == 200:
                data = response.json()
                # GitBook API returns content in various formats
                # Try to extract markdown or plain text
                return self._extract_content(data)

        except Exception:
            logger.debug(
                "Failed to fetch text for page %s in space %s", page_id, space_id
            )

        return ""

    def _extract_content(self, content_data: dict[str, Any]) -> str:
        """
        Extract content from GitBook API response.

        GitBook API can return content in different formats (markdown, HTML, etc.).
        This method tries to extract the best format for indexing.

        Args:
            content_data: Content data from GitBook API

        Returns:
            Content as markdown string
        """
        # Try to get markdown first
        if "markdown" in content_data:
            return content_data["markdown"]

        # Try to get nodes and convert to markdown
        if "nodes" in content_data:
            return self._nodes_to_markdown(content_data["nodes"])

        # Fallback to text if available
        if "text" in content_data:
            return content_data["text"]

        return ""

    def _nodes_to_markdown(self, nodes: list[dict[str, Any]]) -> str:
        """
        Convert GitBook content nodes to markdown format.

        Args:
            nodes: List of content node objects

        Returns:
            Markdown string
        """
        markdown_lines = []

        for node in nodes:
            node_type = node.get("type", "")
            content = ""

            if node_type == "paragraph":
                content = self._format_paragraph(node)
            elif node_type == "heading":
                level = node.get("level", 1)
                content = self._format_heading(node, level)
            elif node_type == "list":
                content = self._format_list(node)
            elif node_type == "code":
                content = self._format_code(node)
            elif node_type == "quote":
                content = self._format_quote(node)
            elif node_type == "divider":
                content = "---"
            elif node_type == "callout":
                content = self._format_callout(node)

            if content:
                markdown_lines.append(content)

        return "\n\n".join(markdown_lines)

    def _format_paragraph(self, node: dict[str, Any]) -> str:
        """Format a paragraph node as markdown."""
        return self._extract_text(node)

    def _format_heading(self, node: dict[str, Any], level: int) -> str:
        """Format a heading node as markdown."""
        text = self._extract_text(node)
        prefix = "#" * level
        return f"{prefix} {text}"

    def _format_list(self, node: dict[str, Any]) -> str:
        """Format a list node as markdown."""
        items = node.get("items", [])
        list_type = node.get("style", "bullet")  # bullet or ordered
        lines = []

        for i, item in enumerate(items):
            text = self._extract_text(item)
            if list_type == "ordered":
                lines.append(f"{i + 1}. {text}")
            else:
                lines.append(f"- {text}")

        return "\n".join(lines)

    def _format_code(self, node: dict[str, Any]) -> str:
        """Format a code node as markdown."""
        code = node.get("code", "")
        language = node.get("language", "")
        return f"```{language}\n{code}\n```"

    def _format_quote(self, node: dict[str, Any]) -> str:
        """Format a quote node as markdown."""
        text = self._extract_text(node)
        return f"> {text}"

    def _format_callout(self, node: dict[str, Any]) -> str:
        """Format a callout node as markdown."""
        text = self._extract_text(node)
        emoji = node.get("icon", "ℹ️")
        return f"> {emoji} {text}"

    def _extract_text(self, node: dict[str, Any]) -> str:
        """
        Extract text from a GitBook content node.

        Args:
            node: Content node object

        Returns:
            Extracted text string
        """
        # Try to get text directly
        if "text" in node:
            return node["text"]

        # Try to get from leaves (text content)
        if "leaves" in node:
            leaves = node["leaves"]
            text_parts = []

            for leaf in leaves:
                if "text" in leaf:
                    text = leaf["text"]
                    marks = leaf.get("marks", [])

                    # Apply formatting
                    for mark in marks:
                        mark_type = mark.get("type", "")
                        if mark_type == "bold":
                            text = f"**{text}**"
                        elif mark_type == "italic":
                            text = f"*{text}*"
                        elif mark_type == "code":
                            text = f"`{text}`"
                        elif mark_type == "strikethrough":
                            text = f"~~{text}~~"

                    text_parts.append(text)

            return "".join(text_parts)

        # Try to get from nested nodes
        if "nodes" in node:
            return "\n".join(self._extract_text(child) for child in node["nodes"])

        return ""

    def disconnect(self) -> None:
        """Close the HTTP session and release resources."""
        if self.session:
            self.session.close()
            self.session = None
        super().disconnect()
