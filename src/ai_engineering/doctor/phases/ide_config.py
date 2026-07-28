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
    results.append(_check_permissions_wildcard(ctx))
    results.append(_check_retired_surface_trees(ctx))
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
    """Check that expected Surface template files exist."""
    if ctx.manifest_config is None:
        return CheckResult(
            name="surface-templates",
            status=CheckStatus.FAIL,
            message="No manifest config available; cannot determine surfaces",
        )
    surfaces = ctx.manifest_config.surfaces.enabled
    if not surfaces:
        return CheckResult(
            name="surface-templates",
            status=CheckStatus.OK,
            message="No Surfaces configured",
        )
    vcs = ctx.manifest_config.providers.vcs
    maps = resolve_template_maps(surfaces=surfaces, vcs_provider=vcs)

    missing: list[str] = []

    for _src, dest in maps.file_map.items():
        if not (ctx.target / dest).exists():
            missing.append(dest)

    for _src_tree, dest_tree in maps.tree_list:
        if not (ctx.target / dest_tree).is_dir():
            missing.append(dest_tree)

    for _src, dest in maps.common_file_map.items():
        if not (ctx.target / dest).exists():
            missing.append(dest)

    if missing:
        return CheckResult(
            name="surface-templates",
            status=CheckStatus.FAIL,
            message=f"Missing surface templates: {', '.join(missing)}",
        )
    return CheckResult(
        name="surface-templates",
        status=CheckStatus.OK,
        message="All surface templates present",
    )


def _check_settings_merge(ctx: DoctorContext) -> CheckResult:
    """Check Claude Code settings.json for deny rules if claude-code is active."""
    if ctx.manifest_config is None:
        return CheckResult(
            name="settings-merge",
            status=CheckStatus.OK,
            message="No manifest config available; skipping settings check",
        )
    surfaces = ctx.manifest_config.surfaces.enabled
    if "claude-code" not in surfaces:
        return CheckResult(
            name="settings-merge",
            status=CheckStatus.OK,
            message="Claude Code not in surfaces; skipping settings check",
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


def _check_permissions_wildcard(ctx: DoctorContext) -> CheckResult:
    """Advisory check (spec-107 D-107-02 / G-3): warn on wildcard allow.

    Reads ``.claude/settings.json`` from the target project and emits a
    WARN advisory when the ``permissions.allow`` list contains the
    literal ``"*"`` wildcard. Pure advisory: never FAIL, never block.
    Missing or unparseable settings produce OK because file presence
    is governed by the existing ``settings-merge`` check.
    """
    advisory_name = "permissions-wildcard-detected"
    settings_path = ctx.target / ".claude" / "settings.json"
    if not settings_path.is_file():
        return CheckResult(
            name=advisory_name,
            status=CheckStatus.OK,
            message=".claude/settings.json not present; nothing to advise",
        )
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Parse errors are surfaced by settings-merge; stay quiet here so
        # the advisory never doubles up failures.
        return CheckResult(
            name=advisory_name,
            status=CheckStatus.OK,
            message=".claude/settings.json not parseable; deferring to settings-merge",
        )
    allow = data.get("permissions", {}).get("allow", [])
    if "*" in allow:
        return CheckResult(
            name=advisory_name,
            status=CheckStatus.WARN,
            message=(
                "Permissions wildcard detected in .claude/settings.json. "
                "Recommended: migrate to narrow explicit list."
            ),
        )
    return CheckResult(
        name=advisory_name,
        status=CheckStatus.OK,
        message=".claude/settings.json uses an explicit allow list",
    )


# Trees spec-201 retired (D-201-04 / D-201-05). Skills collapsed to
# `.claude/skills` + `.agents/skills`, and `.codex/agents` was a namespace
# squat Codex never read.
_RETIRED_SURFACE_TREES: tuple[str, ...] = (
    ".github/skills",
    ".codex/skills",
    ".opencode/skills",
    ".cursor/skills",
    ".codex/agents",
)


def _check_retired_surface_trees(ctx: DoctorContext) -> CheckResult:
    """Advisory check (spec-201 H6): retired surface trees left on disk.

    ``ai-eng update`` cannot remove these. Its orphan sweep only visits
    *disabled* providers, and it enumerates destinations from the current
    ``_SURFACE_TREE_MAPS`` — which no longer names any of these paths, so
    nothing can reach them. A consumer upgrading from 0.13.0 with copilot
    and codex enabled gains ``.agents/skills`` and keeps ``.github/skills``,
    ``.codex/skills`` and ``.codex/agents`` frozen at 0.13.0. Both agents
    natively discover both trees, so they read two divergent copies of
    every skill, the stale ones still cross-referencing ``.codex/agents/``.

    WARN, never FAIL, and not ``fixable``: deleting trees in a consumer
    repo is a destructive sweep that needs its own spec with backup and
    rollback. Until that exists the honest move is to name the paths and
    hand the operator the ``rm``. An empty directory is ignored — it holds
    no divergent copy of anything.
    """
    advisory_name = "retired-surface-trees-present"
    present = [
        rel
        for rel in _RETIRED_SURFACE_TREES
        if (ctx.target / rel).is_dir() and any((ctx.target / rel).rglob("*.md"))
    ]
    if not present:
        return CheckResult(
            name=advisory_name,
            status=CheckStatus.OK,
            message="No retired surface trees on disk",
        )
    return CheckResult(
        name=advisory_name,
        status=CheckStatus.WARN,
        message=(
            f"Retired surface trees still on disk: {', '.join(present)}. "
            "`ai-eng update` cannot remove them, so they stay frozen at the "
            "version that wrote them while your agents keep discovering them "
            "alongside the current .claude/skills and .agents/skills. Remove "
            f"them manually: rm -rf {' '.join(present)}"
        ),
    )
