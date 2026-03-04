"""
Git OAuth API routes

Provides endpoints for GitHub and GitLab OAuth authentication to access user repositories.
"""

import logging
import secrets

from core.config import settings
from core.oauth import oauth
from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)

# Create router for git OAuth endpoints
router = APIRouter(prefix="/api/git", tags=["git-oauth"])


@router.get("/github/authorize")
async def github_authorize(request: Request):
    """
    Initiate GitHub OAuth authorization flow.

    Redirects the user to GitHub's OAuth authorization page where they can
    grant access to their repositories.

    Returns:
        RedirectResponse: 302 redirect to GitHub OAuth page

    Raises:
        HTTPException: 503 if GitHub OAuth is not configured

    Example:
        ```bash
        # Browser redirect
        curl -L http://localhost:8000/api/git/github/authorize
        # Redirects to: https://github.com/login/oauth/authorize?client_id=...
        ```
    """
    # Check if GitHub OAuth is configured
    if not hasattr(oauth, "github") or oauth.github is None:
        logger.error(
            "GitHub OAuth not configured - missing GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.",
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session (in production, use Redis or database)
    # For now, we'll pass it through the OAuth flow
    request.session["oauth_state"] = state

    # Build redirect URI for GitHub callback
    redirect_uri = (
        f"{settings.OAUTH_REDIRECT_URI.rsplit('/callback', 1)[0]}/github/callback"
    )

    # Redirect to GitHub OAuth authorization page
    return await oauth.github.authorize_redirect(request, redirect_uri, state=state)


@router.get("/github/callback")
async def github_callback(request: Request):
    """
    Handle GitHub OAuth callback.

    GitHub redirects here after user authorizes the application. This endpoint
    exchanges the authorization code for an access token.

    Args:
        request: FastAPI request object containing OAuth code and state

    Returns:
        Dictionary with access token and user information

    Raises:
        HTTPException: 400 if state validation fails or token exchange fails
        HTTPException: 503 if GitHub OAuth is not configured

    Example:
        ```bash
        # Called by GitHub after authorization (automatic)
        # GET /api/git/github/callback?code=abc123&state=xyz789
        ```
    """
    # Check if GitHub OAuth is configured
    if not hasattr(oauth, "github") or oauth.github is None:
        logger.error("GitHub OAuth not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured",
        )

    try:
        # Verify state token for CSRF protection
        state = request.query_params.get("state")
        stored_state = request.session.get("oauth_state")

        if not state or state != stored_state:
            logger.error("OAuth state mismatch - possible CSRF attack")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter",
            )

        # Exchange authorization code for access token
        token = await oauth.github.authorize_access_token(request)

        # Get user information from GitHub
        resp = await oauth.github.get("user", token=token)
        user_info = resp.json()

        # Clear the state from session
        request.session.pop("oauth_state", None)

        logger.info(f"GitHub OAuth successful for user: {user_info.get('login')}")

        # TODO: Store token in database associated with user
        # For now, return the token and user info
        return {
            "status": "success",
            "provider": "github",
            "access_token": token.get("access_token"),
            "user": {
                "id": user_info.get("id"),
                "login": user_info.get("login"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
            },
        }

    except Exception as e:
        logger.error(f"GitHub OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth authentication failed",
        )


@router.get("/gitlab/authorize")
async def gitlab_authorize(request: Request):
    """
    Initiate GitLab OAuth authorization flow.

    Redirects the user to GitLab's OAuth authorization page where they can
    grant access to their repositories.

    Returns:
        RedirectResponse: 302 redirect to GitLab OAuth page

    Raises:
        HTTPException: 503 if GitLab OAuth is not configured

    Example:
        ```bash
        # Browser redirect
        curl -L http://localhost:8000/api/git/gitlab/authorize
        # Redirects to: https://gitlab.com/oauth/authorize?client_id=...
        ```
    """
    # Check if GitLab OAuth is configured
    if not hasattr(oauth, "gitlab") or oauth.gitlab is None:
        logger.error(
            "GitLab OAuth not configured - missing GITLAB_CLIENT_ID or GITLAB_CLIENT_SECRET"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitLab OAuth is not configured. Please set GITLAB_CLIENT_ID and GITLAB_CLIENT_SECRET.",
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session
    request.session["oauth_state"] = state

    # Build redirect URI for GitLab callback
    redirect_uri = (
        f"{settings.OAUTH_REDIRECT_URI.rsplit('/callback', 1)[0]}/gitlab/callback"
    )

    # Redirect to GitLab OAuth authorization page
    return await oauth.gitlab.authorize_redirect(request, redirect_uri, state=state)


@router.get("/gitlab/callback")
async def gitlab_callback(request: Request):
    """
    Handle GitLab OAuth callback.

    GitLab redirects here after user authorizes the application. This endpoint
    exchanges the authorization code for an access token.

    Args:
        request: FastAPI request object containing OAuth code and state

    Returns:
        Dictionary with access token and user information

    Raises:
        HTTPException: 400 if state validation fails or token exchange fails
        HTTPException: 503 if GitLab OAuth is not configured

    Example:
        ```bash
        # Called by GitLab after authorization (automatic)
        # GET /api/git/gitlab/callback?code=abc123&state=xyz789
        ```
    """
    # Check if GitLab OAuth is configured
    if not hasattr(oauth, "gitlab") or oauth.gitlab is None:
        logger.error("GitLab OAuth not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitLab OAuth is not configured",
        )

    try:
        # Verify state token for CSRF protection
        state = request.query_params.get("state")
        stored_state = request.session.get("oauth_state")

        if not state or state != stored_state:
            logger.error("OAuth state mismatch - possible CSRF attack")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter",
            )

        # Exchange authorization code for access token
        token = await oauth.gitlab.authorize_access_token(request)

        # Get user information from GitLab
        resp = await oauth.gitlab.get("user", token=token)
        user_info = resp.json()

        # Clear the state from session
        request.session.pop("oauth_state", None)

        logger.info(f"GitLab OAuth successful for user: {user_info.get('username')}")

        # TODO: Store token in database associated with user
        # For now, return the token and user info
        return {
            "status": "success",
            "provider": "gitlab",
            "access_token": token.get("access_token"),
            "user": {
                "id": user_info.get("id"),
                "username": user_info.get("username"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
            },
        }

    except Exception as e:
        logger.error(f"GitLab OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth authentication failed",
        )


@router.get("/status")
async def git_oauth_status():
    """
    Get Git OAuth system status (no auth required).

    Returns information about available OAuth providers and their configuration status.

    Returns:
        Dictionary with OAuth system status
    """
    # Check if OAuth providers are configured
    github_configured = hasattr(oauth, "github") and oauth.github is not None
    gitlab_configured = hasattr(oauth, "gitlab") and oauth.gitlab is not None

    return {
        "status": "ok",
        "providers": {
            "github": {"configured": github_configured, "available": github_configured},
            "gitlab": {"configured": gitlab_configured, "available": gitlab_configured},
        },
        "message": "Git OAuth system is operational",
    }
