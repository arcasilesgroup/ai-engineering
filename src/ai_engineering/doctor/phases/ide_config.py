"""Doctor phase: ide_config -- validates IDE provider template deployment.

Mirrors the ``ide_config`` installer phase. Checks that provider-specific
template files exist and that Claude Code settings.json contains required
deny rules.
"""

from __future__ import annotations

import json
import logging

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.installer.templates import resolve_template_maps

logger = logging.getLogger(__name__)


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all ide_config-phase checks."""
    results: list[CheckResult] = []
    results.append(_check_provider_templates(ctx))
    results.append(_check_settings_merge(ctx))
    return results


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """IDE config checks are not fixable by doctor. Return failed unchanged."""
    return list(failed)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_provider_templates(ctx: DoctorContext) -> CheckResult:
    """Check that expected IDE provider template files exist."""
    if ctx.manifest_config is None:
        return CheckResult(
            name="provider-templates",
            status=CheckStatus.FAIL,
            message="No manifest config available; cannot determine providers",
        )
    ides = ctx.manifest_config.providers.ides
    if not ides:
        return CheckResult(
            name="provider-templates",
            status=CheckStatus.OK,
            message="No IDE providers configured",
        )
    vcs = ctx.manifest_config.providers.vcs
    maps = resolve_template_maps(providers=ides, vcs_provider=vcs)

    missing: list[str] = []

    # Check provider-specific files
    for _src, dest in maps.file_map.items():
        if not (ctx.target / dest).exists():
            missing.append(dest)

    # Check provider-specific tree roots
    for _src_tree, dest_tree in maps.tree_list:
        if not (ctx.target / dest_tree).is_dir():
            missing.append(dest_tree)

    # Check common files
    for _src, dest in maps.common_file_map.items():
        if not (ctx.target / dest).exists():
            missing.append(dest)

    if missing:
        return CheckResult(
            name="provider-templates",
            status=CheckStatus.FAIL,
            message=f"Missing provider templates: {', '.join(missing)}",
        )
    return CheckResult(
        name="provider-templates",
        status=CheckStatus.OK,
        message="All provider templates present",
    )


def _check_settings_merge(ctx: DoctorContext) -> CheckResult:
    """Check Claude Code settings.json for deny rules if claude_code is active."""
    if ctx.manifest_config is None:
        return CheckResult(
            name="settings-merge",
            status=CheckStatus.OK,
            message="No manifest config available; skipping settings check",
        )
    ides = ctx.manifest_config.providers.ides
    if "claude_code" not in ides:
        return CheckResult(
            name="settings-merge",
            status=CheckStatus.OK,
            message="Claude Code not in providers; skipping settings check",
        )
    settings_path = ctx.target / ".claude" / "settings.json"
    if not settings_path.is_file():
        return CheckResult(
            name="settings-merge",
            status=CheckStatus.WARN,
            message=".claude/settings.json not found",
        )
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return CheckResult(
            name="settings-merge",
            status=CheckStatus.FAIL,
            message=f".claude/settings.json not parseable: {exc}",
        )
    permissions = data.get("permissions", {})
    if "deny" not in permissions:
        return CheckResult(
            name="settings-merge",
            status=CheckStatus.FAIL,
            message=".claude/settings.json missing 'deny' key in permissions",
        )
    return CheckResult(
        name="settings-merge",
        status=CheckStatus.OK,
        message=".claude/settings.json contains deny rules",
    )
