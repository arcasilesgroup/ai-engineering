---
spec: "050"
pipeline: full
phases: 6
agents: [build, scan, write, observe]
estimated_tasks: 89
---

# Execution Plan — Spec 050

## Pipeline Classification

**Full** — governance-change, >100 files affected, major framework restructure.

## Phase Overview

```
Phase 1 ─ Foundation & Bugs          ████░░░░░░ P0 (blocking)
Phase 2 ─ Skills Remediation         ████░░░░░░ P0 (user-facing)
Phase 3 ─ Agent Architecture         ███░░░░░░░ P1
Phase 4 ─ Standards Expansion        ████░░░░░░ P1
Phase 5 ─ Multi-IDE & CI Hardening   ███░░░░░░░ P2
Phase 6 ─ Validation & Cleanup       ██░░░░░░░░ P2
```

Each phase is independently shippable. Phase gates require passing `ai-eng doctor` + tests.

---

## Phase 1 — Foundation & Bugs (P0)

**Goal**: Fix the governance backbone so all subsequent phases have a solid foundation.

**Agent**: build (primary), scan (validation)

### 1.1 Bootstrap Decision-Store

Retroactively populate `state/decision-store.json` with ≥15 decisions reconstructed from git log and spec history.

- Scan git log for architectural decisions in specs 001-049
- Create entries with `source: "RECONSTRUCTED"` flag
- Add governance decision: "phase branching descoped — flat main for current scale"
- Add governance decision: "multi-IDE via generated docs, not manual sync"
- Validate schema compliance

### 1.2 Fix metrics_collect Bug

Fix unreachable code path in `observe` agent's `metrics_collect` function.

- Read `agents/observe.md` and trace the metrics_collect logic
- Fix the dead code path
- Add test covering the fixed path

### 1.3 Unify Checkpoint Schema

Resolve the execute/release `session-checkpoint.json` write conflict.

- Define unified checkpoint schema with namespaced sections
- Update `agents/execute.md` to write under `checkpoint.execute`
- Update `agents/release.md` to write under `checkpoint.release`
- Add schema validation in `ai-eng checkpoint load`

### 1.4 Clean Ghost References

Remove manifest.yml references to non-existent skills/agents.

- Diff manifest.yml skill list against actual `skills/*/SKILL.md` files
- Remove or create missing entries
- Run `ai-eng doctor` to validate

### 1.5 Fix Stale Spec Catalog

Update `_catalog.md` to include specs 039-049 and fix `?` metadata entries.

- Scan all spec directories for frontmatter
- Regenerate catalog with correct IDs, statuses, dates
- Mark genuinely stale "in-progress" specs as `stalled`

**Phase 1 Gate**: `ai-eng doctor` passes, decision-store has ≥15 entries, zero ghost references.

---

## Phase 2 — Skills Remediation (P0)

**Goal**: Every skill listed in manifest is complete and usable.

**Agent**: write (primary), build (implementation)

### 2.1 Complete Truncated Skills (3)

Expand `debug`, `architecture`, `api` from stubs to full skills with:
- Purpose, Trigger, Procedure (≥3 steps), Examples, Boundaries
- Minimum 80 lines each

### 2.2 Complete Severely Incomplete Skills (4)

Flesh out `work-item`, `feature-gap`, `product-contract`, `migrate`:
- Add actionable procedures (not just descriptions)
- Add concrete examples
- Define clear boundaries

### 2.3 Decompose PR Skill

Split `pr/SKILL.md` (400+ lines, 5 responsibilities) into focused skills:
- `pr/SKILL.md` — PR creation and description only
- `commit/SKILL.md` — already exists, ensure it's complete
- `review/SKILL.md` — code review procedures (new or extracted)
- Remove branch creation logic (belongs in `spec` skill)
- Remove push logic (belongs in `commit` skill)

### 2.4 Remove Dead-Weight Runbooks (4)

Delete or complete placeholder runbooks:
- `codex-runbook.md` — evaluate: complete or delete
- `gemini-runbook.md` — evaluate: complete or delete
- `installer-runbook.md` — evaluate: complete or delete
- `github-templates-runbook.md` — evaluate: complete or delete

Decision: if runbook has <20% real content, delete. Otherwise complete.

**Phase 2 Gate**: All skills pass `ai-eng doctor` validation, zero truncated skills, PR skill ≤150 lines.

---

## Phase 3 — Agent Architecture (P1)

**Goal**: Agents have clear boundaries, no conflicts, correct references.

**Agent**: write (primary), build (validation)

### 3.1 Agent Boundary Audit

Review all 7 agents for:
- Overlapping responsibilities
- Missing capability declarations
- Stale skill references

### 3.2 Clarify Execute vs Build Boundary

Document and enforce the execute→build delegation:
- Execute dispatches; Build implements
- Remove any direct implementation code from execute agent

### 3.3 Update Agent Skill References

Ensure every agent's `references.skills` list matches actual skills on disk:
- Remove references to deleted/renamed skills
- Add references for new skills from Phase 2

### 3.4 Observe Agent Hardening

