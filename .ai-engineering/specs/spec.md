---
spec: spec-137
slug: event-relevance-discipline
title: Event Relevance Discipline — Kill the 92% Heartbeat Tail
status: approved
effort: large
branch: claude/merge-and-draft-spec-M5T9f
source_brief: .ai-engineering/specs/drafts/event-relevance-discipline-brief.md
target_dispatch: /ai-build
chains_after: spec-136
mantra: "lo que escribamos, donde sea, debe ser relevante"
date_approved: 2026-05-16
auto_approved: true
auto_approval_reason: operator invoked /ai-brainstorm --no-hitl with delegated spec authority for offline plane-travel autonomous run
summary: Collapse the 92% heartbeat tail in framework-events.ndjson by enforcing a single relevance contract at the writer boundary — drop two unconditional polling emitters (spec_verified at 848/day, install_simulate_hook at 382/day), collapse three drifting ALLOWED_EVENT_KINDS frozensets to one authoritative source, introduce a severity tier (S0-S3) as a first-class schema field, declare audit_policy in manifest, retire telemetry-debug.log, and ship the migration in a single PR with all consumers and tests updated.
---

# spec-137 — Event Relevance Discipline

> Mantra: **lo que escribamos, donde sea, debe ser relevante.**
> When 92% of the audit tail is two unconditional emit sites, signal stops being signal.

## Summary

A read-only survey on 2026-05-15 found that 1,230 of 1,335 NDJSON rows (92.1%) in a single working day came from just two unconditional polling emitters: `ai-eng spec verify` writes a `spec_verified` row on every invocation (848 rows/day, fires from the pre-commit hook), and `install_simulate_hook` writes one row per tool per synthetic install (382 rows/day). Neither emit-site honours an "emit only on state change" or "emit only on signal-worthy outcome" guard. Compounding the problem: `ALLOWED_EVENT_KINDS` is declared in three places that drift independently ([tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37), [.ai-engineering/scripts/hooks/_lib/observability.py:24](.ai-engineering/scripts/hooks/_lib/observability.py:24), [.ai-engineering/scripts/hooks/_lib/hook-common.py:54](.ai-engineering/scripts/hooks/_lib/hook-common.py:54)), the `FrameworkEvent` model has no severity/relevance hint, and `telemetry-debug.log` has zero readers anywhere in the codebase.

This spec lands a single PR that (a) enforces a **relevance contract at the writer boundary**, (b) drops the two unconditional polling emitters in favour of emit-on-change semantics with a fail-open carve-out for failures, (c) collapses the three frozensets to a single authoritative source with two import-only mirrors and a CI test that asserts no drift, (d) introduces `severity` as a first-class enum field (`S0` critical, `S1` state-change, `S2` decision, `S3` debug) on `FrameworkEvent` with `schemaVersion` bumped to `2`, (e) declares an `audit_policy:` block in the manifest carrying the kind allow-list and per-kind severity floor, (f) retires `telemetry-debug.log` entirely (no readers), (g) updates every consumer (`audit index`, `query`, `tokens`, `replay`, `otel-export`, instinct extractor) to handle both pre-v2 (read-only) and post-v2 (read+write) shapes via a schema-version-aware reader, (h) rewrites the 18 enumerated tests, (i) adds a new test asserting the three frozenset sites import from the same authority, (j) adds a new test asserting no unconditional emit exists for the two retired heartbeats, (k) records the mechanism decision in `state.db decisions` as D-137-01, and (l) commits a CHANGELOG entry documenting the breakage.

## Goals

