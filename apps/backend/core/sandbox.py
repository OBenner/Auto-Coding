"""Cross-platform sandbox skeleton for direct API providers.

Phase 1.3 of ``docs/roadmap/non-claude-provider-autonomy.md``: today
only the Claude Agent SDK runtime advertises ``sandbox=True`` because
its session ships with an OS-level sandbox. Direct API providers
running through Generic Edit drop straight to the host shell, so
``RuntimeCapabilities.promoted_edit()`` does not claim ``sandbox``.

This module is the first step toward changing that. It exposes a
``SandboxBackend`` enum, a platform detector, and a
``describe_sandbox_backend()`` helper that the autonomy layer consults
before deciding whether to grant the ``sandbox`` capability via
``RuntimePolicy.sandbox_enabled``. The actual command-wrapping work
(Seatbelt profile, bubblewrap arguments, AppContainer SID) is
intentionally not wired into shell execution yet; the policy grant
only flips on when the operator opts in via ``AUTO_CODE_AUTONOMY=safe``
(or higher) AND the platform exposes a real sandbox backend.

Subsequent commits will plug the backend implementations into
``GenericEditRuntimeSession`` shell action execution.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from core.platform import OS, get_current_os

SANDBOX_ENV = "AUTO_CODE_SANDBOX"

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}


class SandboxBackend(StrEnum):
    """Concrete sandbox technology for the current host platform."""

    SEATBELT = "seatbelt"
    BUBBLEWRAP = "bubblewrap"
    APPCONTAINER = "appcontainer"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SandboxBackendInfo:
    """Description of the sandbox backend selected for this host."""

    backend: SandboxBackend
    platform: str
    available: bool
    reason: str
    executable: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe payload for diagnostics."""
        payload = asdict(self)
        payload["backend"] = self.backend.value
        return payload


def _detect_macos_backend() -> SandboxBackendInfo:
    executable = shutil.which("sandbox-exec")
    if executable:
        return SandboxBackendInfo(
            backend=SandboxBackend.SEATBELT,
            platform="darwin",
            available=True,
            reason="macOS Seatbelt available via sandbox-exec.",
            executable=executable,
        )
    return SandboxBackendInfo(
        backend=SandboxBackend.SEATBELT,
        platform="darwin",
        available=False,
        reason="sandbox-exec executable not found on PATH.",
    )


def _detect_linux_backend() -> SandboxBackendInfo:
    executable = shutil.which("bwrap") or shutil.which("bubblewrap")
    if executable:
        return SandboxBackendInfo(
            backend=SandboxBackend.BUBBLEWRAP,
            platform="linux",
            available=True,
            reason="Linux bubblewrap available.",
            executable=executable,
        )
    return SandboxBackendInfo(
        backend=SandboxBackend.BUBBLEWRAP,
        platform="linux",
        available=False,
        reason="bwrap/bubblewrap executable not found on PATH.",
    )


def _detect_windows_backend(env: Mapping[str, str]) -> SandboxBackendInfo:
    # AppContainer requires both the Windows SDK helpers AND the
    # process-spawn wiring (planned for the next step). Until that
    # wiring lands the backend reports ``available=False`` even when
    # the SDK env var is present, so the policy grant cannot pretend to
    # sandbox shell while running unconstrained. Operators who want to
    # try the AppContainer path early can flip
    # ``AUTO_CODE_SANDBOX_WIN_APPCONTAINER_FORCE=true`` knowing the
    # wrapping itself is still a TODO.
    sdk_root = env.get("WindowsSdkDir") or env.get("WIN_SDK")
    force = env.get("AUTO_CODE_SANDBOX_WIN_APPCONTAINER_FORCE", "").strip().lower()
    if sdk_root and force in _TRUTHY:
        return SandboxBackendInfo(
            backend=SandboxBackend.APPCONTAINER,
            platform="win32",
            available=True,
            reason=(
                f"Windows AppContainer force-enabled (SDK at {sdk_root}); "
                "spawn wiring is still experimental."
            ),
        )
    if sdk_root:
        return SandboxBackendInfo(
            backend=SandboxBackend.APPCONTAINER,
            platform="win32",
            available=False,
            reason=(
                f"Windows SDK detected at {sdk_root}, but AppContainer "
                "process-spawn wiring is not yet implemented; set "
                "AUTO_CODE_SANDBOX_WIN_APPCONTAINER_FORCE=true to opt in "
                "to the experimental path."
            ),
        )
    return SandboxBackendInfo(
        backend=SandboxBackend.APPCONTAINER,
        platform="win32",
        available=False,
        reason=(
            "Windows AppContainer requires the Windows SDK and a future "
            "process-spawn implementation; neither WindowsSdkDir nor "
            "WIN_SDK is set."
        ),
    )


def describe_sandbox_backend(
    env: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
) -> SandboxBackendInfo:
    """Return the sandbox backend description for the current host.

    ``platform`` and ``env`` are optional for testability; in normal
    use the helper reads ``os.environ`` and resolves the host via
    :func:`core.platform.get_current_os`. When ``platform`` is given
    (for unit tests), it is matched against the legacy ``sys.platform``
    string family (``darwin``, ``linux*``, ``win32``, ``cygwin``) so
    tests do not need to fabricate :class:`core.platform.OS` instances.
    """
    env_map = os.environ if env is None else env

    # Apply the env-var override exactly once. We allow operators to
    # force the backend off (for incident response) but never to force
    # it on without a real OS backend on PATH — that would risk pretending
    # to sandbox shell while running unconstrained.
    override = env_map.get(SANDBOX_ENV, "").strip().lower()
    forced_off = override in _FALSY

    host = platform if platform is not None else _current_host_token()

    if host == "darwin":
        info = _detect_macos_backend()
    elif host.startswith("linux"):
        info = _detect_linux_backend()
    elif host in {"win32", "cygwin"}:
        info = _detect_windows_backend(env_map)
    else:
        info = SandboxBackendInfo(
            backend=SandboxBackend.UNAVAILABLE,
            platform=host,
            available=False,
            reason=f"No sandbox backend wired for platform '{host}'.",
        )

    if forced_off and info.available:
        return SandboxBackendInfo(
            backend=info.backend,
            platform=info.platform,
            available=False,
            reason=(
                f"{SANDBOX_ENV} explicitly disabled; backend "
                f"{info.backend.value} would have been available."
            ),
            executable=info.executable,
        )
    return info


def sandbox_available(
    env: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
) -> bool:
    """Return whether a real sandbox backend is available on this host."""
    return describe_sandbox_backend(env=env, platform=platform).available


def _current_host_token() -> str:
    """Return a legacy sys.platform-style token for the current host.

    Wraps :func:`core.platform.get_current_os` so the sandbox helper's
    string-based dispatch keeps working unchanged: we still match
    ``darwin``/``linux``/``win32`` even though the canonical detection
    now lives in ``core.platform``.
    """
    os_enum = get_current_os()
    if os_enum is OS.MACOS:
        return "darwin"
    if os_enum is OS.LINUX:
        return "linux"
    if os_enum is OS.WINDOWS:
        return "win32"
    return os_enum.value.lower()
