"""Enforcement test: every install phase MUST have a doctor phase mirror."""

import importlib
import inspect

import pytest

from ai_engineering.installer.phases import PHASE_ORDER

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("phase_name", PHASE_ORDER)
def test_every_install_phase_has_doctor_phase(phase_name):
    """Guarantee 1:1 parity: adding an install phase without a doctor phase fails CI."""
    mod = importlib.import_module(f"ai_engineering.doctor.phases.{phase_name}")

    assert hasattr(mod, "check"), f"doctor/phases/{phase_name}.py must expose check()"
    check_sig = inspect.signature(mod.check)
    assert "ctx" in check_sig.parameters, "check() must accept ctx: DoctorContext"

    assert hasattr(mod, "fix"), f"doctor/phases/{phase_name}.py must expose fix()"
    fix_sig = inspect.signature(mod.fix)
    assert "ctx" in fix_sig.parameters, "fix() must accept ctx: DoctorContext"
    assert "failed" in fix_sig.parameters, "fix() must accept failed: list[CheckResult]"
    assert "dry_run" in fix_sig.parameters, "fix() must accept dry_run keyword"
