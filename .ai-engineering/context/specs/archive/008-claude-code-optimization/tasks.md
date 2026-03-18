---
spec: "008"
total: 18
completed: 18
last_session: "2026-02-11"
next_session: "Done — PR pending"
---

# Tasks — Claude Code Optimization

## Phase 0: Spec Lifecycle [S]

- [x] 0.1 Close spec 005 — create done.md, tasks.md → CLOSED
- [x] 0.2 Create spec 008 scaffold (spec.md, plan.md, tasks.md)
- [x] 0.3 Activate spec 008 in _active.md
- [x] 0.4 Update product-contract.md → 008

## Phase 1: Settings + Protocol [S]

- [x] 1.1 Create `.claude/settings.json` (root)
- [x] 1.2 Create `src/.../project/.claude/settings.json` (template mirror)
- [x] 1.3 Insert Session Start Protocol in CLAUDE.md
- [x] 1.4 Insert Session Start Protocol in AGENTS.md
- [x] 1.5 Sync template mirror CLAUDE.md
- [x] 1.6 Sync template mirror AGENTS.md

## Phase 2: Installer [S]

- [x] 2.1 Adapt `_PROJECT_TEMPLATE_TREES` — `.claude/` full directory

## Phase 3: Command Enrichment [S]

- [x] 3.1 Add preconditions to `.claude/commands/commit.md`
- [x] 3.2 Add preconditions to `.claude/commands/pr.md`
- [x] 3.3 Add preconditions to `.claude/commands/acho.md`
- [x] 3.4 Sync template mirrors for commit.md, pr.md, acho.md

## Phase 4: Governance [S]

- [x] 4.1 Add `.claude/settings.json` to manifest external_framework_managed
- [x] 4.2 Register decision S0-009 in decision-store.json
- [x] 4.3 Append audit event to audit-log.ndjson
