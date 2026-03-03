"""
OAuth configuration for Git providers (GitHub, GitLab)

Uses Authlib for OAuth 2.0 authentication with GitHub and GitLab.
"""

from authlib.integrations.starlette_client import OAuth

from core.config import settings

# Initialize OAuth registry
oauth = OAuth()


def configure_oauth():
    """
    Configure OAuth clients for GitHub and GitLab

    Registers OAuth providers with Authlib. Call this during app startup.
    """
    # GitHub OAuth configuration
    if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
        oauth.register(
            name="github",
            client_id=settings.GITHUB_CLIENT_ID,
            client_secret=settings.GITHUB_CLIENT_SECRET,
            access_token_url="https://github.com/login/oauth/access_token",
            access_token_params=None,
            authorize_url="https://github.com/login/oauth/authorize",
            authorize_params=None,
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": "repo user:email"},
        )

    # GitLab OAuth configuration
    if settings.GITLAB_CLIENT_ID and settings.GITLAB_CLIENT_SECRET:
        oauth.register(
            name="gitlab",
            client_id=settings.GITLAB_CLIENT_ID,
            client_secret=settings.GITLAB_CLIENT_SECRET,
            access_token_url="https://gitlab.com/oauth/token",
            access_token_params=None,
            authorize_url="https://gitlab.com/oauth/authorize",
            authorize_params=None,
            api_base_url="https://gitlab.com/api/v4/",
            client_kwargs={
                "scope": "read_api read_user read_repository write_repository"
            },
        )


# Call configuration on import (will be executed when module is loaded)
configure_oauth()
