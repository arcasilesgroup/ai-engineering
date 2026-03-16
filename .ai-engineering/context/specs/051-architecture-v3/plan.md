---
spec: "051"
approach: "serial-phases"
---

# Plan — Architecture v3

## Architecture

### New Files

| File | Purpose | Agent |
|------|---------|-------|
| `agents/guard.md` | Proactive governance guardian | guard |
| `agents/guide.md` | Developer growth mentor | guide |
| `agents/operate.md` | SRE/operations automation | operate |
| `skills/guard/SKILL.md` | Guard advisory procedures | guard |
| `skills/dispatch/SKILL.md` | Formal task dispatch schema | execute |
| `skills/guide/SKILL.md` | Teaching/explanation procedures | guide |
| `skills/onboard/SKILL.md` | Codebase onboarding | guide |
| `skills/evolve/SKILL.md` | Self-improvement analysis | observe |
| `skills/ops/SKILL.md` | Operational automation | operate |
| `standards/governance/agent-model.md` | Agent session contract | — |
| `.ai-engineering/README.md` | Developer guide | — |

### Modified Files

| File | Change |
|------|--------|
| `agents/plan.md` | Add guard.forecast, remove explain ref, add guide ref |
| `agents/execute.md` | Add formal dispatch, guard.gate pre-dispatch |
| `agents/build.md` | Add guard.advise to post-edit validation, rename build skill→code |
| `agents/verify.md` → `agents/verify.md` | Rename + boundary clarification |
| `agents/ship.md` → `agents/ship.md` | Rename + boundary clarification |
| `agents/observe.md` | Add evolve skill reference |
| `agents/write.md` | Rename docs→document |
| 5 stub skills | Expand to full procedures |
| 12 skill directories | Rename to self-documenting names |
| `skills/create/` + `skills/delete/` | Merge into `skills/lifecycle/` |
| `skills/work-item/` | Rename to `skills/triage/` + refocus |
| All 5 runbooks | Add `owner: operate` (consolidated from 14) |
| `manifest.yml` | 10 agents, 40 skills |
| `framework-contract.md` | Rewrite for v3 architecture |
| `product-contract.md` | Rewrite for v3 |
| `GOVERNANCE_SOURCE.md` | Rewrite canonical source |
| Root `README.md` | Architecture overview |
| `CHANGELOG.md` | v0.3.0 entry |
| Python source (6 files) | Update hardcoded names |
| Tests (3 files) | Update assertions |
| IDE adapters (~80 files) | Regenerate per renames |
| `src/ai_engineering/templates/` | Full mirror sync |

### Mirror Copies

All canonical `.ai-engineering/` content mirrors to `src/ai_engineering/templates/.ai-engineering/`.

## Session Map

### Phase 1: Expand Stubs [M]
- Agent: build
- Why FIRST: Don't rename facades. Fix content before renaming.
- Files: 5 skill SKILL.md files

### Phase 2: Create New Agents + Skills [L]
- Agent: build + plan (governance)
- Files: 3 agents, 6 skills, 5 runbooks, agent cross-references

### Phase 3: Renames [L]
- Agent: build
- Files: 2 agents, 12 skills, Python source, tests, IDE adapters, docs
- Batch: all renames in minimal commits

### Phase 4: Standards Reorganization [M]
- Agent: build
- Files: standards directory restructure

### Phase 5: Contracts + Documentation [L]
- Agent: write + build
- Files: framework-contract, product-contract, README, CHANGELOG, GOVERNANCE_SOURCE, IDE adapters

### Phase 6: Template Mirror + Validation [M]
- Agent: build + scan
- Files: src/ai_engineering/templates/, all tests

## Patterns

- One commit per sub-phase: `spec-051: Phase N.M — description`
- Renames batch to minimize commit count
- Expand stubs BEFORE any rename (Phase 1 before Phase 3)
- Create new content BEFORE rename (Phase 2 before Phase 3)
- Tests updated in SAME commit as the code they test
- Mirror sync as final phase to catch all accumulated changes
