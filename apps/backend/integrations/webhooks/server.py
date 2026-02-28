"""
FastAPI Webhook Server
======================

Provides a FastAPI server for receiving incoming webhooks from external services.
Handles authentication, signature verification, and routing to appropriate handlers.

Design:
- Factory function `create_webhook_server()` creates configured FastAPI app
- Incoming webhook endpoints at /webhooks/{webhook_path}
- Authentication via API keys, bearer tokens, basic auth, or HMAC signatures
- Automatic request logging to webhook storage
- Graceful error handling with detailed responses

Usage:
    >>> from integrations.webhooks.server import create_webhook_server
    >>> app = create_webhook_server(spec_dir=Path("/path/to/spec"))
    >>> # Run with uvicorn: uvicorn app:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import (
    extract_signature_from_header,
    verify_api_key,
    verify_basic_auth,
    verify_bearer_token,
    verify_webhook_signature,
)
from .handlers.outgoing import OutgoingWebhookSender
from .models import (
    WebhookConfig,
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookEventType,
    WebhookLog,
    WebhookType,
)
from .storage import WebhookStorage

logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================


class WebhookRequestBody(BaseModel):
    """Incoming webhook request body. Any JSON data from webhook sender."""


class WebhookResponse(BaseModel):
    """Response for webhook deliveries."""

    success: bool = Field(description="Whether webhook was processed successfully")
    webhook_id: str = Field(description="ID of webhook config that handled this")
    log_id: str = Field(description="ID of log entry for this delivery")
    message: str = Field(default="Webhook received", description="Response message")


class ErrorResponse(BaseModel):
    """Error response for webhook failures."""

    error: str = Field(description="Error type")
    message: str = Field(description="Human-readable error message")
    detail: str | None = Field(default=None, description="Detailed error info")


class TestConnectionRequest(BaseModel):
    """Request to test a webhook connection."""

    webhook_id: str = Field(description="ID of webhook to test")
    project_dir: str = Field(description="Project directory containing webhook config")


class TestConnectionResponse(BaseModel):
    """Response from webhook connection test."""

    success: bool = Field(description="Whether test webhook was sent successfully")
    message: str = Field(description="Human-readable result message")
    log_entry: dict | None = Field(
        default=None, description="Webhook log entry if sent"
    )


# =============================================================================
# Webhook Handler Type
# =============================================================================


WebhookHandler = Callable[[WebhookConfig, dict], None]


# =============================================================================
# Server Factory
# =============================================================================


def _make_lifespan(spec_dir: Path):
    """Create a lifespan context manager for the given spec directory."""

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """
        Lifespan context manager for FastAPI app.

        Handles startup and shutdown events for the webhook server.

        Args:
            app: The FastAPI application instance

        Yields:
            None
        """
        # Startup
        logger.info(f"Starting webhook server for spec dir: {spec_dir}")
        storage = WebhookStorage(spec_dir=spec_dir)
        configs = storage.load_configs()

        incoming_count = sum(
            1 for cfg in configs if cfg.type == WebhookType.INCOMING and cfg.enabled
        )
        outgoing_count = sum(
            1 for cfg in configs if cfg.type == WebhookType.OUTGOING and cfg.enabled
        )

        logger.info(
            f"Loaded {len(configs)} webhook configs "
            f"({incoming_count} incoming enabled, {outgoing_count} outgoing enabled)"
        )

        yield

        # Shutdown
        logger.info("Shutting down webhook server")

    return _lifespan


def create_webhook_server(
    spec_dir: Path,
    custom_handler: WebhookHandler | None = None,
) -> FastAPI:
    """
    Create a FastAPI application for handling webhooks.

    This factory function creates a configured FastAPI app with endpoints
    for receiving incoming webhooks. The app automatically loads webhook
    configurations from the spec directory and handles authentication.

    Args:
        spec_dir: Directory containing webhook configuration files
        custom_handler: Optional custom handler for processing webhook payloads.
                       If None, webhooks are logged but no action is taken.

    Returns:
        Configured FastAPI application

    Examples:
        >>> from pathlib import Path
        >>> spec_dir = Path("/path/to/spec")
        >>> app = create_webhook_server(spec_dir)
        >>> # Run with: uvicorn app:app --host 0.0.0.0 --port 8080
    """
    # Create storage instance
    storage = WebhookStorage(spec_dir=spec_dir)

    # Create FastAPI app with lifespan
    app = FastAPI(
        title="Auto Claude Webhook Server",
        description="Receive and process webhooks from external services",
        version="1.0.0",
        lifespan=_make_lifespan(spec_dir),
    )

    # =============================================================================
    # Health Check Endpoint
    # =============================================================================

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """
        Health check endpoint.

        Returns server status and webhook configuration count.
        """
        configs = storage.load_configs()
        enabled_count = sum(1 for cfg in configs if cfg.enabled)

        return {
            "status": "healthy",
            "webhooks_configured": len(configs),
            "webhooks_enabled": enabled_count,
        }

    # =============================================================================
    # Incoming Webhook Endpoint
    # =============================================================================

    @app.post("/webhooks/{webhook_path:path}", tags=["webhooks"])
    async def receive_webhook(
        webhook_path: str,
        request: Request,
    ) -> JSONResponse:
        """
        Receive and process an incoming webhook.

        This endpoint handles incoming webhooks from external services like
        GitHub, GitLab, or custom webhook senders. It authenticates the request
        using the webhook's configured authentication method, logs the delivery,
        and optionally triggers a custom handler.

        Path Parameters:
            webhook_path: Path component of the webhook URL (matches webhook config)

        Headers:
            X-Webhook-API-Key: API key for authentication (if configured)
            Authorization: Bearer token or Basic auth (if configured)
            X-Hub-Signature-256: HMAC signature for payload verification (if configured)

        Request Body:
            JSON payload from webhook sender

        Returns:
            JSONResponse with delivery status

        Raises:
            HTTPException: If authentication fails or webhook not found
        """
        # Load webhook configs
        configs = storage.load_configs()

        # Find matching webhook config
        webhook_config: WebhookConfig | None = None
        for cfg in configs:
            if cfg.type == WebhookType.INCOMING and cfg.path == f"/{webhook_path}":
                webhook_config = cfg
                break

        if not webhook_config:
            logger.warning("No webhook config found for the requested path")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No webhook configured for the requested path",
            )

        # Check if webhook is enabled
        if not webhook_config.enabled:
            logger.warning(f"Webhook {webhook_config.id} is disabled")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Webhook {webhook_config.id} is disabled",
            )

        # Determine event type from headers or payload, not from config
        # GitHub uses X-GitHub-Event header, GitLab uses X-Gitlab-Event, etc.
        github_event = request.headers.get("X-GitHub-Event")
        gitlab_event = request.headers.get("X-Gitlab-Event")
        if github_event:
            event_type_str = f"github_{github_event}"
        elif gitlab_event:
            event_type_str = f"gitlab_{gitlab_event}"
        else:
            event_type_str = "custom"

        # Map to WebhookEventType, falling back to CUSTOM
        try:
            resolved_event_type = WebhookEventType(event_type_str)
        except ValueError:
            resolved_event_type = WebhookEventType.CUSTOM

        # Create log entry
        log_id = str(uuid.uuid4())
        webhook_log = WebhookLog(
            id=log_id,
            webhook_id=webhook_config.id,
            event_type=resolved_event_type,
            request_method="POST",
            request_url=str(request.url),
        )

        # Get raw body for signature verification
        raw_body = await request.body()

        # Authenticate request
        auth_success = await _authenticate_request(
            request=request,
            webhook_config=webhook_config,
            raw_body=raw_body,
        )

        if not auth_success:
            webhook_log.mark_completed(
                status=WebhookDeliveryStatus.FAILED,
                error_message="Authentication failed",
            )
            storage.save_log(webhook_log)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook authentication failed",
            )

        # Parse request body
        try:
            payload = await request.json()
            webhook_log.request_body = payload
        except Exception:
            webhook_log.mark_completed(
                status=WebhookDeliveryStatus.FAILED,
                error_message="Failed to parse JSON payload",
            )
            storage.save_log(webhook_log)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

        # Log headers (sanitized)
        webhook_log.request_headers = _sanitize_headers(dict(request.headers))

        # Process webhook
        try:
            # Call custom handler if provided (handle both sync and async)
            if custom_handler:
                if inspect.iscoroutinefunction(custom_handler):
                    await custom_handler(webhook_config, payload)
                else:
                    await asyncio.to_thread(custom_handler, webhook_config, payload)

            # Mark as successful
            webhook_log.mark_completed(
                status=WebhookDeliveryStatus.SUCCESS,
                status_code=200,
            )
            storage.save_log(webhook_log)

            logger.info(
                f"Webhook {webhook_config.id} processed successfully (log ID: {log_id})"
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "webhook_id": webhook_config.id,
                    "log_id": log_id,
                    "message": "Webhook received",
                },
            )

        except Exception as e:
            logger.error(f"Error processing webhook {webhook_config.id}: {e}")

            webhook_log.mark_completed(
                status=WebhookDeliveryStatus.FAILED,
                error_message=str(e),
            )
            storage.save_log(webhook_log)

            # Return success to sender (webhooks are async/fire-and-forget)
            # but log the error for debugging
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "success": False,
                    "webhook_id": webhook_config.id,
                    "log_id": log_id,
                    "message": "Webhook received but processing failed",
                },
            )

    # =============================================================================
    # Test Webhook Connection Endpoint
    # =============================================================================

    @app.post("/api/webhooks/test", tags=["webhooks"])
    async def test_webhook_connection(
        request: TestConnectionRequest,
        raw_request: Request,
    ) -> JSONResponse:
        """
        Test a webhook connection by sending a test event.

        This endpoint is restricted to localhost callers only and is used
        by the frontend UI to test webhook configurations before enabling them.

        Args:
            request: TestConnectionRequest with webhook_id and project_dir
            raw_request: FastAPI request for client host verification

        Returns:
            JSONResponse with test result

        Raises:
            HTTPException: If unauthorized, webhook not found, or send fails
        """
        # Restrict to localhost only
        client_host = raw_request.client.host if raw_request.client else None
        if client_host not in ("127.0.0.1", "::1", "localhost"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint is only accessible from localhost",
            )

        try:
            # Validate project_dir to prevent path traversal attacks
            raw_project_dir = request.project_dir

            # Treat project_dir as a path relative to the configured spec_dir root.
            # This prevents directory traversal and absolute-path abuse.
            base_root = spec_dir if isinstance(spec_dir, Path) else Path(spec_dir)
            candidate_dir = (base_root / raw_project_dir).resolve()
            try:
                # Ensure the resolved path is within the allowed root
                candidate_dir.relative_to(base_root)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid project directory",
                )

            project_dir = candidate_dir
            if not project_dir.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid project directory",
                )
            # Restrict to directories containing .auto-claude marker
            auto_claude_marker = project_dir / ".auto-claude"
            if not auto_claude_marker.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid project directory",
                )
            test_storage = WebhookStorage(spec_dir=project_dir)

            config = test_storage.get_config(request.webhook_id)
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Webhook not found",
                )

            # Create test event
            test_event = WebhookEvent(
                type=WebhookEventType.CUSTOM,
                data={
                    "test": True,
                    "message": "This is a test webhook notification from Auto Claude",
                },
            )

            # Send test webhook (temporarily enable if disabled for testing)
            original_enabled = config.enabled
            config.enabled = True
            sender = OutgoingWebhookSender(spec_dir=project_dir)
            try:
                result = await sender.send_webhook(config, test_event)
            finally:
                config.enabled = original_enabled
                await sender.close()

            if result.success:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "success": True,
                        "message": "Test notification sent successfully",
                        "log_entry": result.log_entry.to_dict()
                        if result.log_entry
                        else None,
                    },
                )
            else:
                # Return success=true for IPC but webhook failed
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "success": False,
                        "message": result.log_entry.error_message
                        if result.log_entry
                        else "Webhook test failed",
                        "log_entry": result.log_entry.to_dict()
                        if result.log_entry
                        else None,
                    },
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error testing webhook connection: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred while testing the webhook",
            )

    # =============================================================================
    # List Webhooks Endpoint (Admin)
    # =============================================================================

    @app.get("/webhooks", tags=["admin"])
    async def list_webhooks(request: Request) -> dict[str, list[dict]]:
        """
        List all configured webhooks (admin endpoint).

        Restricted to localhost connections only.
        Returns metadata about configured webhooks without exposing
        sensitive credentials.
        """
        # Restrict admin endpoint to localhost
        client_host = request.client.host if request.client else None
        if client_host not in ("127.0.0.1", "::1", "localhost"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin endpoints are only accessible from localhost",
            )

        configs = storage.load_configs()

        # Sanitize configs (remove secrets)
        sanitized_configs = []
        for cfg in configs:
            sanitized = cfg.to_dict()
            # Remove sensitive auth data
            if "auth" in sanitized:
                auth = sanitized["auth"]
                auth["api_key"] = "***" if auth.get("api_key") else None
                auth["password"] = "***" if auth.get("password") else None
                auth["secret"] = "***" if auth.get("secret") else None
            sanitized_configs.append(sanitized)

        return {"webhooks": sanitized_configs}

    # =============================================================================
    # Error Handlers
    # =============================================================================

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions with JSON responses."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )

    return app


# =============================================================================
# Helper Functions
# =============================================================================


async def _authenticate_request(
    request: Request,
    webhook_config: WebhookConfig,
    raw_body: bytes,
) -> bool:
    """
    Authenticate an incoming webhook request.

    Checks authentication based on the webhook's auth configuration:
    - none: No authentication (not recommended)
    - api_key: X-Webhook-API-Key header
    - bearer_token: Authorization: Bearer <token> header
    - basic_auth: Authorization: Basic <credentials> header
    - signature: HMAC signature in X-Hub-Signature-256 header

    Args:
        request: FastAPI request object
        webhook_config: Webhook configuration with auth settings
        raw_body: Raw request body bytes (for signature verification)

    Returns:
        True if authentication succeeds, False otherwise
    """
    auth_config = webhook_config.auth

    # No authentication
    if auth_config.auth_type == "none":
        logger.debug(f"Webhook {webhook_config.id} has no authentication")
        return True

    # API key authentication
    elif auth_config.auth_type == "api_key":
        header_name = auth_config.api_key_header or "X-Webhook-API-Key"
        api_key = request.headers.get(header_name)
        if verify_api_key(api_key, webhook_config):
            logger.debug(f"Webhook {webhook_config.id} authenticated via API key")
            return True
        return False

    # Bearer token authentication
    elif auth_config.auth_type == "bearer_token":
        auth_header = request.headers.get("Authorization")
        if verify_bearer_token(auth_header, webhook_config):
            logger.debug(f"Webhook {webhook_config.id} authenticated via bearer token")
            return True
        return False

    # Basic authentication
    elif auth_config.auth_type == "basic_auth":
        auth_header = request.headers.get("Authorization")
        if verify_basic_auth(auth_header, webhook_config):
            logger.debug(f"Webhook {webhook_config.id} authenticated via basic auth")
            return True
        return False

    # HMAC signature verification
    elif auth_config.auth_type == "signature":
        if not auth_config.secret:
            logger.warning(
                f"Webhook {webhook_config.id} has signature auth but no secret"
            )
            return False

        # Get signature header
        signature_header = auth_config.signature_header or "X-Hub-Signature-256"
        signature = request.headers.get(signature_header)

        if not signature:
            logger.debug(f"Missing {signature_header} header")
            return False

        # Extract and verify signature
        signature_value = extract_signature_from_header(signature)
        if verify_webhook_signature(
            payload=raw_body,
            signature=signature_value,
            secret=auth_config.secret,
            algorithm=auth_config.signature_algorithm,
            signature_header=signature_header,
        ):
            logger.debug(f"Webhook {webhook_config.id} authenticated via signature")
            return True

        return False

    # Unknown auth type
    else:
        logger.warning(f"Unknown auth type: {auth_config.auth_type}")
        return False


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """
    Sanitize HTTP headers for logging.

    Removes or masks sensitive header values like Authorization
    or API keys to prevent credentials from appearing in logs.

    Args:
        headers: Raw request headers

    Returns:
        Sanitized headers dictionary
    """
    sanitized = {}
    sensitive_headers = {
        "authorization",
        "x-api-key",
        "x-webhook-api-key",
        "x-hub-signature",
        "x-hub-signature-256",
    }

    for key, value in headers.items():
        if key.lower() in sensitive_headers:
            sanitized[key] = "***"
        else:
            sanitized[key] = value

    return sanitized
