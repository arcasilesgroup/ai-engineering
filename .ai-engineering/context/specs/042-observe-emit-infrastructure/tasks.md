---
spec: "042"
total: 18
completed: 0
---

# Tasks — Spec 042

## Phase 1: Enrich Session Event
- [ ] T01: Read checkpoint data in `checkpoint_save()` before emit
- [ ] T02: Pass task, progress, skills to `emit_session_event()`
- [ ] T03: Test enriched session events

## Phase 2: Auto-Remediation Tracking
- [ ] T04: Detect auto-remediation in pre-commit gate checks
- [ ] T05: Add `auto_remediated_count` to gate_result detail
- [ ] T06: Add `noise_ratio_from()` aggregator to signals.py
- [ ] T07: Test gate remediation tracking + aggregator

## Phase 3: Agent Instruction Updates
- [ ] T08: Update build.md agent with emission step
- [ ] T09: Update scan.md agent with emission step
- [ ] T10: Sync agent templates

## Phase 4: Dashboard Expansion
- [ ] T11: Team dashboard — Token Economy section
- [ ] T12: Team dashboard — Noise Ratio section
- [ ] T13: AI dashboard — enriched Context Efficiency
- [ ] T14: Test dashboard sections

## Phase 5: Health Score Integration
- [ ] T15: Add noise ratio to health components
- [ ] T16: Test health score with noise ratio

## Phase 6: Verification
- [ ] T17: Full test suite + linting
- [ ] T18: Smoke test all observe modes
