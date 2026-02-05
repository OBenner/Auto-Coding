"""
Git Service

Service layer for interacting with Git providers (GitHub, GitLab) using OAuth tokens.
Provides methods to list repositories, get repository details, and access repository content.
"""

import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class GitService:
    """
    Service for interacting with Git providers via their REST APIs.

    Supports GitHub and GitLab with OAuth token-based authentication.
    """

    # API base URLs
    GITHUB_API_BASE = "https://api.github.com"
    GITLAB_API_BASE = "https://gitlab.com/api/v4"

    def __init__(self, provider: str, access_token: str):
        """
        Initialize Git service.

        Args:
            provider: Git provider name ("github" or "gitlab")
            access_token: OAuth access token for API authentication

        Raises:
            ValueError: If provider is not supported
        """
        if provider not in ["github", "gitlab"]:
            raise ValueError(f"Unsupported provider: {provider}. Must be 'github' or 'gitlab'")

        self.provider = provider
        self.access_token = access_token

        # Set API base URL based on provider
        if provider == "github":
            self.api_base = self.GITHUB_API_BASE
        else:
            self.api_base = self.GITLAB_API_BASE

        logger.info(f"Initialized GitService for provider: {provider}")

    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for API requests.

        Returns:
            Dictionary of headers with authentication
        """
        if self.provider == "github":
            return {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/vnd.github.v3+json",
            }
        else:  # gitlab
            return {
                "Authorization": f"Bearer {self.access_token}",
            }

    async def get_user_info(self) -> Dict:
        """
        Get authenticated user information.

        Returns:
            Dictionary with user information

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                if self.provider == "github":
                    url = f"{self.api_base}/user"
                else:  # gitlab
                    url = f"{self.api_base}/user"

                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()

                user_data = response.json()
                logger.info(f"Retrieved user info for {self.provider}")

                return user_data

        except httpx.HTTPError as e:
            logger.error(f"Failed to get user info from {self.provider}: {e}")
            raise

    async def list_repositories(
        self,
        visibility: str = "all",
        sort: str = "updated",
        per_page: int = 30,
        page: int = 1
    ) -> List[Dict]:
        """
        List user's repositories.

        Args:
            visibility: Repository visibility filter ("all", "public", "private")
            sort: Sort order ("updated", "created", "pushed", "full_name")
            per_page: Number of results per page (max 100)
            page: Page number for pagination

        Returns:
            List of repository dictionaries

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                if self.provider == "github":
                    url = f"{self.api_base}/user/repos"
                    params = {
                        "visibility": visibility,
                        "sort": sort,
                        "per_page": min(per_page, 100),
                        "page": page,
                    }
                else:  # gitlab
                    url = f"{self.api_base}/projects"
                    params = {
                        "owned": "true",
                        "order_by": sort,
                        "sort": "desc",
                        "per_page": min(per_page, 100),
                        "page": page,
                    }

                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()

                repos = response.json()
                logger.info(
                    f"Retrieved {len(repos)} repositories from {self.provider} "
                    f"(page {page})"
                )

                return repos

        except httpx.HTTPError as e:
            logger.error(f"Failed to list repositories from {self.provider}: {e}")
            raise

    async def get_repository(self, owner: str, repo: str) -> Dict:
        """
        Get details for a specific repository.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Dictionary with repository details

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                if self.provider == "github":
                    url = f"{self.api_base}/repos/{owner}/{repo}"
                else:  # gitlab
                    # GitLab uses URL-encoded path (owner/repo)
                    project_path = f"{owner}%2F{repo}"
                    url = f"{self.api_base}/projects/{project_path}"

                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()

                repo_data = response.json()
                logger.info(f"Retrieved repository {owner}/{repo} from {self.provider}")

                return repo_data

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to get repository {owner}/{repo} from {self.provider}: {e}"
            )
            raise

    async def list_branches(self, owner: str, repo: str) -> List[Dict]:
        """
        List branches for a repository.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            List of branch dictionaries

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                if self.provider == "github":
                    url = f"{self.api_base}/repos/{owner}/{repo}/branches"
                else:  # gitlab
                    project_path = f"{owner}%2F{repo}"
                    url = f"{self.api_base}/projects/{project_path}/repository/branches"

                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()

                branches = response.json()
                logger.info(
                    f"Retrieved {len(branches)} branches for {owner}/{repo} "
                    f"from {self.provider}"
                )

                return branches

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to list branches for {owner}/{repo} from {self.provider}: {e}"
            )
            raise

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None
    ) -> Dict:
        """
        Get content of a file from repository.

        Args:
            owner: Repository owner username
            repo: Repository name
            path: File path in repository
            ref: Git reference (branch, tag, commit SHA). Defaults to default branch.

        Returns:
            Dictionary with file content and metadata

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                if self.provider == "github":
                    url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
                    params = {"ref": ref} if ref else {}
                else:  # gitlab
                    project_path = f"{owner}%2F{repo}"
                    url = f"{self.api_base}/projects/{project_path}/repository/files/{path}"
                    params = {"ref": ref or "main"}

                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()

                content_data = response.json()
                logger.info(
                    f"Retrieved file {path} from {owner}/{repo} "
                    f"(provider: {self.provider})"
                )

                return content_data

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to get file {path} from {owner}/{repo} "
                f"(provider: {self.provider}): {e}"
            )
            raise

    async def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        per_page: int = 30,
        page: int = 1
    ) -> Dict:
        """
        Search for repositories.

        Args:
            query: Search query string
            sort: Sort order ("stars", "forks", "updated")
            per_page: Number of results per page (max 100)
            page: Page number for pagination

        Returns:
            Dictionary with search results and metadata

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                if self.provider == "github":
                    url = f"{self.api_base}/search/repositories"
                    params = {
                        "q": query,
                        "sort": sort,
                        "per_page": min(per_page, 100),
                        "page": page,
                    }
                else:  # gitlab
                    url = f"{self.api_base}/projects"
                    params = {
                        "search": query,
                        "order_by": sort,
                        "sort": "desc",
                        "per_page": min(per_page, 100),
                        "page": page,
                    }

                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()

                results = response.json()
                logger.info(
                    f"Search for '{query}' on {self.provider} returned results"
                )

                return results

        except httpx.HTTPError as e:
            logger.error(f"Failed to search repositories on {self.provider}: {e}")
            raise
