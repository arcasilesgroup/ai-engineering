---
spec: "052"
total: 14
completed: 0
last_session: "2026-03-15"
next_session: "2026-03-15"
---

# Tasks — Spec 052

## Phase 1: Plan Agent — Interrogation Phase [M]

- [ ] T-001: Add Interrogation Phase section to `agents/plan.md` (after Session Recovery, before Behavior)
  - 7 steps: explore, ask ONE AT A TIME, challenge vague, map KNOWN/ASSUMED/UNKNOWN, challenge assumptions, second-order, surface constraints
  - Gate: "Do not proceed until zero UNKNOWNs remain"
- [ ] T-002: Add PLAN-R5 (Interrogation) shared rule to `skills/plan/SKILL.md` after PLAN-B1
- [ ] T-003: Verify plan agent references PLAN-R5 in behavior section

**Phase 1 Gate**: `grep -c "Interrogation Phase" .ai-engineering/agents/plan.md` ≥ 1

## Phase 2: Acceptance Criteria in Spec Scaffold [S]

- [ ] T-004: Modify AC section in `skills/spec/SKILL.md` scaffold — prose → executable table with Verification Command + Expected columns
- [ ] T-005: Add guidance note: "No prose-only ACs. If you can't write a command, the criterion is too vague."

**Phase 2 Gate**: `grep -c "Verification Command" .ai-engineering/skills/spec/SKILL.md` ≥ 1

## Phase 3: TDD Protocol in Build Agent [M]

- [ ] T-006: Add TDD Protocol section to `agents/build.md` (after Code-Simplifier vs Refactor)
  - Phase RED: write failing tests + produce Implementation Contract
  - Phase GREEN: implement without modifying tests
  - REFACTOR: after green only
- [ ] T-007: Add Iron Law rule: "NEVER weaken tests. If tests are wrong, escalate to user."
- [ ] T-008: Add dispatch enforcement guidance: tasks RED and GREEN are separate, tests from RED are immutable in GREEN

**Phase 3 Gate**: `grep -c "TDD Protocol" .ai-engineering/agents/build.md` ≥ 1 AND `grep -c "Iron Law" .ai-engineering/agents/build.md` ≥ 1

## Phase 4: Test Skill Rewrite [L]

- [ ] T-009: Write test/SKILL.md core sections (philosophy, 4 modes, TDD cycle with Iron Law, AAA pattern, naming convention)
- [ ] T-010: Write fakes over mocks section + test categories (unit, integration, e2e)
- [ ] T-011: Write stack-specific sections (Python, TypeScript, .NET, React, Next.js, Node, Rust, Go, Java — ~8 lines each)
- [ ] T-012: Write rationalization table + flaky test diagnostic + verification checklist + governance notes

**Phase 4 Gate**: `wc -l .ai-engineering/skills/test/SKILL.md` < 500 AND ≥5 stack sections present

## Phase 5: Sync + Validate [S]

- [ ] T-013: Run `python scripts/sync_command_mirrors.py` — sync all 5 mirror surfaces
- [ ] T-014: Sync templates + run all 10 ACs from spec.md — all must pass

**Phase 5 Gate**: All 10 ACs pass (see spec.md Acceptance Criteria table)
