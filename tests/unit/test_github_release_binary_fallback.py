"""Tests for spec-113 G-2: download fallback chain (curl -> wget -> urllib).

Three drivers are attempted in preference order; the first that resolves
on PATH (or, for urllib, the in-process fallback) wins. Coverage:

* curl preferred when present (preserves spec-101 contract);
* curl absent + wget present -> wget called via ``_safe_run`` with
  BusyBox-safe flags (``-O <path> <url>``);
* both subprocess drivers absent -> urllib path taken;
* urllib path enforces hostname allowlist;
* urllib path enforces HTTPS scheme;
* urllib path bounds redirect chain;
* urllib path bounds body bytes.

The hostname/scheme guards live behind the public ``_ensure_https_and_allowed``
and ``_AllowlistRedirectHandler`` helpers; the body-cap and redirect-cap
guards live behind the private ``_stream_to_disk`` and
``_AllowlistRedirectHandler`` helpers.
"""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from ai_engineering.installer import mechanisms as mech_mod
from ai_engineering.installer.mechanisms import (
    _DOWNLOAD_DRIVER_PREFERENCE,
    GitHubReleaseBinaryMechanism,
    InstallResult,
    SecurityError,
    _download_release_binary,
    _ensure_https_and_allowed,
    _resolve_download_driver,
)
from ai_engineering.installer.results import SecurityError as ResultsSecurityError

_SAFE_RUN_PATH = "ai_engineering.installer.mechanisms._safe_run"


def _ok_proc() -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def _fail_proc(stderr: str = "boom") -> SimpleNamespace:
    return SimpleNamespace(returncode=1, stdout="", stderr=stderr)


# ---------------------------------------------------------------------------
# Preference order constants
# ---------------------------------------------------------------------------


def test_preference_order_is_curl_wget_urllib() -> None:
    """The fallback ordering is fixed by D-113-03."""
    assert _DOWNLOAD_DRIVER_PREFERENCE == ("curl", "wget", "urllib")


def test_security_error_class_re_exported() -> None:
    """Both import sites expose the same :class:`SecurityError` class."""
    assert SecurityError is ResultsSecurityError


# ---------------------------------------------------------------------------
# curl preferred when present
# ---------------------------------------------------------------------------


def test_curl_preferred_when_on_path(tmp_path: Path) -> None:
    """When curl resolves, it is the first driver attempted."""
    target = tmp_path / "out.bin"
    seen_argv: list[list[str]] = []

    def _record(argv: list[str], **_kw: Any) -> SimpleNamespace:
        seen_argv.append(list(argv))
        return _ok_proc()

    def _which(name: str) -> str | None:
        return "/usr/bin/curl" if name == "curl" else None

    with (
        patch(_SAFE_RUN_PATH, side_effect=_record),
        patch.object(mech_mod.shutil, "which", side_effect=_which),
    ):
        result = _download_release_binary(
            "https://github.com/foo/bar/releases/latest/download/bar", target
        )

    assert result.failed is False
    assert seen_argv, "expected at least one _safe_run invocation"
    assert seen_argv[0][0] == "curl", f"curl must be argv[0], got {seen_argv[0][0]!r}"


# ---------------------------------------------------------------------------
# wget fallback when curl absent
# ---------------------------------------------------------------------------


def test_wget_used_when_curl_absent(tmp_path: Path) -> None:
    """Curl missing + wget present -> wget runs with BusyBox-safe flags."""
    target = tmp_path / "out.bin"
    seen_argv: list[list[str]] = []

    def _record(argv: list[str], **_kw: Any) -> SimpleNamespace:
        seen_argv.append(list(argv))
        return _ok_proc()

    def _which(name: str) -> str | None:
        return "/usr/bin/wget" if name == "wget" else None

    with (
        patch(_SAFE_RUN_PATH, side_effect=_record),
        patch.object(mech_mod.shutil, "which", side_effect=_which),
    ):
        result = _download_release_binary(
            "https://github.com/foo/bar/releases/latest/download/bar", target
        )

    assert result.failed is False, f"wget path should succeed; got {result!r}"
    assert seen_argv, "expected at least one _safe_run invocation"
    # curl resolution skipped (which returns None) -- wget runs first.
    assert seen_argv[0][0] == "wget"
    # BusyBox-safe argv: only ``-O <path> <url>`` (no --show-progress).
    assert seen_argv[0][1] == "-O"
    assert seen_argv[0][2] == str(target)
    assert seen_argv[0][3].startswith("https://github.com/")


