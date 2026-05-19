# PR Handoff — spec-144

## Summary

Spec-144 rewrites the README surfaces around the current `{ai} engineering` brand voice and hard-renames `/ai-repo-tidy` to `/ai-branch-cleanup` with no alias, shim, or compatibility fallback.

## Sub-Spec Completion

| # | Title | Status | Wave |
|---|-------|--------|------|
| sub-001 | Brand Voice Contract | complete | 1 |
| sub-002 | README Contracts and Rewrite | complete | 2 |
| sub-003 | Canonical Skill Rename | complete | 1 |
| sub-004 | Mirror and Template Propagation | complete | 2 |
| sub-005 | Changelog Audit and Follow-up | complete | 2 |
| sub-006 | Sanity Review and Final Gates | complete | 3 |

## Quality State

[PASS] Final reassessment is clean after one bounded remediation pass.

Bounded remediation was used once for three integration findings from the initial full-suite run:

1. Active `spec.md` did not satisfy `spec_lint` conventions.
2. Nested `.ai-engineering/specs/spec-144/` follow-up files violated canonical specs-directory structure.
3. Trusted hooks manifest was stale after script/template updates.

All three were finding-scoped and revalidated before the terminal full-suite run.

## Test Plan

- `rtk .venv/bin/python -m pytest tests/unit/docs/test_brand_voice_contract.py -q` — passed.
- `rtk .venv/bin/python -m pytest tests/architecture/test_naming_clarity.py tests/unit/test_cleanup_history_rotation.py tests/unit/test_consolidate_spec_action.py tests/unit/validator/test_history_md_warn.py tests/unit/installer/test_phases.py tests/unit/test_session_bootstrap_template_parity.py tests/architecture/test_surface_parity.py -q` — `43 passed, 6 skipped`.
- `rtk .venv/bin/python -m pytest tests/docs/test_links.py tests/unit/docs/test_brand_voice_contract.py tests/unit/docs/test_readme_brand_contract.py tests/unit/docs/test_governance_readme_template_parity.py -q` — `365 passed, 2 skipped`.
- `rtk .venv/bin/python -m pytest tests/integration/test_skill_mirror_consistency.py tests/unit/test_template_skill_parity.py tests/integration/test_shared_handler_mirror.py tests/unit/test_sync_mirrors.py tests/integration/sync_mirrors/test_new_surface_targets.py -q` — `205 passed`.
- `rtk .venv/bin/python -m pytest tests/unit/docs/test_changelog_spec144.py tests/unit/test_changelog_parser.py tests/unit/test_changelog_breaking_keywords.py -q` — `18 passed`.
- `rtk .venv/bin/python -m pytest tests/unit/specs/test_canonical_structure.py tests/integration/test_spec_lint_e2e.py -q` — `7 passed` after remediation.
- `rtk .venv/bin/python -m pytest tests/unit/hooks/test_trusted_script_lane_manifest.py::test_check_mode_passes_when_fresh -q` — passed after manifest regeneration.
- `rtk .venv/bin/python -m ruff format` and `rtk .venv/bin/python -m ruff check` — passed after formatting imports and normalizing the `spec_lint` stream guard.
- `rtk .venv/bin/ai-eng dev sync --check` — passed.
- `rtk .venv/bin/python -m spec_lint --check` — passed.
- `rtk .venv/bin/ai-eng audit verify` — passed.
- `rtk .venv/bin/ai-eng verify` — `100/100`.
- `rtk .venv/bin/python -m pytest -q` — `7785 passed, 27 skipped, 1 deselected, 1 xpassed`.
- Final focused gate bundle with ruff/sync/spec-lint/audit/verify and documentation/rename/template regressions — `566 passed, 2 skipped`.

## Old-Slug Residual Classification

[PASS] Active code, generated surfaces, installer templates, tests, scripts, and README/reference docs have no literal `ai-repo-tidy` hits.

Allowed residual hits are delivery or historical context only:

- Active spec/plan text describing the rename contract and execution plan.
- Draft and archived spec material documenting the historical decision path.
- `CHANGELOG.md` `[Unreleased]` breaking entry and historical changelog entries.
- Append-only framework audit/state history, when searched with ignored files included.

## No-Shim Confirmation

[PASS] No `/ai-repo-tidy` alias, command wrapper, registry fallback, or compatibility shim was added. External automation must update to `/ai-branch-cleanup`.

## Asset and State Discipline

[PASS] `.pen` design assets were not edited.

[PASS] Historical audit/state records were not rewritten. The rename traceability was emitted as an append-only `framework_operation` event with `detail.operation=skill_renamed`.

## Follow-up

- `spec-144-asset-follow-up.md` contains the deferred design-asset count update payload.
