"""Doctor phase: detect -- validates install-state presence and coherence.

Mirrors the ``detect`` installer phase. Checks that the install_state
singleton row in state.db exists, parses correctly, has the expected
schema version, that the detected VCS provider matches the current git
remote, and that manifest stacks match file-system-detected stacks.

Spec-125: install_state moved from a JSON file (``install-state.json``)
to the ``install_state`` table in ``state.db``. The check now verifies
the singleton row at ``id=1`` is present and decodes to a valid
``InstallState`` model.
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.installer.autodetect import detect_stacks
from ai_engineering.state.service import load_install_state

logger = logging.getLogger(__name__)

_STATE_DB_REL = ".ai-engineering/state/state.db"


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all detect-phase checks."""
    results: list[CheckResult] = []
    results.append(_check_install_state_exists(ctx))
    results.append(_check_install_state_coherent(ctx))
    results.append(_check_detection_current(ctx))
    results.append(_check_stack_drift(ctx))
    return results


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Detect checks are non-fixable. Return failed list unchanged."""
    return list(failed)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_install_state_exists(ctx: DoctorContext) -> CheckResult:
    """Verify the install_state singleton row exists and parses cleanly.

    Spec-125: probes ``state.db`` for the ``install_state`` table and
    reads the singleton row at ``id=1``. The legacy JSON file at
    ``.ai-engineering/state/install-state.json`` is no longer the
    source of truth.
    """
    db_path = ctx.target / _STATE_DB_REL
    if not db_path.is_file():
        return CheckResult(
            name="install-state-exists",
            status=CheckStatus.FAIL,
            message=f"state.db not found at {db_path}",
        )
    try:
        conn = sqlite3.connect(db_path, timeout=2)
        try:
            tbl = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='install_state'"
            ).fetchone()
            if tbl is None:
                return CheckResult(
                    name="install-state-exists",
                    status=CheckStatus.FAIL,
                    message="install_state table missing in state.db",
                )
            row = conn.execute("SELECT 1 FROM install_state WHERE id = 1").fetchone()
            if row is None:
                return CheckResult(
                    name="install-state-exists",
                    status=CheckStatus.FAIL,
                    message="install_state singleton row (id=1) missing",
                )
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return CheckResult(
            name="install-state-exists",
            status=CheckStatus.FAIL,
            message=f"state.db unreadable: {exc}",
        )

    try:
        load_install_state(ctx.target / ".ai-engineering" / "state")
    except Exception as exc:
        return CheckResult(
            name="install-state-exists",
            status=CheckStatus.FAIL,
            message=f"install_state row validation failed: {exc}",
        )
    return CheckResult(
        name="install-state-exists",
        status=CheckStatus.OK,
        message="install_state row present and valid",
    )


def _check_install_state_coherent(ctx: DoctorContext) -> CheckResult:
    """Verify schema_version and operational_readiness are sane."""
    if ctx.install_state is None:
        return CheckResult(
            name="install-state-coherent",
            status=CheckStatus.FAIL,
            message="No install state available (file missing or invalid)",
        )
    problems: list[str] = []
    if ctx.install_state.schema_version != "2.0":
        problems.append(f"schema_version is '{ctx.install_state.schema_version}', expected '2.0'")
    if ctx.install_state.operational_readiness.status == "pending":
        problems.append("operational_readiness.status is 'pending'")
    if problems:
        return CheckResult(
            name="install-state-coherent",
            status=CheckStatus.FAIL,
            message="; ".join(problems),
        )
    return CheckResult(
        name="install-state-coherent",
        status=CheckStatus.OK,
        message="Install state is coherent",
    )


def _check_detection_current(ctx: DoctorContext) -> CheckResult:
    """Verify the install-state VCS provider matches the current git remote.

    spec-113 G-8 / D-113-09: when ``vcs_provider`` is set in install state
    AND the project has no git remote configured yet (typical for a freshly
    installed repo), the check reports OK with an informative message
    instead of warning. The pre-spec-113 behaviour fired a duplicate WARN
    alongside ``tools-vcs`` (gh missing) and ``vcs-auth`` (cannot verify
    auth), all rooted in the same gh-missing reality.
    """
    if ctx.install_state is None:
        return CheckResult(
            name="detection-current",
            status=CheckStatus.WARN,
            message="No install state available; cannot verify VCS provider",
        )
    stored_vcs = ctx.install_state.vcs_provider
    current_vcs = _detect_vcs_from_remote(ctx.target)
    if current_vcs is None:
        # spec-113 G-8: stored provider with no remote configured is the
        # normal post-install state. Surface OK with an actionable hint.
        if stored_vcs:
            return CheckResult(
                name="detection-current",
                status=CheckStatus.OK,
                message=(
                    f"VCS provider '{stored_vcs}' set; no git remote configured "
                    "yet (run: git remote add origin <url>)"
                ),
            )
        return CheckResult(
            name="detection-current",
            status=CheckStatus.WARN,
            message="Could not determine VCS provider from git remote",
        )
    if stored_vcs != current_vcs:
        return CheckResult(
            name="detection-current",
            status=CheckStatus.WARN,
            message=f"VCS mismatch: stored='{stored_vcs}', detected='{current_vcs}'",
        )
    return CheckResult(
        name="detection-current",
        status=CheckStatus.OK,
        message=f"VCS provider matches: {current_vcs}",
    )


def _check_stack_drift(ctx: DoctorContext) -> CheckResult:
    """Warn when manifest stacks diverge from file-system-detected stacks.

    spec-113 G-7 / D-113-08: a freshly-created project (manifest declares
    stacks but the operator has not landed any source files yet) used to
    fire a stack-drift WARN that was just noise -- the user is doing
    nothing wrong, the code just hasn't been written. The new
    suppression: when manifest declares stacks AND ZERO stacks are
    detected on disk, return OK with an informative message. Real drift
    (manifest declares "go" but disk has "python") still fires.
    """
    if ctx.manifest_config is None:
        return CheckResult(
            name="stack-drift",
            status=CheckStatus.WARN,
            message="No manifest config available; cannot verify stack drift",
        )
    manifest_stacks = set(ctx.manifest_config.providers.stacks)
    if not manifest_stacks:
        return CheckResult(
            name="stack-drift",
            status=CheckStatus.WARN,
            message="Manifest providers.stacks is empty",
        )
    detected = set(detect_stacks(ctx.target))

    # spec-113 G-7: suppress when manifest declares stacks but disk is empty.
    # The freshly-installed project case is genuine OK, not noise. The
    # suppression keys on detected being empty (NO stacks present) so a
    # manifest:[python,typescript] vs detected:[python] case still fires
    # genuine drift on the typescript leg.
    if not detected:
        stacks_label = ", ".join(sorted(manifest_stacks))
        return CheckResult(
            name="stack-drift",
            status=CheckStatus.OK,
            message=(
                f"manifest declares {stacks_label}; no source files yet -- "
                "first commit will populate detection"
            ),
        )

    extra_in_manifest = sorted(manifest_stacks - detected)
    missing_from_manifest = sorted(detected - manifest_stacks)
    if extra_in_manifest or missing_from_manifest:
        parts: list[str] = []
        if extra_in_manifest:
            parts.append(f"in manifest but not detected: {', '.join(extra_in_manifest)}")
        if missing_from_manifest:
            parts.append(f"detected but not in manifest: {', '.join(missing_from_manifest)}")
        return CheckResult(
            name="stack-drift",
            status=CheckStatus.WARN,
            message=f"Stack drift: {'; '.join(parts)}",
        )
    return CheckResult(
        name="stack-drift",
        status=CheckStatus.OK,
        message="Manifest stacks match detected stacks",
    )


def _detect_vcs_from_remote(target: Path) -> str | None:
    """Detect VCS provider by inspecting git remote origin URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=target,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        if "dev.azure.com" in url:
            return "azure_devops"
        return "github"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
