---
spec: "035"
total: 11
completed: 0
last_session: "2026-03-04"
next_session: "Phase 0 — Scaffold"
---

# Tasks — Extend feature-gap with wiring detection

## Phase 0: Scaffold [S]

- [ ] 0.1 Create branch `spec-035/feature-gap-wiring` from main
- [ ] 0.2 Scaffold spec.md, plan.md, tasks.md
- [ ] 0.3 Activate in `_active.md`
- [ ] 0.4 Atomic commit: `spec-035: Phase 0 — scaffold spec files and activate`

## Phase 1: Update feature-gap skill [S]

- [ ] 1.1 Update metadata: description adds "wiring gaps", tags add `wiring`, `dead-code-functional`
- [ ] 1.2 Update Purpose section to cover implementation-vs-integration gaps
- [ ] 1.3 Add procedure step 5.5 — Detect wiring gaps (6 detection categories)
- [ ] 1.4 Add Wiring Matrix table to Output section
- [ ] 1.5 Atomic commit: `spec-035: Phase 1 — extend feature-gap skill with wiring detection`

## Phase 2: Update scan agent [S]

- [ ] 2.1 Update mode table: feature-gap description includes wiring gaps
- [ ] 2.2 Update threshold table: feature-gap includes ">5 unwired exports" critical threshold
- [ ] 2.3 Atomic commit: `spec-035: Phase 2 — update scan agent for wiring coverage`

## Phase 3: Validate [S]

- [ ] 3.1 Read updated files, verify procedure coherence (steps 1-6 with 5.5)
- [ ] 3.2 Run `ai-eng validate` — zero integrity errors
