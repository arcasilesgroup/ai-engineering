"""Tests for ``ai-eng doctor --fix`` stack-drift repair (spec-133 D-133-25)."""

from __future__ import annotations

from pathlib import Path


def _write_manifest(root: Path, stacks: list[str]) -> None:
    (root / ".ai-engineering").mkdir(parents=True, exist_ok=True)
    yml = root / ".ai-engineering" / "manifest.yml"
    yml.write_text(
        "schema_version: '2.0'\n"
        "framework_version: '0.4.0'\n"
        "name: test\n"
        "providers:\n"
        f"  stacks: [{', '.join(stacks)}]\n"
        "  vcs: github\n",
        encoding="utf-8",
    )


def test_resolve_stacks_returns_empty_when_manifest_has_no_stacks(tmp_path: Path) -> None:
    """spec-133 D-133-25 / B16 Gap 1+2: greenfield drops or ['python'] coercion.

    When a manifest explicitly carries an empty ``providers.stacks`` list,
    ``_resolve_stacks`` returns ``[]`` instead of coercing to ``["python"]``.
    The legacy default behaviour (defaulting to python when no manifest at
    all) is preserved for back-compat.
    """
    (tmp_path / ".ai-engineering").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "manifest.yml").write_text(
        "schema_version: '2.0'\nproviders:\n  stacks: []\n  vcs: github\n",
        encoding="utf-8",
    )
    from ai_engineering.doctor.models import DoctorContext
    from ai_engineering.doctor.phases.tools import _resolve_stacks

    ctx = DoctorContext(target=tmp_path, install_state=None, manifest_config=None)
    assert _resolve_stacks(ctx) == []


def test_doctor_phase_scripts_check_detects_missing_scripts(tmp_path: Path) -> None:
    from ai_engineering.doctor.models import DoctorContext
    from ai_engineering.doctor.phases.scripts import check

    ctx = DoctorContext(target=tmp_path, install_state=None, manifest_config=None)
    results = check(ctx)
    assert any(r.name == "scripts-deployed" for r in results)


def test_doctor_phase_scripts_fix_redeploys(tmp_path: Path) -> None:
    """Fix mode redeploys missing scripts idempotently."""
    from ai_engineering.doctor.models import DoctorContext
    from ai_engineering.doctor.phases.scripts import check, fix

    ctx = DoctorContext(target=tmp_path, install_state=None, manifest_config=None)
    failed = check(ctx)
    fix_results = fix(ctx, failed=failed, dry_run=False)
    # Scripts should now exist on disk
    deployed = tmp_path / ".ai-engineering" / "scripts"
    assert (deployed / "session_bootstrap.py").exists()
    assert (deployed / "spec_lifecycle.py").exists()


def test_doctor_phase_scripts_fix_dry_run_reports_no_changes(tmp_path: Path) -> None:
    from ai_engineering.doctor.models import DoctorContext
    from ai_engineering.doctor.phases.scripts import check, fix

    ctx = DoctorContext(target=tmp_path, install_state=None, manifest_config=None)
    failed = check(ctx)
    results = fix(ctx, failed=failed, dry_run=True)
    # Dry-run leaves disk untouched
    deployed = tmp_path / ".ai-engineering" / "scripts"
    assert not deployed.exists() or not list(deployed.glob("*.py"))
    assert all("dry-run" in r.message.lower() for r in results)
