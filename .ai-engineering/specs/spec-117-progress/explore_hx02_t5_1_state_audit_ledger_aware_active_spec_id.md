# Explore - HX-02 / T-5.1 / state-audit-ledger-aware-active-spec-id

## Slice Goal

Make `state.audit._read_active_spec()` stop treating placeholder `spec.md` as authoritative `None` when the resolved spec-local work plane still has live ledger tasks. The slice needs an explicit fallback identifier policy for placeholder-backed active work planes.

## Local Anchor

- `src/ai_engineering/state/audit.py::_read_active_spec()`
- `tests/unit/test_state.py` active-spec enrichment tests

## Existing Behavior

- `_read_active_spec()` already resolves the active work plane before reading `spec.md`.
- It still returns `None` immediately when the resolved spec file starts with `# No active spec`.
- The helper is cached, so any fallback identifier decision must remain deterministic and cache-safe.

## Falsifiable Hypothesis

If `_read_active_spec()` mirrors the placeholder-to-ledger rule used elsewhere and derives a stable fallback identifier from the resolved work-plane directory name when the readable ledger still has a non-done task, then audit enrichment will stop dropping the active spec context for live spec-local work planes without disturbing the existing frontmatter and heading fast paths.

## Cheapest Discriminating Check

Add a focused `test_read_active_spec_placeholder_live_resolved_ledger` regression in `tests/unit/test_state.py` that points the active work plane at a spec-local directory with placeholder `spec.md`, writes a readable ledger containing one live task, resets the enrichment cache, and asserts that `_read_active_spec(tmp_path)` returns a stable non-`None` identifier derived from that resolved work-plane root.

## Proposed Write Scope

- `src/ai_engineering/state/audit.py`
- `tests/unit/test_state.py`

## Notes

- This slice must choose and document the fallback identifier shape before implementation. A likely starting point is the resolved work-plane directory name, but the downstream consumers of audit metadata should be checked before the cutover lands.
- After this slice, `vcs.pr_description` remains the other obvious placeholder-based identifier reader in `T-5.1`.
