"""CodeGraph installer: asset resolution, downloader, and install-path helpers.

This module is the user-local installer for the external `codegraph` binary
(https://github.com/colbymchenry/codegraph). It is a Python-only helper: no
shelling out, no curl-pipe-sh.

Install layout (matches the official release tarball)::

    ~/.auto-claude/bin/codegraph/
        v0.9.3/
            node                 (bundled Node.js runtime)
            bin/
                codegraph        (POSIX) or codegraph.exe (Windows)
            lib/
                ...
        v0.9.4/
            ...

The `AUTO_CLAUDE_CODEGRAPH_DIR` env var overrides the root for tests and for
users who want the install somewhere else.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import uuid
import zipfile
from pathlib import Path
from urllib import parse as urllib_parse
from urllib.request import Request, urlopen

from core.platform import is_windows as _platform_is_windows

_BINARY_NAME = "codegraph"
_DEFAULT_DIRNAME = Path(".auto-claude") / "bin" / "codegraph"
_ENV_OVERRIDE = "AUTO_CLAUDE_CODEGRAPH_DIR"
_TAR_GZ_SUFFIX = ".tar.gz"
_TGZ_SUFFIX = ".tgz"
_ZIP_SUFFIX = ".zip"
_TARBALL_SUFFIXES: tuple[str, ...] = (_TAR_GZ_SUFFIX, _TGZ_SUFFIX)
_RELEASE_URL_TEMPLATE = (
    "https://github.com/colbymchenry/codegraph/releases/download/{version}/{asset}"
)
_GITHUB_API_LATEST_TEMPLATE = "https://api.github.com/repos/{repo}/releases/latest"
_DEFAULT_REPO = "colbymchenry/codegraph"
_DOWNLOAD_CHUNK_BYTES = 64 * 1024
_GITHUB_API_USER_AGENT = "auto-claude-codegraph-installer"
_NETWORK_TIMEOUT_SECONDS = 30.0
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_COMPANION_SUFFIX = ".sha256"
_MAX_COMPANION_BYTES = 64 * 1024

_VERSION_DIR_RE = re.compile(r"^v\d+(?:\.\d+){0,3}(?:[-+][\w.]+)?$")

_ARCH_ALIASES: dict[str, str] = {
    "arm64": "arm64",
    "aarch64": "arm64",
    "x64": "x64",
    "x86_64": "x64",
    "amd64": "x64",
}

_OS_ALIASES: dict[str, str] = {
    "darwin": "darwin",
    "macos": "darwin",
    "mac": "darwin",
    "linux": "linux",
    "windows": "win32",
    "win": "win32",
    "win32": "win32",
}

_ASSET_EXTENSION: dict[str, str] = {
    "darwin": _TAR_GZ_SUFFIX.lstrip("."),
    "linux": _TAR_GZ_SUFFIX.lstrip("."),
    "win32": _ZIP_SUFFIX.lstrip("."),
}


_ALLOWED_URL_SCHEMES = frozenset({"https"})


class UnsupportedPlatformError(RuntimeError):
    """Raised when no CodeGraph release asset matches the given OS/arch."""


class UnsafeURLError(RuntimeError):
    """Raised when a URL uses a non-HTTPS scheme (e.g. ``file://``, ``http://``)."""


class InstallExistsError(RuntimeError):
    """Raised when a version directory already exists and ``force`` is False."""


class ChecksumMismatchError(RuntimeError):
    """Raised when the downloaded asset's SHA-256 does not match the expected value."""


class ExtractionError(RuntimeError):
    """Raised when an archive member would escape the extraction root."""


def _is_windows() -> bool:
    """Thin indirection over ``core.platform.is_windows`` so tests can monkeypatch.

    Why not call ``is_windows`` from ``core.platform`` directly: monkeypatching
    the imported name inside this module is local to the installer, leaves the
    shared abstraction untouched, and keeps the cross-platform tests
    deterministic regardless of the host OS.
    """
    return _platform_is_windows()


def resolve_asset_name(os_name: str, arch: str) -> str:
    """Return the GitHub release asset filename for an OS/arch pair.

    Args:
        os_name: ``darwin``/``macos``, ``linux``, or ``windows``/``win``/``win32``.
            Case-insensitive.
        arch: ``arm64``/``aarch64``, or ``x64``/``x86_64``/``amd64``/``AMD64``.
            Case-insensitive.

    Returns:
        Asset filename, e.g. ``codegraph-darwin-arm64.tar.gz``.

    Raises:
        UnsupportedPlatformError: when the OS or arch is not in the release matrix.
    """
    normalized_os = _OS_ALIASES.get(os_name.strip().casefold()) if os_name else None
    normalized_arch = _ARCH_ALIASES.get(arch.strip().casefold()) if arch else None

    if normalized_os is None or normalized_arch is None:
        raise UnsupportedPlatformError(
            f"Unsupported CodeGraph platform: os={os_name!r}, arch={arch!r}. "
            "Supported: darwin/linux/windows on arm64 or x64."
        )

    extension = _ASSET_EXTENSION[normalized_os]
    return f"{_BINARY_NAME}-{normalized_os}-{normalized_arch}.{extension}"


def install_root() -> Path:
    """Return the directory holding all CodeGraph version installs.

    Respects the ``AUTO_CLAUDE_CODEGRAPH_DIR`` env var. Otherwise resolves to
    ``~/.auto-claude/bin/codegraph``.
    """
    override = os.environ.get(_ENV_OVERRIDE)
    if override:
        return Path(override)
    return Path.home() / _DEFAULT_DIRNAME


def installed_version(root: Path) -> str | None:
    """Return the highest installed version under ``root``, or ``None``.

    A version directory is recognized when its name matches ``v<semver-ish>``
    and it contains a ``codegraph`` (or ``codegraph.exe``) file. Multiple
    versions sort by their numeric components so ``v0.9.10`` > ``v0.9.2``.
    A final release wins over a prerelease with the same numeric prefix —
    ``v1.0.0`` beats ``v1.0.0-rc1`` even though the numeric parts tie.
    """
    if not root.exists() or not root.is_dir():
        return None

    candidates: list[tuple[tuple[int, ...], int, str]] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if not _VERSION_DIR_RE.match(name):
            continue
        if not binary_path(root, name).exists():
            continue
        # Tie-break ordering: release (1) > prerelease/build-suffixed (0).
        release_rank = 0 if _has_version_suffix(name) else 1
        candidates.append((_version_key(name), release_rank, name))

    if not candidates:
        return None

    candidates.sort()
    return candidates[-1][2]


def binary_path(root: Path, version: str) -> Path:
    """Return the absolute path to the installed CodeGraph binary.

    The CodeGraph release tarball lays out as::

        <version>/
            node               (bundled Node.js runtime)
            bin/
                codegraph      (POSIX) or codegraph.exe (Windows)
            lib/
                ...

    so the launcher lives one level deeper than the version directory.
    """
    suffix = ".exe" if _is_windows() else ""
    return root / version / "bin" / f"{_BINARY_NAME}{suffix}"


def download_and_install(
    *,
    version: str,
    os_name: str,
    arch: str,
    install_root: Path,
    expected_sha256: str | None = None,
    force: bool = False,
    asset_url: str | None = None,
) -> Path:
    """Download a CodeGraph release, verify, and extract it under ``install_root``.

    The install is **atomic-ish**: extraction happens in a staging directory
    and is then ``shutil.move``-d into ``install_root/<version>/``. A failed
    download or checksum mismatch leaves no trace; a tar/zip traversal attempt
    aborts before any file leaks outside the staging dir.

    Args:
        version: Release tag, e.g. ``v0.9.3``. Used as the install subdirectory
            name and to build the asset URL.
        os_name: ``darwin``/``linux``/``windows`` — see :func:`resolve_asset_name`.
        arch: ``arm64``/``x64`` and aliases.
        install_root: Parent dir; this function creates it if missing.
        expected_sha256: Optional hex digest. When provided, the download is
            verified before extraction; mismatch raises :class:`ChecksumMismatchError`.
        force: When False (default), refuses to overwrite an existing
            ``install_root/<version>/`` and raises :class:`InstallExistsError`.
            When True, the existing directory is removed first.
        asset_url: Override the auto-constructed GitHub release URL. Useful for
            testing and for users behind a mirror.

    Returns:
        The absolute path of the installed ``codegraph`` binary.
    """
    version_dir = install_root / version
    if version_dir.exists() and not force:
        raise InstallExistsError(
            f"CodeGraph {version} is already installed at {version_dir}. "
            "Pass force=True to reinstall."
        )

    if asset_url is None:
        asset_name = resolve_asset_name(os_name, arch)
        asset_url = _RELEASE_URL_TEMPLATE.format(version=version, asset=asset_name)
    else:
        # urlsplit().path drops any ``?query`` or ``#fragment`` from
        # a presigned mirror URL like ``...tar.gz?token=...`` so the
        # extension dispatch still sees ``.tar.gz``.
        asset_name = Path(urllib_parse.urlsplit(asset_url).path).name

    install_root.mkdir(parents=True, exist_ok=True)

    archive_handle = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=_archive_suffix(asset_name),
        dir=str(install_root),
        prefix=".download-",
    )
    archive_path = Path(archive_handle.name)
    staging_dir = install_root / f".staging-{version}-{uuid.uuid4().hex}"

    try:
        actual_sha = _stream_download(asset_url, archive_handle)
        archive_handle.close()

        if (
            expected_sha256 is not None
            and actual_sha.lower() != expected_sha256.lower()
        ):
            raise ChecksumMismatchError(
                f"SHA-256 mismatch for {asset_name}: "
                f"expected {expected_sha256.lower()}, got {actual_sha}"
            )

        staging_dir.mkdir(parents=True)
        _extract_archive(archive_path, asset_name, staging_dir)
        _strip_single_wrapper(staging_dir)

        binary_in_staging = (
            staging_dir
            / "bin"
            / (f"{_BINARY_NAME}.exe" if _is_windows() else _BINARY_NAME)
        )
        if binary_in_staging.exists() and not _is_windows():
            current = binary_in_staging.stat().st_mode & 0o777
            binary_in_staging.chmod(current | 0o755)

        if version_dir.exists():
            shutil.rmtree(version_dir)
        shutil.move(str(staging_dir), str(version_dir))
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    finally:
        try:
            archive_handle.close()
        except Exception:
            # The handle may already have been closed inside the try block
            # (the happy path closes it after streaming) — a second close on
            # most platforms is a no-op, but on Windows it can raise. We do
            # not care about that here: the file is gone after unlink.
            pass
        archive_path.unlink(missing_ok=True)

    return binary_path(install_root, version)


