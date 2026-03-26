"""Doctor phase: detect -- validates install-state presence and coherence.

Mirrors the ``detect`` installer phase. Checks that install-state.json
exists, parses correctly, has the expected schema version, that the
detected VCS provider matches the current git remote, and that manifest
stacks match file-system-detected stacks.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.installer.autodetect import detect_stacks
from ai_engineering.state.models import InstallState

logger = logging.getLogger(__name__)

_STATE_REL = ".ai-engineering/state/install-state.json"


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
    """Verify install-state.json exists and is parseable as InstallState."""
    state_path = ctx.target / _STATE_REL
    if not state_path.is_file():
        return CheckResult(
            name="install-state-exists",
            status=CheckStatus.FAIL,
            message=f"install-state.json not found at {state_path}",
        )
    try:
        raw = state_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        InstallState.model_validate(data)
    except (json.JSONDecodeError, OSError) as exc:
        return CheckResult(
            name="install-state-exists",
            status=CheckStatus.FAIL,
            message=f"install-state.json not parseable: {exc}",
        )
    except Exception as exc:
        return CheckResult(
            name="install-state-exists",
            status=CheckStatus.FAIL,
            message=f"install-state.json validation failed: {exc}",
        )
    return CheckResult(
        name="install-state-exists",
        status=CheckStatus.OK,
        message="install-state.json present and valid",
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
    """Warn if the VCS provider in install state doesn't match the current git remote."""
    if ctx.install_state is None:
        return CheckResult(
            name="detection-current",
            status=CheckStatus.WARN,
            message="No install state available; cannot verify VCS provider",
        )
    current_vcs = _detect_vcs_from_remote(ctx.target)
    stored_vcs = ctx.install_state.vcs_provider
    if current_vcs is None:
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
    """Warn when manifest stacks diverge from file-system-detected stacks."""
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
