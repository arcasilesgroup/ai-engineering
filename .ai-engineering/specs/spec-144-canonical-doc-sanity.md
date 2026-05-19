# Canonical Doc Sanity — spec-144

## Scope

Reviewed the canonical cross-IDE entry surfaces after the README rewrite and branch-cleanup rename:

- `CONSTITUTION.md`
- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.github/copilot-instructions.md`
- `.ai-engineering/reference/surface-axioms.md`
- `.ai-engineering/reference/model-dispatch-policy.md`

## Result

[PASS] No canonical rulebook rewrite was needed for spec-144 beyond the intended active-reference rename from `/ai-repo-tidy` to `/ai-branch-cleanup`.

[PASS] Root IDE mirrors stayed aligned after `ai-eng dev sync` and `ai-eng dev sync --check`.

[PASS] Installer-template mirrors stayed aligned after the orphan cleanup fix included `.opencode`, `.cursor`, and `.agent` template surfaces.

## Evidence

- `tests/architecture/test_surface_parity.py` passed in the targeted rename/parity suite.
- `tests/integration/test_skill_mirror_consistency.py`, `tests/unit/test_template_skill_parity.py`, `tests/integration/test_shared_handler_mirror.py`, `tests/unit/test_sync_mirrors.py`, and `tests/integration/sync_mirrors/test_new_surface_targets.py` passed as the mirror propagation suite.
- `ai-eng dev sync --check` reported mirrors in sync during final verification.
- Full pytest passed: `7785 passed, 27 skipped, 1 deselected, 1 xpassed`.

## Divergence Review

No unexpected divergence was found. IDE-specific extras remain fenced in their allowed sections; canonical payload changes came from the mirror sync pipeline rather than hand-edited generated drift.

## Follow-up

None for canonical docs. Design asset count drift remains tracked separately in `spec-144-asset-follow-up.md`.