def latest_release(
    repo: str = _DEFAULT_REPO,
) -> tuple[str, dict[str, tuple[str, str | None]]]:
    """Query GitHub for the latest CodeGraph release.

    Args:
        repo: GitHub ``owner/name``. Defaults to the upstream CodeGraph repo;
            override for forks or mirrors.

    Returns:
        ``(tag_name, asset_map)`` where ``asset_map[name] = (download_url, sha256)``.
        ``sha256`` is the hex digest read from an adjacent ``<name>.sha256`` asset
        (sha256sum-format) when present, or ``None`` if no companion exists or
        the companion is unparseable. Companion ``.sha256`` assets are excluded
        from ``asset_map`` — they are metadata, not installable artifacts.

    The function does not authenticate. The unauthenticated GitHub API has a
    low rate limit but it is fine for occasional checks.
    """
    api_url = _GITHUB_API_LATEST_TEMPLATE.format(repo=repo)
    request = Request(api_url, headers={"User-Agent": _GITHUB_API_USER_AGENT})
    with _safe_urlopen(request) as response:
        data = json.loads(response.read())

    tag_name: str = data.get("tag_name", "")
    raw_assets = data.get("assets") or []

    name_to_url: dict[str, str] = {}
    for asset in raw_assets:
        name = asset.get("name")
        url = asset.get("browser_download_url")
        if name and url:
            name_to_url[name] = url

    companions: dict[str, str] = {
        name[: -len(_COMPANION_SUFFIX)]: url
        for name, url in name_to_url.items()
        if name.endswith(_COMPANION_SUFFIX)
    }

    # Cache companion bodies — a single SHA256SUMS-style file may serve multiple assets.
    companion_body_cache: dict[str, str] = {}

    result: dict[str, tuple[str, str | None]] = {}
    for name, url in name_to_url.items():
        if name.endswith(_COMPANION_SUFFIX):
            continue
        sha256: str | None = None
        companion_url = companions.get(name)
        if companion_url is not None:
            body = companion_body_cache.get(companion_url)
            if body is None:
                body = _fetch_companion_body(companion_url)
                companion_body_cache[companion_url] = body
            sha256 = _parse_sha256_companion(body, asset_name=name)
        result[name] = (url, sha256)

    return tag_name, result


