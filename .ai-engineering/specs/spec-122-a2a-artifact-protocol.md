# spec-122 — Agent-to-agent (A2A) artifact protocol + ACI severity

**Status:** approved (carved out of harness gap closure 2026-05-04)
**Author:** harness-gap-closure-2026-05-04
**Depends on:** spec-118 (memory layer), spec-120 (audit projection)

## Summary

Two doctrine primitives that were missing from the framework and would
otherwise have shipped as silent gaps:

* **A2A artifact protocol (P3.1)** — Every agent invocation produces a
  schema-bound `AgentArtifact` JSON persisted under
  `.ai-engineering/state/agent-artifacts/<run-id>.json`. Subagent
  dispatchers (`Task` / `Agent`) can write the artifact at exit and
  downstream consumers (replay, audit, eval-gate) can recover the
  parent → children chain without re-parsing strings.

* **ACI severity (P3.2)** — The `framework_error` event family gains
  `detail.severity ∈ {recoverable, terminal, advisory}` and an optional
  `detail.recovery_hint`. The wire schema bumps from `1.0` to `1.1`
  with backward compatibility (consumers default severity to
  `advisory` when the field is absent). The SQLite audit projection
  surfaces both fields as top-level columns so SQL filters don't need
  `json_extract()` round-trips.

## Decisions

* **D-122-01** — `AgentArtifact` is a frozen dataclass (no Pydantic).
  Stays in `_lib/agent_protocol.py` so hook scripts can import without
  paying the `ai_engineering.*` import cost.
* **D-122-02** — Atomic write via tempfile + `os.replace`.
  Concurrent writes for the same `run_id` resolve to a single winner.
* **D-122-03** — `severity` field is **optional** in v1.1.
  Backward compat: events without it parse fine; consumers default to
  `advisory`. A `terminal` severity is the strongest signal a recovery
  path is impossible.
* **D-122-04** — Audit-index migration is additive ALTER inside
  `_create_schema`. SQLite raises `OperationalError` on duplicate
  column add; the helper catches and ignores so re-runs are no-ops.
* **D-122-05** — `confidence ∈ [0.0, 1.0]` is optional and self-
  reported by the agent. No automatic calibration in v1.

## Out of scope (deferred)

* `runs/<session-id>/` symlink layout for fast trace lookups (current
  impl walks the artifacts directory; ~10k entries → ~100ms scan).
* CLI surface `ai-eng agent inspect` / `ai-eng agent trace` is
  documented as the integration point; the implementation lives in
  spec-123 (a follow-up).

## Tests

* `tests/unit/_lib/test_agent_protocol.py` — schema round-trip,
  invalid status raises, atomic concurrent writes, trace_session walk,
  nested parent_run_id, on-disk JSON shape.
* `tests/unit/hooks/test_event_schema_v11.py` — schema version
  bumped, severity validation, audit-index projection, legacy v1.0
  events still parse with NULL severity.

## Acceptance

* `tests/unit/_lib/test_agent_protocol.py` passes (8 tests).
* `tests/unit/hooks/test_event_schema_v11.py` passes (7 tests).
* `.ai-engineering/state/audit-index.sqlite` has `severity` +
  `recovery_hint` columns after rebuild.
* All pre-existing v1.0 tests still pass.
