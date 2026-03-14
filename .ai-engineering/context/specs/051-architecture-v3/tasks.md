---
spec: "051"
total: 72
completed: 27
last_session: "2026-03-15"
next_session: "Phase 2 remainder (T-017/18/24/29) + Phase 3 — Renames"
---

# Tasks — Spec 051

## Phase 0: Scaffold [S]
- [ ] T-001: Create spec.md, plan.md, tasks.md
- [ ] T-002: Update _active.md to point to spec-051
- [ ] T-003: Commit scaffold

## Phase 1: Expand Stubs [M]
- [x] T-004: Expand `skills/security/SKILL.md` (58→216 lines): OWASP mapping, severity classification, remediation patterns, 4-mode procedures
- [x] T-005: Expand `skills/quality/SKILL.md` (45→175 lines): code review 7-dimension checklist, quality thresholds table, 4-mode procedures
- [x] T-006: Expand `skills/governance/SKILL.md` (48→153 lines): integrity/compliance/ownership/operational procedures, systemic pattern analysis
- [x] T-007: Expand `skills/build/SKILL.md` (45→257 lines): holistic analysis, post-edit validation pipeline, 2 examples, full 7-step procedure
- [x] T-008: Expand `skills/perf/SKILL.md` (46→150 lines): profiling guidance, 3 anti-pattern examples, hot spots scoring

**Phase 1 Gate**: All 5 skills >100 lines with procedures, examples, output contracts

## Phase 2: Create New Agents + Skills [L]

### 2.1 Guard Agent
- [x] T-009: Create `agents/guard.md` (159 lines) — advise, gate, drift modes with full procedures
- [x] T-010: Create `skills/guard/SKILL.md` (213 lines) — advise/gate/drift procedures
- [x] T-011: Update `agents/build.md` — guard.advise added as Step 2 in post-edit validation
- [x] T-012: Update `agents/execute.md` — dispatch + guard skills referenced
- [x] T-013: Update `agents/plan.md` — guard.forecast ref added, explain removed, lifecycle replaces create+delete

### 2.2 Guide Agent
- [x] T-014: Create `agents/guide.md` (146 lines) — teach, tour, why, onboard modes
- [x] T-015: Create `skills/guide/SKILL.md` (111 lines) — teaching/explanation with Bloom's depth
- [x] T-016: Create `skills/onboard/SKILL.md` (107 lines) — 7-phase progressive codebase discovery
- [ ] T-017: Reassign `skills/explain/SKILL.md` ownership: guide (primary), plan (secondary ref)
- [ ] T-018: Update `agents/plan.md` to reference guide for explain

### 2.3 Operate Agent
- [x] T-019: Create `agents/operate.md` (156 lines) — run, incident, status modes
- [x] T-020: Create `skills/ops/SKILL.md` (142 lines) — runbook execution + incident response
- [x] T-021: Add `owner: operate` frontmatter to all 13 runbooks

### 2.4 Evolve Skill (Self-Improvement)
- [x] T-022: Create `skills/evolve/SKILL.md` (193 lines) — 12 analysis rules, data sources, report template
- [x] T-023: Update `agents/observe.md` — evolve skill referenced
- [ ] T-024: Add verify.gap --framework mode to verify agent

### 2.5 Dispatch Skill
- [x] T-025: Create `skills/dispatch/SKILL.md` (178 lines) — formal Task Dispatch Schema + DAG
- [x] T-026: Update `agents/execute.md` — dispatch skill referenced

### 2.6 Lifecycle Skill (merge create+delete)
- [x] T-027: Create `skills/lifecycle/SKILL.md` (93 lines) — merged create + delete procedures
- [x] T-028: Update `agents/plan.md` — lifecycle replaces create+delete
- [ ] T-029: Delete `skills/create/SKILL.md` and `skills/delete/SKILL.md`

**Phase 2 Gate**: 3 new agents defined, 6 new skills created, all 14 runbooks owned, explain reassigned

## Phase 3: Renames [L]

### 3.1 Agent Renames
- [ ] T-030: Rename `agents/scan.md` → `agents/verify.md` (file + frontmatter + all cross-refs)
- [ ] T-031: Rename `agents/release.md` → `agents/ship.md` (file + frontmatter + all cross-refs)
- [ ] T-032: Update all agents that reference scan/release by name

