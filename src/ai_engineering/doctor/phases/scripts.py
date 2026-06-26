"""Doctor phase: framework scripts deployment integrity (spec-133 D-133-21).

Checks:
- scripts-deployed: All 9 root framework scripts exist on disk under
  ``.ai-engineering/scripts/``.
- scripts-executable: The 2 hook-runtime scripts (regenerate-hooks-manifest,
  runtime_rotate) carry the executable bit so hook-installer machinery
  can call them.
- skill-scripts-lib: spec-128 Wave 4 — the ``skill_scripts_lib`` package and
  ``skill_scripts`` subdir under ``.ai-engineering/scripts/skills/`` are
  importable. Without them ``session_bootstrap.py``, ``commit_compose.py``,
  ``pr_body_compose.py``, and ``standup_render.py`` raise ModuleNotFoundError.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.installer.phases.scripts import ROOT_SCRIPT_FILES
from ai_engineering.installer.templates import get_ai_engineering_template_root

_SCRIPTS_REL = ".ai-engineering/scripts"
_MANIFEST_REL = ".ai-engineering/state/hooks-manifest.json"
_HOOKS_MANIFEST_PREFIX = ".ai-engineering/"
_CHECK_SHA_DRIFT = "hooks-manifest-sha-drift"
_REPIN_SCRIPT_REL = ".ai-engineering/scripts/regenerate-hooks-manifest.py"
_REPIN_TIMEOUT_SEC = 60
_EXECUTABLE_SCRIPTS = frozenset({"regenerate-hooks-manifest.py", "runtime_rotate.py"})
_IS_WINDOWS = os.name == "nt"
_SKILLS_SUBTREE_REL = "skills"
_SKILL_SCRIPTS_LIB_MODULES: tuple[str, ...] = (
    "skill_scripts_lib/__init__.py",
    "skill_scripts_lib/git_activity.py",
    "skill_scripts_lib/markdown_render.py",
    "skill_scripts_lib/manifest_reader.py",
    "skill_scripts/__init__.py",
)


def _check_scripts_deployed(ctx: DoctorContext) -> CheckResult:
    root = Path(ctx.target) / _SCRIPTS_REL
    missing: list[str] = []
    for name in ROOT_SCRIPT_FILES:
        if not (root / name).exists():
            missing.append(name)
    if missing:
        return CheckResult(
            name="scripts-deployed",
            status=CheckStatus.FAIL,
            message=(
                f"{len(missing)} of {len(ROOT_SCRIPT_FILES)} framework scripts "
                f"missing under {_SCRIPTS_REL}/: {missing[:5]}"
                + (" ..." if len(missing) > 5 else "")
            ),
            fixable=True,
        )
    return CheckResult(
        name="scripts-deployed",
        status=CheckStatus.OK,
        message=f"All {len(ROOT_SCRIPT_FILES)} framework scripts present",
        fixable=False,
    )


def _check_scripts_executable(ctx: DoctorContext) -> CheckResult:
    # Windows does not track POSIX executable bits; scripts run via
    # python.exe + .py extension association, not the exec bit. Skip.
    if _IS_WINDOWS:
        return CheckResult(
            name="scripts-executable",
            status=CheckStatus.OK,
            message="Executable bit check skipped on Windows (not applicable)",
            fixable=False,
        )
    root = Path(ctx.target) / _SCRIPTS_REL
    non_exec: list[str] = []
    for name in _EXECUTABLE_SCRIPTS:
        path = root / name
        if path.exists() and not (path.stat().st_mode & 0o100):
            non_exec.append(name)
    if non_exec:
        return CheckResult(
            name="scripts-executable",
            status=CheckStatus.FAIL,
            message=f"Scripts missing executable bit: {non_exec}",
            fixable=True,
        )
    return CheckResult(
        name="scripts-executable",
        status=CheckStatus.OK,
        message="All hook-runtime scripts are executable",
        fixable=False,
    )


def _check_skill_scripts_lib(ctx: DoctorContext) -> CheckResult:
    """Verify spec-128 Wave 4 skill_scripts_lib subtree is on disk.

    Without these files ``session_bootstrap.py`` and three other scripts
    fail at import time with ``ModuleNotFoundError: skill_scripts_lib``.
    """
    skills_root = Path(ctx.target) / _SCRIPTS_REL / _SKILLS_SUBTREE_REL
    missing: list[str] = []
    for rel in _SKILL_SCRIPTS_LIB_MODULES:
        if not (skills_root / rel).exists():
            missing.append(rel)
    if missing:
        return CheckResult(
            name="skill-scripts-lib",
            status=CheckStatus.FAIL,
            message=(
                f"{len(missing)} skill_scripts_lib module(s) missing under "
                f"{_SCRIPTS_REL}/{_SKILLS_SUBTREE_REL}/: {missing[:5]}"
                + (" ..." if len(missing) > 5 else "")
                + " — run `ai-eng install --repair` to redeliver."
            ),
            fixable=True,
        )
    return CheckResult(
        name="skill-scripts-lib",
        status=CheckStatus.OK,
        message="skill_scripts_lib + skill_scripts subtree present",
        fixable=False,
    )


def _normalized_sha256(path: Path) -> str:
    """sha256 of ``path`` with CRLF→LF normalization (matches the manifest)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _load_pins(ctx: DoctorContext) -> dict[str, str]:
    """Return the merged ``hooks`` + ``trustedScripts`` sha pins from the manifest."""
    manifest = Path(ctx.target) / _MANIFEST_REL
    data = json.loads(manifest.read_text(encoding="utf-8"))
    pins: dict[str, str] = {}
    pins.update(data.get("hooks", {}))
    pins.update(data.get("trustedScripts", {}))
    return pins


