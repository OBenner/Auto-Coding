"""Tests for the codegraph installer module (Task 8, Steps 1 & 4)."""

from __future__ import annotations

import hashlib
import io
import os
import stat
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_PKG_ROOT = (
    REPO_ROOT / "apps" / "backend" / "plugins" / "system" / "codebase-intelligence"
)
if str(_PLUGIN_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_PKG_ROOT))


from codebase_intelligence import installer  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Archive fixtures and urlopen mock
# ---------------------------------------------------------------------------


def _make_tarball(
    files: dict[str, bytes],
    *,
    wrapper: str | None = None,
    executable: set[str] | None = None,
) -> bytes:
    """Build an in-memory gzipped tarball."""
    executable = executable or set()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            arc = f"{wrapper}/{name}" if wrapper else name
            info = tarfile.TarInfo(arc)
            info.size = len(data)
            info.mode = 0o755 if name in executable else 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _make_zip(files: dict[str, bytes], *, wrapper: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            arc = f"{wrapper}/{name}" if wrapper else name
            zf.writestr(arc, data)
    return buf.getvalue()


def _make_tarball_with_traversal() -> bytes:
    """Tarball whose member resolves outside the extraction root."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo("../escaped.txt")
        payload = b"pwned"
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


class _FakeResponse:
    """Minimal stand-in for ``urllib.request.urlopen`` context manager."""

    def __init__(self, data: bytes) -> None:
        self._buf = io.BytesIO(data)

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def _url_of(target: Any) -> str:
    """Extract a string URL from either a bare URL or a ``urllib.request.Request``."""
    if hasattr(target, "full_url"):
        return target.full_url
    return target


def _install_fake_urlopen(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> list[str]:
    """Capture URLs and return ``payload`` for any urlopen call."""
    captured: list[str] = []

    def _fake(target: Any, *args: Any, **kwargs: Any) -> _FakeResponse:
        captured.append(_url_of(target))
        return _FakeResponse(payload)

    monkeypatch.setattr(installer, "urlopen", _fake)
    return captured


def _install_url_router(
    monkeypatch: pytest.MonkeyPatch, routes: dict[str, bytes]
) -> list[str]:
    """Route urlopen calls to per-URL payloads. Unmatched URLs fail loudly."""
    captured: list[str] = []

    def _fake(target: Any, *args: Any, **kwargs: Any) -> _FakeResponse:
        url = _url_of(target)
        captured.append(url)
        if url not in routes:
            raise AssertionError(f"unexpected urlopen({url!r}) — not in routes")
        return _FakeResponse(routes[url])

    monkeypatch.setattr(installer, "urlopen", _fake)
    return captured


class TestResolveAssetName:
    """`resolve_asset_name(os_name, arch)` returns the GitHub release asset filename."""

    @pytest.mark.parametrize(
        "os_name,arch,expected",
        [
            ("darwin", "arm64", "codegraph-darwin-arm64.tar.gz"),
            ("darwin", "x64", "codegraph-darwin-x64.tar.gz"),
            ("linux", "arm64", "codegraph-linux-arm64.tar.gz"),
            ("linux", "x64", "codegraph-linux-x64.tar.gz"),
            ("windows", "arm64", "codegraph-win32-arm64.zip"),
            ("windows", "x64", "codegraph-win32-x64.zip"),
        ],
    )
    def test_returns_expected_asset_for_supported_platforms(
        self, os_name: str, arch: str, expected: str
    ) -> None:
        assert installer.resolve_asset_name(os_name, arch) == expected

    @pytest.mark.parametrize(
        "raw_arch,normalized",
        [
            ("aarch64", "arm64"),
            ("arm64", "arm64"),
            ("AMD64", "x64"),
            ("x86_64", "x64"),
            ("x64", "x64"),
        ],
    )
    def test_normalizes_arch_aliases(self, raw_arch: str, normalized: str) -> None:
        # darwin chosen arbitrarily — arch normalization should be OS-agnostic
        expected = f"codegraph-darwin-{normalized}.tar.gz"
        assert installer.resolve_asset_name("darwin", raw_arch) == expected

    @pytest.mark.parametrize(
        "os_name,arch",
        [
            ("linux", "armv7"),
            ("linux", "i386"),
            ("freebsd", "x64"),
            ("darwin", "ppc64"),
            ("", "x64"),
            ("linux", ""),
        ],
    )
    def test_raises_for_unsupported_platforms(self, os_name: str, arch: str) -> None:
        with pytest.raises(installer.UnsupportedPlatformError) as excinfo:
            installer.resolve_asset_name(os_name, arch)
        # Error should name both pieces so users know what to fix
        message = str(excinfo.value).lower()
        assert os_name.lower() in message or "unsupported" in message
        if arch:
            assert arch.lower() in message or "unsupported" in message

    def test_os_name_is_case_insensitive(self) -> None:
        assert (
            installer.resolve_asset_name("Darwin", "arm64")
            == "codegraph-darwin-arm64.tar.gz"
        )
        assert (
            installer.resolve_asset_name("WINDOWS", "x64") == "codegraph-win32-x64.zip"
        )


class TestInstallRoot:
    """`install_root()` returns the user-local install directory."""

    def test_defaults_to_home_auto_claude_bin_codegraph(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("AUTO_CLAUDE_CODEGRAPH_DIR", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        # On Windows, Path.home() reads USERPROFILE; set it too for cross-platform tests
        monkeypatch.setenv("USERPROFILE", str(tmp_path))

        root = installer.install_root()

        assert root == tmp_path / ".auto-claude" / "bin" / "codegraph"

    def test_respects_env_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        override = tmp_path / "custom" / "codegraph"
        monkeypatch.setenv("AUTO_CLAUDE_CODEGRAPH_DIR", str(override))

        assert installer.install_root() == override


class TestInstalledVersion:
    """`installed_version(root)` returns the version of the install on disk, or None."""

    def test_returns_none_when_root_missing(self, tmp_path: Path) -> None:
        assert installer.installed_version(tmp_path / "does-not-exist") is None

    def test_returns_none_when_root_empty(self, tmp_path: Path) -> None:
        tmp_path.mkdir(exist_ok=True)
        assert installer.installed_version(tmp_path) is None

    def test_returns_version_when_directory_present(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Pin to POSIX so the fixture binary name is stable across the CI matrix.
        # OS-specific extension is covered by TestBinaryPath below.
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        (tmp_path / "v0.9.3").mkdir(parents=True)
        (tmp_path / "v0.9.3" / "codegraph").write_text("#!/bin/sh\n")

        assert installer.installed_version(tmp_path) == "v0.9.3"

    def test_returns_highest_when_multiple_present(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        for version in ("v0.9.1", "v0.9.3", "v0.9.2"):
            (tmp_path / version).mkdir(parents=True)
            (tmp_path / version / "codegraph").write_text("#!/bin/sh\n")

        assert installer.installed_version(tmp_path) == "v0.9.3"


class TestBinaryPath:
    """`binary_path(root, version)` returns the absolute binary path for the install."""

    def test_posix_binary_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)

        path = installer.binary_path(tmp_path, "v0.9.3")

        assert path == tmp_path / "v0.9.3" / "codegraph"

    def test_windows_binary_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: True)

        path = installer.binary_path(tmp_path, "v0.9.3")

        assert path == tmp_path / "v0.9.3" / "codegraph.exe"


class TestDownloadAndInstall:
    """`download_and_install(...)` downloads, verifies, and extracts a release."""

    def test_happy_path_extracts_binary_and_makes_it_executable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        tarball = _make_tarball(
            {"codegraph": b"#!/bin/sh\necho hi\n", "README.md": b"hello"},
            executable={"codegraph"},
        )
        _install_fake_urlopen(monkeypatch, tarball)

        result = installer.download_and_install(
            version="v0.9.3",
            os_name="darwin",
            arch="arm64",
            install_root=tmp_path,
        )

        assert result == tmp_path / "v0.9.3" / "codegraph"
        assert result.exists()
        assert (tmp_path / "v0.9.3" / "README.md").read_bytes() == b"hello"
        # The executable bit is a POSIX concept. Windows does not honor
        # S_IXUSR regardless of our chmod call, so only assert it on POSIX.
        if os.name != "nt":
            mode = result.stat().st_mode & 0o777
            assert mode & stat.S_IXUSR, (
                f"binary should be executable, got mode {oct(mode)}"
            )

    def test_constructs_github_release_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        tarball = _make_tarball({"codegraph": b"x"}, executable={"codegraph"})
        urls = _install_fake_urlopen(monkeypatch, tarball)

        installer.download_and_install(
            version="v0.9.3",
            os_name="linux",
            arch="x64",
            install_root=tmp_path,
        )

        assert urls == [
            "https://github.com/colbymchenry/codegraph/releases/download/"
            "v0.9.3/codegraph-linux-x64.tar.gz"
        ]

    def test_verifies_sha256_match(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        tarball = _make_tarball({"codegraph": b"x"}, executable={"codegraph"})
        digest = hashlib.sha256(tarball).hexdigest()
        _install_fake_urlopen(monkeypatch, tarball)

        result = installer.download_and_install(
            version="v0.9.3",
            os_name="darwin",
            arch="arm64",
            install_root=tmp_path,
            expected_sha256=digest,
        )

        assert result.exists()

    def test_raises_on_sha256_mismatch_and_leaves_no_install(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        tarball = _make_tarball({"codegraph": b"x"}, executable={"codegraph"})
        _install_fake_urlopen(monkeypatch, tarball)

        with pytest.raises(installer.ChecksumMismatchError):
            installer.download_and_install(
                version="v0.9.3",
                os_name="darwin",
                arch="arm64",
                install_root=tmp_path,
                expected_sha256="0" * 64,
            )

        assert not (tmp_path / "v0.9.3").exists()
        # No staging leftovers should remain
        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".staging")]
        assert leftovers == []

    def test_refuses_to_overwrite_without_force(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        existing = tmp_path / "v0.9.3"
        existing.mkdir(parents=True)
        (existing / "codegraph").write_text("old")
        tarball = _make_tarball({"codegraph": b"new"}, executable={"codegraph"})
        urls = _install_fake_urlopen(monkeypatch, tarball)

        with pytest.raises(installer.InstallExistsError):
            installer.download_and_install(
                version="v0.9.3",
                os_name="darwin",
                arch="arm64",
                install_root=tmp_path,
            )

        # Should not even download
        assert urls == []
        # Existing install must be untouched
        assert (existing / "codegraph").read_text() == "old"

    def test_overwrites_existing_with_force(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        existing = tmp_path / "v0.9.3"
        existing.mkdir(parents=True)
        (existing / "codegraph").write_text("old")
        (existing / "stale.txt").write_text("stale")
        tarball = _make_tarball({"codegraph": b"new"}, executable={"codegraph"})
        _install_fake_urlopen(monkeypatch, tarball)

        result = installer.download_and_install(
            version="v0.9.3",
            os_name="darwin",
            arch="arm64",
            install_root=tmp_path,
            force=True,
        )

        assert result.read_bytes() == b"new"
        # Stale file from old install must be gone after overwrite
        assert not (existing / "stale.txt").exists()

    def test_strips_wrapper_directory(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        tarball = _make_tarball(
            {"codegraph": b"x", "lib/runtime.so": b"y"},
            wrapper="codegraph-darwin-arm64",
            executable={"codegraph"},
        )
        _install_fake_urlopen(monkeypatch, tarball)

        result = installer.download_and_install(
            version="v0.9.3",
            os_name="darwin",
            arch="arm64",
            install_root=tmp_path,
        )

        assert result == tmp_path / "v0.9.3" / "codegraph"
        assert result.exists()
        assert (tmp_path / "v0.9.3" / "lib" / "runtime.so").exists()
        # Wrapper directory must NOT survive
        assert not (tmp_path / "v0.9.3" / "codegraph-darwin-arm64").exists()

    def test_zip_archive_for_windows(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: True)
        zip_bytes = _make_zip({"codegraph.exe": b"MZ", "readme.txt": b"hi"})
        _install_fake_urlopen(monkeypatch, zip_bytes)

        result = installer.download_and_install(
            version="v0.9.3",
            os_name="windows",
            arch="x64",
            install_root=tmp_path,
        )

        assert result == tmp_path / "v0.9.3" / "codegraph.exe"
        assert result.exists()
        assert (tmp_path / "v0.9.3" / "readme.txt").exists()

    def test_rejects_tar_path_traversal(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        bad_tarball = _make_tarball_with_traversal()
        _install_fake_urlopen(monkeypatch, bad_tarball)

        with pytest.raises(installer.ExtractionError):
            installer.download_and_install(
                version="v0.9.3",
                os_name="darwin",
                arch="arm64",
                install_root=tmp_path,
            )

        # Nothing should have escaped the install root
        escaped = tmp_path.parent / "escaped.txt"
        assert not escaped.exists(), f"path traversal succeeded — found {escaped}"
        # And no install dir should remain
        assert not (tmp_path / "v0.9.3").exists()
        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".staging")]
        assert leftovers == []

    def test_rejects_zip_path_traversal(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: True)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w") as zf:
            zf.writestr("../escape.txt", b"pwned")
        _install_fake_urlopen(monkeypatch, buf.getvalue())

        with pytest.raises(installer.ExtractionError):
            installer.download_and_install(
                version="v0.9.3",
                os_name="windows",
                arch="x64",
                install_root=tmp_path,
            )

        assert not (tmp_path.parent / "escape.txt").exists()

    def test_install_root_is_created_when_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(installer, "_is_windows", lambda: False)
        tarball = _make_tarball({"codegraph": b"x"}, executable={"codegraph"})
        _install_fake_urlopen(monkeypatch, tarball)
        # Use a nested path that does not exist yet
        nested = tmp_path / "nested" / "deep" / "root"

        result = installer.download_and_install(
            version="v0.9.3",
            os_name="darwin",
            arch="arm64",
            install_root=nested,
        )

        assert result.exists()
        assert result.is_relative_to(nested)


class TestLatestRelease:
    """`latest_release()` queries GitHub for the newest release tag + assets."""

    _BASE_API = "https://api.github.com/repos/colbymchenry/codegraph/releases/latest"
    _RELEASES = "https://github.com/colbymchenry/codegraph/releases/download"

    def _release_json(self, tag: str, assets: list[dict[str, str]]) -> bytes:
        import json

        return json.dumps(
            {
                "tag_name": tag,
                "assets": [
                    {"name": a["name"], "browser_download_url": a["url"]}
                    for a in assets
                ],
            }
        ).encode("utf-8")

    def test_returns_tag_and_assets_without_companion_sha(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tarball_url = f"{self._RELEASES}/v0.9.3/codegraph-darwin-arm64.tar.gz"
        zip_url = f"{self._RELEASES}/v0.9.3/codegraph-win32-x64.zip"
        payload = self._release_json(
            "v0.9.3",
            [
                {"name": "codegraph-darwin-arm64.tar.gz", "url": tarball_url},
                {"name": "codegraph-win32-x64.zip", "url": zip_url},
            ],
        )
        urls = _install_url_router(monkeypatch, {self._BASE_API: payload})

        tag, assets = installer.latest_release()

        assert tag == "v0.9.3"
        assert assets == {
            "codegraph-darwin-arm64.tar.gz": (tarball_url, None),
            "codegraph-win32-x64.zip": (zip_url, None),
        }
        # Only the API call should be made; no per-asset network hits
        assert urls == [self._BASE_API]

    def test_reads_companion_sha256_when_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tarball_url = f"{self._RELEASES}/v0.9.3/codegraph-darwin-arm64.tar.gz"
        sha_url = f"{tarball_url}.sha256"
        digest = "a" * 64
        api_payload = self._release_json(
            "v0.9.3",
            [
                {"name": "codegraph-darwin-arm64.tar.gz", "url": tarball_url},
                {"name": "codegraph-darwin-arm64.tar.gz.sha256", "url": sha_url},
            ],
        )
        # Standard `sha256sum` format: "<hex>  <filename>"
        sha_body = f"{digest}  codegraph-darwin-arm64.tar.gz\n".encode()

        _install_url_router(
            monkeypatch, {self._BASE_API: api_payload, sha_url: sha_body}
        )

        tag, assets = installer.latest_release()

        assert tag == "v0.9.3"
        # The .sha256 itself MUST NOT appear as an installable asset
        assert "codegraph-darwin-arm64.tar.gz.sha256" not in assets
        assert assets == {
            "codegraph-darwin-arm64.tar.gz": (tarball_url, digest),
        }

    def test_handles_bare_hex_sha256_format(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tarball_url = f"{self._RELEASES}/v0.9.3/codegraph-linux-x64.tar.gz"
        sha_url = f"{tarball_url}.sha256"
        digest = "b" * 64
        api_payload = self._release_json(
            "v0.9.3",
            [
                {"name": "codegraph-linux-x64.tar.gz", "url": tarball_url},
                {"name": "codegraph-linux-x64.tar.gz.sha256", "url": sha_url},
            ],
        )
        _install_url_router(
            monkeypatch,
            {
                self._BASE_API: api_payload,
                sha_url: f"{digest}\n".encode(),
            },
        )

        _, assets = installer.latest_release()

        assert assets["codegraph-linux-x64.tar.gz"] == (tarball_url, digest)

    def test_returns_none_for_malformed_companion(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tarball_url = f"{self._RELEASES}/v0.9.3/codegraph-linux-arm64.tar.gz"
        sha_url = f"{tarball_url}.sha256"
        api_payload = self._release_json(
            "v0.9.3",
            [
                {"name": "codegraph-linux-arm64.tar.gz", "url": tarball_url},
                {"name": "codegraph-linux-arm64.tar.gz.sha256", "url": sha_url},
            ],
        )
        _install_url_router(
            monkeypatch,
            {
                self._BASE_API: api_payload,
                sha_url: b"not a valid sha256 file\n",
            },
        )

        _, assets = installer.latest_release()

        assert assets["codegraph-linux-arm64.tar.gz"] == (tarball_url, None)

    def test_picks_correct_line_when_companion_lists_multiple(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        url_a = f"{self._RELEASES}/v0.9.3/codegraph-darwin-arm64.tar.gz"
        url_b = f"{self._RELEASES}/v0.9.3/codegraph-darwin-x64.tar.gz"
        sha_url = f"{self._RELEASES}/v0.9.3/SHA256SUMS"
        digest_a = "a" * 64
        digest_b = "b" * 64
        api_payload = self._release_json(
            "v0.9.3",
            [
                {"name": "codegraph-darwin-arm64.tar.gz", "url": url_a},
                {"name": "codegraph-darwin-x64.tar.gz", "url": url_b},
                {"name": "codegraph-darwin-arm64.tar.gz.sha256", "url": sha_url},
                {"name": "codegraph-darwin-x64.tar.gz.sha256", "url": sha_url},
            ],
        )
        combined = (
            f"{digest_a}  codegraph-darwin-arm64.tar.gz\n"
            f"{digest_b}  codegraph-darwin-x64.tar.gz\n"
        ).encode()
        _install_url_router(
            monkeypatch, {self._BASE_API: api_payload, sha_url: combined}
        )

        _, assets = installer.latest_release()

        assert assets["codegraph-darwin-arm64.tar.gz"] == (url_a, digest_a)
        assert assets["codegraph-darwin-x64.tar.gz"] == (url_b, digest_b)

    def test_accepts_custom_repo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        api_url = "https://api.github.com/repos/example/fork/releases/latest"
        payload = self._release_json("v1.0.0", [])
        urls = _install_url_router(monkeypatch, {api_url: payload})

        tag, assets = installer.latest_release(repo="example/fork")

        assert tag == "v1.0.0"
        assert assets == {}
        assert urls == [api_url]

    def test_strips_sha256_companions_from_asset_map(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tarball_url = f"{self._RELEASES}/v0.9.3/codegraph-linux-x64.tar.gz"
        sha_url = f"{tarball_url}.sha256"
        api_payload = self._release_json(
            "v0.9.3",
            [
                {"name": "codegraph-linux-x64.tar.gz", "url": tarball_url},
                {"name": "codegraph-linux-x64.tar.gz.sha256", "url": sha_url},
            ],
        )
        _install_url_router(
            monkeypatch,
            {
                self._BASE_API: api_payload,
                sha_url: f"{'c' * 64}  codegraph-linux-x64.tar.gz\n".encode(),
            },
        )

        _, assets = installer.latest_release()

        assert set(assets) == {"codegraph-linux-x64.tar.gz"}


@pytest.fixture(autouse=True)
def _no_unintended_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense in depth: blow up on any non-mocked network attempt.

    Each test that needs the network installs its own fake via
    ``_install_fake_urlopen``; this fixture ensures forgetting that does not
    silently hit GitHub.
    """

    def _bomb(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "real urlopen called in tests — install _install_fake_urlopen"
        )

    monkeypatch.setattr(installer, "urlopen", _bomb, raising=False)
    # Guarantee a clean env so install_root() tests do not see real overrides
    monkeypatch.delenv("AUTO_CLAUDE_CODEGRAPH_DIR", raising=False)
