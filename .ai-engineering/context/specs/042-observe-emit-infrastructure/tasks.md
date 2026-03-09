---
spec: "042"
total: 18
completed: 18
---

# Tasks — Spec 042

## Phase 1: Enrich Session Event
- [x] T01: Read checkpoint data in `checkpoint_save()` before emit
- [x] T02: Pass task, progress, skills to `emit_session_event()`
- [x] T03: Test enriched session events

## Phase 2: Auto-Remediation Tracking
- [x] T04: Detect fixable checks via `_FIXABLE_CHECKS` frozenset
- [x] T05: Add `fixable_failures` to gate_result detail
- [x] T06: Add `noise_ratio_from()` aggregator to signals.py
- [x] T07: Test gate remediation tracking + aggregator

## Phase 3: Agent Instruction Updates
- [x] T08: Verified build.md agent already has emission step (lines 86-93)
- [x] T09: Verified scan.md agent already has emission step (lines 73-80)
- [x] T10: Sync agent templates

## Phase 4: Dashboard Expansion
- [x] T11: Team dashboard — Token Economy section
- [x] T12: Team dashboard — Noise Ratio section
- [x] T13: AI dashboard — enriched Context Efficiency (avg tokens/session)
- [x] T14: Test dashboard sections (18 tests in test_emit_infrastructure.py)

## Phase 5: Health Score Integration
- [x] T15: Add noise ratio as optional health component (Gate signal quality)
- [x] T16: Test health score with noise ratio

## Phase 6: Verification
- [x] T17: Full test suite (1339 passed) + ruff + ty clean
- [x] T18: Smoke test — all observe modes verified