1. **Volume reduction.** After this PR, framework-events.ndjson contains ≤ 150 lines after a typical working day (down from 1,335 — ~89% reduction). Measured via a synthetic full-day session in the post-merge follow-up; the unit-test substitute is `tests/unit/state/test_event_relevance_no_heartbeats.py` asserting zero unconditional emit sites for the two retired operations.
2. **Single source of truth for kinds.** Only one authoritative `ALLOWED_EVENT_KINDS` exists at [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37); the other two sites are import-only mirrors. Test `tests/unit/state/test_event_kinds_single_source.py` asserts the three sites resolve to the same frozenset membership.
3. **Severity is first-class.** `FrameworkEvent` carries a required `severity` field with the four-value enum `S0|S1|S2|S3`. All emitters post-migration set it explicitly. Default-deny posture: callers must pick a tier; no fallback default.
4. **Manifest declares the policy.** [.ai-engineering/manifest.yml:98](.ai-engineering/manifest.yml:98) carries a new `audit_policy:` block with `kind_allowlist`, `severity_floor`, `sampling`, and `failure_emission` fields. The installer carries the policy default. Test `tests/unit/test_manifest_audit_policy_default.py` asserts the default block is loaded by every template.
5. **Telemetry-debug.log retired.** All four call sites stripped; no new emit sites; `AIENG_TELEMETRY_DEBUG` env var removed from runtime tunables; `state/telemetry-debug.log` no longer created.
6. **Hot-path budget preserved.** Relevance gate is pure-Python dict lookup (manifest-loaded kind allow-list) plus int comparison (severity floor). Pre-commit < 1 s, pre-push < 5 s (CLAUDE.md Hot-Path Discipline).
7. **Audit chain integrity preserved.** `ai-eng audit verify` green; `prev_event_hash` chain unbroken end-to-end across the migration cut. The chain is append-only; the migration only changes what is written after the cut, not what was written before.
8. **Consumers updated.** `ai-eng audit index`, `query`, `tokens`, `replay`, `otel-export` all green against both pre-v2 (read-only, historical) and post-v2 (read+write, current) event shapes via a schema-version-aware reader. The instinct extractor handles the new kind set.
9. **Failure-emission asymmetric.** Even if normal-success row is filtered, the corresponding failure row always emits. `spec_verified` with `drift_detected=true` always emits; `install_simulate_hook` with `outcome != success` always emits. Encoded as the `failure_emission: always` field in the manifest audit policy.
10. **CHANGELOG documents the breakage.** Entry under "Unreleased" enumerates retired emit semantics, retired sinks, schemaVersion bump (1 → 2), and the new manifest `audit_policy:` shape.

## Non-Goals

- Do **not** retire any `ALLOWED_EVENT_KINDS` member. All 13 declared kinds preserved (D-137-02).
- Do **not** unify `observation-events.ndjson` with `framework-events.ndjson` (D-137-03).
- Do **not** bring `lock-failures.ndjson` under the relevance contract (D-137-04).
- Do **not** rewrite historical NDJSON (D-137-05).
- Do **not** introduce an `AIENG_AUDIT_POLICY_PATH` env-var runtime override (D-137-06).
- Do **not** add a CI gate rejecting new emit sites without a paired policy entry (D-137-07; deferred).
- Do **not** bootstrap `state.db decisions` with historical decisions (D-137-08; deferred).
- Do **not** introduce per-kind sampling beyond the existing 10% policy-decision allow-sampler (D-137-09; deferred).
- Do **not** redesign the `outcome` enum (D-137-10).

## Decisions

- **D-137-01 — Relevance mechanism is hybrid: kind allow-list + severity tier + change-driven emission.** Three-layer contract at the writer boundary: (1) kind allow-list (manifest-driven, empty means no restriction), (2) per-kind severity floor S0..S3 (manifest-driven), (3) caller-asserted change-driven emission for the two retired heartbeats (`spec_verified` only when drift_detected; `install_simulate_hook` only when outcome != success).
  *Rationale*: combines OTel-semconv allow-list, OTel SeverityNumber tier, and Honeycomb / Observability 2.0 caller-asserted relevance. Filtering happens at the writer boundary, not at the reader, so noise never enters the chain.

- **D-137-02 — All 13 declared kinds preserved in ALLOWED_EVENT_KINDS.**
  *Rationale*: removing kinds is a breaking change for consumers (audit_index, otel_export, instinct extractor, three rollup views). Making the gate conditional achieves the volume goal without breaking the consumer surface.

- **D-137-03 — Observation-events bifurcation preserved.**
  *Rationale*: the instincts sliding window has a distinct schema, distinct lifecycle, and self-pruning policy. Bringing it into the append-only audit chain would violate CONSTITUTION.md §13.1 or defeat the instincts purpose.

- **D-137-04 — Lock-failure sidecar stays separate.**
  *Rationale*: lock failures happen precisely when the writer is contended. Writing them to the same chain would be self-referential and lossy. Sidecar (`lock-failures.ndjson`) keeps its own discipline outside the hash chain.

- **D-137-05 — Historical NDJSON readability via schema-version-aware reader, not rewrite.**
  *Rationale*: rewriting historical rows would break `prev_event_hash` chain integrity. Reader inspects `schemaVersion` per row and projects accordingly; writer emits only the new shape after the cut.

- **D-137-06 — No runtime env-var override (no AIENG_AUDIT_POLICY_PATH).**
  *Rationale*: defence-in-depth requires that the active policy be inspectable from the manifest snapshot at any moment. An env-var override would let an operator silently change emission behaviour without leaving a manifest-diff trail.

