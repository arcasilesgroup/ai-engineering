---
spec: "031"
total: 56
completed: 0
last_session: "2026-03-02"
next_session: "Phase 1 — Author 6 New Agents"
---

# Tasks — Architecture Refactor: Agents, Skills & Standards

## Phase 0: Scaffold [S]
- [x] 0.1 Create spec branch `spec/031-framework-optimization`
- [x] 0.2 Scaffold spec.md, plan.md, tasks.md
- [x] 0.3 Update `_active.md` to point to 031
- [x] 0.4 Atomic commit: scaffold

## Phase 1: Author 6 New Agents [L]
- [ ] 1.1 Write `agents/plan.md` — orchestrator + planning pipeline + dispatch
- [ ] 1.2 Write `agents/build.md` — implementation (merges 8 agents), skill-routing protocol
- [ ] 1.3 Write `agents/review.md` — reviews + governance (merges 6), individual modes
- [ ] 1.4 Write `agents/scan.md` — feature scanner (spec-vs-code gap analysis)
- [ ] 1.5 Write `agents/write.md` — documentation + test docs
- [ ] 1.6 Write `agents/triage.md` — auto-prioritization

## Phase 2: Restructure 44 Skills [L]
- [ ] 2.1 Move `workflows/commit` → `commit`
- [ ] 2.2 Move `workflows/pr` → `pr`
- [ ] 2.3 Move `workflows/cleanup` → `cleanup`
- [ ] 2.4 Move `workflows/self-improve` → `improve`
- [ ] 2.5 Move `dev/debug` → `debug`
- [ ] 2.6 Move `dev/refactor` → `refactor`
- [ ] 2.7 Move `dev/code-review` → `code-review`
- [ ] 2.8 Move `dev/data-modeling` → `data-model`
- [ ] 2.9 Move `dev/test-runner` → `test-run`
- [ ] 2.10 Move `dev/test-strategy` → `test-plan`
- [ ] 2.11 Move `dev/migration` → `migrate`
- [ ] 2.12 Move `dev/deps-update` → `deps`
- [ ] 2.13 Move `dev/cicd-generate` → `cicd`
- [ ] 2.14 Move `dev/cli-ux` → `cli`
- [ ] 2.15 Move `dev/multi-agent` → `multi-agent`
- [ ] 2.16 Move `dev/api-design` → `api`
- [ ] 2.17 Move `dev/infrastructure` → `infra`
- [ ] 2.18 Move `dev/database-ops` → `db`
- [ ] 2.19 Move `dev/sonar-gate` → `sonar`
- [ ] 2.20 Move `dev/discovery-interrogation` → `discover`
- [ ] 2.21 Move `review/architecture` → `arch-review`
- [ ] 2.22 Move `review/performance` → `perf-review`
- [ ] 2.23 Move `review/security` → `sec-review`
- [ ] 2.24 Move `review/specialized-security` → `sec-deep`
- [ ] 2.25 Move `review/accessibility` → `a11y`
- [ ] 2.26 Move `docs/changelog` → `changelog`
- [ ] 2.27 Move `docs/explain` → `explain`
- [ ] 2.28 Move `docs/writer` → `docs`
- [ ] 2.29 Move `docs/simplify` → `simplify`
- [ ] 2.30 Move `docs/prompt-design` → `prompt`
- [ ] 2.31 Move `govern/integrity-check` → `integrity`
- [ ] 2.32 Move `govern/contract-compliance` → `compliance`
- [ ] 2.33 Move `govern/ownership-audit` → `ownership`
- [ ] 2.34 Move `govern/adaptive-standards` → `standards`
- [ ] 2.35 Move `govern/create-spec` → `spec`
- [ ] 2.36 Move `govern/agent-lifecycle` → `agent-lifecycle`
- [ ] 2.37 Move `govern/skill-lifecycle` → `skill-lifecycle`
- [ ] 2.38 Move `govern/risk-lifecycle` → `risk`
- [ ] 2.39 Move `quality/audit-code` → `audit`
- [ ] 2.40 Move `quality/docs-audit` → `docs-audit`
- [ ] 2.41 Move `quality/install-check` → `install`
- [ ] 2.42 Move `quality/release-gate` → `release`
- [ ] 2.43 Move `quality/test-gap-analysis` → `test-gap`
- [ ] 2.44 Move `quality/sbom` → `sbom`

## Phase 3: Author 3 New Skills [M]
- [ ] 3.1 Write `skills/work-item/SKILL.md`
- [ ] 3.2 Write `skills/agent-card/SKILL.md`
- [ ] 3.3 Write `skills/triage/SKILL.md`

## Phase 4: Update Standards + Manifest [M]
- [ ] 4.1 Update `skills-schema.md` — remove `category` required, add `platforms`, update inventory
- [ ] 4.2 Update `manifest.yml` — agents 6, skills 47, flat org, `work_items` section

## Phase 5: External Integration [L]
- [ ] 5.1 Create 6 new `.github/agents/*.agent.md`
- [ ] 5.2 Delete 19 old `.github/agents/*.agent.md`
- [ ] 5.3 Rename/recreate 47 `.github/prompts/ai-*.prompt.md`
- [ ] 5.4 Delete old `.github/prompts/` files
- [ ] 5.5 Create `.claude/commands/ai/` with 47 skill + 6 agent commands
- [ ] 5.6 Delete old `.claude/commands/{agent,dev,docs,govern,quality,review,workflows}/`

## Phase 6: Instruction Files [M]
- [ ] 6.1 Update `CLAUDE.md` — 6 agents, 47 skills, `/ai:*` commands
- [ ] 6.2 Update `AGENTS.md` — 6 agents, new command contract
- [ ] 6.3 Update `.github/copilot-instructions.md`
- [ ] 6.4 Update `.github/copilot/` files
- [ ] 6.5 Update cross-references in skill bodies (old agent/skill names → new)

## Phase 7: Template Mirrors [L]
- [ ] 7.1 Mirror 6 new agents to `src/ai_engineering/templates/.ai-engineering/agents/`
- [ ] 7.2 Mirror 47 flat skills to `src/ai_engineering/templates/.ai-engineering/skills/`
- [ ] 7.3 Mirror updated manifest.yml and standards
- [ ] 7.4 Delete old template agent/skill mirrors

## Phase 8: Delete Old Files [L]
- [ ] 8.1 Delete 19 old `.ai-engineering/agents/<old-name>.md`
- [ ] 8.2 Delete 6 empty category directories under `.ai-engineering/skills/`
- [ ] 8.3 Verify no orphaned files remain

## Phase 9: Verification [M]
- [ ] 9.1 Count verification: 6 agents, 47 skills in all locations
- [ ] 9.2 `ruff check` + `ruff format --check` pass
- [ ] 9.3 Zero orphaned references (grep for old agent/skill names)
- [ ] 9.4 Template mirrors byte-identical to source
- [ ] 9.5 CHANGELOG entry
- [ ] 9.6 Create `done.md`
