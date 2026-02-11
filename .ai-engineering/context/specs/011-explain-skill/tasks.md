---
spec: "011"
total: 26
completed: 26
last_session: "2026-02-11"
next_session: "Done — PR pending"
---

# Tasks — Explain Skill

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `feat/explain-skill` from main
- [x] 0.2 Create spec 011 scaffold (spec.md, plan.md, tasks.md)
- [x] 0.3 Activate spec 011 in _active.md
- [x] 0.4 Update product-contract.md → 011

## Phase 1: Author [M]

- [x] 1.1 Create canonical `.ai-engineering/skills/swe/explain.md` with all 6 sections

## Phase 2: Mirror + Command [S]

- [x] 2.1 Create template mirror at `src/ai_engineering/templates/.ai-engineering/skills/swe/explain.md`
- [x] 2.2 Create slash command wrapper at `.claude/commands/swe/explain.md`
- [x] 2.3 Create command mirror at `src/ai_engineering/templates/project/.claude/commands/swe/explain.md`

## Phase 3: Register [M]

- [x] 3.1 Add to CLAUDE.md SWE Skills
- [x] 3.2 Add to AGENTS.md SWE Skills
- [x] 3.3 Add to codex.md SWE Skills
- [x] 3.4 Add to .github/copilot-instructions.md SWE Skills
- [x] 3.5 Add to src/ai_engineering/templates/project/CLAUDE.md SWE Skills
- [x] 3.6 Add to src/ai_engineering/templates/project/AGENTS.md SWE Skills
- [x] 3.7 Add to src/ai_engineering/templates/project/codex.md SWE Skills
- [x] 3.8 Add to src/ai_engineering/templates/project/copilot-instructions.md SWE Skills
- [x] 3.9 Update product-contract.md counters 32 → 33
- [x] 3.10 Add CHANGELOG entry

## Phase 4: Cross-Reference [S]

- [x] 4.1 Add explain.md ref to debug.md (canonical + mirror)
- [x] 4.2 Add explain.md ref to code-review.md (canonical + mirror)
- [x] 4.3 Add explain.md ref to architecture-analysis.md (canonical + mirror)
- [x] 4.4 Add explain.md ref to debugger.md (canonical + mirror)
- [x] 4.5 Add explain.md ref to architect.md (canonical + mirror)

## Phase 5: Verify [S]

- [x] 5.1 Canonical exists with all 6 sections
- [x] 5.2 Skill mirror byte-identical
- [x] 5.3 Command wrapper + mirror exist and are byte-identical
- [x] 5.4 grep confirm 8 instruction files
- [x] 5.5 Counter = 33 in product-contract
- [x] 5.6 CHANGELOG entry present
- [x] 5.7 Cross-refs in 6 skill files + 4 agent files
- [x] 5.8 Content-integrity pass
