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
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

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
    # AppContainer requires the Windows SDK helpers; for now we detect
    # via WIN_SDK env var or known Microsoft toolchain paths. This is a
    # skeleton — concrete process spawn wiring lands later.
    sdk_root = env.get("WindowsSdkDir") or env.get("WIN_SDK")
    if sdk_root:
        return SandboxBackendInfo(
            backend=SandboxBackend.APPCONTAINER,
            platform="win32",
            available=True,
            reason=(f"Windows AppContainer available via Windows SDK at {sdk_root}."),
        )
    return SandboxBackendInfo(
        backend=SandboxBackend.APPCONTAINER,
        platform="win32",
        available=False,
        reason=(
            "Windows AppContainer requires the Windows SDK; set "
            "WindowsSdkDir or WIN_SDK to enable it."
        ),
    )


def describe_sandbox_backend(
    env: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
) -> SandboxBackendInfo:
    """Return the sandbox backend description for the current host.

    ``platform`` and ``env`` are optional for testability; in normal
    use the helper reads ``sys.platform`` and ``os.environ``.
    """
    env_map = os.environ if env is None else env
    host = platform if platform is not None else sys.platform

    # Apply the env-var override exactly once. We allow operators to
    # force the backend off (for incident response) but never to force
    # it on without a real OS backend on PATH — that would risk pretending
    # to sandbox shell while running unconstrained.
    override = env_map.get(SANDBOX_ENV, "").strip().lower()
    forced_off = override in _FALSY

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