def _drifted_pins(ctx: DoctorContext) -> list[str]:
    """Return the relative paths whose on-disk sha differs from the manifest pin.

    Missing files are skipped (that is the ``scripts-deployed`` check's concern).
    """
    drifted: list[str] = []
    for rel, pinned in _load_pins(ctx).items():
        path = Path(ctx.target) / rel
        if not path.exists():
            continue
        if _normalized_sha256(path) != pinned:
            drifted.append(rel)
    return drifted


def _check_hooks_manifest_sha_drift(ctx: DoctorContext) -> CheckResult:
    """spec-179 D-179-02: detect sha drift on pinned ``.ai-engineering/scripts/``.

    A WARN (not FAIL) because formatter-induced reflow is recoverable — the
    ``--fix`` path re-pins benign drift. Fail-open on missing/unreadable
    manifest: integrity plumbing absence is not the doctor's failure to raise.
    """
    if not (Path(ctx.target) / _MANIFEST_REL).exists():
        return CheckResult(
            name=_CHECK_SHA_DRIFT,
            status=CheckStatus.OK,
            message="no hooks-manifest.json (skipped)",
            fixable=False,
        )
    try:
        drifted = _drifted_pins(ctx)
    except (OSError, ValueError):
        return CheckResult(
            name=_CHECK_SHA_DRIFT,
            status=CheckStatus.OK,
            message="hooks-manifest.json unreadable (skipped)",
            fixable=False,
        )
    if drifted:
        return CheckResult(
            name=_CHECK_SHA_DRIFT,
            status=CheckStatus.WARN,
            message=(
                f"{len(drifted)} pinned script(s) drifted from hooks-manifest.json "
                f"(likely formatter reflow): {drifted[:5]}"
                + (" ..." if len(drifted) > 5 else "")
                + " — run `ai-eng doctor --fix` to re-pin reflow-only drift."
            ),
            fixable=True,
        )
    return CheckResult(
        name=_CHECK_SHA_DRIFT,
        status=CheckStatus.OK,
        message="all pinned scripts match hooks-manifest.json",
        fixable=False,
    )


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all script-deployment checks for the doctor pipeline."""
    return [
        _check_scripts_deployed(ctx),
        _check_scripts_executable(ctx),
        _check_skill_scripts_lib(ctx),
        _check_hooks_manifest_sha_drift(ctx),
    ]


def _bundled_reference(rel: str) -> Path | None:
    """Resolve the framework's bundled reference copy of a pinned script.

    Manifest keys are repo-relative (``.ai-engineering/scripts/...``); the
    bundled template root already points at ``templates/.ai-engineering``, so
    strip the leading ``.ai-engineering/`` segment. Returns ``None`` when the
    template tree is unavailable (e.g. an sdist without data files) OR when the
    key escapes the bundled root via ``..`` traversal — a tampered manifest key
    must never resolve the "trusted reference" outside the bundled tree, or the
    D-179-03 AST-equivalence check would compare against attacker-chosen bytes.
    """
    if not rel.startswith(_HOOKS_MANIFEST_PREFIX):
        return None
    try:
        root = get_ai_engineering_template_root().resolve()
    except Exception:
        return None
    candidate = (root / rel[len(_HOOKS_MANIFEST_PREFIX) :]).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _is_benign_reflow(on_disk: Path, reference: Path) -> bool:
    """True when ``on_disk`` differs from ``reference`` by formatting only.

    Python files compare by AST (``include_attributes=False`` so line/column
    shifts from reflow do not count); shell/PowerShell scripts fall back to
    CRLF-normalized byte equality. A parse failure or read error is treated as
    NOT benign (fail-closed — never auto-pin what we cannot prove safe).
    """
    if not reference.exists():
        return False
    try:
        disk_bytes = on_disk.read_bytes().replace(b"\r\n", b"\n")
        ref_bytes = reference.read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return False
    if on_disk.suffix == ".py":
        try:
            disk_ast = ast.dump(ast.parse(disk_bytes), include_attributes=False)
            ref_ast = ast.dump(ast.parse(ref_bytes), include_attributes=False)
        except SyntaxError:
            return False
        return disk_ast == ref_ast
    return disk_bytes == ref_bytes


def _repin_manifest(ctx: DoctorContext) -> bool:
    """Re-pin the whole hooks-manifest by invoking the regenerator (atomic walk)."""
    script = Path(ctx.target) / _REPIN_SCRIPT_REL
    if not script.exists():
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ctx.target),
            capture_output=True,
            text=True,
            timeout=_REPIN_TIMEOUT_SEC,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _fix_hooks_manifest_sha_drift(ctx: DoctorContext, *, dry_run: bool) -> CheckResult:
    """spec-179 D-179-03: re-pin drift ONLY when provably reflow-only.

    Re-scans drift on entry (does not trust the failure message). Any drifted
    script that diverges from — or lacks — its bundled reference blocks the
    whole re-pin and is reported for manual review (fail-closed).
    """
    try:
        drifted = _drifted_pins(ctx)
    except (OSError, ValueError):
        return CheckResult(
            name=_CHECK_SHA_DRIFT,
            status=CheckStatus.OK,
            message="hooks-manifest.json unreadable (skipped)",
            fixable=False,
        )
    if not drifted:
        return CheckResult(
            name=_CHECK_SHA_DRIFT,
            status=CheckStatus.OK,
            message="no pinned-script drift remaining",
            fixable=False,
        )
    divergent: list[str] = []
    for rel in drifted:
        reference = _bundled_reference(rel)
        if reference is None or not _is_benign_reflow(Path(ctx.target) / rel, reference):
            divergent.append(rel)
    if divergent:
        return CheckResult(
            name=_CHECK_SHA_DRIFT,
            status=CheckStatus.WARN,
            message=(
                f"{len(divergent)} drifted script(s) diverge from the bundled "
                f"reference — manual review required, NOT auto-pinned: {divergent[:5]}"
                + (" ..." if len(divergent) > 5 else "")
            ),
            fixable=False,
        )
    if dry_run:
        return CheckResult(
            name=_CHECK_SHA_DRIFT,
            status=CheckStatus.FIXED,
            message=f"dry-run: would re-pin {len(drifted)} reflow-only drifted script(s)",
            fixable=False,
        )
    if not _repin_manifest(ctx):
        return CheckResult(
            name=_CHECK_SHA_DRIFT,
            status=CheckStatus.WARN,
            message="re-pin failed (regenerate-hooks-manifest.py unavailable or errored)",
            fixable=False,
        )
    return CheckResult(
        name=_CHECK_SHA_DRIFT,
        status=CheckStatus.FIXED,
        message=f"re-pinned {len(drifted)} reflow-only drifted script(s)",
        fixable=False,
    )


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Dispatch repairs by failed-check name.

    spec-179 D-179-02/03: the manifest-drift fixer is separate from the
    script-deployment redeploy so a drift-only run never re-copies files.
    """
    actionable = {
        cr.name for cr in failed if cr.fixable and cr.status in (CheckStatus.FAIL, CheckStatus.WARN)
    }
    results: list[CheckResult] = []
    deploy_checks = {"scripts-deployed", "scripts-executable", "skill-scripts-lib"}
    if actionable & deploy_checks:
        results.extend(_fix_scripts_deployed(ctx, dry_run=dry_run))
    if _CHECK_SHA_DRIFT in actionable:
        results.append(_fix_hooks_manifest_sha_drift(ctx, dry_run=dry_run))
    return results


def _fix_scripts_deployed(
    ctx: DoctorContext,
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Repair script deployment by re-running ScriptsPhase logic."""
    from ai_engineering.installer.phases import InstallContext, InstallMode
    from ai_engineering.installer.phases.scripts import ScriptsPhase

    target = Path(ctx.target)
    install_ctx = InstallContext(
        target=target,
        mode=InstallMode.REPAIR,
        surfaces=[],
        vcs_provider="github",
        stacks=[],
    )
    phase = ScriptsPhase()

    if dry_run:
        return [
            CheckResult(
                name="scripts-deployed",
                status=CheckStatus.OK,
                message="dry-run: would re-deploy 9 framework scripts",
                fixable=False,
            )
        ]

    plan = phase.plan(install_ctx)
    result = phase.execute(plan, install_ctx)
    verdict = phase.verify(result, install_ctx)
    status = CheckStatus.OK if verdict.passed else CheckStatus.FAIL
    return [
        CheckResult(
            name="scripts-deployed",
            status=status,
            message=(
                f"redeployed: created={len(result.created)} "
                f"skipped={len(result.skipped)} failed={len(result.failed)}"
            ),
            fixable=False,
        )
    ]
