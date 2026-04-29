"""Tests for spec-113 G-8 / D-113-09: detection-current OK when no remote."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.phases import detect
from ai_engineering.state.models import InstallState


def test_ok_when_vcs_provider_set_and_no_remote(tmp_path: Path) -> None:
    """G-8: vcs_provider set in install state + no git remote => OK with hint."""
    state = InstallState(vcs_provider="github")
    ctx = DoctorContext(target=tmp_path, install_state=state)
    with patch(
        "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
        return_value=None,
    ):
        results = detect.check(ctx)
    current = next(r for r in results if r.name == "detection-current")
    assert current.status == CheckStatus.OK
    assert "github" in current.message
    assert "git remote add origin" in current.message


def test_warn_when_no_provider_and_no_remote(tmp_path: Path) -> None:
    """No vcs_provider + no remote -> still WARN (cannot determine intent)."""
    state = InstallState(vcs_provider=None)
    ctx = DoctorContext(target=tmp_path, install_state=state)
    with patch(
        "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
        return_value=None,
    ):
        results = detect.check(ctx)
    current = next(r for r in results if r.name == "detection-current")
    assert current.status == CheckStatus.WARN


def test_warn_on_real_mismatch(tmp_path: Path) -> None:
    """Real drift between stored and detected -> WARN survives."""
    state = InstallState(vcs_provider="github")
    ctx = DoctorContext(target=tmp_path, install_state=state)
    with patch(
        "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
        return_value="azure_devops",
    ):
        results = detect.check(ctx)
    current = next(r for r in results if r.name == "detection-current")
    assert current.status == CheckStatus.WARN
    assert "mismatch" in current.message.lower()
