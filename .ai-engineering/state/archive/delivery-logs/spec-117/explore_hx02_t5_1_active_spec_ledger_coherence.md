# HX-02 T-5.1 Active Spec Ledger Coherence - Exploration Handoff

## Current Anchor

- Owning seam: `src/ai_engineering/validator/categories/manifest_coherence.py`
- Current branch treats placeholder `spec.md` as authoritative idle state and returns before the readable-ledger helper chain runs.
- Nearest test anchor: `tests/unit/test_validator.py::TestManifestCoherence`
- Runtime neighbors still using placeholder gates exist in `src/ai_engineering/policy/orchestrator.py` and `src/ai_engineering/work_items/service.py`, but they are not the first cutover slice.

## Candidates Considered

- Placeholder spec plus readable active ledger mismatch
- Orchestrator wave1 spec-verify gating
- Work-items active-spec detection

The first option is the smallest safe slice because it removes an existing validator authority leak without inventing new runtime readiness semantics.

## Local Hypothesis

If the resolved active work plane has a readable `task-ledger.json` with any non-done task, placeholder `spec.md` is stale compatibility text, so `manifest-coherence` should fail instead of treating the work plane as idle.

## Recommended Next Slice

- Name the slice `active-spec-ledger-coherence`.
- Keep ownership inside `src/ai_engineering/validator/categories/manifest_coherence.py`.
- Flip behavior only for this narrow state:
  - `spec.md` is the placeholder
  - `task-ledger.json` is readable
  - at least one task is not done
- Preserve current true-idle behavior when the placeholder spec is paired with an empty ledger.
- Preserve current malformed-ledger behavior when the ledger is unreadable.
- Do not widen into `plan.md` semantic checks, CLI behavior, or runtime policy gates in this slice.

## Allowed Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

## Failing-Test-First Candidate

- Add one failing case: placeholder `spec.md` plus one `in_progress` task in `task-ledger.json` should fail `manifest-coherence`.
- Keep one passing idle case: placeholder `spec.md` plus empty ledger remains a passing idle state.
- Keep one guardrail case: malformed `task-ledger.json` still warns and skips readable-ledger subchecks.

## Cheapest Validation

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_active_spec_placeholder_with_non_done_task_in_ledger_fails -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k "active_spec_placeholder or malformed_task_ledger" -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

## Boundaries

- Do not change `src/ai_engineering/state/work_plane.py`.
- Do not change `src/ai_engineering/policy/orchestrator.py`.
- Do not change `src/ai_engineering/work_items/service.py`.
- Do not change schema, models, templates, or placeholder text.
- Do not broaden this slice into full runtime build-readiness cutover.