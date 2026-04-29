"""Tests for spec-113 G-1 (defence-in-depth): pinned + empty pin still raises.

The skip path lives behind ``sha256_pinned=False`` (the explicit
DEC-038-pending opt-out). The other half of the contract: when a
descriptor declares ``sha256_pinned=True`` but ``expected_sha256`` is
empty / None, ``_verify_sha256`` keeps raising ``Sha256MismatchError`` so
a future registry regression cannot silently land an unverified binary.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from ai_engineering.installer.mechanisms import (
    _PIN_REQUIRED,
    GitHubReleaseBinaryMechanism,
    Sha256MismatchError,
    _verify_sha256,
)


def _ok_proc() -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_pin_required_default_is_true() -> None:
    """Production default keeps strict pinning enforced."""
    assert _PIN_REQUIRED is True


def test_verify_sha256_raises_with_empty_pin_under_pin_required(tmp_path: Path) -> None:
    """``_verify_sha256(path, "")`` raises when ``_PIN_REQUIRED`` is True."""
    artefact = tmp_path / "fake-binary"
    artefact.write_bytes(b"hello world")
    with pytest.raises(Sha256MismatchError) as excinfo:
        _verify_sha256(artefact, "")
    assert "<missing>" in str(excinfo.value)


def test_pinned_install_with_empty_digest_invokes_verify_and_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``sha256_pinned=True`` with no digest still raises through the install path."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    seen_argv: list[list[str]] = []

    def _record(argv: list[str], **_kw: Any) -> SimpleNamespace:
        seen_argv.append(list(argv))
        # Simulate a successful download so the SHA verifier fires.
        target = Path(argv[argv.index("--output") + 1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake")
        return _ok_proc()

    def _which(name: str) -> str | None:
        return "/usr/bin/curl" if name == "curl" else None

    with (
        patch(
            "ai_engineering.installer.mechanisms._safe_run",
            side_effect=_record,
        ),
        patch(
            "ai_engineering.installer.mechanisms.shutil.which",
            side_effect=_which,
        ),
    ):
        mech = GitHubReleaseBinaryMechanism(
            repo="some/repo",
            binary="some-bin",
            sha256_pinned=True,
            expected_sha256=None,
        )
        with pytest.raises(Sha256MismatchError):
            mech.install()


def test_pinned_install_with_correct_digest_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinned + matching digest -> install completes without raising."""
    import hashlib

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    payload = b"pinned-binary-payload"
    expected_digest = hashlib.sha256(payload).hexdigest()

    def _record(argv: list[str], **_kw: Any) -> SimpleNamespace:
        target = Path(argv[argv.index("--output") + 1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return _ok_proc()

    def _which(name: str) -> str | None:
        return "/usr/bin/curl" if name == "curl" else None

    with (
        patch("ai_engineering.installer.mechanisms._safe_run", side_effect=_record),
        patch("ai_engineering.installer.mechanisms.shutil.which", side_effect=_which),
    ):
        mech = GitHubReleaseBinaryMechanism(
            repo="ok/repo",
            binary="ok-bin",
            sha256_pinned=True,
            expected_sha256=expected_digest,
        )
        result = mech.install()
        assert result.failed is False
