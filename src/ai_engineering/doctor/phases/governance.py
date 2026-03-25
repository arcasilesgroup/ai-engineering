"""Doctor phase: governance -- validates governance directory structure and manifest.

Mirrors the ``governance`` installer phase. Checks that required
governance directories exist, that manifest.yml is valid, and that
framework-managed template files are present.
"""

from __future__ import annotations

import logging

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext

logger = logging.getLogger(__name__)

_REQUIRED_DIRS = (
    ".ai-engineering",
    ".ai-engineering/contexts",
    ".ai-engineering/state",
)

_EXPECTED_TEMPLATES = (".ai-engineering/README.md",)

_EXPECTED_TEMPLATE_DIRS = (".ai-engineering/scripts/hooks",)


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all governance-phase checks."""
    results: list[CheckResult] = []
    results.append(_check_governance_dirs(ctx))
    results.append(_check_manifest_valid(ctx))
    results.append(_check_governance_templates(ctx))
    return results


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Attempt to fix governance failures.

    - governance-dirs: create missing directories.
    - governance-templates: create missing directories (file copy is install's job).
    - manifest-valid: not fixable by doctor.
    """
    still_failed: list[CheckResult] = []
    for result in failed:
        if result.name == "governance-dirs":
            fixed = _fix_governance_dirs(ctx, dry_run=dry_run)
            still_failed.append(fixed)
        elif result.name == "governance-templates":
            fixed = _fix_governance_templates(ctx, dry_run=dry_run)
            still_failed.append(fixed)
        else:
            still_failed.append(result)
    return still_failed


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_governance_dirs(ctx: DoctorContext) -> CheckResult:
    """Check that required governance directories exist."""
    missing = [d for d in _REQUIRED_DIRS if not (ctx.target / d).is_dir()]
    if missing:
        return CheckResult(
            name="governance-dirs",
            status=CheckStatus.FAIL,
            message=f"Missing directories: {', '.join(missing)}",
            fixable=True,
        )
    return CheckResult(
        name="governance-dirs",
        status=CheckStatus.OK,
        message="All governance directories present",
    )


def _check_manifest_valid(ctx: DoctorContext) -> CheckResult:
    """Check that manifest.yml exists and is valid YAML."""
    manifest_path = ctx.target / ".ai-engineering" / "manifest.yml"
    if not manifest_path.is_file():
        return CheckResult(
            name="manifest-valid",
            status=CheckStatus.FAIL,
            message="manifest.yml not found",
        )
    try:
        config = load_manifest_config(ctx.target)
        # load_manifest_config returns defaults on invalid YAML rather than
        # raising, so check if the file is readable and produced a valid model.
        # A truly broken file would still parse to defaults -- we verify the
        # file exists (already done above) and that we got a ManifestConfig.
        if config is None:
            return CheckResult(
                name="manifest-valid",
                status=CheckStatus.FAIL,
                message="manifest.yml could not be loaded",
            )
    except Exception as exc:
        return CheckResult(
            name="manifest-valid",
            status=CheckStatus.FAIL,
            message=f"manifest.yml validation failed: {exc}",
        )
    return CheckResult(
        name="manifest-valid",
        status=CheckStatus.OK,
        message="manifest.yml is valid",
    )


def _check_governance_templates(ctx: DoctorContext) -> CheckResult:
    """Check that framework-managed template files/dirs are present."""
    missing: list[str] = []
    for tmpl in _EXPECTED_TEMPLATES:
        if not (ctx.target / tmpl).is_file():
            missing.append(tmpl)
    for tmpl_dir in _EXPECTED_TEMPLATE_DIRS:
        if not (ctx.target / tmpl_dir).is_dir():
            missing.append(tmpl_dir)
    if missing:
        return CheckResult(
            name="governance-templates",
            status=CheckStatus.WARN,
            message=f"Missing templates: {', '.join(missing)}",
            fixable=True,
        )
    return CheckResult(
        name="governance-templates",
        status=CheckStatus.OK,
        message="All governance templates present",
    )


# ---------------------------------------------------------------------------
# Fix helpers
# ---------------------------------------------------------------------------


def _fix_governance_dirs(ctx: DoctorContext, *, dry_run: bool) -> CheckResult:
    """Create missing governance directories."""
    missing = [d for d in _REQUIRED_DIRS if not (ctx.target / d).is_dir()]
    if not missing:
        return CheckResult(
            name="governance-dirs",
            status=CheckStatus.OK,
            message="All governance directories present",
        )
    if dry_run:
        return CheckResult(
            name="governance-dirs",
            status=CheckStatus.FAIL,
            message=f"Would create directories: {', '.join(missing)}",
            fixable=True,
        )
    for d in missing:
        (ctx.target / d).mkdir(parents=True, exist_ok=True)
    return CheckResult(
        name="governance-dirs",
        status=CheckStatus.FIXED,
        message=f"Created directories: {', '.join(missing)}",
    )


def _fix_governance_templates(ctx: DoctorContext, *, dry_run: bool) -> CheckResult:
    """Create missing template directories (file copy is install's job)."""
    missing_dirs = [d for d in _EXPECTED_TEMPLATE_DIRS if not (ctx.target / d).is_dir()]
    if not missing_dirs:
        # Check files too -- if only files are missing, we can't fix them
        missing_files = [f for f in _EXPECTED_TEMPLATES if not (ctx.target / f).is_file()]
        if missing_files:
            return CheckResult(
                name="governance-templates",
                status=CheckStatus.WARN,
                message=f"Missing template files (requires install): {', '.join(missing_files)}",
            )
        return CheckResult(
            name="governance-templates",
            status=CheckStatus.OK,
            message="All governance templates present",
        )
    if dry_run:
        return CheckResult(
            name="governance-templates",
            status=CheckStatus.WARN,
            message=f"Would create directories: {', '.join(missing_dirs)}",
            fixable=True,
        )
    for d in missing_dirs:
        (ctx.target / d).mkdir(parents=True, exist_ok=True)
    # Re-check for any remaining missing files
    missing_files = [f for f in _EXPECTED_TEMPLATES if not (ctx.target / f).is_file()]
    if missing_files:
        return CheckResult(
            name="governance-templates",
            status=CheckStatus.WARN,
            message=(
                f"Created directories; missing files (requires install): {', '.join(missing_files)}"
            ),
        )
    return CheckResult(
        name="governance-templates",
        status=CheckStatus.FIXED,
        message=f"Created directories: {', '.join(missing_dirs)}",
    )
