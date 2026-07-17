---
spec: spec-185
title: "Plan — spec-185 amended: observe-first close-out"
status: approved
pipeline: light
phases: 2
execution_route:
  version: 1
  spec: spec-185
  executor: build
  automation: assisted
  concern_count: 1
  estimated_files: 8
  reason: "Amendment D-185-15 collapsed the five-concern program to two one-line-class fixes on the already-landed C0 substrate plus PR delivery. Single concern, <10 files, no cross-surface fan-out. Direct build on the existing branch."
  safe_next_command: "/ai-build"
---

# Plan — spec-185 amended (observe-first driver-tier telemetry)

Two one-line-class fixes on the already-landed C0 substrate, then ship
PR #639. No new mechanisms. Supersedes the M0-M4 five-concern plan per
D-185-15 (adaptive scope removed; re-entry trigger is a real
non-frontier driver observed in the sidecar).

## Phase 1 — fixes

### T-A1 AIENG_DRIVER_TIER split (D-185-16)

- [ ] Rename the resolver override env var `AIENG_MODEL_TIER` ->
      `AIENG_DRIVER_TIER` in `src/ai_engineering/state/driver_tier.py`
      (constant + docstrings), the hook mirror
      `.ai-engineering/scripts/hooks/_lib/driver_tier.py`, and the
      byte-identical template twin; update the env references in
      `tests/unit/state/test_driver_tier.py`,
      `tests/unit/hooks/test_driver_tier_parity.py`, and
      `tests/unit/hooks/test_runtime_session_start.py`.
      Gate: driver-tier + session-start suites green; hook/template twin
      byte-identical; hooks-manifest sha regenerated.

### T-A2 mimo demoted to conservative floor (D-185-17)

- [ ] Change `("mimo", "standard-floor")` -> `("mimo", "stretch-floor")`
      in all three `_FAMILY_TIERS` copies; update the mimo expectation
      in `tests/unit/state/test_driver_tier.py`.
      Gate: parity + resolver suites green (family maps equal across all
      copies).

## Phase 2 — delivery

### T-A3 ship

- [ ] Commit spec/plan amendment + fixes to
      `spec-185/open-model-resilience`; update PR #639 title/body to the
      amended scope (telemetry + two fixes; no C1-C4 promises); mark
      ready.
      Gate: CI green on the PR.