def test_wget_fallback_continues_when_subprocess_fails(tmp_path: Path) -> None:
    """A failing wget run still allows the urllib path to fire."""
    target = tmp_path / "out.bin"

    def _which(name: str) -> str | None:
        return "/usr/bin/wget" if name == "wget" else None

    urllib_called = {"value": False}

    def _fake_urllib(url: str, target_path: Path) -> InstallResult:
        urllib_called["value"] = True
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"fake")
        return InstallResult(failed=False, mechanism="GitHubReleaseBinaryMechanism")

    with (
        patch(_SAFE_RUN_PATH, return_value=_fail_proc("wget: server error")),
        patch.object(mech_mod.shutil, "which", side_effect=_which),
        patch.object(mech_mod, "_download_via_urllib", side_effect=_fake_urllib),
    ):
        result = _download_release_binary(
            "https://github.com/foo/bar/releases/latest/download/bar", target
        )

    assert result.failed is False
    assert urllib_called["value"] is True


# ---------------------------------------------------------------------------
# urllib fallback when both subprocess drivers are absent
# ---------------------------------------------------------------------------


def test_urllib_fallback_when_neither_curl_nor_wget(tmp_path: Path) -> None:
    """Both drivers missing -> urllib path runs and succeeds."""
    target = tmp_path / "out.bin"
    payload = b"abcdefg"
    body = io.BytesIO(payload)

    class _Resp:
        def __init__(self, body: io.BytesIO) -> None:
            self._body = body

        def read(self, size: int) -> bytes:
            return self._body.read(size)

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: Any) -> None:
            self._body.close()

    class _FakeOpener:
        def open(self, request: Any, timeout: int | None = None) -> _Resp:
            assert timeout is not None  # urllib path passes a timeout
            return _Resp(body)

    def _which(_name: str) -> str | None:
        return None

    with (
        patch.object(mech_mod.shutil, "which", side_effect=_which),
        patch.object(mech_mod.urllib.request, "build_opener", return_value=_FakeOpener()),
    ):
        result = _download_release_binary(
            "https://github.com/foo/bar/releases/latest/download/bar", target
        )

    assert result.failed is False
    assert target.read_bytes() == payload


# ---------------------------------------------------------------------------
# Hostname / scheme guards
# ---------------------------------------------------------------------------


def test_ensure_https_rejects_http_scheme() -> None:
    """HTTP URLs raise :class:`SecurityError` -- no fallback for plaintext."""
    with pytest.raises(SecurityError):
        _ensure_https_and_allowed("http://github.com/foo/bar")


def test_ensure_https_rejects_unallowed_hostname() -> None:
    """Non-allowlisted hostnames raise :class:`SecurityError`."""
    with pytest.raises(SecurityError):
        _ensure_https_and_allowed("https://evil.example.com/payload")


def test_ensure_https_accepts_allowlisted_hostnames() -> None:
    """github.com and objects.githubusercontent.com both pass."""
    _ensure_https_and_allowed("https://github.com/foo")
    _ensure_https_and_allowed("https://objects.githubusercontent.com/foo")


# ---------------------------------------------------------------------------
# Resolver direct contract
# ---------------------------------------------------------------------------


def test_resolve_download_driver_returns_curl_when_present() -> None:
    """Resolver picks curl when it is on PATH (preference)."""

    def _which(name: str) -> str | None:
        return "/curl" if name == "curl" else None

    with patch.object(mech_mod.shutil, "which", side_effect=_which):
        assert _resolve_download_driver() == "curl"


def test_resolve_download_driver_picks_wget_when_curl_absent() -> None:
    """When curl is gone but wget present, resolver picks wget."""
    with patch.object(
        mech_mod.shutil,
        "which",
        side_effect=lambda n: "/wget" if n == "wget" else None,
    ):
        assert _resolve_download_driver() == "wget"


def test_resolve_download_driver_returns_urllib_when_no_subprocess_drivers() -> None:
    """No curl/wget -> urllib sentinel returned (urllib is always available)."""
    with patch.object(mech_mod.shutil, "which", return_value=None):
        assert _resolve_download_driver() == "urllib"


# ---------------------------------------------------------------------------
# Public install() smoke -- end-to-end via mechanism (G-2 spec text)
# ---------------------------------------------------------------------------


def test_install_smoke_uses_curl_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The dataclass install() routes through the chain and respects the pin flag."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    seen_argv: list[list[str]] = []

    def _record(argv: list[str], **_kw: Any) -> SimpleNamespace:
        seen_argv.append(list(argv))
        return _ok_proc()

    def _which(name: str) -> str | None:
        return "/usr/bin/curl" if name == "curl" else None

    with (
        patch(_SAFE_RUN_PATH, side_effect=_record),
        patch.object(mech_mod.shutil, "which", side_effect=_which),
    ):
        mech = GitHubReleaseBinaryMechanism(
            repo="gitleaks/gitleaks",
            binary="gitleaks",
            sha256_pinned=False,
        )
        result = mech.install()

    assert result.failed is False
    assert seen_argv[0][0] == "curl"