### 3.2 Skill Renames (batch)
- [ ] T-033: Rename `skills/build/` → `skills/code/` + update frontmatter
- [ ] T-034: Rename `skills/db/` → `skills/schema/` + update frontmatter
- [ ] T-035: Rename `skills/cicd/` → `skills/pipeline/` + update frontmatter
- [ ] T-036: Rename `skills/a11y/` → `skills/accessibility/` + update frontmatter
- [ ] T-037: Rename `skills/feature-gap/` → `skills/gap/` + update frontmatter
- [ ] T-038: Rename `skills/code-simplifier/` → `skills/simplify/` + update frontmatter
- [ ] T-039: Rename `skills/perf/` → `skills/performance/` + update frontmatter
- [ ] T-040: Rename `skills/docs/` → `skills/document/` + update frontmatter
- [ ] T-041: Rename `skills/observe/` → `skills/dashboard/` + update frontmatter
- [ ] T-042: Rename `skills/product-contract/` → `skills/contract/` + update frontmatter
- [ ] T-043: Rename `skills/work-item/` → `skills/triage/` + refocus on triage

### 3.3 Cross-Reference Updates
- [ ] T-044: Update `src/ai_engineering/state/audit.py` telemetry actor names
- [ ] T-045: Update `src/ai_engineering/cli_commands/governance_cmd.py` skill_names list
- [ ] T-046: Update `scripts/sync_command_mirrors.py` AGENT_DESCRIPTIONS dict
- [ ] T-047: Update `tests/unit/test_validator.py` agent/skill path lists
- [ ] T-048: Update `tests/unit/test_skill_agent_telemetry.py` agent name assertions
- [ ] T-049: Update `tests/unit/test_governance_cmd.py` skill count validation
- [ ] T-050: Rename all `.claude/commands/ai/*.md` files per skill renames
- [ ] T-051: Rename all `.github/prompts/ai-*.prompt.md` files per skill renames
- [ ] T-052: Rename all `.github/agents/*.agent.md` files per agent renames

**Phase 3 Gate**: All renames complete, all tests pass, ai-eng validate clean

## Phase 4: Standards Reorganization [M]
- [ ] T-053: Move `standards/framework/core.md` → `standards/core.md`
- [ ] T-054: Create `standards/governance/agent-model.md` (extract from core.md)
- [ ] T-055: Move `standards/framework/quality/core.md` → `standards/governance/quality-model.md`
- [ ] T-056: Move `standards/framework/security/owasp-top10-2025.md` → `standards/governance/security-model.md`
- [ ] T-057: Move `standards/framework/stacks/` → `standards/stacks/`
- [ ] T-058: Move `standards/framework/cross-cutting/` → `standards/cross-cutting/`
- [ ] T-059: Update all standard references in agents, skills, manifest
- [ ] T-060: Update `state/ownership-map.json` for new paths

**Phase 4 Gate**: Standards reorganized, all references updated, validate clean

## Phase 5: Contracts + Documentation [L]
- [ ] T-061: Rewrite `framework-contract.md` for 10 agents, dispatch schema, guard integration, evolve
- [ ] T-062: Rewrite `product-contract.md` for v0.3.0 (10 agents, 40 skills, new roadmap)
- [ ] T-063: Create `.ai-engineering/README.md` (developer guide)
- [ ] T-064: Rewrite `GOVERNANCE_SOURCE.md` for new agent/skill catalog
- [ ] T-065: Regenerate all IDE adapters from GOVERNANCE_SOURCE
- [ ] T-066: Update root `README.md` with new architecture overview
- [ ] T-067: Update `CHANGELOG.md` with v0.3.0 entry
- [ ] T-068: Update `manifest.yml` (10 agents, 40 skills, new paths)

**Phase 5 Gate**: All contracts accurate, README complete, IDE adapters regenerated

## Phase 6: Template Mirror + Validation [M]
- [ ] T-069: Sync ALL to `src/ai_engineering/templates/.ai-engineering/`
- [ ] T-070: Run full test suite → 0 failures
- [ ] T-071: Run `ai-eng validate` → 0 findings
- [ ] T-072: Run `/ai:verify gap --framework` → document remaining gaps in done.md

**Phase 6 Gate**: Tests pass, validate clean, gaps documented, ready for PR
