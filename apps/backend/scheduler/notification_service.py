"""
Notification Service - Build Event Notifications
================================================

Provides desktop and webhook notifications for scheduled build events.
Supports platform-specific desktop notifications and HTTP webhooks.

Design Principles:
- Graceful degradation if notification unavailable
- Platform-specific desktop notifications (Windows/macOS/Linux)
- Webhook support for external integrations
- Non-blocking async notifications

Notification Types:
- Desktop: Native OS notifications (toast/notify-send/osascript)
- Webhook: HTTP POST to configured URL
"""

import asyncio
import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

from core.platform import is_linux, is_macos, is_windows


class NotificationType(str, Enum):
    """Types of notification channels."""

    DESKTOP = "desktop"
    WEBHOOK = "webhook"


class BuildEvent(str, Enum):
    """Build lifecycle events for notifications."""

    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"
    BUILD_RETRYING = "build_retrying"
    BUILD_CANCELLED = "build_cancelled"


# Environment variables
DESKTOP_NOTIFICATIONS_ENABLED = "SCHEDULER_DESKTOP_NOTIFICATIONS"
WEBHOOK_URL = "SCHEDULER_WEBHOOK_URL"
WEBHOOK_ENABLED = "SCHEDULER_WEBHOOK_ENABLED"


@dataclass
class NotificationConfig:
    """Configuration for build notifications."""

    enabled: bool = True
    desktop_enabled: bool = False
    webhook_enabled: bool = False
    webhook_url: str | None = None
    webhook_headers: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "enabled": self.enabled,
            "desktop_enabled": self.desktop_enabled,
            "webhook_enabled": self.webhook_enabled,
            "webhook_url": self.webhook_url,
            "webhook_headers": self.webhook_headers,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NotificationConfig":
        """Create NotificationConfig from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            desktop_enabled=data.get("desktop_enabled", False),
            webhook_enabled=data.get("webhook_enabled", False),
            webhook_url=data.get("webhook_url"),
            webhook_headers=data.get("webhook_headers"),
        )

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        """Create NotificationConfig from environment variables."""
        desktop = os.environ.get(DESKTOP_NOTIFICATIONS_ENABLED, "").lower() in (
            "1",
            "true",
            "yes",
        )

        webhook_url = os.environ.get(WEBHOOK_URL, "")
        webhook = webhook_url and os.environ.get(WEBHOOK_ENABLED, "").lower() in (
            "1",
            "true",
            "yes",
        )

        return cls(
            enabled=desktop or webhook,
            desktop_enabled=desktop,
            webhook_enabled=webhook,
            webhook_url=webhook_url if webhook else None,
        )

    @classmethod
    def from_build_config(cls, config: dict[str, Any]) -> "NotificationConfig":
        """
        Create NotificationConfig from a build's notification_config dict.

        Merges environment defaults with build-specific settings.
        """
        env_config = cls.from_env()

        # Build-specific settings override environment
        desktop = config.get("desktop_enabled", env_config.desktop_enabled)

        webhook_url = config.get("webhook_url") or env_config.webhook_url
        webhook_enabled = config.get("webhook_enabled", env_config.webhook_enabled)

        return cls(
            enabled=desktop or (webhook_enabled and webhook_url),
            desktop_enabled=desktop,
            webhook_enabled=webhook_enabled and bool(webhook_url),
            webhook_url=webhook_url,
            webhook_headers=config.get("webhook_headers"),
        )


class NotificationService:
    """
    Service for sending build event notifications.

    Provides unified interface for desktop and webhook notifications.
    Gracefully handles failures and unavailable notification channels.

    Example:
        # Use environment configuration
        service = NotificationService()
        await service.notify_build_started(build)

        # Use custom configuration
        config = NotificationConfig(desktop_enabled=True, webhook_enabled=True, webhook_url="https://...")
        service = NotificationService(config)
        await service.notify_build_completed(build)
    """

    def __init__(self, config: NotificationConfig | None = None):
        """
        Initialize the notification service.

        Args:
            config: Notification configuration (defaults to environment variables)
        """
        self.config = config or NotificationConfig.from_env()

    async def notify(
        self,
        event: BuildEvent,
        build: Any,
    ) -> bool:
        """
        Send notification for a build event.

        Args:
            event: Build event type
            build: ScheduledBuild instance or dict with build data

        Returns:
            True if at least one notification succeeded
        """
        return await send_build_notification(event, build, self.config)

    async def notify_build_started(self, build: Any) -> bool:
        """Send notification when build starts."""
        return await self.notify(BuildEvent.BUILD_STARTED, build)

    async def notify_build_completed(self, build: Any) -> bool:
        """Send notification when build completes successfully."""
        return await self.notify(BuildEvent.BUILD_COMPLETED, build)

    async def notify_build_failed(self, build: Any) -> bool:
        """Send notification when build fails."""
        return await self.notify(BuildEvent.BUILD_FAILED, build)

    async def notify_build_retrying(self, build: Any) -> bool:
        """Send notification when build is being retried."""
        return await self.notify(BuildEvent.BUILD_RETRYING, build)

    async def notify_build_cancelled(self, build: Any) -> bool:
        """Send notification when build is cancelled."""
        return await self.notify(BuildEvent.BUILD_CANCELLED, build)

    def is_enabled(self) -> bool:
        """Check if any notifications are enabled."""
        return self.config.enabled

    def is_desktop_enabled(self) -> bool:
        """Check if desktop notifications are enabled."""
        return self.config.desktop_enabled

    def is_webhook_enabled(self) -> bool:
        """Check if webhook notifications are enabled."""
        return self.config.webhook_enabled


def is_desktop_available() -> bool:
    """Check if desktop notifications are available on this platform."""
    if is_windows():
        # Windows: Check if toast notification is available (Windows 10+)
        try:
            import subprocess  # noqa: F401

            return True
        except Exception:
            return False

    if is_macos():
        # macOS: osascript is always available
        return True

    if is_linux():
        # Linux: Check for notify-send
        try:
            import shutil

            return shutil.which("notify-send") is not None
        except Exception:
            return False

    return False


async def send_desktop_notification(
    title: str,
    message: str,
) -> bool:
    """
    Send a desktop notification.

    Platform-specific implementations:
    - Windows: PowerShell BurntToast or Windows Forms
    - macOS: osascript with display notification
    - Linux: notify-send

    Args:
        title: Notification title
        message: Notification message body

    Returns:
        True if successful, False otherwise
    """
    if not is_desktop_available():
        return False

    try:
        if is_windows():
            # Windows: Use PowerShell to show toast notification
            # Using Windows.Forms which is built into .NET on Windows
            ps_command = f"""
            Add-Type -AssemblyName System.Windows.Forms;
            $balloon = New-Object System.Windows.Forms.NotifyIcon;
            $balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info;
            $balloon.BalloonTipText = '{message}';
            $balloon.BalloonTipTitle = '{title}';
            $balloon.Visible = $true;
            $balloon.ShowBalloonTip(10000);
            """
            proc = await asyncio.create_subprocess_shell(
                f"powershell.exe -Command \"{ps_command}\"",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0

        elif is_macos():
            # macOS: Use osascript
            script = f'display notification "{message}" with title "{title}"'
            proc = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0

        elif is_linux():
            # Linux: Use notify-send
            proc = await asyncio.create_subprocess_exec(
                "notify-send",
                title,
                message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0

    except Exception as e:
        # Silent failure - notifications shouldn't break the build
        pass

    return False


async def send_webhook_notification(
    webhook_url: str,
    event: BuildEvent,
    build_data: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> bool:
    """
    Send a webhook notification for a build event.

    Args:
        webhook_url: URL to send webhook to
        event: Build event type
        build_data: Build information (spec_id, spec_name, status, etc.)
        headers: Optional HTTP headers to include

    Returns:
        True if successful, False otherwise
    """
    if not webhook_url:
        return False

    # Prepare webhook payload
    payload = {
        "event": event.value,
        "timestamp": build_data.get("updated_at"),
        "build": {
            "id": build_data.get("id"),
            "spec_id": build_data.get("spec_id"),
            "spec_name": build_data.get("spec_name"),
            "status": build_data.get("status"),
            "priority": build_data.get("priority"),
            "started_at": build_data.get("started_at"),
            "completed_at": build_data.get("completed_at"),
            "error_message": build_data.get("error_message"),
            "retry_count": build_data.get("retry_count"),
            "duration_seconds": build_data.get("duration_seconds"),
        },
    }

    # Default headers
    default_headers = {
        "Content-Type": "application/json",
        "User-Agent": "Auto-Claude-Scheduler/1.0",
    }

    if headers:
        default_headers.update(headers)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers=default_headers,
            )
            response.raise_for_status()
            return True

    except httpx.HTTPError:
        # Silent failure - webhook errors shouldn't break the build
        pass
    except Exception:
        # Silent failure
        pass

    return False


async def send_build_notification(
    event: BuildEvent,
    build: Any,  # ScheduledBuild object
    config: NotificationConfig | None = None,
) -> bool:
    """
    Send notifications for a build event.

    Sends notifications to all enabled channels (desktop, webhook).

    Args:
        event: Build event type
        build: ScheduledBuild instance
        config: Notification configuration (defaults to env vars)

    Returns:
        True if at least one notification succeeded
    """
    if not config:
        config = NotificationConfig.from_env()

    if not config.enabled:
        return False

    # Build notification message
    title, message = _format_notification_message(event, build)

    # Convert build to dict for webhook
    build_dict = build.to_dict() if hasattr(build, "to_dict") else {}

    # Send to all enabled channels concurrently
    tasks = []

    if config.desktop_enabled:
        tasks.append(send_desktop_notification(title, message))

    if config.webhook_enabled and config.webhook_url:
        tasks.append(
            send_webhook_notification(
                config.webhook_url,
                event,
                build_dict,
                config.webhook_headers,
            )
        )

    if not tasks:
        return False

    # Wait for all notifications (collect results)
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Return True if at least one succeeded
    return any(isinstance(r, bool) and r for r in results)


def _format_notification_message(
    event: BuildEvent,
    build: Any,
) -> tuple[str, str]:
    """
    Format notification title and message for a build event.

    Args:
        event: Build event type
        build: ScheduledBuild instance

    Returns:
        Tuple of (title, message)
    """
    spec_name = getattr(build, "spec_name", "Unknown Build")
    spec_id = getattr(build, "spec_id", "unknown")

    if event == BuildEvent.BUILD_STARTED:
        title = "Build Started"
        message = f"Started building: {spec_name} ({spec_id})"

    elif event == BuildEvent.BUILD_COMPLETED:
        duration = getattr(build, "duration_seconds", None)
        if duration:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = "unknown"

        title = "Build Completed"
        message = f"✓ {spec_name} completed in {duration_str}"

    elif event == BuildEvent.BUILD_FAILED:
        error = getattr(build, "error_message", "Unknown error")
        # Truncate long error messages
        if len(error) > 100:
            error = error[:97] + "..."

        title = "Build Failed"
        message = f"✗ {spec_name} failed: {error}"

    elif event == BuildEvent.BUILD_RETRYING:
        retry_count = getattr(build, "retry_count", 0)
        max_retries = getattr(build, "max_retries", 3)

        title = "Retrying Build"
        message = f"Retrying {spec_name} (attempt {retry_count}/{max_retries})"

    elif event == BuildEvent.BUILD_CANCELLED:
        title = "Build Cancelled"
        message = f"Build cancelled: {spec_name}"

    else:
        title = "Build Event"
        message = f"{spec_name}: {event.value}"

    return title, message


# === Convenience functions for specific build events ===


async def notify_build_started(build: Any, config: NotificationConfig | None = None) -> bool:
    """Send notification when build starts."""
    return await send_build_notification(BuildEvent.BUILD_STARTED, build, config)


async def notify_build_completed(build: Any, config: NotificationConfig | None = None) -> bool:
    """Send notification when build completes successfully."""
    return await send_build_notification(BuildEvent.BUILD_COMPLETED, build, config)


async def notify_build_failed(build: Any, config: NotificationConfig | None = None) -> bool:
    """Send notification when build fails."""
    return await send_build_notification(BuildEvent.BUILD_FAILED, build, config)


async def notify_build_retrying(build: Any, config: NotificationConfig | None = None) -> bool:
    """Send notification when build is being retried."""
    return await send_build_notification(BuildEvent.BUILD_RETRYING, build, config)


async def notify_build_cancelled(build: Any, config: NotificationConfig | None = None) -> bool:
    """Send notification when build is cancelled."""
    return await send_build_notification(BuildEvent.BUILD_CANCELLED, build, config)