def _fetch_companion_body(url: str) -> str:
    """Fetch a ``.sha256`` companion file, capped at a sane size."""
    request = Request(url, headers={"User-Agent": _GITHUB_API_USER_AGENT})
    with _safe_urlopen(request) as response:
        raw = response.read(_MAX_COMPANION_BYTES + 1)
    if len(raw) > _MAX_COMPANION_BYTES:
        # Refuse to parse pathological companion files
        return ""
    return raw.decode("utf-8", errors="replace")


def _parse_sha256_companion(body: str, *, asset_name: str) -> str | None:
    """Extract the digest for ``asset_name`` from a ``sha256sum``-style file.

    Recognized line shapes (lines starting with ``#`` are ignored):

    - ``<hex>``                       — bare digest, accepted if exactly one
                                        line in the file holds a hex value
    - ``<hex>  <filename>``           — standard ``sha256sum`` output
    - ``<hex> *<filename>``           — ``sha256sum --binary`` output (``*`` prefix)

    Returns the lowercased hex digest, or ``None`` when nothing matches.
    """
    hex_only_candidates: list[str] = []

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        digest = parts[0].lower()
        if not _SHA256_HEX_RE.match(digest):
            continue

        if len(parts) == 1:
            hex_only_candidates.append(digest)
            continue

        filename = parts[1].lstrip("*")
        if filename == asset_name or filename.endswith("/" + asset_name):
            return digest

    if len(hex_only_candidates) == 1:
        return hex_only_candidates[0]
    return None


