"""Tests for spec-113 G-1: ``sha256_pinned=False`` skips _verify_sha256.

The previous behaviour (spec-101) treated ``sha256_pinned`` as a decorative
flag -- ``install()`` always called ``_verify_sha256`` and the pin-required
defence raised ``Sha256MismatchError`` whenever the pin was empty. This
left every Linux GitHub-release entry permanently broken because the
registry declares ``sha256_pinned=False`` until DEC-038 ships.

D-113-01 makes the flag load-bearing:

* ``sha256_pinned=False`` -> skip digest verify, emit WARNING + audit event.
* ``sha256_pinned=True``  -> existing pin-required defence preserved.

Tests cover:

* the skip path returns a successful :class:`InstallResult` without raising;
* the WARNING fires to stderr exactly once;
* the ``sha_pin_skipped`` framework event lands on disk;
* dedup R-10: a second invocation in the same process emits no second event;
* pinned + empty digest still raises (defence-in-depth).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from ai_engineering.installer.mechanisms import (
    _SHA_PIN_SKIPPED_AUDIT_SEEN,
    GitHubReleaseBinaryMechanism,
    InstallResult,
    Sha256MismatchError,
)

_SAFE_RUN_PATH = "ai_engineering.installer.mechanisms._safe_run"
_VERIFY_SHA_PATH = "ai_engineering.installer.mechanisms._verify_sha256"


def _ok_proc() -> SimpleNamespace:
    """``_safe_run`` success placeholder."""
    return SimpleNamespace(returncode=0, stdout="", stderr="")


@pytest.fixture(autouse=True)
def _reset_audit_dedup() -> None:
    """Clear the per-process dedup set so each test starts fresh (R-10)."""
    _SHA_PIN_SKIPPED_AUDIT_SEEN.clear()
    yield
    _SHA_PIN_SKIPPED_AUDIT_SEEN.clear()


@pytest.fixture
def in_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run the test from a tmp project root so audit events land predictably."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _read_framework_events(project_root: Path) -> list[dict[str, Any]]:
    """Return all framework events written by the audit emitter."""
    events_path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not events_path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw_line in events_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line:
            out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# G-1: sha256_pinned=False skips verify and emits WARNING + audit event
# ---------------------------------------------------------------------------


def test_unpinned_install_skips_verify_and_warns(
    in_project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``sha256_pinned=False`` install() returns success without calling _verify_sha256."""
    mech = GitHubReleaseBinaryMechanism(
        repo="gitleaks/gitleaks",
        binary="gitleaks",
        sha256_pinned=False,
    )
    with (
        patch(_SAFE_RUN_PATH, return_value=_ok_proc()),
        patch(_VERIFY_SHA_PATH) as mock_verify,
    ):
        result = mech.install()

    assert isinstance(result, InstallResult)
    assert result.failed is False, f"unpinned install must succeed; got {result!r}"
    mock_verify.assert_not_called()

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "gitleaks" in captured.err
    assert "DEC-038" in captured.err


def test_unpinned_install_emits_audit_event(in_project: Path) -> None:
    """``sha256_pinned=False`` lands a ``sha_pin_skipped`` event in framework-events."""
    mech = GitHubReleaseBinaryMechanism(
        repo="jqlang/jq",
        binary="jq",
        sha256_pinned=False,
    )
    with patch(_SAFE_RUN_PATH, return_value=_ok_proc()):
        mech.install()

    events = _read_framework_events(in_project)
    assert events, "expected at least one framework event after unpinned install"
    matching = [
        e
        for e in events
        if e.get("detail", {}).get("operation") == "sha_pin_skipped"
        and e.get("detail", {}).get("tool") == "jq"
    ]
    assert matching, f"expected sha_pin_skipped event for jq; got events: {events}"
    detail = matching[0]["detail"]
    assert detail["mechanism"] == "GitHubReleaseBinaryMechanism"
    assert detail["reason"] == "DEC-038 pending"
    assert detail["type"] == "sha_pin_skipped"


def test_unpinned_install_dedups_audit_within_session(in_project: Path) -> None:
    """R-10: a second install of the same tool emits at most one audit event."""
    mech = GitHubReleaseBinaryMechanism(
        repo="koalaman/shellcheck",
        binary="shellcheck",
        sha256_pinned=False,
    )
    with patch(_SAFE_RUN_PATH, return_value=_ok_proc()):
        mech.install()
        mech.install()

    events = _read_framework_events(in_project)
    matching = [
        e
        for e in events
        if e.get("detail", {}).get("operation") == "sha_pin_skipped"
        and e.get("detail", {}).get("tool") == "shellcheck"
    ]
    assert len(matching) == 1, (
        f"expected exactly one dedup'd sha_pin_skipped event; got {len(matching)}"
    )


def test_unpinned_install_propagates_download_failure(in_project: Path) -> None:
    """A failed download returns the failure unchanged -- no audit event fires."""
    mech = GitHubReleaseBinaryMechanism(
        repo="missing/missing",
        binary="missing",
        sha256_pinned=False,
    )

    def _fail(*_args: Any, **_kw: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="curl: 404")

    with (
        patch(_SAFE_RUN_PATH, side_effect=_fail),
        patch("shutil.which", return_value=None),
    ):
        result = mech.install()

    assert result.failed is True

    events = _read_framework_events(in_project)
    assert not [e for e in events if e.get("detail", {}).get("operation") == "sha_pin_skipped"], (
        "skip-audit MUST NOT fire when download failed"
    )


# ---------------------------------------------------------------------------
# Defence-in-depth: pinned + empty digest still raises
# ---------------------------------------------------------------------------


def test_pinned_with_empty_digest_still_raises() -> None:
    """``sha256_pinned=True`` + empty pin keeps raising :class:`Sha256MismatchError`.

    The defence-in-depth contract for spec-101 R-21 must survive spec-113 --
    a future descriptor that declares pinned=True with no digest is still a
    fail-closed event.
    """
    mech = GitHubReleaseBinaryMechanism(
        repo="some/repo",
        binary="some-bin",
        sha256_pinned=True,
        expected_sha256=None,
    )
    with patch(_SAFE_RUN_PATH, return_value=_ok_proc()):
        # _verify_sha256 with empty pin and _PIN_REQUIRED=True raises.
        # We patch Path.exists/open via tmp file because the real verify
        # opens the downloaded artefact; instead, patch the helper itself
        # to assert it gets invoked (NOT the no-op path).
        with (
            patch(
                _VERIFY_SHA_PATH,
                side_effect=Sha256MismatchError(
                    expected="<missing>", received="abc123", path="/tmp/some-bin"
                ),
            ) as mock_verify,
            pytest.raises(Sha256MismatchError),
        ):
            mech.install()
        mock_verify.assert_called_once()
