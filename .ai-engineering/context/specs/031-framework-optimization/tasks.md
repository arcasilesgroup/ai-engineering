---
spec: "031"
total: 56
completed: 56
last_session: "2026-03-02"
next_session: "complete"
---

# Tasks — Architecture Refactor: Agents, Skills & Standards

## Phase 0: Scaffold [S]
- [x] 0.1 Create spec branch `spec/031-framework-optimization`
- [x] 0.2 Scaffold spec.md, plan.md, tasks.md
- [x] 0.3 Update `_active.md` to point to 031
- [x] 0.4 Atomic commit: scaffold

## Phase 1: Author 6 New Agents [L]
- [x] 1.1 Write `agents/plan.md` — orchestrator + planning pipeline + dispatch
- [x] 1.2 Write `agents/build.md` — implementation (merges 8 agents), skill-routing protocol
- [x] 1.3 Write `agents/review.md` — reviews + governance (merges 6), individual modes
- [x] 1.4 Write `agents/scan.md` — feature scanner (spec-vs-code gap analysis)
- [x] 1.5 Write `agents/write.md` — documentation + test docs
- [x] 1.6 Write `agents/triage.md` — auto-prioritization

## Phase 2: Restructure 44 Skills [L]
- [x] 2.1 Move `workflows/commit` → `commit`
- [x] 2.2 Move `workflows/pr` → `pr`
- [x] 2.3 Move `workflows/cleanup` → `cleanup`
- [x] 2.4 Move `workflows/self-improve` → `improve`
- [x] 2.5 Move `dev/debug` → `debug`
- [x] 2.6 Move `dev/refactor` → `refactor`
- [x] 2.7 Move `dev/code-review` → `code-review`
- [x] 2.8 Move `dev/data-modeling` → `data-model`
- [x] 2.9 Move `dev/test-runner` → `test-run`
- [x] 2.10 Move `dev/test-strategy` → `test-plan`
- [x] 2.11 Move `dev/migration` → `migrate`
- [x] 2.12 Move `dev/deps-update` → `deps`
- [x] 2.13 Move `dev/cicd-generate` → `cicd`
- [x] 2.14 Move `dev/cli-ux` → `cli`
- [x] 2.15 Move `dev/multi-agent` → `multi-agent`
- [x] 2.16 Move `dev/api-design` → `api`
- [x] 2.17 Move `dev/infrastructure` → `infra`
- [x] 2.18 Move `dev/database-ops` → `db`
- [x] 2.19 Move `dev/sonar-gate` → `sonar`
- [x] 2.20 Move `dev/discovery-interrogation` → `discover`
- [x] 2.21 Move `review/architecture` → `arch-review`
- [x] 2.22 Move `review/performance` → `perf-review`
- [x] 2.23 Move `review/security` → `sec-review`
- [x] 2.24 Move `review/specialized-security` → `sec-deep`
- [x] 2.25 Move `review/accessibility` → `a11y`
- [x] 2.26 Move `docs/changelog` → `changelog`
- [x] 2.27 Move `docs/explain` → `explain`
- [x] 2.28 Move `docs/writer` → `docs`
- [x] 2.29 Move `docs/simplify` → `simplify`
- [x] 2.30 Move `docs/prompt-design` → `prompt`
- [x] 2.31 Move `govern/integrity-check` → `integrity`
- [x] 2.32 Move `govern/contract-compliance` → `compliance`
- [x] 2.33 Move `govern/ownership-audit` → `ownership`
- [x] 2.34 Move `govern/adaptive-standards` → `standards`
- [x] 2.35 Move `govern/create-spec` → `spec`
- [x] 2.36 Move `govern/agent-lifecycle` → `agent-lifecycle`
- [x] 2.37 Move `govern/skill-lifecycle` → `skill-lifecycle`
- [x] 2.38 Move `govern/risk-lifecycle` → `risk`
- [x] 2.39 Move `quality/audit-code` → `audit`
- [x] 2.40 Move `quality/docs-audit` → `docs-audit`
- [x] 2.41 Move `quality/install-check` → `install`
- [x] 2.42 Move `quality/release-gate` → `release`
- [x] 2.43 Move `quality/test-gap-analysis` → `test-gap`
- [x] 2.44 Move `quality/sbom` → `sbom`

## Phase 3: Author 3 New Skills [M]
- [x] 3.1 Write `skills/work-item/SKILL.md`
- [x] 3.2 Write `skills/agent-card/SKILL.md`
- [x] 3.3 Write `skills/triage/SKILL.md`

## Phase 4: Update Standards + Manifest [M]
- [x] 4.1 Update `skills-schema.md` — remove `category` required, add `platforms`, update inventory
- [x] 4.2 Update `manifest.yml` — agents 6, skills 47, flat org, `work_items` section

## Phase 5: External Integration [L]
- [x] 5.1 Create 6 new `.github/agents/*.agent.md`
- [x] 5.2 Delete 19 old `.github/agents/*.agent.md`
- [x] 5.3 Rename/recreate 47 `.github/prompts/ai-*.prompt.md`
- [x] 5.4 Delete old `.github/prompts/` files
- [x] 5.5 Create `.claude/commands/ai/` with 47 skill + 6 agent commands
- [x] 5.6 Delete old `.claude/commands/{agent,dev,docs,govern,quality,review,workflows}/`

## Phase 6: Instruction Files [M]
- [x] 6.1 Update `CLAUDE.md` — 6 agents, 47 skills, `/ai:*` commands
- [x] 6.2 Update `AGENTS.md` — 6 agents, new command contract
- [x] 6.3 Update `.github/copilot-instructions.md`
- [x] 6.4 Update `.github/copilot/` files
- [x] 6.5 Update cross-references in skill bodies (old agent/skill names → new)

## Phase 7: Template Mirrors [L]
- [x] 7.1 Mirror 6 new agents to `src/ai_engineering/templates/.ai-engineering/agents/`
- [x] 7.2 Mirror 47 flat skills to `src/ai_engineering/templates/.ai-engineering/skills/`
- [x] 7.3 Mirror updated manifest.yml and standards
- [x] 7.4 Delete old template agent/skill mirrors

## Phase 8: Delete Old Files [L]
- [x] 8.1 Delete 19 old `.ai-engineering/agents/<old-name>.md`
- [x] 8.2 Delete 6 empty category directories under `.ai-engineering/skills/`
- [x] 8.3 Verify no orphaned files remain

## Phase 9: Verification [M]
- [x] 9.1 Count verification: 6 agents, 47 skills in all locations
- [x] 9.2 `ruff check` + `ruff format --check` pass
- [x] 9.3 Zero orphaned references (grep for old agent/skill names)
- [x] 9.4 Unit tests: 761 passed, integration tests: 402 passed
- [x] 9.5 CHANGELOG entry
- [x] 9.6 Create `done.md`
