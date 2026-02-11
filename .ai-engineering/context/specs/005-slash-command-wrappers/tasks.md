---
spec: "005"
total: 7
completed: 7
last_session: "2026-02-10"
next_session: "CLOSED"
---

# Tasks — Slash Command Wrappers

## Phase 1: Command Wrappers [S]

- [x] 1.1 Create `.claude/commands/` wrappers for all workflow skills
- [x] 1.2 Create `.claude/commands/swe/` wrappers for all SWE skills
- [x] 1.3 Create `.claude/commands/lifecycle/` wrappers for all lifecycle skills
- [x] 1.4 Create `.claude/commands/quality/` wrappers for all quality skills
- [x] 1.5 Create `.claude/commands/agent/` wrappers for all agents

## Phase 2: Template Mirrors [S]

- [x] 2.1 Create byte-identical mirrors in `src/ai_engineering/templates/project/.claude/commands/`

## Phase 3: Governance Registration [S]

- [x] 3.1 Update manifest.yml — add `.claude/commands/**` to external_framework_managed
- [x] 3.2 Update lifecycle skills — add Phase 4b/3b for slash command steps
- [x] 3.3 Update content-integrity skill — add `.claude/commands/**` mirror pair
- [x] 3.4 Update CLAUDE.md, AGENTS.md, copilot-instructions.md (and template mirrors)
- [x] 3.5 Record decision S0-008 in decision-store.json
