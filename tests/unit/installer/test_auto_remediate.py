"""Tests for spec-109 D-109-05 install auto-remediation helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.doctor.models import CheckResult, CheckStatus
from ai_engineering.installer import auto_remediate as ar
from ai_engineering.installer.phases import PHASE_HOOKS, PHASE_TOOLS


class _FakeModule:
    """Stub doctor module exposing check + fix used by the remediation table."""

    def __init__(
        self,
        check_results: list[CheckResult],
        fix_results: list[CheckResult] | None = None,
        check_raises: BaseException | None = None,
        fix_raises: BaseException | None = None,
    ) -> None:
        self._check_results = check_results
        self._fix_results = fix_results or []
        self._check_raises = check_raises
        self._fix_raises = fix_raises
        self.fix_calls: list[list[CheckResult]] = []

    def check(self, ctx) -> list[CheckResult]:
        if self._check_raises is not None:
            raise self._check_raises
        return list(self._check_results)

    def fix(self, ctx, failed, *, dry_run: bool = False) -> list[CheckResult]:
        self.fix_calls.append(list(failed))
        if self._fix_raises is not None:
            raise self._fix_raises
        return list(self._fix_results)


@pytest.fixture
def install_table(monkeypatch):
    """Patch the remediation table with stub modules; return them by phase."""
    table: dict[str, _FakeModule] = {}

    def install(phase: str, module: _FakeModule) -> None:
        table[phase] = module
        monkeypatch.setitem(ar._REMEDIATION_TABLE, phase, (module, module))

    install._table = table  # type: ignore[attr-defined]
    return install


def test_no_failures_returns_uninvoked_report(tmp_path: Path) -> None:
    """When the pipeline reports zero non-critical failures, remediate is a no-op."""
    report = ar.auto_remediate_after_install(tmp_path, [])
    assert report.invoked is False
    assert report.success is False  # never invoked => not a success either
    assert report.applied == []
    assert report.failed == []


def test_remediates_tools_phase_via_doctor(tmp_path: Path, install_table) -> None:
    """A tools failure flows through doctor.tools.check + fix and surfaces as applied."""
    fake = _FakeModule(
        check_results=[
            CheckResult(
                name="tools-required",
                status=CheckStatus.FAIL,
                message="missing tools: gitleaks",
                fixable=True,
            )
        ],
        fix_results=[
            CheckResult(
                name="tools-required",
                status=CheckStatus.FIXED,
                message="installed: gitleaks",
            )
        ],
    )
    install_table(PHASE_TOOLS, fake)

    report = ar.auto_remediate_after_install(tmp_path, [PHASE_TOOLS])

    assert report.invoked is True
    assert report.success is True
    assert report.applied == ["tools.tools-required: installed: gitleaks"]
    assert report.failed == []
    assert len(fake.fix_calls) == 1
    assert fake.fix_calls[0][0].name == "tools-required"


def test_non_fixable_failure_reported_as_manual(tmp_path: Path, install_table) -> None:
    """Doctor checks that report fail without ``fixable=True`` go to ``failed``."""
    fake = _FakeModule(
        check_results=[
            CheckResult(
                name="tools-required",
                status=CheckStatus.FAIL,
                message="manual remediation only",
                fixable=False,
            )
        ],
    )
    install_table(PHASE_TOOLS, fake)

    report = ar.auto_remediate_after_install(tmp_path, [PHASE_TOOLS])

    assert report.invoked is True
    assert report.success is False
    assert report.applied == []
    assert report.failed == ["tools.tools-required: manual remediation only"]
    assert fake.fix_calls == []  # fix() never invoked because nothing was fixable


def test_fix_raises_recorded_as_error(tmp_path: Path, install_table) -> None:
    """Exceptions from fix() surface as errors but never propagate."""
    fake = _FakeModule(
        check_results=[
            CheckResult(
                name="tools-required",
                status=CheckStatus.FAIL,
                message="x",
                fixable=True,
            )
        ],
        fix_raises=RuntimeError("boom"),
    )
    install_table(PHASE_TOOLS, fake)

    report = ar.auto_remediate_after_install(tmp_path, [PHASE_TOOLS])

    assert report.invoked is True
    assert report.success is False
    assert any("tools.fix raised: boom" in e for e in report.errors)
    assert any("tools: fix failed" in f for f in report.failed)


def test_unknown_phase_reported_without_remediation(tmp_path: Path) -> None:
    """A phase with no remediation table entry surfaces a clear failure note."""
    report = ar.auto_remediate_after_install(tmp_path, ["unknown_phase"])
    assert report.invoked is True
    assert report.success is False
    assert "unknown_phase: no auto-remediation registered" in report.failed


def test_remediates_tools_and_hooks_in_order(tmp_path: Path, install_table) -> None:
    """When BOTH tools and hooks failed, both are remediated; order honors input."""
    tools = _FakeModule(
        check_results=[
            CheckResult(
                name="tools-required",
                status=CheckStatus.FAIL,
                message="missing: gitleaks",
                fixable=True,
            )
        ],
        fix_results=[
            CheckResult(
                name="tools-required",
                status=CheckStatus.FIXED,
                message="installed: gitleaks",
            )
        ],
    )
    hooks = _FakeModule(
        check_results=[
            CheckResult(
                name="hooks-integrity",
                status=CheckStatus.FAIL,
                message="hook verification failed: pre-commit",
                fixable=True,
            )
        ],
        fix_results=[
            CheckResult(
                name="hooks-integrity",
                status=CheckStatus.FIXED,
                message="reinstalled hooks: pre-commit",
            )
        ],
    )
    install_table(PHASE_TOOLS, tools)
    install_table(PHASE_HOOKS, hooks)

    report = ar.auto_remediate_after_install(tmp_path, [PHASE_TOOLS, PHASE_HOOKS])

    assert report.invoked is True
    assert report.success is True
    assert len(report.applied) == 2
    assert "tools.tools-required" in report.applied[0]
    assert "hooks.hooks-integrity" in report.applied[1]


def test_to_dict_round_trip_shape(tmp_path: Path) -> None:
    """JSON envelope serialisation surface is stable + additive."""
    rep = ar.AutoRemediateReport(
        invoked=True,
        applied=["a"],
        failed=["b"],
        errors=["c"],
    )
    data = rep.to_dict()
    assert set(data.keys()) == {"invoked", "success", "applied", "failed", "errors"}
    assert data["invoked"] is True
    assert data["success"] is False  # has failed entries -> not a success
