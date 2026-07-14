"""spec-184 D-184-05: doctor framework-drift CheckResult (advise-only)."""

from __future__ import annotations

from pathlib import Path

from ai_engineering import __version__
from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.phases.detect import _check_framework_drift


def _ctx(framework_version: str | None) -> DoctorContext:
    cfg = (
        ManifestConfig(framework_version=framework_version)
        if framework_version is not None
        else None
    )
    return DoctorContext(target=Path("."), manifest_config=cfg)


def test_warn_when_behind() -> None:
    result = _check_framework_drift(_ctx("0.0.1"))
    assert result.name == "framework-drift"
    assert result.status is CheckStatus.WARN  # advise-only, never FAIL
    assert "ai-eng update" in result.message


def test_ok_when_current() -> None:
    result = _check_framework_drift(_ctx(__version__))
    assert result.status is CheckStatus.OK


def test_ok_when_no_manifest() -> None:
    result = _check_framework_drift(_ctx(None))
    assert result.status is CheckStatus.OK  # no manifest → no drift, no nag


def test_never_fail_status() -> None:
    # advise-only invariant: this check must NEVER return FAIL
    for v in ("0.0.1", __version__, ""):
        assert _check_framework_drift(_ctx(v)).status is not CheckStatus.FAIL
