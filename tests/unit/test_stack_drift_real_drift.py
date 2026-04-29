"""Companion test for spec-113 G-7: real drift survives the suppression.

The G-7 suppression only fires when the disk has ZERO detected stacks. As
soon as ANY stack is detected, the comparison resumes and surfaces real
drift. This test fixture is the load-bearing assertion that the safe-by-
default WARN survives the empty-project carve-out.
"""

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


def test_real_drift_still_warns_after_suppression(tmp_path: Path) -> None:
    """Manifest declares Go; disk has Python -> WARN survives."""
    with patch(
        "ai_engineering.doctor.phases.detect.detect_stacks",
        return_value=["python"],
    ):
        results = detect.check(_ctx(tmp_path, ["go"]))
    drift = next(r for r in results if r.name == "stack-drift")
    assert drift.status == CheckStatus.WARN
    assert "Stack drift" in drift.message
