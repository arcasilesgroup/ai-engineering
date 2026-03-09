---
spec: "043"
total: 11
completed: 0
last_session: "2026-03-09"
next_session: "Phase 1 — Consolidate Contracts"
---

# Tasks — Slim Root Instructions

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec directory and files
- [x] 0.2 Activate spec in `_active.md`
- [x] 0.3 Commit scaffold

## Phase 1: Consolidate Contracts [M]

- [ ] 1.1 Add Command Contract section to `framework-contract.md` (§5 or append to §2)
- [ ] 1.2 Verify pipeline strategy is complete in `framework-contract.md`
- [ ] 1.3 Verify skills/agents/CLI tables are current in `product-contract.md`

## Phase 2: Slim Root Files [M]

- [ ] 2.1 Rewrite `CLAUDE.md` to ≤60 lines (keep prohibitions + session start + pointers)
- [ ] 2.2 Rewrite `AGENTS.md` to ≤70 lines (keep agent mandates + session start + pointers)
- [ ] 2.3 Rewrite `.github/copilot-instructions.md` to ≤40 lines (keep spec-as-gate + pointers)

## Phase 3: Add Loading Directives [S]

- [ ] 3.1 Update `skills/spec/SKILL.md` — add "read product-contract §7" in Phase 5
- [ ] 3.2 Update `skills/pr/SKILL.md` — add "read product-contract" directive
- [ ] 3.3 Update `agents/plan.md` — add explicit "read contracts" step in Behavior

## Phase 4: Validate [S]

- [ ] 4.1 Run `ai-eng validate` and fix any broken references
- [ ] 4.2 Verify line counts: CLAUDE.md ≤60, AGENTS.md ≤70, copilot ≤40
