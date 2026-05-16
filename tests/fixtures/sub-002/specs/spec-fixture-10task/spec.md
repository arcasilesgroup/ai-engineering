---
spec: spec-fixture
title: "10-task synthetic spec fixture for sub-002 telemetry test"
status: approved
effort: medium
---

## Summary

Synthetic 10-task fixture used by `tests/integration/test_quality_loop_telemetry.py`
to validate the ≈90 % drop in per-task `verify_dispatch` and `review_dispatch`
events delivered by spec-131 D-131-05 (single quality loop, fail-loud).

## Goals

- Provide a deterministic 10-task corpus for telemetry regression.

## Non-Goals

- This fixture is not run by `/ai-build`; it feeds a baseline NDJSON snapshot
  consumed by the integration test.

## Decisions

- **D-fixture-01 — Static fixture.** Test depends on the committed NDJSON
  snapshot at `tests/fixtures/sub-002/baseline-events.ndjson`, not on a
  live re-dispatch. *Rationale*: keeps the test hermetic and deterministic
  across CI runs.

## Risks

- **R-fixture-01 — Fixture drift if event schema changes.** Mitigation:
  bump the fixture and the assertion together; the assertion checks the
  `subagent_type` field by name, not by ordinal.
