"""spec-179 D-179-02/03 — doctor scripts phase: hooks-manifest sha drift.

The pre-commit gate / PostToolUse formatters used to reflow sha-pinned
``.ai-engineering/scripts/`` files, breaking hook integrity in consumer repos.
The doctor ``scripts`` phase now (a) DETECTS pinned-script sha drift and
(b) under ``--fix`` re-pins it SAFELY: only when the on-disk script is
AST-equivalent (pure reflow) to the framework's bundled reference. Substantive
or unprovable drift is reported, never auto-pinned (fail-closed, D-179-03).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.phases import scripts as scripts_phase

_DRIFT = "hooks-manifest-sha-drift"
_REL = ".ai-engineering/scripts/hooks/sample.py"

_CANONICAL = "def add(a, b):\n    return a + b\n"
# AST-equivalent reflow of _CANONICAL (whitespace/wrapping only).
_REFLOW = "def add(\n    a,\n    b,\n):\n    return a + b\n"
# Real logic change (AST differs).
_DIVERGENT = "def add(a, b):\n    return a - b\n"


def _nsha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest()


def _make_project(tmp_path: Path, *, on_disk: str, pinned_sha: str) -> Path:
    target = tmp_path / "proj"
    hook = target / ".ai-engineering" / "scripts" / "hooks" / "sample.py"
    hook.parent.mkdir(parents=True)
    hook.write_text(on_disk, encoding="utf-8")
    manifest = target / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"hooks": {_REL: pinned_sha}, "trustedScripts": {}}),
        encoding="utf-8",
    )
    return target


def _bundled_template(tmp_path: Path, content: str | None) -> Path:
    """Build a fake ``templates/.ai-engineering`` root holding the reference."""
    root = tmp_path / "templates" / ".ai-engineering"
    if content is not None:
        ref = root / "scripts" / "hooks" / "sample.py"
        ref.parent.mkdir(parents=True)
        ref.write_text(content, encoding="utf-8")
    else:
        root.mkdir(parents=True)
    return root


# ── check: drift detection (T-7) ───────────────────────────────────────


def test_check_ok_when_pins_match(tmp_path: Path) -> None:
    target = _make_project(tmp_path, on_disk=_CANONICAL, pinned_sha=_nsha(_CANONICAL))
    result = next(r for r in scripts_phase.check(DoctorContext(target=target)) if r.name == _DRIFT)
    assert result.status == CheckStatus.OK
    assert result.fixable is False


def test_check_warn_when_pin_drifts(tmp_path: Path) -> None:
    # manifest pins canonical sha; on-disk is reflowed → drift.
    target = _make_project(tmp_path, on_disk=_REFLOW, pinned_sha=_nsha(_CANONICAL))
    result = next(r for r in scripts_phase.check(DoctorContext(target=target)) if r.name == _DRIFT)
    assert result.status == CheckStatus.WARN
    assert result.fixable is True
    assert "sample.py" in result.message


def test_check_skips_when_no_manifest(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    (target / ".ai-engineering").mkdir(parents=True)
    result = next(r for r in scripts_phase.check(DoctorContext(target=target)) if r.name == _DRIFT)
    assert result.status == CheckStatus.OK


# ── fix: safe-by-default re-pin (T-10 / D-179-03) ──────────────────────


def _drift_failure() -> CheckResult:
    return CheckResult(name=_DRIFT, status=CheckStatus.WARN, message="drift", fixable=True)


def test_fix_repins_reflow_only_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _make_project(tmp_path, on_disk=_REFLOW, pinned_sha=_nsha(_CANONICAL))
    monkeypatch.setattr(
        scripts_phase,
        "get_ai_engineering_template_root",
        lambda: _bundled_template(tmp_path, _CANONICAL),
    )
    repinned: list[Path] = []
    monkeypatch.setattr(
        scripts_phase, "_repin_manifest", lambda ctx: repinned.append(ctx.target) or True
    )

    results = scripts_phase.fix(DoctorContext(target=target), [_drift_failure()], dry_run=False)
    drift = next(r for r in results if r.name == _DRIFT)
    assert drift.status == CheckStatus.FIXED
    assert repinned == [target], "reflow-only drift must trigger a re-pin"


def test_fix_warns_on_ast_divergence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _make_project(tmp_path, on_disk=_DIVERGENT, pinned_sha=_nsha(_CANONICAL))
    monkeypatch.setattr(
        scripts_phase,
        "get_ai_engineering_template_root",
        lambda: _bundled_template(tmp_path, _CANONICAL),
    )
    repinned: list[Path] = []
    monkeypatch.setattr(
        scripts_phase, "_repin_manifest", lambda ctx: repinned.append(ctx.target) or True
    )

    results = scripts_phase.fix(DoctorContext(target=target), [_drift_failure()], dry_run=False)
    drift = next(r for r in results if r.name == _DRIFT)
    assert drift.status == CheckStatus.WARN
    assert drift.fixable is False
    assert repinned == [], "AST-divergent drift must NOT be auto-pinned (fail-closed)"


def test_fix_warns_when_reference_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _make_project(tmp_path, on_disk=_REFLOW, pinned_sha=_nsha(_CANONICAL))
    monkeypatch.setattr(
        scripts_phase,
        "get_ai_engineering_template_root",
        lambda: _bundled_template(tmp_path, None),  # no reference file
    )
    repinned: list[Path] = []
    monkeypatch.setattr(
        scripts_phase, "_repin_manifest", lambda ctx: repinned.append(ctx.target) or True
    )

    results = scripts_phase.fix(DoctorContext(target=target), [_drift_failure()], dry_run=False)
    drift = next(r for r in results if r.name == _DRIFT)
    assert drift.status == CheckStatus.WARN
    assert repinned == [], "missing reference cannot prove benign → no auto-pin"


def test_fix_dry_run_does_not_repin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _make_project(tmp_path, on_disk=_REFLOW, pinned_sha=_nsha(_CANONICAL))
    monkeypatch.setattr(
        scripts_phase,
        "get_ai_engineering_template_root",
        lambda: _bundled_template(tmp_path, _CANONICAL),
    )
    repinned: list[Path] = []
    monkeypatch.setattr(
        scripts_phase, "_repin_manifest", lambda ctx: repinned.append(ctx.target) or True
    )

    results = scripts_phase.fix(DoctorContext(target=target), [_drift_failure()], dry_run=True)
    drift = next(r for r in results if r.name == _DRIFT)
    assert drift.status == CheckStatus.FIXED
    assert repinned == [], "dry-run must not invoke the re-pin subprocess"


def test_bundled_reference_rejects_path_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """security-1: a manifest key escaping the bundled root via ``..`` must NOT
    resolve a reference (else the AST check compares against attacker bytes)."""
    root = _bundled_template(tmp_path, _CANONICAL)
    monkeypatch.setattr(scripts_phase, "get_ai_engineering_template_root", lambda: root)
    assert scripts_phase._bundled_reference(".ai-engineering/../evil.py") is None
    assert scripts_phase._bundled_reference(".ai-engineering/../../evil.py") is None
    # A legitimate in-tree key still resolves.
    assert scripts_phase._bundled_reference(_REL) is not None


def test_fix_warns_on_traversal_manifest_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """security-1 end-to-end: drift on a traversal key resolves no trusted
    reference → WARN, never auto-pinned."""
    target = tmp_path / "proj"
    # Key ".ai-engineering/../evil.py" resolves to <target>/evil.py.
    hook = target / "evil.py"
    hook.parent.mkdir(parents=True)
    hook.write_text(_DIVERGENT, encoding="utf-8")
    manifest = target / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {"hooks": {".ai-engineering/../evil.py": _nsha(_CANONICAL)}, "trustedScripts": {}}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        scripts_phase,
        "get_ai_engineering_template_root",
        lambda: _bundled_template(tmp_path, _CANONICAL),
    )
    repinned: list[Path] = []
    monkeypatch.setattr(
        scripts_phase, "_repin_manifest", lambda ctx: repinned.append(ctx.target) or True
    )

    results = scripts_phase.fix(DoctorContext(target=target), [_drift_failure()], dry_run=False)
    drift = next(r for r in results if r.name == _DRIFT)
    assert drift.status == CheckStatus.WARN
    assert repinned == [], "traversal key must not be auto-pinned"


def test_fix_still_redeploys_missing_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-regression: when a scripts-deployment check failed, the existing
    redeploy path still runs (dispatch must not swallow it)."""
    target = _make_project(tmp_path, on_disk=_CANONICAL, pinned_sha=_nsha(_CANONICAL))
    failed = CheckResult(
        name="scripts-deployed", status=CheckStatus.FAIL, message="missing", fixable=True
    )
    results = scripts_phase.fix(DoctorContext(target=target), [failed], dry_run=True)
    assert any(r.name == "scripts-deployed" for r in results)
