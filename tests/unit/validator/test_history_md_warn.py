"""Tests for ``_record_spec_buffer_result`` WARN downgrade (spec-132
D-132-09 + spec-133 pristine-install suppression).

spec-131 D-131-04 established ``/ai-repo-tidy`` as the lifecycle owner of
``.ai-engineering/specs/_history.md``; installer must not ship a stub
nor hard-fail when the file is absent at install time.

spec-133 layered a pristine-install guard on top: when the consumer
repo has zero commits, the WARN itself is suppressed (status OK) so
first contact is silent. Once the repo is established (any commit
exists), the WARN re-engages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.state.work_plane import ActiveWorkPlane
from ai_engineering.validator._shared import IntegrityReport, IntegrityStatus
from ai_engineering.validator.categories.file_existence import _record_spec_buffer_result


def _seed_established_repo(target: Path) -> None:
    """Create a ``.git`` tree that ``_is_pristine_install`` treats as established."""
    git_dir = target / ".git"
    (git_dir / "refs" / "heads").mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "refs" / "heads" / "main").write_text("0" * 40 + "\n", encoding="utf-8")


@pytest.fixture()
def work_plane(tmp_path: Path) -> ActiveWorkPlane:
    """Build an ActiveWorkPlane with spec.md + plan.md but NO _history.md."""
    specs_dir = tmp_path / ".ai-engineering" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    spec_path = specs_dir / "spec.md"
    plan_path = specs_dir / "plan.md"
    history_path = specs_dir / "_history.md"
    spec_path.write_text("# spec\n", encoding="utf-8")
    plan_path.write_text("# plan\n", encoding="utf-8")
    # _history.md deliberately NOT created -- /ai-repo-tidy writes it later.
    return ActiveWorkPlane(
        project_root=tmp_path,
        ai_eng_dir=tmp_path / ".ai-engineering",
        specs_dir=specs_dir,
        spec_path=spec_path,
        plan_path=plan_path,
        history_path=history_path,
    )


def test_missing_history_md_is_warn_on_established_repo(work_plane: ActiveWorkPlane) -> None:
    """spec-132 D-132-09: missing _history.md with spec+plan present is WARN
    once the consumer repo has any commits (established install)."""
    _seed_established_repo(work_plane.project_root)
    report = IntegrityReport()
    _record_spec_buffer_result(report, work_plane)

    spec_checks = [c for c in report.checks if c.name == "spec-buffer"]
    assert len(spec_checks) == 1, "exactly one spec-buffer check should be recorded"
    check = spec_checks[0]
    assert check.status == IntegrityStatus.WARN, (
        f"_history.md absence should warn on established repo; got {check.status}"
    )
    assert "_history.md" in check.message


def test_missing_history_md_is_ok_on_pristine_install(work_plane: ActiveWorkPlane) -> None:
    """spec-133: missing _history.md on a pristine install (no commits) is OK."""
    # Deliberately do NOT seed .git -- pristine install.
    report = IntegrityReport()
    _record_spec_buffer_result(report, work_plane)

    spec_checks = [c for c in report.checks if c.name == "spec-buffer"]
    assert len(spec_checks) == 1, "exactly one spec-buffer check should be recorded"
    check = spec_checks[0]
    assert check.status == IntegrityStatus.OK, (
        f"_history.md absence on pristine install should be OK; got {check.status}"
    )
    assert "pristine install" in check.message


def test_all_three_present_is_ok(tmp_path: Path) -> None:
    """When all three files exist the result is OK (existing behaviour)."""
    specs_dir = tmp_path / ".ai-engineering" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    for name in ("spec.md", "plan.md", "_history.md"):
        (specs_dir / name).write_text("# header\n", encoding="utf-8")

    work_plane = ActiveWorkPlane(
        project_root=tmp_path,
        ai_eng_dir=tmp_path / ".ai-engineering",
        specs_dir=specs_dir,
        spec_path=specs_dir / "spec.md",
        plan_path=specs_dir / "plan.md",
        history_path=specs_dir / "_history.md",
    )
    report = IntegrityReport()
    _record_spec_buffer_result(report, work_plane)

    assert report.checks[-1].status == IntegrityStatus.OK


def test_missing_spec_md_is_still_fail(tmp_path: Path) -> None:
    """When spec.md is missing the WARN downgrade does NOT apply.

    The downgrade gate is "spec.md + plan.md exist". If spec.md is
    missing, the install is genuinely incomplete and FAIL is correct.
    """
    specs_dir = tmp_path / ".ai-engineering" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    # spec.md absent.

    work_plane = ActiveWorkPlane(
        project_root=tmp_path,
        ai_eng_dir=tmp_path / ".ai-engineering",
        specs_dir=specs_dir,
        spec_path=specs_dir / "spec.md",
        plan_path=specs_dir / "plan.md",
        history_path=specs_dir / "_history.md",
    )
    report = IntegrityReport()
    _record_spec_buffer_result(report, work_plane)

    spec_checks = [c for c in report.checks if c.name == "spec-buffer"]
    assert spec_checks[0].status == IntegrityStatus.FAIL
