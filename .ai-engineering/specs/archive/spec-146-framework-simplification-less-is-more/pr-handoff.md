# Spec 146 PR Handoff — Framework Simplification Less Is More

Existing PR: `arcasilesgroup/ai-engineering#530`.

This handoff records the spec-146 changes landed on the existing branch and PR only. No new branch or PR was created.

## Summary

Spec-146 fixed the update ownership read path first, reconciled persistence documentation, cleaned duplicate `.ai-engineering/` data surfaces, promoted implemented tunables into default-bearing docs, and deleted only inventory-proven dead/test-only Python surfaces.

## Fixed

- `ai-eng update` now reads `state.db.ownership_map` through raw and updater-ready helpers before evaluating create/update decisions.
- Deny/team ownership rows now protect missing files from being recreated by update.
- Legacy `ownership-map.json` is a one-time fallback only when SQLite has no ownership rows; non-dry-run migration seeds SQLite and removes the sidecar.
- Final quality-loop drift was remediated in one bounded pass: the sub-005 runtime plan now carries its North Star preamble, and the install directory schema fixture reflects the spec-authorized removal of `.ai-engineering/references/`.

## Changed

- `docs/persistence-doctrine.md` now classifies each `state.db` table by role.
- `gate-findings.json` remains the primary gate/risk/verify artifact for this spec; `state.db.gate_findings` is documented as transitional/non-primary.
- Runtime Layer Tunables docs now show implemented defaults for hook cache TTL, autoformat debounce, and NDJSON rotation limits.
- `installer/mechanisms/__init__.py` was split into focused mechanism modules while preserving the internal package-root registry import surface.
- The policy orchestrator now reads decisions through `DurableStateRepository` directly instead of the `StateService` forwarding facade.

## Removed

- `.ai-engineering/references/IOCS_ATTRIBUTION.md`
- `src/ai_engineering/templates/.ai-engineering/references/IOCS_ATTRIBUTION.md`
- `.ai-engineering/team/lessons.md`
- `.ai-engineering/state/strategic-compact.json`
- `.ai-engineering/state/instinct-observations.ndjson`
- `src/ai_engineering/state/agentsview.py`
- `src/ai_engineering/state/outbox.py`
- `src/ai_engineering/cli_ui_skill_ref.py`
- `src/ai_engineering/governance/policy_engine.py`
- Preservation-only tests for the deleted modules.

## Preserved by Inventory

- `src/ai_engineering/state/trace_context.py`
- `src/ai_engineering/state/capabilities.py`
- `src/ai_engineering/state/context_packs.py`
- `src/ai_engineering/state/relevance.py`
- `src/ai_engineering/state/repository.py`
- Remaining `StateService` callsites outside the smallest orchestrator flattening.

See `.ai-engineering/specs/spec-146-caller-inventory.md` for evidence and decisions.

## Quality Loop

- Initial full pytest found 2 failures after the main implementation: a missing sub-005 North Star preamble and stale install directory snapshot entry for `.ai-engineering/references/`.
- One bounded, finding-scoped remediation pass was used.
- Focused remediation verification passed: `tests/docs/test_links.py::test_sub005_plan_has_north_star_preamble` and `tests/integration/installer/test_install_dir_schema.py::test_install_directory_layout_matches_snapshot` (2 passed).
- Final full pytest passed: 7844 passed, 27 skipped, 1 deselected, 1 xpassed, 20 warnings.

## Validation Evidence

- Ownership/update bundle: 41 passed.
- Persistence/gate-findings/hot-path bundle: 38 passed.
- Data-tree cleanup bundle: 56 passed; hook manifest check passed.
- Tunables docs/mirror bundle: 23 passed; mirror sync check passed.
- Caller inventory/module simplification bundle: 101 passed.
- Spec-146 targeted quality bundle: 136 passed.
- Focused remediation tests: 2 passed.
- Full pytest: 7844 passed, 27 skipped, 1 deselected, 1 xpassed, 20 warnings.
- `ruff check .`: passed.
- `ruff format --check .`: passed after formatting.
- `ai-eng dev sync --check`: passed after mirror sync.
- `ai-eng spec verify --sections .ai-engineering/specs/spec.md`: passed.
- `ai-eng spec verify`: passed (38/38).
- `spec_lint --check .ai-engineering/specs/spec.md`: passed (6/6 checks).
- `regenerate-hooks-manifest.py --check`: passed (74 hooks).
- `git diff --check`: passed.

## Residual Follow-ups

- A later approved spec may migrate `gate-findings.json` consumers into SQLite if that cross-surface migration is desired.
- Additional `StateService` or repository flattening should be handled callsite-by-callsite, not as a broad facade purge.
- SHA256 pins for GitHub release binary installer mechanisms remain the existing DEC-038 follow-up, unrelated to spec-146.
