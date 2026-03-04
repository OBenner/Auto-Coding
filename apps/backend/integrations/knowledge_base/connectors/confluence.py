"""
Confluence Knowledge Base Connector
====================================

Connects to Atlassian Confluence to fetch documentation pages.
Supports both full sync and incremental sync based on last modified date.

Environment Variables:
- KNOWLEDGE_BASE_CONFLUENCE_API_KEY: Confluence API token (required)
- KNOWLEDGE_BASE_CONFLUENCE_API_URL: Confluence base URL (required, e.g., https://your-domain.atlassian.net/wiki)
- KNOWLEDGE_BASE_CONFLUENCE_SPACE_KEY: Space key to sync (required, e.g., 'DOC' or 'OPS')
- KNOWLEDGE_BASE_CONFLUENCE_EMAIL: Account email for authentication (required)

Confluence API tokens can be created at https://id.atlassian.com/manage-profile/security/api-tokens

Key Features:
- Fetch all pages from a Confluence space
- Convert Confluence storage format to markdown
- Incremental sync based on last modified date
- Error handling and retry logic
"""

import base64
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from ..base import BaseConnector
from ..config import (
    SYNC_STATUS_FAILED,
    KnowledgeBaseConfig,
)

logger = logging.getLogger(__name__)


class ConfluenceConnector(BaseConnector):
    """
    Connector for Atlassian Confluence.

    Fetches documentation pages from a Confluence space using the REST API.
    Converts Confluence storage format to markdown for indexing in Graphiti.

    Attributes:
        config: KnowledgeBaseConfig instance
        spec_dir: Spec directory for state storage
        api_key: Confluence API token
        api_url: Confluence base URL
        space_key: Confluence space key
        email: Account email for authentication
        session: requests.Session for HTTP requests
    """

    def __init__(self, config: KnowledgeBaseConfig, spec_dir: Path):
        """
        Initialize the Confluence connector.

        Args:
            config: KnowledgeBaseConfig with Confluence settings
            spec_dir: Spec directory for state storage

        Raises:
            ValueError: If config is invalid or missing required fields
        """
        super().__init__(config, spec_dir)

        self.api_key = config.api_key
        self.api_url = config.api_url
        self.space_key = config.space_key
        self.email = os.environ.get("KNOWLEDGE_BASE_CONFLUENCE_EMAIL", "")
        self.session: requests.Session | None = None

        if not self.api_key:
            raise ValueError("CONFLUENCE_API_KEY is required for Confluence connector")
        if not self.api_url:
            raise ValueError("CONFLUENCE_API_URL is required for Confluence connector")
        if not self.space_key:
            raise ValueError(
                "CONFLUENCE_SPACE_KEY is required for Confluence connector"
            )
        if not self.email:
            raise ValueError("CONFLUENCE_EMAIL is required for Confluence connector")

    def connect(self) -> bool:
        """
        Establish connection to Confluence API and verify authentication.

        Tests the API credentials by making a simple request to the space.
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
                    "Authorization": self._get_auth_header(),
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            )

            # Test connection by fetching space info
            space_url = self._build_api_url(f"/space/{self.space_key}")
            response = self._make_request("GET", space_url)

            if response and response.status_code == 200:
                self._connected = True
                return True

            return False

        except (OSError, requests.RequestException):
            return False

    def fetch_documents(self) -> list[dict[str, Any]]:
        """
        Fetch all documents (pages) from the Confluence space.

        Performs a full sync, retrieving all pages from the configured space.
        Converts Confluence storage format to markdown.

        Returns:
            List of document dictionaries, each containing:
            - id: Page ID
            - title: Page title
            - content: Page content as markdown
            - url: Page URL
            - metadata: Dict with last_modified, created_at, etc.

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to Confluence API")

        documents = []
        errors = []

        try:
            # Fetch all pages from the space
            pages = self._fetch_all_pages()

            for page in pages:
                try:
                    doc = self._fetch_page_content(page)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    errors.append(f"Failed to fetch page {page.get('id')}: {e}")

            # Update state
            self._update_full_sync_state(documents, errors)

            # Populate doc_mapping for incremental sync
            self.state.doc_mapping = {
                doc["id"]: {
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "last_modified": doc.get("metadata", {}).get("last_modified", ""),
                    "source": "Confluence",
                }
                for doc in documents
                if doc.get("id")
            }

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
            raise ConnectionError("Not connected to Confluence API")

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

            # Fetch all pages and filter by last modified date
            all_pages = self._fetch_all_pages()

            # Filter pages modified since last sync
            updated_pages = [
                p
                for p in all_pages
                if p.get("_links", {}).get("webui")
                and self._is_page_modified_after(p, last_sync)
            ]

            # Process each updated page
            for page in updated_pages:
                try:
                    doc = self._fetch_page_content(page)
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
                            "last_modified": doc["metadata"]["last_modified"],
                            "source": "Confluence",
                        }

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(
                        f"Failed to sync page {page.get('id')}: {e}"
                    )

            # Update state
            self._update_incremental_sync_state(result)

        except Exception as e:
            self._handle_sync_error(result, e)

        return result

    def _get_auth_header(self) -> str:
        """
        Generate HTTP Basic Auth header for Confluence API.

        Returns:
            Basic Auth header string
        """
        credentials = f"{self.email}:{self.api_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _build_api_url(self, endpoint: str) -> str:
        """
        Build full API URL for an endpoint.

        Args:
            endpoint: API endpoint path (e.g., "/content/123")

        Returns:
            Full URL
        """
        # Ensure api_url ends with /wiki or /rest/api
        base = self.api_url.rstrip("/")
        if not base.endswith("/wiki") and not base.endswith("/rest/api"):
            base = f"{base}/wiki"

        # Add /rest/api if not present
        if not base.endswith("/rest/api"):
            base = f"{base}/rest/api"

        return urljoin(base + "/", endpoint.lstrip("/"))

    def _make_request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json_data: dict | None = None,
        retries: int = 3,
    ) -> requests.Response | None:
        """
        Make an HTTP request to the Confluence API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            params: Query parameters
            json_data: Request body for POST requests
            retries: Number of retries on failure

        Returns:
            Response object or None if all retries fail
        """
        if not self.session:
            return None

        for attempt in range(retries):
            try:
                response = self.session.request(
                    method, url, params=params, json=json_data, timeout=30
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

    def _fetch_all_pages(self) -> list[dict[str, Any]]:
        """
        Fetch all pages from the configured Confluence space.

        Uses the content search API with pagination to retrieve all pages.

        Returns:
            List of page objects with id, title, _links, etc.
        """
        pages = []
        start: int = 0
        limit: int = 50

        while True:
            params = {
                "spaceKey": self.space_key,
                "type": "page",
                "status": "current",
                "expand": "version,history",
                "start": start,
                "limit": limit,
            }

            url = self._build_api_url("/content")
            response = self._make_request("GET", url, params=params)

            if not response or response.status_code != 200:
                break

            data = response.json()
            results = data.get("results", [])
            pages.extend(results)

            # Check for more pages
            if len(results) < limit:
                break

            start += limit

        return pages

    def _is_page_modified_after(
        self, page: dict[str, Any], timestamp: str | None
    ) -> bool:
        """
        Check if a page was modified after the given timestamp.

        Args:
            page: Page object from Confluence API
            timestamp: ISO format timestamp string, or None

        Returns:
            True if page was modified after timestamp
        """
        if timestamp is None:
            return True

        try:
            # Try to get last modified from history
            history = page.get("history", {})
            last_modified = history.get("lastUpdated", {}).get("when")

            if last_modified:
                modified_time = datetime.fromisoformat(
                    last_modified.replace("Z", "+00:00")
                )
                sync_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return modified_time > sync_time

        except (ValueError, AttributeError, TypeError):
            logger.debug(
                "Could not parse modification time for page %s", page.get("id")
            )

        return False

    def _fetch_page_content(self, page: dict[str, Any]) -> dict[str, Any] | None:
        """
        Fetch the full content of a Confluence page.

        Retrieves the page body in storage format and converts to markdown.

        Args:
            page: Page object from Confluence API

        Returns:
            Document dict with id, title, content, url, metadata
        """
        page_id = page.get("id")
        if not page_id:
            return None

        # Get basic page info
        title = page.get("title", "Untitled")
        webui_link = page.get("_links", {}).get("webui", "")
        base_url = (
            self.api_url.rstrip("/").replace("/rest/api", "").replace("/wiki", "")
        )
        url = f"{base_url}{webui_link}" if webui_link else ""

        # Get metadata
        created_at = page.get("history", {}).get("createdDate", "")
        history = page.get("history", {})
        last_modified = history.get("lastUpdated", {}).get("when", "")
        version = page.get("version", {}).get("number", 1)

        # Fetch page body with content expansion
        content_url = self._build_api_url(f"/content/{page_id}")
        params = {
            "expand": "body.storage,version,history",
            "status": "current",
        }

        response = self._make_request("GET", content_url, params=params)

        if not response or response.status_code != 200:
            return None

        content_data = response.json()
        body_storage = content_data.get("body", {}).get("storage", {})
        content_html = body_storage.get("value", "")

        # Convert Confluence storage format to markdown
        content = self._storage_to_markdown(content_html)

        return {
            "id": page_id,
            "title": title,
            "content": content,
            "url": url,
            "metadata": {
                "created_at": created_at,
                "last_modified": last_modified,
                "version": version,
                "space_key": self.space_key,
                "source": "Confluence",
            },
        }

    def _storage_to_markdown(self, storage_html: str) -> str:
        """
        Convert Confluence storage format HTML to markdown.

        This is a simplified conversion that handles common elements:
        - Headings (h1-h6)
        - Paragraphs
        - Bold, italic, code, strikethrough
        - Links
        - Lists (ordered and unordered)
        - Code blocks
        - Tables (basic)
        - Block quotes

        Args:
            storage_html: HTML string from Confluence storage format

        Returns:
            Markdown string
        """
        # Import html.parser for HTML processing
        from html.parser import HTMLParser

        class ConfluenceParser(HTMLParser):
            """Custom HTML to markdown parser for Confluence."""

            def __init__(self):
                super().__init__()
                self.output = []
                self.in_heading = False
                self.heading_level = 0
                self.in_list = False
                self.list_type_stack = []  # Stack of 'ul'/'ol' for nesting
                self.list_depth = 0
                self.list_counter_stack = []  # Stack of counters for nested ol
                self.in_code_block = False
                self.in_link = False
                self.link_url = ""
                self.link_text = []
                self.in_table = False
                self.in_table_row = False
                self.in_table_cell = False
                self.table_cells = []
                self.table_rows = []
                self.in_blockquote = False

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)

                if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    self.in_heading = True
                    self.heading_level = int(tag[1])

                elif tag == "p":
                    pass  # Paragraphs get newline handling

                elif tag in ("b", "strong"):
                    self.output.append("**")

                elif tag in ("i", "em"):
                    self.output.append("*")

                elif tag in ("code", "tt"):
                    self.output.append("`")

                elif tag in ("s", "strike", "del"):
                    self.output.append("~~")

                elif tag == "a":
                    self.in_link = True
                    self.link_url = attrs_dict.get("href", "")

                elif tag in ("ul", "ol"):
                    self.in_list = True
                    list_type = "ol" if tag == "ol" else "ul"
                    self.list_type_stack.append(list_type)
                    self.list_depth += 1
                    if list_type == "ol":
                        self.list_counter_stack.append(1)

                elif tag == "li":
                    # List item marker added in handle_data
                    pass

                elif tag == "pre":
                    self.in_code_block = True
                    self.output.append("\n```\n")

                elif tag == "blockquote":
                    self.in_blockquote = True

                elif tag == "table":
                    self.in_table = True
                    self.table_rows = []

                elif tag == "tr":
                    self.in_table_row = True
                    self.table_cells = []

                elif tag in ("td", "th"):
                    self.in_table_cell = True

                elif tag == "br":
                    self.output.append("\n")

            def handle_endtag(self, tag):
                if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    self.in_heading = False
                    self.heading_level = 0

                elif tag == "p":
                    self.output.append("\n\n")

                elif tag in ("b", "strong"):
                    self.output.append("**")

                elif tag in ("i", "em"):
                    self.output.append("*")

                elif tag in ("code", "tt"):
                    self.output.append("`")

                elif tag in ("s", "strike", "del"):
                    self.output.append("~~")

                elif tag == "a":
                    self.in_link = False
                    link_text = "".join(self.link_text).strip()
                    if link_text and self.link_url:
                        self.output.append(f"[{link_text}]({self.link_url})")
                    elif link_text:
                        self.output.append(link_text)
                    self.link_text = []
                    self.link_url = ""

                elif tag in ("ul", "ol"):
                    if self.list_type_stack:
                        exiting_type = self.list_type_stack.pop()
                        if exiting_type == "ol" and self.list_counter_stack:
                            self.list_counter_stack.pop()
                    self.list_depth -= 1
                    self.in_list = self.list_depth > 0
                    self.output.append("\n")

                elif tag == "li":
                    self.output.append("\n")

                elif tag == "pre":
                    self.in_code_block = False
                    self.output.append("\n```\n\n")

                elif tag == "blockquote":
                    self.in_blockquote = False
                    self.output.append("\n\n")

                elif tag == "td":
                    self.in_table_cell = False

                elif tag == "tr":
                    self.in_table_row = False
                    if self.table_cells:
                        self.table_rows.append(" | ".join(self.table_cells))
                        self.table_cells = []

                elif tag == "table":
                    self.in_table = False
                    if self.table_rows:
                        self.output.append("\n\n")
                        self.output.append("\n".join(self.table_rows))
                        self.output.append("\n\n")
                        self.table_rows = []

            def handle_data(self, data):
                if self.in_link:
                    self.link_text.append(data)
                elif self.in_table_cell:
                    self.table_cells.append(data.strip())
                elif self.in_code_block:
                    self.output.append(data)
                elif self.in_heading:
                    prefix = "#" * self.heading_level
                    self.output.append(f"{prefix} {data}\n\n")
                elif self.in_blockquote:
                    self.output.append(f"> {data}\n")
                elif self.in_list:
                    indent = "  " * (self.list_depth - 1)
                    current_type = (
                        self.list_type_stack[-1] if self.list_type_stack else "ul"
                    )
                    if current_type == "ul":
                        self.output.append(f"{indent}- {data}")
                    else:  # ol
                        count = (
                            self.list_counter_stack[-1]
                            if self.list_counter_stack
                            else 1
                        )
                        self.output.append(f"{indent}{count}. {data}")
                        if self.list_counter_stack:
                            self.list_counter_stack[-1] += 1
                elif data.strip():
                    self.output.append(data)

            def get_markdown(self) -> str:
                return "".join(self.output)

        # Parse the HTML
        parser = ConfluenceParser()
        try:
            parser.feed(storage_html)
        except Exception:
            # Fallback: return basic text if parsing fails
            logger.debug("HTML parsing failed, returning raw content")
            return storage_html

        markdown = parser.get_markdown()

        # Clean up excessive whitespace
        lines = markdown.split("\n")
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            is_empty = not line.strip()
            if not (is_empty and prev_empty):
                cleaned_lines.append(line)
            prev_empty = is_empty

        return "\n".join(cleaned_lines).strip()

    def disconnect(self) -> None:
        """Close the HTTP session and release resources."""
        if self.session:
            self.session.close()
            self.session = None
        super().disconnect()