Beyond the bug fix in 1.2:
- Validate all telemetry emission paths work
- Ensure `ai-eng signals emit` commands are correct
- Test cross-IDE telemetry compatibility

**Phase 3 Gate**: All agent files pass schema validation, zero stale references, execute/build boundary documented.

---

## Phase 4 — Standards Expansion (P1)

**Goal**: Complete stack coverage and add cross-cutting standards.

**Agent**: write (primary)

### 4.1 Create 10 Missing Stack Standards

Create lean (≤1 page) standards for:

| Stack | Priority | Notes |
|-------|----------|-------|
| Rust | High | Growing adoption |
| Java/Kotlin | High | Enterprise staple |
| Terraform | High | IaC critical |
| Swift | Medium | Mobile |
| Ruby | Medium | Legacy but present |
| PHP | Medium | Web legacy |
| C/C++ | Medium | Systems |
| Helm | Low | K8s specific |
| Ansible | Low | Config mgmt |
| Pulumi | Low | IaC alternative |

Template for each:
```markdown
---
stack: <name>
version: 1.0.0
---
# <Stack> Standard
## Toolchain
## Quality Gates
## Security
## CI Integration
```

### 4.2 Create Cross-Cutting Standards (8 minimum)

| Standard | Priority | Scope |
|----------|----------|-------|
| error-handling | P0 | Exception patterns, error boundaries |
| logging | P0 | Structured logging, levels, PII |
| configuration | P0 | Env vars, secrets, config files |
| observability | P1 | Metrics, traces, health checks |
| testing | P1 | Test patterns, coverage rules |
| api-design | P1 | REST/GraphQL conventions |
| dependency-management | P2 | Version pinning, audit |
| documentation | P2 | Code docs, ADRs |

### 4.3 Standards Index

Create `standards/INDEX.md` — single-page map of all standards with status and ownership.

**Phase 4 Gate**: All 10 stack files exist and pass linting, ≥8 cross-cutting standards created, INDEX.md generated.

---

## Phase 5 — Multi-IDE & CI Hardening (P2)

**Goal**: Governance docs generated from single source; multi-IDE validation tooling.

**Agent**: build (primary), scan (validation)

### 5.1 Consolidate Governance Docs

Implement single-source → generated pattern:
- Define `GOVERNANCE_SOURCE.md` as the canonical governance document
- Generate `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `COPILOT.md`, `.cursorrules` from source
- Add `ai-eng governance sync` command to regenerate
- Add CI check that generated files match source

### 5.2 Mirror Sync Validation

Add tooling to detect governance doc divergence:
- `ai-eng governance diff` — show differences between IDE instruction files
- Add to CI pipeline as warning (not blocking initially)
- Track drift metrics

### 5.3 Multi-IDE Test Matrix

Create manual + automated test matrix:
- Claude Code: full automated validation
- GitHub Copilot: semi-automated (workspace commands)
- Gemini CLI: semi-automated (context loading)
- Codex: manual checklist

### 5.4 CI Pipeline Hardening

- Add governance sync check to CI
- Add manifest validation to CI
- Ensure `ai-eng doctor` runs in CI

**Phase 5 Gate**: Governance docs generated from single source, mirror sync validation passing, CI pipeline includes governance checks.

---

## Phase 6 — Validation & Cleanup (P2)

**Goal**: Verify all fixes, clean dead artifacts, update contracts.

**Agent**: scan (primary), observe (telemetry)

### 6.1 Re-Run Full Audit

Execute the same 8-dimension audit from 2026-03-12 to measure improvement:
- Target: ≥8.5/10 global score
- Document remaining gaps as tracked tech debt

### 6.2 Update Contracts

- Update `product-contract.md` to reflect v2 capabilities
- Update `framework-contract.md` to remove unimplemented claims
- Remove phase branching references (descoped)
- Update manifest.yml counts

### 6.3 Test Coverage Push

- Add integration tests for governance validation
- Add tests for skill loading and schema validation
- Target: 60%+ meaningful test coverage (not line count)

### 6.4 Spec Lifecycle Cleanup

- Close stale specs (mark `stalled` or `closed`)
- Update `_catalog.md` as final step
- Archive completed work

**Phase 6 Gate**: Audit score ≥8.5/10, contracts accurate, test coverage ≥60%, zero stale specs.

---

## Agent Assignment Matrix

| Phase | Primary Agent | Support Agents | Skills Used |
|-------|--------------|----------------|-------------|
| 1 | build | scan | debug, governance, cleanup |
| 2 | write | build | create, delete, refactor |
| 3 | write | build | architecture, explain |
| 4 | write | — | standards, create |
| 5 | build | scan | cicd, governance, test |
| 6 | scan | observe | cleanup, test, quality |

## Execution Order

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──┐
                                    ├──→ Phase 5 ──→ Phase 6
                        Phase 4 ──┘
```

Phases 3 and 4 can execute in parallel after Phase 2.
Phase 5 depends on both 3 and 4.
Phase 6 is always last.

## STOP

Plan complete. Review the execution plan above. To begin implementation:

```
/ai:execute
```