def _archive_suffix(asset_name: str) -> str:
    lower = asset_name.lower()
    if lower.endswith(_TAR_GZ_SUFFIX):
        return _TAR_GZ_SUFFIX
    if lower.endswith(_ZIP_SUFFIX):
        return _ZIP_SUFFIX
    return ""


def _stream_download(url: str, file_obj) -> str:
    """Download ``url`` into ``file_obj``, returning the SHA-256 hex digest."""
    hasher = hashlib.sha256()
    with _safe_urlopen(url) as response:
        while True:
            chunk = response.read(_DOWNLOAD_CHUNK_BYTES)
            if not chunk:
                break
            hasher.update(chunk)
            file_obj.write(chunk)
    file_obj.flush()
    return hasher.hexdigest()


def _extract_archive(archive: Path, asset_name: str, dest: Path) -> None:
    """Dispatch to tarball or zip extraction based on the asset name."""
    lower = asset_name.lower()
    if lower.endswith(_TARBALL_SUFFIXES):
        _extract_tarball(archive, dest)
    elif lower.endswith(_ZIP_SUFFIX):
        _extract_zip(archive, dest)
    else:
        raise ExtractionError(f"Unsupported archive format: {asset_name}")


def _extract_tarball(archive: Path, dest: Path) -> None:
    dest_resolved = dest.resolve()
    with tarfile.open(archive, mode="r:*") as tar:
        for member in tar.getmembers():
            _validate_member_name(member.name, dest_resolved)
            if member.issym() or member.islnk():
                _validate_link_target(
                    member_name=member.name,
                    link_target=member.linkname,
                    dest=dest_resolved,
                )
            # Extract members one by one so Bandit can see the per-member gate
            # (B202). ``filter='data'`` provides defense in depth on top of our
            # own path resolution checks.
            tar.extract(member, path=dest, filter="data")


