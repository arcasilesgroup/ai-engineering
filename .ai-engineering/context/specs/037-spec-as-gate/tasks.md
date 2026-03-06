---
spec: "037"
total: 12
completed: 9
last_session: "2026-03-06"
next_session: "Phase 4 — Validation"
---

# Tasks — Spec-as-Gate

## Phase 0: Scaffold [S]
- [x] 0.1 Create spec, plan, tasks under `context/specs/037-spec-as-gate/`

## Phase 1: CLI `ai-eng spec save` [M]
- [x] 1.1 Create `src/ai_engineering/cli_commands/spec_save.py` — parse stdin, validate, scaffold
- [x] 1.2 Register `spec save` subcommand in `cli_factory.py`
- [ ] 1.3 Unit tests for spec_save (parse, validate, scaffold, error cases)

## Phase 2: Update agent + skills [S]
- [x] 2.1 Update `agents/plan.md` — produce spec as text + call `ai-eng spec save` + STOP
- [x] 2.2 Update `skills/spec/SKILL.md` — add CLI-driven path section
- [x] 2.3 Update `skills/plan/SKILL.md` — reference CLI save in shared rules

## Phase 3: Cross-IDE configuration [S]
- [x] 3.1 Update `.github/copilot-instructions.md` with Spec-as-Gate flow
- [x] 3.2 Create `.cursor/rules/ai-engineering.mdc`
- [x] 3.3 Document other IDEs setup in docs/

## Phase 4: Validation [S]
- [ ] 4.1 Integration test: stdin pipe -> spec files on disk
- [ ] 4.2 End-to-end validation: plan -> save -> execute reads spec
