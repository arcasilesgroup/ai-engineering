---
spec: "035"
total: 14
completed: 14
last_session: "2026-03-04"
next_session: "CLOSED"
---

# Tasks — Extend feature-gap with wiring detection

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `spec-035/feature-gap-wiring` from main
- [x] 0.2 Scaffold spec.md, plan.md, tasks.md
- [x] 0.3 Activate in `_active.md`
- [x] 0.4 Atomic commit: `spec-035: Phase 0 — scaffold spec files and activate`

## Phase 1: Update feature-gap skill [S]

- [x] 1.1 Update metadata: description adds "wiring gaps", tags add `wiring`, `dead-code-functional`
- [x] 1.2 Update Purpose section to cover implementation-vs-integration gaps
- [x] 1.3 Add procedure step 5.5 — Detect wiring gaps (6 detection categories)
- [x] 1.4 Add Wiring Matrix table to Output section
- [x] 1.5 Atomic commit: `spec-035: Phase 1 — extend feature-gap skill with wiring detection`

## Phase 2: Update scan agent [S]

- [x] 2.1 Update mode table: feature-gap description includes wiring gaps
- [x] 2.2 Update threshold table: feature-gap includes ">5 unwired exports" critical threshold
- [x] 2.3 Atomic commit: `spec-035: Phase 2 — update scan agent for wiring coverage`

## Phase 3: Validate [S]

- [x] 3.1 Read updated files, verify procedure coherence (steps 1-6 with 5.5)
- [x] 3.2 Run `ai-eng validate` — zero integrity errors