- **D-137-07 — CI guard for new emit sites deferred to spec-138.**
  *Rationale*: the relevance contract is already enforced at runtime via the manifest gate. A static CI guard that greps the diff for `emit_framework_event` without paired policy entry is additive hardening, valuable but not blocking; deferring keeps this PR scoped.

- **D-137-08 — Decisions table backfill deferred.**
  *Rationale*: `state.db decisions` is empty today; D-137-01 is the first row inserted. Historical decision archaeology (backfilling D-110-03, D-122-23, D-127-10, etc.) is a separate project.

- **D-137-09 — Per-kind sampling deferred.**
  *Rationale*: the existing 10% policy-decision allow-sampler stays as-is. Per-kind manifest-driven sampling is a future cost/budget tuning knob, out of scope for this PR. Volume goal is met by allow-list + floor + change-driven emission.

- **D-137-10 — `outcome` enum preserved unchanged.**
  *Rationale*: `outcome` is the current-state quality hint (`success` / `failure` / `degraded` / `warn` / `allow` / `blocked`); `severity` is the orthogonal relevance signal. Two distinct concerns; both stay first-class.

## Architecture

The intervention lives at the **writer boundary** — the two canonical writers [src/ai_engineering/state/observability.py:107](src/ai_engineering/state/observability.py:107) (package side, `_append_framework_events_locked`) and [.ai-engineering/scripts/hooks/_lib/observability.py:224](.ai-engineering/scripts/hooks/_lib/observability.py:224) (hook-side stdlib mirror). Both writers gain a `_relevance_admits(event, policy)` precondition that returns `True` if the event survives the contract; otherwise the writer drops silently.

```
┌───────────────────────────────────────────────────────────────────┐
│ Caller emits with kind, severity, detail                          │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ Relevance Contract  (audit_policy from manifest)                  │
│   1. kind ∈ kind_allowlist?  ─ no → DROP                          │
│   2. severity ≥ severity_floor[kind]?  ─ no → DROP                │
│   3. failure_emission=always AND outcome != success?  ─ yes → KEEP│
│   4. caller's relevance_claim admissible?  ─ no → DROP             │
└───────────────────────────────┬───────────────────────────────────┘
                                │ admitted
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ Canonical writer (chooses sink)                                   │
│   - framework-events.ndjson (hash-chained)                        │
│   - state.db events (projection)                                  │
│   - runtime/event-sidecars/<sha>.json                             │
└───────────────────────────────────────────────────────────────────┘
```

The contract is implemented in a single helper, `relevance_gate(event, policy) -> bool`, located in `src/ai_engineering/state/relevance.py`. The hook-side stdlib copy at `.ai-engineering/scripts/hooks/_lib/relevance.py` mirrors it byte-for-byte (asserted by a parity test).

The three `ALLOWED_EVENT_KINDS` frozensets collapse: only [tools/skill_domain/event_schema.py:37](tools/skill_domain/event_schema.py:37) is authoritative; the hook-side mirror re-declares the constant and a CI test asserts the membership equality.

`FrameworkEvent` gains a new required field `severity: Literal["S0", "S1", "S2", "S3"]`. `schemaVersion` bumps `1 → 2`. The `events` table in `state.db` gains a new nullable `severity` column.

## Implementation Surface (M1..M7)

### M1 — Decision row

- Persist D-137-01 into `state.db decisions` with rationale, alternatives, and SHA placeholder.

### M2 — Schema migration (single source of truth + severity field)

- Add `severity` to [tools/skill_domain/event_schema.py](tools/skill_domain/event_schema.py) required-field tuple and `FrameworkEvent` TypedDict.
- Bump `schemaVersion` constant `1 → 2`.
- Mirror sites: re-declare `_ALLOWED_KINDS` in [.ai-engineering/scripts/hooks/_lib/observability.py:24](.ai-engineering/scripts/hooks/_lib/observability.py:24) and [.ai-engineering/scripts/hooks/_lib/hook-common.py:54](.ai-engineering/scripts/hooks/_lib/hook-common.py:54); add CI test asserting equality with authority.
- Add `severity` to `state.db events` table via new migration.

### M3 — Relevance gate + emitter updates

- Create `src/ai_engineering/state/relevance.py` exporting `relevance_gate(event, policy) -> bool`.
- Create `.ai-engineering/scripts/hooks/_lib/relevance.py` (stdlib mirror).
- Wire `relevance_gate` into both canonical writers before the write.
- Update `spec_verified` emit-site: emit only when drift detected or state changed.
- Update `install_simulate_hook` emit-site: emit only on failure or first-seen mechanism.
- All other emitters: add explicit `severity=` argument.

