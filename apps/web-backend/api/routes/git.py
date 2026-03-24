"""
Git OAuth API routes

Provides endpoints for GitHub and GitLab OAuth authentication to access user repositories.
"""

import logging
import secrets
from urllib.parse import ParseResult, urlparse

from core.config import settings
from core.oauth import oauth
from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)

# Create router for git OAuth endpoints
router = APIRouter(prefix="/api/git", tags=["git-oauth"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require_oauth_provider(provider_name: str, provider_obj) -> None:
    """Raise HTTP 503 if the named OAuth provider is not configured.

    Args:
        provider_name: Human-readable provider name ("GitHub" or "GitLab").
        provider_obj: The provider object from the OAuth registry (may be None).

    Raises:
        HTTPException: 503 if the provider object is None.
    """
    if provider_obj is None:
        logger.error(
            "%s OAuth not configured - check CLIENT_ID / CLIENT_SECRET env vars",
            provider_name,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider_name} OAuth is not configured.",
        )


async def _initiate_oauth_authorize(
    request: Request, provider, provider_name: str, redirect_uri: str
):
    """Generate a CSRF state token, store it in the session, and redirect to the
    provider's authorization page.

    Args:
        request: FastAPI request object.
        provider: Authlib OAuth client for the provider.
        provider_name: Human-readable provider name (used only for logging).
        redirect_uri: Callback URI to pass to the provider.

    Returns:
        RedirectResponse to the provider's OAuth authorization page.
    """
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    logger.debug("Initiating %s OAuth flow", provider_name)
    return await provider.authorize_redirect(request, redirect_uri, state=state)


async def _handle_oauth_callback(
    request: Request,
    provider,
    provider_name: str,
    user_id_key: str,
) -> dict:
    """Validate the CSRF state, exchange the authorization code for a token,
    and return a sanitized response dict.

    The raw OAuth access token is *not* returned to the caller; instead only a
    masked placeholder is included so that downstream consumers know that
    authentication succeeded without receiving the secret credential.

    Args:
        request: FastAPI request object.
        provider: Authlib OAuth client for the provider.
        provider_name: Human-readable provider name.
        user_id_key: Key used for the primary identifier in the provider's user
            response (e.g. ``"login"`` for GitHub, ``"username"`` for GitLab).

    Returns:
        Dict with ``status``, ``provider``, ``token_type``, and ``user`` keys.

    Raises:
        HTTPException: 400 if the state token is missing/mismatched or if the
            token exchange fails.
    """
    # Verify CSRF state
    state = request.query_params.get("state")
    stored_state = request.session.get("oauth_state")

    if not state or state != stored_state:
        logger.error("OAuth state mismatch - possible CSRF attack")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    # Exchange authorization code for access token
    token = await provider.authorize_access_token(request)

    # Fetch the authenticated user's profile
    resp = await provider.get("user", token=token)
    user_info = resp.json()

    # Clear the one-time CSRF state from the session
    request.session.pop("oauth_state", None)

    user_identifier = user_info.get(user_id_key)
    logger.info("%s OAuth successful for user: %s", provider_name, user_identifier)

    # Return a response that confirms success but does NOT expose the raw
    # OAuth access token.  Callers that need to make provider API calls should
    # store the token server-side (database / encrypted session) and retrieve
    # it from there.
    return {
        "status": "success",
        "provider": provider_name.lower(),
        "token_type": token.get("token_type", "bearer"),
        "user": {
            "id": user_info.get("id"),
            user_id_key: user_identifier,
            "email": user_info.get("email"),
            "name": user_info.get("name"),
        },
    }


def _build_callback_uri(provider_slug: str) -> str:
    """Derive the callback URI for *provider_slug* from the configured base URI.

    Uses ``urllib.parse`` for robust URI construction rather than fragile
    string splitting.

    Args:
        provider_slug: Lower-case provider identifier, e.g. ``"github"``.

    Returns:
        Absolute callback URI string.

    Example:
        If ``OAUTH_REDIRECT_URI`` is ``"http://host/api/git/callback"`` and
        ``provider_slug`` is ``"github"`` the result is
        ``"http://host/api/git/github/callback"``.
    """
    parsed: ParseResult = urlparse(settings.OAUTH_REDIRECT_URI)
    # Strip the trailing "/callback" segment (or the last path component) to
    # obtain the common base path, then append the provider-specific suffix.
    base_path = parsed.path.rstrip("/")
    if base_path.endswith("/callback"):
        base_path = base_path[: -len("/callback")]
    new_path = f"{base_path}/{provider_slug}/callback"
    return parsed._replace(path=new_path).geturl()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


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
    provider = getattr(oauth, "github", None)
    _require_oauth_provider("GitHub", provider)
    return await _initiate_oauth_authorize(
        request, provider, "GitHub", _build_callback_uri("github")
    )


@router.get("/github/callback")
async def github_callback(request: Request):
    """
    Handle GitHub OAuth callback.

    GitHub redirects here after user authorizes the application. This endpoint
    exchanges the authorization code for an access token.

    Args:
        request: FastAPI request object containing OAuth code and state

    Returns:
        Dictionary with authentication status and user information

    Raises:
        HTTPException: 400 if state validation fails or token exchange fails
        HTTPException: 503 if GitHub OAuth is not configured

    Example:
        ```bash
        # Called by GitHub after authorization (automatic)
        # GET /api/git/github/callback?code=abc123&state=xyz789
        ```
    """
    provider = getattr(oauth, "github", None)
    _require_oauth_provider("GitHub", provider)

    try:
        return await _handle_oauth_callback(request, provider, "GitHub", "login")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("GitHub OAuth callback error: %s", e, exc_info=True)
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
    provider = getattr(oauth, "gitlab", None)
    _require_oauth_provider("GitLab", provider)
    return await _initiate_oauth_authorize(
        request, provider, "GitLab", _build_callback_uri("gitlab")
    )


@router.get("/gitlab/callback")
async def gitlab_callback(request: Request):
    """
    Handle GitLab OAuth callback.

    GitLab redirects here after user authorizes the application. This endpoint
    exchanges the authorization code for an access token.

    Args:
        request: FastAPI request object containing OAuth code and state

    Returns:
        Dictionary with authentication status and user information

    Raises:
        HTTPException: 400 if state validation fails or token exchange fails
        HTTPException: 503 if GitLab OAuth is not configured

    Example:
        ```bash
        # Called by GitLab after authorization (automatic)
        # GET /api/git/gitlab/callback?code=abc123&state=xyz789
        ```
    """
    provider = getattr(oauth, "gitlab", None)
    _require_oauth_provider("GitLab", provider)

    try:
        return await _handle_oauth_callback(request, provider, "GitLab", "username")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("GitLab OAuth callback error: %s", e, exc_info=True)
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
