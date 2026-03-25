"""Selective test scope resolution for local gates and CI.

Single-source-of-truth test scoping engine used by:
- pre-push gate selective execution
- CI tier test jobs
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Literal

from ai_engineering.git.operations import current_branch, get_changed_files, get_merge_base, run_git

Tier = Literal["unit", "integration", "e2e"]
ScopeMode = Literal["shadow", "enforce", "off"]


@dataclass
class ScopeRule:
    """Map source globs to per-tier test paths."""

    __test__ = False
    name: str
    source_globs: list[str]
    tiers: dict[str, list[str]]


@dataclass
class TestScope:
    """Resolved test scope with traceability metadata."""

    __test__ = False
    selected_tests: list[str]
    mode: Literal["selective", "full"]
    reasons: list[str]
    changed_files: list[str]
    matched_rules: list[str]
    unmatched_src_files: list[str]


ALWAYS_RUN: dict[str, list[str]] = {
    "unit": [],
    "integration": [
        "tests/integration/test_gap_fillers4.py",
        "tests/integration/test_coverage_closure.py",
    ],
    "e2e": [],
}

FULL_SUITE_TRIGGERS: list[str] = [
    "pyproject.toml",
    "tests/conftest.py",
    ".github/workflows/ci.yml",
]

HIGH_RISK_GLOBS: list[str] = [
    "scripts/**",
    "uv.lock",
    ".semgrep.yml",
    ".gitleaks.toml",
]

FULL_TIER_TARGETS: dict[str, list[str]] = {
    "unit": ["tests/unit"],
    "integration": ["tests/integration"],
    "e2e": ["tests/e2e"],
}


TEST_SCOPE_RULES: list[ScopeRule] = [
    ScopeRule(
        name="root",
        source_globs=[
            "src/ai_engineering/__init__.py",
            "src/ai_engineering/__version__.py",
            "src/ai_engineering/cli.py",
            "src/ai_engineering/cli_envelope.py",
            "src/ai_engineering/cli_factory.py",
            "src/ai_engineering/cli_output.py",
            "src/ai_engineering/cli_progress.py",
            "src/ai_engineering/cli_ui.py",
            "src/ai_engineering/paths.py",
        ],
        tiers={
            "unit": [
                "tests/unit/test_cli_entrypoint.py",
                "tests/unit/test_cli_errors.py",
                "tests/unit/test_cli_envelope.py",
                "tests/unit/test_cli_output.py",
                "tests/unit/test_cli_progress.py",
                "tests/unit/test_cli_ui.py",
                "tests/unit/test_paths_helpers.py",
            ],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="lib",
        source_globs=["src/ai_engineering/lib/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_emit_infrastructure.py",
                "tests/unit/test_health_history.py",
                "tests/unit/test_lib_signals.py",
                "tests/unit/test_parsing.py",
                "tests/unit/test_security_posture.py",
                "tests/unit/test_signal_aggregators.py",
                "tests/unit/test_skill_agent_telemetry.py",
                "tests/unit/test_spec_helpers.py",
                "tests/unit/test_test_confidence.py",
            ],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="cli_commands",
        source_globs=["src/ai_engineering/cli_commands/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_setup_cli.py",
                "tests/unit/test_release_cli.py",
                "tests/unit/test_provider_cli.py",
                "tests/unit/test_cli_observe.py",
                "tests/unit/test_cli_decisions.py",
                "tests/unit/test_cli_scan_report.py",
                "tests/unit/test_cli_signals.py",
                "tests/unit/test_cli_sync.py",
                "tests/unit/test_cli_metrics.py",
                "tests/unit/test_spec_cmd.py",
                "tests/unit/test_observe_dashboards.py",
                "tests/unit/test_workflow_cmd.py",
                "tests/unit/test_cli_install_non_interactive.py",
            ],
            "integration": [
                "tests/integration/test_cli_command_modules.py",
                "tests/integration/test_cli_install_doctor.py",
            ],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="release",
        source_globs=["src/ai_engineering/release/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_deploy_event_wiring.py",
                "tests/unit/test_release_orchestrator.py",
                "tests/unit/test_version_bump.py",
                "tests/unit/test_changelog_parser.py",
            ],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="commands",
        source_globs=["src/ai_engineering/commands/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_workflow_helpers.py"],
            "integration": ["tests/integration/test_command_workflows.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="credentials",
        source_globs=["src/ai_engineering/credentials/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_credentials.py",
                "tests/unit/test_sonar_gate.py",
            ],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="detector",
        source_globs=["src/ai_engineering/detector/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_readiness.py"],
            "integration": ["tests/integration/test_readiness_integration.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="doctor",
        source_globs=["src/ai_engineering/doctor/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_doctor.py", "tests/unit/test_doctor_feeds.py"],
            "integration": ["tests/integration/test_doctor_integration.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="git",
        source_globs=["src/ai_engineering/git/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_git_context.py"],
            "integration": ["tests/integration/test_git_operations.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="hooks",
        source_globs=["src/ai_engineering/hooks/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_hooks.py"],
            "integration": ["tests/integration/test_hooks_git.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="installer",
        source_globs=["src/ai_engineering/installer/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_installer.py",
                "tests/unit/test_installer_tools.py",
                "tests/unit/installer/test_phases.py",
                "tests/unit/installer/test_pipeline.py",
                "tests/unit/installer/test_merge.py",
                "tests/unit/installer/test_detect.py",
                "tests/unit/installer/test_ui.py",
                "tests/unit/installer/test_autodetect.py",
                "tests/unit/installer/test_wizard.py",
            ],
            "integration": [
                "tests/integration/test_installer_integration.py",
                "tests/integration/test_install_operational_flows.py",
                "tests/integration/test_provider_commands.py",
                "tests/integration/test_install_matrix.py",
                "tests/integration/test_phase_failure.py",
            ],
            "e2e": [
                "tests/e2e/test_install_clean.py",
                "tests/e2e/test_install_existing.py",
            ],
        },
    ),
    ScopeRule(
        name="maintenance",
        source_globs=["src/ai_engineering/maintenance/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/maintenance/test_repo_status.py",
                "tests/unit/maintenance/test_spec_reset.py",
            ],
            "integration": [
                "tests/integration/test_branch_cleanup.py",
                "tests/integration/test_repo_status_integration.py",
                "tests/integration/test_spec_reset_integration.py",
            ],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="platforms",
        source_globs=["src/ai_engineering/platforms/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_platforms.py",
                "tests/unit/test_sonarlint.py",
            ],
            "integration": ["tests/integration/test_platform_onboarding.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="policy",
        source_globs=["src/ai_engineering/policy/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_gates.py",
                "tests/unit/test_duplication.py",
                "tests/unit/test_sonar_measures.py",
                "tests/unit/test_test_scope.py",
            ],
            "integration": ["tests/integration/test_gates_integration.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="skills",
        source_globs=["src/ai_engineering/skills/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_skills_maintenance.py",
                "tests/unit/test_skills_status.py",
            ],
            "integration": ["tests/integration/test_skills_integration.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="state",
        source_globs=["src/ai_engineering/state/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_state.py",
                "tests/unit/test_audit.py",
                "tests/unit/test_risk_lifecycle.py",
                "tests/unit/test_decision_store.py",
            ],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="updater",
        source_globs=["src/ai_engineering/updater/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_updater.py"],
            "integration": ["tests/integration/test_updater.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="validator",
        source_globs=["src/ai_engineering/validator/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_validator.py",
                "tests/unit/test_validator_extra.py",
                "tests/unit/test_skill_schema_validation.py",
                "tests/unit/test_agent_schema_validation.py",
                "tests/unit/test_real_project_integrity.py",
                "tests/unit/test_sync_mirrors.py",
                "tests/unit/test_handler_routing_completeness.py",
                "tests/unit/test_template_prompt_parity.py",
            ],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="verify",
        source_globs=["src/ai_engineering/verify/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_verify_scoring.py",
                "tests/unit/test_verify_service.py",
            ],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="vcs",
        source_globs=["src/ai_engineering/vcs/**/*.py"],
        tiers={
            "unit": [
                "tests/unit/test_api_fallback.py",
                "tests/unit/test_pr_description.py",
                "tests/unit/test_repo_context.py",
                "tests/unit/test_vcs_providers.py",
            ],
            "integration": [
                "tests/integration/test_vcs_factory.py",
                "tests/integration/test_vcs_github.py",
                "tests/integration/test_vcs_azure_devops.py",
            ],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="work_items",
        source_globs=["src/ai_engineering/work_items/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_work_items_service.py"],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="version",
        source_globs=["src/ai_engineering/version/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_version_lifecycle.py"],
            "integration": ["tests/integration/test_version_checker.py"],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="scripts",
        source_globs=["scripts/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_check_workflow_policy.py"],
            "integration": [],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="telemetry-hooks",
        source_globs=[
            ".ai-engineering/scripts/hooks/**",
            ".github/hooks/**",
            ".claude/settings.json",
        ],
        tiers={
            "unit": ["tests/unit/test_strategic_compact.py"],
            "integration": [
                "tests/integration/test_telemetry_canary.py",
                "tests/integration/test_strategic_compact_integration.py",
            ],
            "e2e": [],
        },
    ),
    ScopeRule(
        name="templates",
        source_globs=["src/ai_engineering/templates/**/*.py"],
        tiers={
            "unit": ["tests/unit/test_template_parity.py"],
            "integration": [],
            "e2e": [],
        },
    ),
]

_DOC_EXTENSIONS: frozenset[str] = frozenset({".md", ".mdx", ".rst", ".txt"})


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def _is_docs_file(path: str) -> bool:
    lowered = path.lower()
    return any(lowered.endswith(ext) for ext in _DOC_EXTENSIONS)


def _is_tier_test(path: str, tier: Tier) -> bool:
    return path.startswith(f"tests/{tier}/") and path.endswith(".py")


def _resolve_base_ref(project_root: Path, base_ref: str) -> str:
    if base_ref != "auto":
        return base_ref

    ok, output = run_git(
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        project_root,
    )
    if ok and output.strip():
        return _normalize_path(output.splitlines()[0])

    ok, _ = run_git(["rev-parse", "--verify", "origin/main"], project_root)
    if ok:
        return "origin/main"

    return "origin/main"


def resolve_scope_mode(env: Mapping[str, str] | None = None) -> ScopeMode:
    """Resolve scope mode from environment variables.

    Priority:
    1. `AI_ENG_TEST_SCOPE=off` emergency bypass
    2. `AI_ENG_TEST_SCOPE_MODE` in {shadow, enforce, off}
    3. default `shadow`
    """
    env_vars = env if env is not None else os.environ
    if env_vars.get("AI_ENG_TEST_SCOPE", "").strip().lower() == "off":
        return "off"

    mode = env_vars.get("AI_ENG_TEST_SCOPE_MODE", "shadow").strip().lower()
    if mode in {"shadow", "enforce", "off"}:
        return mode  # type: ignore[return-value]
    return "shadow"


def _parse_renamed_paths(project_root: Path, base_ref: str) -> list[str]:
    merge_base = get_merge_base(project_root, base_ref)
    ok, output = run_git(
        [
            "diff",
            "--name-status",
            "--diff-filter=R",
            f"{merge_base}...HEAD",
        ],
        project_root,
    )
    if not ok:
        raise RuntimeError(f"failed to parse rename diff: {output}")

    renamed: list[str] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        renamed.append(_normalize_path(parts[1]))
        renamed.append(_normalize_path(parts[2]))
    return renamed


def _full_scope(
    *,
    tier: Tier,
    reasons: list[str],
    changed_files: list[str],
    matched_rules: list[str],
    unmatched_src_files: list[str],
) -> TestScope:
    return TestScope(
        selected_tests=sorted(set(FULL_TIER_TARGETS[tier])),
        mode="full",
        reasons=sorted(set(reasons)),
        changed_files=sorted(set(changed_files)),
        matched_rules=sorted(set(matched_rules)),
        unmatched_src_files=sorted(set(unmatched_src_files)),
    )


def _compute_scope_internal(
    project_root: Path,
    *,
    tier: Tier,
    base_ref: str,
) -> tuple[TestScope, str]:
    base_ref_resolved = _resolve_base_ref(project_root, base_ref)

    try:
        changed = get_changed_files(project_root, base_ref_resolved, diff_filter="ACMRT")
        deleted = get_changed_files(project_root, base_ref_resolved, diff_filter="D")
        renamed = _parse_renamed_paths(project_root, base_ref_resolved)
    except Exception as exc:
        reason = f"base_ref_resolution_failed:{base_ref_resolved}:{exc}"
        scope = _full_scope(
            tier=tier,
            reasons=[reason],
            changed_files=[],
            matched_rules=[],
            unmatched_src_files=[],
        )
        return scope, base_ref_resolved

    changed_files = sorted({_normalize_path(path) for path in [*changed, *renamed]})
    deleted_files = sorted(set(_normalize_paths(deleted)))
    all_changed = sorted({*changed_files, *deleted_files})

    if not all_changed:
        scope = _full_scope(
            tier=tier,
            reasons=["no_changed_files"],
            changed_files=all_changed,
            matched_rules=[],
            unmatched_src_files=[],
        )
        return scope, base_ref_resolved

    branch = current_branch(project_root)
    if branch in {"main", "master"}:
        scope = _full_scope(
            tier=tier,
            reasons=[f"main_branch:{branch}"],
            changed_files=all_changed,
            matched_rules=[],
            unmatched_src_files=[],
        )
        return scope, base_ref_resolved

    if any(path.startswith("src/") for path in deleted_files):
        scope = _full_scope(
            tier=tier,
            reasons=["src_delete_detected"],
            changed_files=all_changed,
            matched_rules=[],
            unmatched_src_files=[p for p in deleted_files if p.startswith("src/")],
        )
        return scope, base_ref_resolved

    if any(path in FULL_SUITE_TRIGGERS for path in all_changed):
        scope = _full_scope(
            tier=tier,
            reasons=["full_suite_trigger_changed"],
            changed_files=all_changed,
            matched_rules=[],
            unmatched_src_files=[],
        )
        return scope, base_ref_resolved

    if any(_matches_any_glob(path, HIGH_RISK_GLOBS) for path in all_changed):
        scope = _full_scope(
            tier=tier,
            reasons=["high_risk_path_changed"],
            changed_files=all_changed,
            matched_rules=[],
            unmatched_src_files=[],
        )
        return scope, base_ref_resolved

    if all(_is_docs_file(path) for path in all_changed):
        return (
            TestScope(
                selected_tests=[],
                mode="selective",
                reasons=["docs_only"],
                changed_files=all_changed,
                matched_rules=[],
                unmatched_src_files=[],
            ),
            base_ref_resolved,
        )

    selected_tests: set[str] = set()
    matched_rules: set[str] = set()
    unmatched_src_files: set[str] = set()

    for path in changed_files:
        if not path.startswith("src/"):
            continue

        matching = [rule for rule in TEST_SCOPE_RULES if _matches_rule(path, rule)]
        if not matching:
            unmatched_src_files.add(path)
            continue

        for rule in matching:
            matched_rules.add(rule.name)
            selected_tests.update(rule.tiers.get(tier, []))

    for path in changed_files:
        if path.startswith("tests/") and _is_tier_test(path, tier):
            selected_tests.add(path)

    selected_tests.update(ALWAYS_RUN.get(tier, []))

    if unmatched_src_files:
        scope = _full_scope(
            tier=tier,
            reasons=["unmatched_src_files"],
            changed_files=all_changed,
            matched_rules=sorted(matched_rules),
            unmatched_src_files=sorted(unmatched_src_files),
        )
        return scope, base_ref_resolved

    has_code_changes = any(not _is_docs_file(path) for path in all_changed)
    if not selected_tests and has_code_changes:
        scope = _full_scope(
            tier=tier,
            reasons=["empty_after_code_change"],
            changed_files=all_changed,
            matched_rules=sorted(matched_rules),
            unmatched_src_files=[],
        )
        return scope, base_ref_resolved

    return (
        TestScope(
            selected_tests=sorted(selected_tests),
            mode="selective",
            reasons=["selective"],
            changed_files=all_changed,
            matched_rules=sorted(matched_rules),
            unmatched_src_files=[],
        ),
        base_ref_resolved,
    )


def _matches_rule(path: str, rule: ScopeRule) -> bool:
    return any(_matches_glob(path, pattern) for pattern in rule.source_globs)


def _matches_any_glob(path: str, patterns: list[str]) -> bool:
    return any(_matches_glob(path, pattern) for pattern in patterns)


def _matches_glob(path: str, pattern: str) -> bool:
    """Match glob patterns while allowing `/**/` to include direct children too."""
    if fnmatch(path, pattern):
        return True
    return "/**/" in pattern and fnmatch(path, pattern.replace("/**/", "/"))


def _normalize_paths(paths: list[str]) -> list[str]:
    return [_normalize_path(path) for path in paths]


def compute_test_scope(
    project_root: Path,
    *,
    tier: Tier,
    base_ref: str = "auto",
) -> TestScope:
    """Resolve test scope for a tier.

    Args:
        project_root: Repository root path.
        tier: Test tier (`unit`, `integration`, or `e2e`).
        base_ref: Comparison base ref, or `auto`.

    Returns:
        TestScope with selected tests and fallback diagnostics.
    """
    scope, _ = _compute_scope_internal(project_root, tier=tier, base_ref=base_ref)
    return scope


def compute_test_scope_diagnostic(
    project_root: Path,
    *,
    tier: Tier,
    base_ref: str = "auto",
) -> dict[str, Any]:
    """Resolve scope and return JSON-safe diagnostic payload."""
    started = time.perf_counter()
    scope, base_ref_resolved = _compute_scope_internal(project_root, tier=tier, base_ref=base_ref)
    duration_ms = int((time.perf_counter() - started) * 1000)

    return {
        "tier": tier,
        "base_ref_resolved": base_ref_resolved,
        "changed_files": scope.changed_files,
        "matched_rules": scope.matched_rules,
        "unmatched_src_files": scope.unmatched_src_files,
        "selected_tests": scope.selected_tests,
        "mode": scope.mode,
        "reasons": scope.reasons,
        "duration_ms": duration_ms,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve selective test scope")
    parser.add_argument("--tier", choices=["unit", "integration", "e2e"], required=True)
    parser.add_argument("--base-ref", default="auto")
    parser.add_argument("--format", choices=["args", "json"], default="args")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    project_root = Path.cwd()
    tier: Tier = args.tier

    diagnostic = compute_test_scope_diagnostic(project_root, tier=tier, base_ref=args.base_ref)

    if args.format == "json":
        print(json.dumps(diagnostic, indent=2, sort_keys=True))
        return 0

    selected_tests = diagnostic["selected_tests"]
    print(" ".join(selected_tests))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
