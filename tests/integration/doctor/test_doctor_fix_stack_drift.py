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
    fix(ctx, failed=failed, dry_run=False)
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


def test_doctor_fix_repins_reflow_drift_via_real_regenerator(tmp_path: Path, monkeypatch) -> None:
    """spec-179 D-179-03 end-to-end: a reflow-only drifted pinned script is
    re-pinned through the REAL ``regenerate-hooks-manifest.py`` subprocess, and a
    follow-up check reports clean. Exercises ``_repin_manifest`` for real (unit
    tests mock it)."""
    import hashlib
    import json
    import shutil

    from ai_engineering.doctor.models import CheckStatus, DoctorContext
    from ai_engineering.doctor.phases import scripts as scripts_phase

    repo = Path(scripts_phase.__file__).resolve().parents[4]
    canonical = "def add(a, b):\n    return a + b\n"
    reflow = "def add(\n    a,\n    b,\n):\n    return a + b\n"

    def nsha(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest()

    target = tmp_path / "proj"
    regen_dst = target / ".ai-engineering" / "scripts" / "regenerate-hooks-manifest.py"
    regen_dst.parent.mkdir(parents=True)
    shutil.copy2(repo / ".ai-engineering" / "scripts" / "regenerate-hooks-manifest.py", regen_dst)

    hook = target / ".ai-engineering" / "scripts" / "hooks" / "sample.py"
    hook.parent.mkdir(parents=True)
    hook.write_text(reflow, encoding="utf-8")

    rel = ".ai-engineering/scripts/hooks/sample.py"
    manifest = target / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"hooks": {rel: nsha(canonical)}, "trustedScripts": {}}),
        encoding="utf-8",
    )

    tmpl = tmp_path / "templates" / ".ai-engineering"
    ref = tmpl / "scripts" / "hooks" / "sample.py"
    ref.parent.mkdir(parents=True)
    ref.write_text(canonical, encoding="utf-8")
    monkeypatch.setattr(scripts_phase, "get_ai_engineering_template_root", lambda: tmpl)

    ctx = DoctorContext(target=target, install_state=None, manifest_config=None)
    drift = next(r for r in scripts_phase.check(ctx) if r.name == "hooks-manifest-sha-drift")
    assert drift.status == CheckStatus.WARN and drift.fixable

    results = scripts_phase.fix(ctx, [drift], dry_run=False)
    fixed = next(r for r in results if r.name == "hooks-manifest-sha-drift")
    assert fixed.status == CheckStatus.FIXED, fixed.message

    after = json.loads(manifest.read_text(encoding="utf-8"))
    assert after["hooks"][rel] == nsha(reflow), "manifest must be re-pinned to on-disk bytes"
    drift2 = next(r for r in scripts_phase.check(ctx) if r.name == "hooks-manifest-sha-drift")
    assert drift2.status == CheckStatus.OK, "re-check must be clean after re-pin"
