# Phase 1 Governance Review — spec-119 Foundation

Reviewer: ai-guard (autonomous, batch dispatch)
Date: 2026-05-04 (UTC)
Scope: T-1.1 through T-1.8 deltas

## Review surface

| Artefact | Location | Change |
|---|---|---|
| Spike | `.ai-engineering/specs/spec-119-progress/spike-spec-117-funcs.md` | new — documents that spec-117 T-3.3 named funcs do not exist; redirects D-119-07 to fresh `src/ai_engineering/eval/` module landing in Phase 2/4 |
| Deps | `pyproject.toml` | new optional extra `eval = ["deepeval>=2.0,<3.0"]`; new pytest markers `eval` and `eval_slow` |
| Audit kind (canonical hook) | `.ai-engineering/scripts/hooks/_lib/observability.py:36` | `"eval_run"` added to `_ALLOWED_KINDS` |
| Audit kind (Python validator) | `src/ai_engineering/state/event_schema.py:38` | `"eval_run"` added to `ALLOWED_EVENT_KINDS`; `"memory_event"` repaired (spec-118 mirror gap closed as side-effect) |
| Audit kind (template observability) | `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/observability.py:35-36` | `"memory_event"` + `"eval_run"` added |
| Audit kind (template hook-common) | `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/hook-common.py:65-66` | `"memory_event"` + `"eval_run"` added |
| Audit-event schema | `.ai-engineering/schemas/audit-event.schema.json` | new `$defs/detail_eval_run` covering 8 sub-operations + matching `allOf` discriminated branch |
| Lint-violation schema | `.ai-engineering/schemas/lint-violation.schema.json` | new (D-119-05) |
| Manifest section | `.ai-engineering/manifest.yml:99-117` | new top-level `evaluation:` block per D-119-04 |
| Manifest schema | `.ai-engineering/schemas/manifest.schema.json` | new `evaluation` property block (required); also `gates` block declared (parity repair — section existed in manifest but not in schema) |
| Emit helpers (canonical) | `.ai-engineering/scripts/hooks/_lib/observability.py` (tail) | `_emit_eval_run` plus 8 thin wrappers; verdict mapping for `emit_eval_gated` |
| Emit helpers (template mirror) | `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/observability.py` (tail) | mirror of canonical |
| Tests | `tests/unit/eval/` | 36 tests across `test_emit_eval_helpers.py`, `test_lint_violation_schema.py`, `test_manifest_evaluation_section.py`. All green. |

## Findings

### F-1 — spec-117 named functions absent (resolved by spike)

D-119-07 named `build_replay_outcome`, `summarize_replay_outcomes`, `build_reliability_scorecard` as if they existed in `src/ai_engineering/`. Grep confirms zero hits. The spike re-anchors the SSOT under a new module to land in Phase 2/4 (`src/ai_engineering/eval/`). Acceptance criterion in spec-119 is amended in the spike file: "the eval primitives at `src/ai_engineering/eval/` are imported by ai-evaluator runtime; no duplicated implementation exists in agent files or hooks". No spec-117 amendment is filed because the work is forward-looking.

**Disposition**: Accepted. Spike documents the divergence transparently.

### F-2 — spec-118 memory_event Python validator gap

The Python `ALLOWED_EVENT_KINDS` in `event_schema.py` did not include `memory_event` even though the canonical stdlib hook has had it since spec-118. Any caller routing through the Python `validate_event_schema` would have rejected memory_event events. Side-effect of Phase 1 T-1.3 was to add both `memory_event` and `eval_run` to the validator. Repair is documented inline in `event_schema.py` and in this review.

**Disposition**: Accepted. Side-effect repair is in scope per the SSOT principle in CONSTITUTION.md Article V.

### F-3 — Manifest schema gap on `gates`

The manifest declares a `gates:` section but the schema did not. With `additionalProperties: false` at the root, this is a latent regression — the schema would reject any manifest that uses `gates`. Phase 1 T-1.6 added the `gates` schema declaration alongside the new `evaluation` block.

**Disposition**: Accepted. Side-effect repair in scope.

### F-4 — `evaluation` is required vs optional

The manifest schema declares the top-level `evaluation` property in `properties` but the spec-119 acceptance criterion requires the section to be populated. Schema implementation makes `evaluation`'s nested keys all `required` so the section, when present, must be complete. The top-level `required` array is unchanged — projects that have not adopted spec-119 are not retroactively broken.

**Disposition**: Accepted. Conservative: enforce the contract when the section is present, do not retroactively gate.

## Ownership boundary check

Per CONSTITUTION.md Article V (SSOT) and the spec-118 D-118-04 SSOT pattern:

- `_lib/observability.py` (canonical) is the authority for stdlib hook events. ✅ updated.
- `src/ai_engineering/state/event_schema.py` is the authority for the Python validator. ✅ updated.
- `src/ai_engineering/templates/.../observability.py` and `hook-common.py` are the install templates. ✅ updated for parity.
- `.ai-engineering/schemas/audit-event.schema.json` is the JSON-schema authority. ✅ updated.
- `.ai-engineering/manifest.yml` is the per-project policy authority. ✅ updated with `evaluation:` section.
- `.ai-engineering/schemas/manifest.schema.json` is the manifest schema authority. ✅ updated.
- `.ai-engineering/schemas/lint-violation.schema.json` is the new lint-as-prompt envelope authority. ✅ created.

No ownership boundary violations.

## Hot-path impact

- Canonical `_lib/observability.py` grew by 200 lines of pure-Python helpers; no new I/O, no new dependencies. Hook entry-points unchanged. Pre-commit / pre-push budget not affected.
- New `evaluation:` manifest section is read on demand by `/ai-eval-gate` (Phase 4) — not loaded on hot paths.

## Test evidence

```
tests/unit/eval/test_emit_eval_helpers.py ............... [ 41%]
tests/unit/eval/test_lint_violation_schema.py ......      [ 58%]
tests/unit/eval/test_manifest_evaluation_section.py ......[100%]
36 passed in 0.28s
```

## Sign-off

Phase 1 foundation deltas accepted. Phase 2 (`ai-evaluator` agent) cleared to start.

Open follow-ups for the merge tracker:

- F-2 and F-3 are framework-wide repairs landed under spec-119; document in CHANGELOG once Phase 5 closes.
- spec-117 plan-117-hx-11 marks T-3.3 complete despite the named functions being absent. After spec-119 lands, raise a ticket to either retroactively credit spec-117 for the new `src/ai_engineering/eval/` module or amend plan-117 to clarify scope. Out of scope for Phase 1.
