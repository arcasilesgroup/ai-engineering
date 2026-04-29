"""Tests for spec-113 G-7 / D-113-08: stack-drift suppression on empty projects."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.phases import detect


class _StackProviders:
    def __init__(self, stacks: list[str]) -> None:
        self.stacks = list(stacks)


class _Manifest:
    def __init__(self, stacks: list[str]) -> None:
        self.providers = _StackProviders(stacks)


def _ctx(tmp_path: Path, stacks: list[str]) -> DoctorContext:
    return DoctorContext(
        target=tmp_path,
        manifest_config=_Manifest(stacks),
        install_state=None,
    )


def test_stack_drift_suppressed_when_disk_empty(tmp_path: Path) -> None:
    """G-7: manifest declares stacks but no disk detection -> OK + informative hint."""
    with patch("ai_engineering.doctor.phases.detect.detect_stacks", return_value=[]):
        results = detect.check(_ctx(tmp_path, ["python", "typescript"]))
    drift = next(r for r in results if r.name == "stack-drift")
    assert drift.status == CheckStatus.OK
    assert "no source files yet" in drift.message
    assert "python" in drift.message
    assert "typescript" in drift.message


def test_stack_drift_real_drift_still_warns(tmp_path: Path) -> None:
    """Real drift (manifest says go but disk has python) keeps the WARN."""
    with patch(
        "ai_engineering.doctor.phases.detect.detect_stacks",
        return_value=["python"],
    ):
        results = detect.check(_ctx(tmp_path, ["go"]))
    drift = next(r for r in results if r.name == "stack-drift")
    assert drift.status == CheckStatus.WARN
    assert "go" in drift.message
    assert "python" in drift.message


def test_stack_drift_partial_match_still_warns(tmp_path: Path) -> None:
    """Manifest [python, typescript], disk [python] still WARNs on typescript leg."""
    with patch(
        "ai_engineering.doctor.phases.detect.detect_stacks",
        return_value=["python"],
    ):
        results = detect.check(_ctx(tmp_path, ["python", "typescript"]))
    drift = next(r for r in results if r.name == "stack-drift")
    assert drift.status == CheckStatus.WARN
    assert "typescript" in drift.message


def test_stack_drift_perfect_match_is_ok(tmp_path: Path) -> None:
    """No drift -> OK as before."""
    with patch(
        "ai_engineering.doctor.phases.detect.detect_stacks",
        return_value=["python"],
    ):
        results = detect.check(_ctx(tmp_path, ["python"]))
    drift = next(r for r in results if r.name == "stack-drift")
    assert drift.status == CheckStatus.OK