def _extract_zip(archive: Path, dest: Path) -> None:
    dest_resolved = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            _validate_member_name(info.filename, dest_resolved)
            zf.extract(info, path=dest)


def _validate_member_name(name: str, dest_resolved: Path) -> None:
    if not name:
        raise ExtractionError("Archive contains an empty member name")
    if name.startswith(("/", "\\")):
        raise ExtractionError(f"Archive contains absolute path: {name}")
    candidate = (dest_resolved / name).resolve()
    if not _is_within(candidate, dest_resolved):
        raise ExtractionError(
            f"Archive member escapes extraction root: {name!r} -> {candidate}"
        )


def _validate_link_target(*, member_name: str, link_target: str, dest: Path) -> None:
    if link_target.startswith(("/", "\\")):
        raise ExtractionError(
            f"Archive link target is absolute: {member_name} -> {link_target}"
        )
    member_parent = (dest / member_name).resolve().parent
    candidate = (member_parent / link_target).resolve()
    if not _is_within(candidate, dest):
        raise ExtractionError(
            f"Archive link target escapes root: {member_name} -> {link_target}"
        )


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_urlopen(target, *, timeout: float = _NETWORK_TIMEOUT_SECONDS):
    """Open a URL or Request, refusing any scheme other than HTTPS.

    Bandit B310 flags raw ``urllib.request.urlopen()`` because it can in
    theory open ``file://``, ``ftp://``, or custom schemes. We pre-validate
    the scheme here so callers can stay readable, and we put the actual
    ``urlopen`` call behind a single ``# nosec`` annotation with the gate
    visible right above it. The default timeout prevents a flaky network from
    hanging release discovery or downloads indefinitely.
    """
    if hasattr(target, "full_url"):
        url = target.full_url
    else:
        url = str(target)
    scheme = urllib_parse.urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise UnsafeURLError(
            f"Refusing to open URL with disallowed scheme {scheme!r}: {url}"
        )
    return urlopen(  # noqa: S310 (scheme validated above)  # nosec B310
        target, timeout=timeout
    )


def _strip_single_wrapper(staging_dir: Path) -> None:
    """If the archive contained one top-level wrapper directory, hoist its contents up.

    Heuristic: skip stripping when ``staging/bin/<binary>`` already exists.
    That means the archive shipped contents directly at the install root
    (and the one top-level dir we see — likely ``bin/`` itself — is part
    of the install layout, not a wrapper).
    """
    entries = list(staging_dir.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        return
    direct_binary = staging_dir / "bin" / _BINARY_NAME
    direct_binary_exe = staging_dir / "bin" / f"{_BINARY_NAME}.exe"
    if direct_binary.exists() or direct_binary_exe.exists():
        return
    wrapper = entries[0]
    # Move each child up one level; use a fresh uuid temp name to dodge name
    # collisions with the wrapper itself (e.g. wrapper named "codegraph").
    relocated: list[tuple[Path, Path]] = []
    for child in wrapper.iterdir():
        temp_name = staging_dir / f".relocate-{uuid.uuid4().hex}"
        shutil.move(str(child), str(temp_name))
        relocated.append((temp_name, staging_dir / child.name))
    wrapper.rmdir()
    for temp, final in relocated:
        shutil.move(str(temp), str(final))


def _version_key(name: str) -> tuple[int, ...]:
    """Numeric sort key for a version directory name.

    ``v0.9.3`` → ``(0, 9, 3)``. Pre-release/build suffixes are dropped from
    this key; release vs. prerelease tie-breaking happens via
    :func:`_has_version_suffix` in :func:`installed_version`.
    """
    stripped = name.lstrip("v")
    head = re.split(r"[-+]", stripped, maxsplit=1)[0]
    parts: list[int] = []
    for piece in head.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _has_version_suffix(name: str) -> bool:
    """Return True if ``name`` carries a prerelease/build suffix (``-rc1``, ``+build``)."""
    return "-" in name.lstrip("v") or "+" in name
