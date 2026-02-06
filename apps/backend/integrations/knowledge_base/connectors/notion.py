"""
Notion Knowledge Base Connector
================================

Connects to Notion workspace to fetch documentation pages.
Supports both full sync and incremental sync based on last edited time.

Environment Variables:
- KNOWLEDGE_BASE_NOTION_API_KEY: Notion integration token (required)
- KNOWLEDGE_BASE_NOTION_WORKSPACE_ID: Notion workspace ID (optional, for filtering)

The Notion API requires an integration token created at https://www.notion.so/my-integrations.

Key Features:
- Fetch all pages from workspace
- Convert Notion blocks to markdown
- Incremental sync based on last_edited_time
- Error handling and retry logic
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from ..base import BaseConnector
from ..config import (
    SYNC_STATUS_FAILED,
    SYNC_STATUS_PARTIAL,
    SYNC_STATUS_SUCCESS,
    KnowledgeBaseConfig,
    KnowledgeBaseState,
    PROVIDER_NOTION,
)


class NotionConnector(BaseConnector):
    """
    Connector for Notion workspaces.

    Fetches documentation pages from a Notion workspace using the Notion API.
    Converts Notion blocks to markdown format for indexing in Graphiti.

    Attributes:
        config: KnowledgeBaseConfig instance
        spec_dir: Spec directory for state storage
        api_key: Notion integration token
        workspace_id: Optional workspace ID for filtering
        session: requests.Session for HTTP requests
        api_version: Notion API version
    """

    API_BASE_URL = "https://api.notion.com/v1"
    API_VERSION = "2022-06-28"

    def __init__(self, config: KnowledgeBaseConfig, spec_dir: Path):
        """
        Initialize the Notion connector.

        Args:
            config: KnowledgeBaseConfig with Notion settings
            spec_dir: Spec directory for state storage

        Raises:
            ValueError: If config is invalid or missing API key
        """
        super().__init__(config, spec_dir)

        self.api_key = config.api_key
        self.workspace_id = config.workspace_id or ""
        self.session: Optional[requests.Session] = None

        if not self.api_key:
            raise ValueError("NOTION_API_KEY is required for Notion connector")

    def connect(self) -> bool:
        """
        Establish connection to Notion API and verify authentication.

        Tests the API key by making a simple search request.
        Sets self._connected = True on success.

        Returns:
            True if connection successful, False otherwise
        """
        if self._connected:
            return True

        try:
            # Create HTTP session
            self.session = requests.Session()
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Notion-Version": self.API_VERSION,
                "Content-Type": "application/json",
            })

            # Test connection with a simple search
            response = self._make_request(
                "POST",
                "/search",
                json={"query": "", "page_size": 1}
            )

            if response and response.status_code == 200:
                self._connected = True
                return True

            return False

        except (OSError, requests.RequestException):
            return False

    def fetch_documents(self) -> List[Dict[str, Any]]:
        """
        Fetch all documents (pages) from the Notion workspace.

        Performs a full sync, retrieving all accessible pages from the workspace.
        Converts Notion blocks to markdown format.

        Returns:
            List of document dictionaries, each containing:
            - id: Page ID
            - title: Page title
            - content: Page content as markdown
            - url: Page URL
            - metadata: Dict with last_edited_time, created_time, etc.

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to Notion API")

        documents = []
        errors = []

        try:
            # Search for all pages in workspace
            pages = self._fetch_all_pages()

            for page in pages:
                try:
                    doc = self._fetch_page_content(page)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    errors.append(f"Failed to fetch page {page.get('id')}: {e}")

            # Update state
            if not self.state or not self.state.initialized:
                self._initialize_state()

            self.state.total_docs = len(documents)
            self.state.indexed_docs = len(documents)
            self.state.failed_docs = len(errors)
            self.state.last_sync = datetime.now().isoformat()
            self.state.sync_status = SYNC_STATUS_SUCCESS if not errors else SYNC_STATUS_PARTIAL
            self.state.error_message = "; ".join(errors[:5])  # First 5 errors
            self._save_state()

        except Exception as e:
            if self.state:
                self.state.sync_status = SYNC_STATUS_FAILED
                self.state.error_message = str(e)
                self._save_state()
            raise

        return documents

    def incremental_sync(self) -> Dict[str, Any]:
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
            raise ConnectionError("Not connected to Notion API")

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

            # Fetch all pages and filter by last_edited_time
            all_pages = self._fetch_all_pages()

            # Filter pages edited since last sync
            updated_pages = [
                p for p in all_pages
                if p.get("last_edited_time") and p["last_edited_time"] > last_sync
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
                            "last_edited_time": doc["metadata"]["last_edited_time"],
                            "source": "Notion",
                        }

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"Failed to sync page {page.get('id')}: {e}")

            # Update state
            self.state.total_docs = len(self.state.doc_mapping)
            self.state.indexed_docs = len(self.state.doc_mapping)
            self.state.failed_docs = result["failed"]
            self.state.last_sync = datetime.now().isoformat()
            self.state.sync_status = SYNC_STATUS_SUCCESS if not result["failed"] else SYNC_STATUS_PARTIAL
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
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retries: int = 3,
    ) -> Optional[requests.Response]:
        """
        Make an HTTP request to the Notion API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/search")
            json_data: Request body for POST requests
            params: Query parameters
            retries: Number of retries on failure

        Returns:
            Response object or None if all retries fail
        """
        if not self.session:
            return None

        url = f"{self.API_BASE_URL}{endpoint}"

        for attempt in range(retries):
            try:
                response = self.session.request(
                    method,
                    url,
                    json=json_data,
                    params=params,
                    timeout=30
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
                time.sleep(2 ** attempt)

            except (OSError, requests.RequestException):
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None

        return None

    def _fetch_all_pages(self) -> List[Dict[str, Any]]:
        """
        Fetch all pages from the Notion workspace.

        Uses the search API with pagination to retrieve all pages.

        Returns:
            List of page objects with id, title, last_edited_time, url
        """
        pages = []
        next_cursor: Optional[str] = None

        while True:
            search_body = {
                "filter": {
                    "value": "page",
                    "property": "object"
                }
            }

            if next_cursor:
                search_body["start_cursor"] = next_cursor

            response = self._make_request("POST", "/search", json_data=search_body)

            if not response or response.status_code != 200:
                break

            data = response.json()
            results = data.get("results", [])
            pages.extend(results)

            # Check for more pages
            next_cursor = data.get("next_cursor")
            if not data.get("has_more"):
                break

        return pages

    def _fetch_page_content(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch the full content of a Notion page.

        Retrieves all blocks from the page and converts them to markdown.

        Args:
            page: Page object from Notion API

        Returns:
            Document dict with id, title, content, url, metadata
        """
        page_id = page.get("id")
        if not page_id:
            return None

        # Get page title
        title = self._extract_page_title(page)

        # Get page URL
        url = page.get("url", "")

        # Get metadata
        created_time = page.get("created_time", "")
        last_edited_time = page.get("last_edited_time", "")

        # Fetch page blocks
        blocks = self._fetch_page_blocks(page_id)

        # Convert blocks to markdown
        content = self._blocks_to_markdown(blocks)

        return {
            "id": page_id,
            "title": title,
            "content": content,
            "url": url,
            "metadata": {
                "created_time": created_time,
                "last_edited_time": last_edited_time,
                "source": "Notion",
            }
        }

    def _fetch_page_blocks(self, block_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all blocks from a page (recursive for nested blocks).

        Args:
            block_id: Page or block ID

        Returns:
            List of block objects
        """
        blocks = []
        next_cursor: Optional[str] = None

        while True:
            params = {}
            if next_cursor:
                params["start_cursor"] = next_cursor

            response = self._make_request(
                "GET",
                f"/blocks/{block_id}/children",
                params=params
            )

            if not response or response.status_code != 200:
                break

            data = response.json()
            results = data.get("results", [])
            blocks.extend(results)

            # Recursively fetch nested blocks
            for block in results:
                if block.get("has_children"):
                    child_blocks = self._fetch_page_blocks(block["id"])
                    blocks.extend(child_blocks)

            # Check for more blocks
            next_cursor = data.get("next_cursor")
            if not data.get("has_more"):
                break

        return blocks

    def _extract_page_title(self, page: Dict[str, Any]) -> str:
        """
        Extract the title from a Notion page.

        Args:
            page: Page object from Notion API

        Returns:
            Page title string
        """
        # Try to get title from properties
        properties = page.get("properties", {})

        # Check for title property (commonly named "title" or "Name")
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_array = prop_data.get("title", [])
                if title_array:
                    return title_array[0].get("plain_text", "")

        # Fallback to page ID
        return page.get("id", "Untitled")

    def _blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """
        Convert Notion blocks to markdown format.

        Args:
            blocks: List of Notion block objects

        Returns:
            Markdown string
        """
        markdown_lines = []

        for block in blocks:
            block_type = block.get("type", "")
            content = ""

            if block_type == "paragraph":
                content = self._format_paragraph(block)
            elif block_type == "heading_1":
                content = self._format_heading(block, 1)
            elif block_type == "heading_2":
                content = self._format_heading(block, 2)
            elif block_type == "heading_3":
                content = self._format_heading(block, 3)
            elif block_type == "bulleted_list_item":
                content = self._format_list_item(block, "-")
            elif block_type == "numbered_list_item":
                content = self._format_list_item(block, "1.")
            elif block_type == "to_do":
                content = self._format_todo(block)
            elif block_type == "code":
                content = self._format_code(block)
            elif block_type == "quote":
                content = self._format_quote(block)
            elif block_type == "divider":
                content = "---"
            elif block_type == "callout":
                content = self._format_callout(block)

            if content:
                markdown_lines.append(content)

        return "\n\n".join(markdown_lines)

    def _format_paragraph(self, block: Dict[str, Any]) -> str:
        """Format a paragraph block as markdown."""
        text = self._extract_rich_text(block.get("paragraph", {}))
        return text

    def _format_heading(self, block: Dict[str, Any], level: int) -> str:
        """Format a heading block as markdown."""
        text = self._extract_rich_text(block.get(f"heading_{level}", {}))
        prefix = "#" * level
        return f"{prefix} {text}"

    def _format_list_item(self, block: Dict[str, Any], prefix: str) -> str:
        """Format a list item block as markdown."""
        text = self._extract_rich_text(block.get(block["type"], {}))
        return f"{prefix} {text}"

    def _format_todo(self, block: Dict[str, Any]) -> str:
        """Format a to-do block as markdown."""
        todo_data = block.get("to_do", {})
        checked = todo_data.get("checked", False)
        text = self._extract_rich_text(todo_data)
        checkbox = "[x]" if checked else "[ ]"
        return f"{checkbox} {text}"

    def _format_code(self, block: Dict[str, Any]) -> str:
        """Format a code block as markdown."""
        code_data = block.get("code", {})
        code = self._extract_plain_text(code_data.get("rich_text", []))
        language = code_data.get("language", "")
        return f"```{language}\n{code}\n```"

    def _format_quote(self, block: Dict[str, Any]) -> str:
        """Format a quote block as markdown."""
        text = self._extract_rich_text(block.get("quote", {}))
        return f"> {text}"

    def _format_callout(self, block: Dict[str, Any]) -> str:
        """Format a callout block as markdown."""
        text = self._extract_rich_text(block.get("callout", {}))
        emoji = block.get("callout", {}).get("icon", {}).get("emoji", "ℹ️")
        return f"> {emoji} {text}"

    def _extract_rich_text(self, block_data: Dict[str, Any]) -> str:
        """
        Extract text from Notion rich text array.

        Args:
            block_data: Block data with rich_text array

        Returns:
            Plain text string with formatting
        """
        rich_text = block_data.get("rich_text", [])
        return self._extract_plain_text(rich_text)

    def _extract_plain_text(self, rich_text: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from Notion rich text array.

        Args:
            rich_text: List of rich text objects

        Returns:
            Concatenated plain text
        """
        text_parts = []

        for text_obj in rich_text:
            plain_text = text_obj.get("plain_text", "")
            annotations = text_obj.get("annotations", {})

            # Apply basic markdown formatting
            if annotations.get("code"):
                plain_text = f"`{plain_text}`"
            if annotations.get("bold"):
                plain_text = f"**{plain_text}**"
            if annotations.get("italic"):
                plain_text = f"*{plain_text}*"
            if annotations.get("strikethrough"):
                plain_text = f"~~{plain_text}~~"

            text_parts.append(plain_text)

        return "".join(text_parts)

    def disconnect(self) -> None:
        """Close the HTTP session and release resources."""
        if self.session:
            self.session.close()
            self.session = None
        super().disconnect()
