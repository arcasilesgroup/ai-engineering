# Plan 002: Cross-Reference Hardening + Skill Registration

## Environment

- **Python**: 3.11.4
- **Package manager**: `uv`
- **Linter/formatter**: `ruff` (line-length 100)
- **Type checker**: `ty`
- **OS**: Windows primary
- **VCS**: GitHub (`arcasilesgroup/ai-engineering`)
- **Branch**: `main` (direct — content-only changes, no Python code)

## Architecture Overview

```
Phase 0: Scaffold
├── Create spec 002 directory and files
└── Update _active.md

Phase 1: New Skill Creation
├── Create 4 canonical skill files (docs/)
└── Create 4 template mirrors

Phase 2: Cross-Reference Hardening
├── Add cross-refs to 5 agents
├── Add cross-refs to 8 SWE skills
├── Add cross-refs to 2 utility skills
├── Add cross-refs to 1 validation skill
├── Add cross-refs to 2 workflow skills
├── Update 6 instruction files
├── Update product-contract counters
└── Update CHANGELOG.md

Phase 3: Lifecycle Category
├── Create skills/govern/ directory
├── Move create-skill from dev/ to govern/
├── Move create-agent from dev/ to govern/
├── Update create-skill procedure (add govern/ category)
├── Update all 6 instruction files (new subsection)
└── Update all internal cross-references

Phase 4: Verify + Close
├── Verify canonical/mirror parity
├── Verify counter accuracy
└── Create done.md
```

## File Structure

### New files

```
.ai-engineering/
├── context/specs/002-cross-ref-hardening/
│   ├── spec.md                          # NEW (this spec)
│   ├── plan.md                          # NEW (this plan)
│   ├── tasks.md                         # NEW (task tracker)
│   └── done.md                          # NEW (closure — Phase 4)
├── skills/
│   ├── govern/                          # NEW (category)
│   │   ├── create-skill.md              # MOVED from dev/
│   │   └── create-agent.md              # MOVED from dev/
│   └── docs/
│       ├── changelog.md                 # NEW
│       └── writer.md                    # NEW

src/ai_engineering/templates/.ai-engineering/
├── skills/
│   ├── govern/                          # NEW (mirror category)
│   │   ├── create-skill.md              # MOVED mirror
│   │   └── create-agent.md              # MOVED mirror
│   └── docs/
│       ├── changelog.md                 # NEW mirror
│       └── writer.md                    # NEW mirror
```

### Modified files (cross-references added)

```
Agents (5 files):
  code-simplifier.md    — +quality/core.md ref
  codebase-mapper.md    — +doc-writer.md ref
  principal-engineer.md — +security-review.md ref
  quality-auditor.md    — +stacks/python.md ref
  verify-app.md         — +migration.md ref

SWE skills (8 files):
  code-review.md        — +security-review, test-strategy, performance-analysis, code-simplifier refs
  debug.md              — +verify-app ref
  dependency-update.md  — +security-reviewer ref
  performance-analysis.md — +principal-engineer ref
  pr-creation.md        — +changelog-documentation, stacks/python refs
  prompt-engineer.md    — +create-skill, create-agent refs
  python-mastery.md     — +architect, code-simplifier, codebase-mapper, principal-engineer refs
  test-strategy.md      — +debugger, principal-engineer, verify-app refs

Utility skills (2 files):
  git-helpers.md        — +commit, pr, core.md refs
  platform-detection.md — +install-readiness, core.md refs

Validation skills (1 file):
  install-readiness.md  — +platform-detection, core.md, verify-app refs

Workflow skills (2 files):
  commit.md             — +verify-app ref
  pr.md                 — +pr-creation, verify-app refs

Instruction files (6 files):
  .github/copilot-instructions.md
  AGENTS.md
  CLAUDE.md
  src/ai_engineering/templates/project/copilot-instructions.md
  src/ai_engineering/templates/project/AGENTS.md
  src/ai_engineering/templates/project/CLAUDE.md

Counters (1 file):
  context/product/product-contract.md — 18→22 skills

Changelog (1 file):
  CHANGELOG.md — 4 new skill entries
```

All modified files above are updated in BOTH canonical and template mirror copies (where applicable).

## Session Map

| Session | Agent | Scope | Size |
|---------|-------|-------|------|
| S0 | Agent-1 | Phase 0 (scaffold) + Phase 1 (new skills) + Phase 2 (cross-refs) | L |
| S1 | Agent-1 | Phase 3 (lifecycle category) + Phase 4 (verify + close) | M |
