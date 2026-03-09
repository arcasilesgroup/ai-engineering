---
spec: "043"
total: 11
completed: 11
last_session: "2026-03-09"
next_session: "CLOSED"
---

# Tasks — Slim Root Instructions

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec directory and files
- [x] 0.2 Activate spec in `_active.md`
- [x] 0.3 Commit scaffold

## Phase 1: Consolidate Contracts [M]

- [x] 1.1 Add Command Contract section to `framework-contract.md` (§5)
- [x] 1.2 Verify pipeline strategy is complete in `framework-contract.md`
- [x] 1.3 Add skills/agents/CLI tables to `product-contract.md` (§2.2)

## Phase 2: Slim Root Files [M]

- [x] 2.1 Rewrite `CLAUDE.md` to 50 lines (target ≤60)
- [x] 2.2 Rewrite `AGENTS.md` to 68 lines (target ≤70)
- [x] 2.3 Rewrite `copilot-instructions.md` to 40 lines (target ≤40)

## Phase 3: Add Loading Directives [S]

- [x] 3.1 Update `skills/spec/SKILL.md` — add "read product-contract §7" in Phase 5
- [x] 3.2 Update `skills/pr/SKILL.md` — add "read product-contract" directive
- [x] 3.3 Update `agents/plan.md` — add explicit "read contracts" step in Behavior

## Phase 4: Validate [S]

- [x] 4.1 Run `ai-eng validate` — 7/7 PASS, update validators for pointer format
- [x] 4.2 Verify line counts: CLAUDE.md 50 ≤60 ✓, AGENTS.md 68 ≤70 ✓, copilot 40 ≤40 ✓
