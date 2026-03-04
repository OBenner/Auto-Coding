"""
GitHub Wiki Knowledge Base Connector
====================================

Connects to GitHub Wiki repositories to fetch documentation pages.
Supports both full sync and incremental sync based on file modification time.

GitHub Wikis are git repositories hosted at https://github.com/owner/repo.wiki.git.
This connector clones the wiki repo and reads markdown files.

Environment Variables:
- KNOWLEDGE_BASE_GITHUB_WIKI_API_KEY: GitHub personal access token (required)
- KNOWLEDGE_BASE_GITHUB_WIKI_REPOSITORY: Repository in 'owner/repo' format (required)

The GitHub API token is used for authentication when cloning the wiki repository.
Create a personal access token at https://github.com/settings/tokens.

Key Features:
- Clone wiki repository
- Read all markdown files
- Incremental sync based on file modification time
- Error handling and cleanup
"""

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from ..base import BaseConnector
from ..config import (
    SYNC_STATUS_FAILED,
    KnowledgeBaseConfig,
)

# Configure logger
logger = logging.getLogger(__name__)


class GitHubWikiConnector(BaseConnector):
    """
    Connector for GitHub Wiki repositories.

    Fetches documentation pages from a GitHub Wiki by cloning the wiki repository
    and reading markdown files. The wiki repository is at:
    https://github.com/owner/repo.wiki.git

    Attributes:
        config: KnowledgeBaseConfig instance
        spec_dir: Spec directory for state storage
        api_key: GitHub personal access token
        repository: Repository in 'owner/repo' format
        wiki_dir: Temporary directory for cloned wiki
    """

    def __init__(self, config: KnowledgeBaseConfig, spec_dir: Path):
        """
        Initialize the GitHub Wiki connector.

        Args:
            config: KnowledgeBaseConfig with GitHub Wiki settings
            spec_dir: Spec directory for state storage

        Raises:
            ValueError: If config is invalid or missing required fields
        """
        super().__init__(config, spec_dir)

        self.api_key = config.api_key
        self.repository = config.repository
        self.wiki_dir: Path | None = None

        if not self.api_key:
            raise ValueError(
                "GITHUB_WIKI_API_KEY is required for GitHub Wiki connector"
            )
        if not self.repository:
            raise ValueError("GITHUB_WIKI_REPOSITORY is required (format: owner/repo)")

        # Validate repository format
        if "/" not in self.repository or self.repository.count("/") != 1:
            raise ValueError(
                "GITHUB_WIKI_REPOSITORY must be in 'owner/repo' format, "
                f"got: {self.repository}"
            )

    def connect(self) -> bool:
        """
        Establish connection to GitHub Wiki by cloning the repository.

        Clones the wiki repository to a temporary directory to verify access.
        Sets self._connected = True on success.

        Returns:
            True if connection successful, False otherwise
        """
        if self._connected:
            return True

        try:
            # Create temporary directory for wiki clone
            self.wiki_dir = self.spec_dir / ".wiki_clone"
            self.wiki_dir.mkdir(parents=True, exist_ok=True)

            # Clone wiki repository
            wiki_url = self._get_wiki_url()
            success = self._clone_wiki(wiki_url, self.wiki_dir)

            if success:
                self._connected = True
                logger.info(
                    "Successfully cloned wiki repository for %s", self.repository
                )
                return True

            logger.error("Failed to clone wiki repository for %s", self.repository)
            return False

        except (OSError, subprocess.SubprocessError) as e:
            logger.error(f"Error connecting to GitHub Wiki: {e}")
            return False

    def fetch_documents(self) -> list[dict[str, Any]]:
        """
        Fetch all documents (pages) from the GitHub Wiki.

        Performs a full sync, retrieving all markdown files from the cloned
        wiki repository.

        Returns:
            List of document dictionaries, each containing:
            - id: File path relative to wiki root
            - title: Page title (derived from filename)
            - content: Page content as markdown
            - url: Page URL on GitHub
            - metadata: Dict with file_path, modified_time, etc.

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError("Not connected to GitHub Wiki")

        if not self.wiki_dir or not self.wiki_dir.exists():
            raise ConnectionError("Wiki repository not cloned")

        documents = []
        errors = []

        try:
            # Find all markdown files in wiki
            md_files = list(self.wiki_dir.rglob("*.md"))

            if not md_files:
                logger.warning(
                    f"No markdown files found in wiki repository at {self.wiki_dir}"
                )

            for md_file in md_files:
                try:
                    doc = self._read_wiki_page(md_file)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    errors.append(f"Failed to read {md_file.name}: {e}")

            # Update state
            self._update_full_sync_state(documents, errors)

            # Build doc_mapping
            for doc in documents:
                self.state.doc_mapping[doc["id"]] = {
                    "title": doc["title"],
                    "url": doc["url"],
                    "file_path": doc["metadata"]["file_path"],
                    "modified_time": doc["metadata"]["modified_time"],
                    "source": "GitHub Wiki",
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

        Fetches only files that have been created or modified since
        self.state.last_sync by pulling latest changes and checking
        file modification times.

        Returns:
            Dict with sync results:
            - success: bool
            - added: int (new documents)
            - updated: int (modified documents)
            - failed: int
            - errors: list of error messages
        """
        if not self._connected:
            raise ConnectionError("Not connected to GitHub Wiki")

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
            # Pull latest changes
            if not self._pull_wiki():
                logger.warning("Git pull failed, proceeding with stale wiki data")

            # Get last sync time
            last_sync = self.state.last_sync

            # Find all markdown files
            md_files = list(self.wiki_dir.rglob("*.md")) if self.wiki_dir else []

            for md_file in md_files:
                try:
                    # Get file modification time
                    mod_time_str = datetime.fromtimestamp(
                        md_file.stat().st_mtime
                    ).isoformat()

                    # Check if file was modified since last sync
                    if last_sync and mod_time_str <= last_sync:
                        continue

                    # Read the page
                    doc = self._read_wiki_page(md_file)
                    if doc:
                        doc_id = doc["id"]

                        # Check if this is a new or updated document
                        if doc_id in self.state.doc_mapping:
                            result["updated"] += 1
                        else:
                            result["added"] += 1

                        # Update doc_mapping
                        self.state.doc_mapping[doc_id] = {
                            "title": doc["title"],
                            "url": doc["url"],
                            "file_path": doc["metadata"]["file_path"],
                            "modified_time": doc["metadata"]["modified_time"],
                            "source": "GitHub Wiki",
                        }

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"Failed to sync {md_file.name}: {e}")

            # Update state
            self._update_incremental_sync_state(result)

        except Exception as e:
            self._handle_sync_error(result, e)

        return result

    def disconnect(self) -> None:
        """
        Close connection and clean up cloned repository.

        Removes the temporary wiki clone directory.
        """
        super().disconnect()

        # Clean up cloned wiki repository
        if self.wiki_dir and self.wiki_dir.exists():
            try:
                shutil.rmtree(self.wiki_dir)
                logger.info(f"Cleaned up wiki clone at {self.wiki_dir}")
            except OSError as e:
                logger.warning(f"Failed to clean up wiki clone: {e}")

    def _get_wiki_url(self) -> str:
        """
        Get the wiki repository URL with authentication.

        Returns:
            HTTPS URL with embedded token for authentication
        """
        owner, repo = self.repository.split("/")
        wiki_repo = f"{repo}.wiki"
        return f"https://{self.api_key}@github.com/{owner}/{wiki_repo}.git"

    def _sanitize_output(self, text: str) -> str:
        """
        Sanitize text output to remove credentials before logging.

        Args:
            text: Text that may contain credentials (e.g., git URLs with tokens)

        Returns:
            Sanitized text with credentials replaced
        """
        if self.api_key and self.api_key in text:
            return text.replace(self.api_key, "***")
        return text

    def _clone_wiki(self, url: str, target_dir: Path) -> bool:
        """
        Clone the wiki repository to target directory.

        Args:
            url: Wiki repository URL
            target_dir: Target directory for clone

        Returns:
            True if clone successful, False otherwise
        """
        try:
            # Remove existing directory if present
            if target_dir.exists():
                shutil.rmtree(target_dir)

            # Clone repository
            result = subprocess.run(
                ["git", "clone", url, str(target_dir)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            )

            if result.returncode == 0:
                return True

            # Sanitize stderr to avoid leaking credentials in logs
            sanitized_stderr = self._sanitize_output(result.stderr)
            logger.error("Git clone failed: %s", sanitized_stderr)
            return False

        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.error(
                "Error cloning wiki repository: %s", self._sanitize_output(str(e))
            )
            return False

    def _pull_wiki(self) -> bool:
        """
        Pull latest changes from wiki repository.

        Returns:
            True if pull successful, False otherwise
        """
        if not self.wiki_dir or not self.wiki_dir.exists():
            return False

        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=str(self.wiki_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )

            if result.returncode == 0:
                return True

            sanitized_stderr = self._sanitize_output(result.stderr)
            logger.error("Git pull failed: %s", sanitized_stderr)
            return False

        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.error(
                "Error pulling wiki repository: %s", self._sanitize_output(str(e))
            )
            return False

    def _read_wiki_page(self, md_file: Path) -> dict[str, Any] | None:
        """
        Read a wiki page from a markdown file.

        Args:
            md_file: Path to markdown file

        Returns:
            Document dict with id, title, content, url, metadata
            or None if file cannot be read
        """
        try:
            # Read file content
            content = md_file.read_text(encoding="utf-8")

            # Get relative path from wiki root
            rel_path = (
                md_file.relative_to(self.wiki_dir) if self.wiki_dir else md_file.name
            )

            # Derive title from filename (remove .md extension)
            title = md_file.stem
            # Replace hyphens/underscores with spaces and capitalize
            title = title.replace("-", " ").replace("_", " ").title()

            # Get file modification time
            mod_time = datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()

            # Build GitHub URL for the page
            # GitHub Wiki URLs are: https://github.com/owner/repo/wiki/Page-Name
            page_name = md_file.stem.replace("_", "-")
            url = f"https://github.com/{self.repository}/wiki/{page_name}"

            return {
                "id": str(rel_path),
                "title": title,
                "content": content,
                "url": url,
                "metadata": {
                    "file_path": str(rel_path),
                    "modified_time": mod_time,
                    "file_size": md_file.stat().st_size,
                },
            }

        except (OSError, UnicodeDecodeError) as e:
            logger.error(f"Error reading wiki page {md_file}: {e}")
            return None