### M4 — Consumer updates (schema-version-aware reader)

- Add `severity` column to the `events` projection in `audit_index.py`.
- Bulk-read inspects `schemaVersion` per row and applies default severity for v1 rows.
- Map `severity` to OTel `SeverityNumber` in `audit_otel_export.py`.

### M5 — Test updates

Rewrite the 18 enumerated tests in brief §5 to include `severity` and post-v2 shape.

New tests:
- `tests/unit/state/test_event_kinds_single_source.py` — asserts the three frozenset sites cannot drift.
- `tests/unit/state/test_event_relevance_gate.py` — parametrized over all 13 kinds × 4 severities × failure_emission on/off.
- `tests/unit/state/test_event_relevance_no_heartbeats.py` — grep-test asserting no unconditional emit for the two retired heartbeats.
- `tests/unit/test_manifest_audit_policy_default.py` — asserts default audit_policy shape in manifest.
- `tests/unit/hooks/test_telemetry_debug_log_retired.py` — asserts no call sites + env-var removed.

### M6 — Manifest + docs

Add to `.ai-engineering/manifest.yml`:
```yaml
audit_policy:
  kind_allowlist: [skill_invoked, agent_dispatched, context_load, ide_hook,
    framework_error, framework_operation, git_hook, control_outcome, task_trace,
    memory_event, eval_run, retention_applied, policy_decision]
  severity_floor:
    framework_operation: S2
    ide_hook: S2
    framework_error: S0
    default: S1
  sampling:
    policy_decision_allow: 0.10
  failure_emission: always
```

Mirror into installer template. Create `docs/event-relevance.md`.

### M7 — Audit chain verification + CHANGELOG

- `ai-eng audit verify` green.
- CHANGELOG entry under `## Unreleased` enumerating breakages and migration.

## Acceptance

- [ ] Relevance mechanism implemented; D-137-01 persisted.
- [ ] Single-source-of-truth test green.
- [ ] `severity` first-class; `schemaVersion=2`.
- [ ] Manifest carries `audit_policy:` with documented default.
- [ ] `telemetry-debug.log` retired.
- [ ] Hot-path budget preserved.
- [ ] `ai-eng audit verify` green.
- [ ] All 18 enumerated tests rewritten; 5 new tests added.
- [ ] No suppression added; no backwards-compat shim.
- [ ] CHANGELOG entry committed.
- [ ] `pytest tests/unit/` green.

## Risks

| ID | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | A retired heartbeat turns out to carry signal we depend on (audit blind spot). | Medium | High | Failure-emission asymmetry keeps failure rows; drift_detected rows still emit; tests assert the conditional shape. |
| R2 | Audit chain integrity breaks during migration cut. | Low | Critical | Chain is append-only; migration only changes what is written after the cut. `ai-eng audit verify` green. |
| R3 | Three-frozenset drift returns when a future PR adds a kind to only one site. | Medium | Medium | `test_event_kinds_single_source.py` asserts membership equality on every CI run. |
| R4 | Hot-path budget regresses if relevance gate is heavy. | Low | High | Gate is pure-Python dict lookup + int compare; benchmark holds pre-commit < 1s, pre-push < 5s. |
| R5 | Operators bypass the policy via a hidden env var. | Low | Medium | D-137-06: no env-var override exists; policy is manifest-only. |
| R6 | A future polling emitter violates the contract without being caught. | High | Medium | D-137-07 CI guard deferred; until then, code review plus the heartbeat AST guard catch the two known offenders. |
| R7 | Test rewrites miss an assertion that locks a retired emit semantic. | Medium | Medium | Exhaustive grep for `spec_verified` and `install_simulate_hook` in tests; one local plus one CI sweep before merge. |
| R8 | Severity field semantics drift across emitters as new callers pick the wrong tier. | Medium | Low | `docs/event-relevance.md` (follow-up) documents the four-tier vocabulary; default S1 keeps the change backward-compatible. |

## Quality Stamps

- **§10.1 KISS** — Fewer rows, one contract surface, one writer pair, one frozenset authority.
- **§10.2 YAGNI** — No env-var override, no per-kind sampling, no CI guard, no historical bootstrap.
- **§10.5 TDD** — New tests precede writer changes.
- **§10.6 SDD** — Brief → spec → plan → build.
- **§10.7 Clean Code** — `severity` named at point of emission; relevance is a precondition.

---

**Handoff**: this spec is the contract for `/ai-plan`.
