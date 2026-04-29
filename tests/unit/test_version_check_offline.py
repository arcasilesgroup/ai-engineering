"""Tests for spec-113 G-10 / D-113-13: version check offline downgrade."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.runtime import version


def _ctx(tmp_path: Path) -> DoctorContext:
    return DoctorContext(target=tmp_path, install_state=None)


def test_registry_unavailable_emits_ok(tmp_path: Path) -> None:
    """G-10: 'Version registry unavailable' -> OK (network failure is not a problem)."""
    fake = MagicMock(
        status=None,
        is_current=False,
        is_deprecated=False,
        is_eol=False,
        message="Version registry unavailable -- skipping lifecycle check",
    )
    with patch.object(version, "check_version", return_value=fake):
        results = version.check(_ctx(tmp_path))
    assert results[0].status == CheckStatus.OK


def test_version_not_in_registry_emits_ok(tmp_path: Path) -> None:
    """'Version <X> not found in registry' (lookup miss) downgrades to OK too."""
    fake = MagicMock(
        status=None,
        is_current=False,
        is_deprecated=False,
        is_eol=False,
        message="Version 0.5.0 not found in registry",
    )
    with patch.object(version, "check_version", return_value=fake):
        results = version.check(_ctx(tmp_path))
    assert results[0].status == CheckStatus.OK


def test_explicit_deprecation_keeps_fail(tmp_path: Path) -> None:
    """Real deprecation response keeps FAIL."""
    fake = MagicMock(
        status="deprecated",
        is_current=False,
        is_deprecated=True,
        is_eol=False,
        message="0.4.0 (deprecated -- security vulnerability)",
    )
    with patch.object(version, "check_version", return_value=fake):
        results = version.check(_ctx(tmp_path))
    assert results[0].status == CheckStatus.FAIL


def test_outdated_keeps_warn(tmp_path: Path) -> None:
    """Outdated-but-supported version keeps WARN."""
    fake = MagicMock(
        status="supported",
        is_current=False,
        is_deprecated=False,
        is_eol=False,
        message="0.4.0 (outdated -- latest is 0.5.0)",
    )
    with patch.object(version, "check_version", return_value=fake):
        results = version.check(_ctx(tmp_path))
    assert results[0].status == CheckStatus.WARN
