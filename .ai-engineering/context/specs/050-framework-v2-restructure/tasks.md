---
spec: "050"
total: 89
completed: 52
---

# Tasks — Spec 050

## Phase 1 — Foundation & Bugs (P0)

### 1.1 Bootstrap Decision-Store
- [x] T-001: Scan git log for architectural decisions across specs 001-049
- [x] T-002: Create decision-store entry template with `source: RECONSTRUCTED` field
- [x] T-003: Populate ≥10 retroactive decisions from spec history
- [x] T-004: Add decision: "phase branching descoped — flat main for current scale"
- [x] T-005: Add decision: "multi-IDE via generated docs, not manual sync"
- [x] T-006: Add decision: "single checkpoint schema with namespaced sections"
- [x] T-007: Add decision: "lean standards ≤1 page per stack"
- [x] T-008: Add decision: "PR skill decomposition into focused skills"
- [x] T-009: Validate decision-store schema compliance
- [x] T-010: Verify ≥15 total entries in decision-store (18 entries)

### 1.2 Fix metrics_collect Bug
- [x] T-011: Read observe agent and identify unreachable code path in metrics_collect
- [x] T-012: Fix the dead code path (added Typer annotation for --days)
- [x] T-013: Add test covering the fixed metrics_collect path (test_custom_days_window passes)

### 1.3 Unify Checkpoint Schema
- [x] T-014: Define unified checkpoint schema with `checkpoint.execute` and `checkpoint.release` namespaces
- [x] T-015: Update execute agent to write under namespaced key (--agent flag)
- [x] T-016: Update release agent to write under namespaced key (backward compat)
- [x] T-017: Add schema validation to `ai-eng checkpoint load` (--agent flag)
- [x] T-018: Test checkpoint load/save with both agent types (12 tests pass)

### 1.4 Clean Ghost References
- [x] T-019: Diff manifest.yml skill list against `skills/*/SKILL.md` on disk
- [x] T-020: Remove manifest entries for non-existent skills (CLEAN — none found)
- [x] T-021: Diff manifest.yml agent list against `agents/*.md` on disk
- [x] T-022: Remove manifest entries for non-existent agents (CLEAN — none found)
- [x] T-023: Run `ai-eng doctor` to validate zero ghost references

### 1.5 Fix Stale Spec Catalog
- [x] T-024: Scan all spec directories (001-050) for frontmatter
- [x] T-025: Add specs 039-049 to catalog with correct metadata (fixed _find_all_spec_files)
- [x] T-026: Fix `?` entries with data from spec frontmatter (data issue in 041, 042)
- [x] T-027: Mark stale "in-progress" specs older than 14 days as `stalled`
- [x] T-028: Regenerate catalog via `ai-eng spec catalog` (37→50 specs)

**Phase 1 Gate**:
- [x] T-029: 1372 tests pass, ruff clean
- [x] T-030: Decision-store has 18 entries (≥15 target)
- [x] T-031: Zero ghost references in manifest (confirmed clean)

## Phase 2 — Skills Remediation (P0)

### 2.1 Complete Truncated Skills
- [x] T-032: `debug/SKILL.md` — already 95 lines, complete (audit was wrong)
- [x] T-033: Expand `architecture/SKILL.md` — expanded from 38→110 lines
- [x] T-034: `api/SKILL.md` — already 101 lines, complete (audit was wrong)

### 2.2 Complete Severely Incomplete Skills
- [x] T-035: `work-item/SKILL.md` — already 153 lines, complete (audit was wrong)
- [x] T-036: Complete `feature-gap/SKILL.md` — added examples, boundaries, governance notes
- [x] T-037: `product-contract/SKILL.md` — already 139 lines, complete (audit was wrong)
- [x] T-038: `migrate/SKILL.md` — already 96 lines, complete (audit was wrong)

### 2.3 Decompose PR Skill
- [x] T-039: Audit `pr/SKILL.md` — identified duplicated pipeline with commit skill
- [x] T-040: Refactor PR to reference commit pipeline (234→140 lines)
- [x] T-041: Branch creation already in commit/spec (no move needed)
- [x] T-042: Push logic already in commit (no move needed)
- [x] T-043: Review procedures stay in PR (code review is part of PR flow)
- [x] T-044: Agent references unchanged (skills not renamed)
- [x] T-045: Validated cross-references (commit/pr/changelog/docs chain intact)

### 2.4 Remove Dead-Weight Runbooks
- [x] T-046: `codex-runbook.md` — does not exist on disk (already removed)
- [x] T-047: `gemini-runbook.md` — does not exist on disk (already removed)
- [x] T-048: `installer-runbook.md` — does not exist on disk (already removed)
- [x] T-049: `github-templates-runbook.md` — does not exist on disk (already removed)

**Phase 2 Gate**:
- [x] T-050: All skills have valid structure
- [x] T-051: Zero truncated skills (<30 lines) — architecture expanded
- [x] T-052: PR skill 140 lines (≤150 target)

## Phase 3 — Agent Architecture (P1)

### 3.1 Agent Boundary Audit
- [ ] T-053: Review all 7 agents for overlapping responsibilities
- [ ] T-054: Document agent responsibility matrix (agent × capability)
- [ ] T-055: Identify and resolve any overlapping capabilities

### 3.2 Clarify Execute vs Build Boundary
- [ ] T-056: Audit execute agent for direct implementation code
- [ ] T-057: Move any implementation logic from execute to build
- [ ] T-058: Document the execute→build delegation contract

### 3.3 Update Agent Skill References
- [ ] T-059: Diff each agent's `references.skills` against actual skills on disk
- [ ] T-060: Remove stale skill references from all agents
- [ ] T-061: Add new skill references from Phase 2 decomposition

### 3.4 Observe Agent Hardening
- [ ] T-062: Validate all telemetry emission paths in observe agent
- [ ] T-063: Verify `ai-eng signals emit` commands are syntactically correct
- [ ] T-064: Test cross-IDE telemetry compatibility (Claude Code, Copilot)

**Phase 3 Gate**:
- [ ] T-065: All agents pass schema validation
- [ ] T-066: Zero stale skill references across all agents
- [ ] T-067: Execute/build boundary documented and enforced

## Phase 4 — Standards Expansion (P1)

### 4.1 Create Missing Stack Standards
- [ ] T-068: Create `standards/stacks/rust.md` (Rust standard)
- [ ] T-069: Create `standards/stacks/java-kotlin.md` (Java/Kotlin standard)
- [ ] T-070: Create `standards/stacks/terraform.md` (Terraform standard)
- [ ] T-071: Create `standards/stacks/swift.md` (Swift standard)
- [ ] T-072: Create `standards/stacks/ruby.md` (Ruby standard)
- [ ] T-073: Create `standards/stacks/php.md` (PHP standard)
- [ ] T-074: Create `standards/stacks/c-cpp.md` (C/C++ standard)
- [ ] T-075: Create `standards/stacks/helm.md` (Helm standard)
- [ ] T-076: Create `standards/stacks/ansible.md` (Ansible standard)
- [ ] T-077: Create `standards/stacks/pulumi.md` (Pulumi standard)

### 4.2 Create Cross-Cutting Standards
- [ ] T-078: Create `standards/cross-cutting/error-handling.md`
- [ ] T-079: Create `standards/cross-cutting/logging.md`
- [ ] T-080: Create `standards/cross-cutting/configuration.md`
- [ ] T-081: Create `standards/cross-cutting/observability.md`
- [ ] T-082: Create `standards/cross-cutting/testing.md`
- [ ] T-083: Create `standards/cross-cutting/api-design.md`
- [ ] T-084: Create `standards/cross-cutting/dependency-management.md`
- [ ] T-085: Create `standards/cross-cutting/documentation.md`

### 4.3 Standards Index
- [ ] T-086: Create `standards/INDEX.md` with all standards, status, and ownership

**Phase 4 Gate**:
- [ ] T-087: All 10 stack standard files exist and pass linting
- [ ] T-088: ≥8 cross-cutting standards created
- [ ] T-089: INDEX.md generated and accurate

## Phase 5 — Multi-IDE & CI Hardening (P2)

### 5.1 Consolidate Governance Docs
- [ ] T-090: Create `GOVERNANCE_SOURCE.md` as single canonical governance document
- [ ] T-091: Define generation templates for CLAUDE.md, AGENTS.md, GEMINI.md, COPILOT.md, .cursorrules
- [ ] T-092: Implement `ai-eng governance sync` command
- [ ] T-093: Generate all IDE instruction files from source
- [ ] T-094: Verify generated files are functionally equivalent to current files
- [ ] T-095: Add CI check: generated files match source

### 5.2 Mirror Sync Validation
- [ ] T-096: Implement `ai-eng governance diff` command
- [ ] T-097: Add governance diff to CI as warning
- [ ] T-098: Track drift metrics in health-history.json

### 5.3 Multi-IDE Test Matrix
- [ ] T-099: Create Claude Code automated validation script
- [ ] T-100: Create Copilot semi-automated test checklist
- [ ] T-101: Create Gemini CLI semi-automated test checklist
- [ ] T-102: Create Codex manual test checklist
- [ ] T-103: Run initial validation across all 4 IDEs

### 5.4 CI Pipeline Hardening
- [ ] T-104: Add governance sync check to ci.yml
- [ ] T-105: Add manifest validation to ci.yml
- [ ] T-106: Ensure `ai-eng doctor` runs in CI
- [ ] T-107: Add skill schema validation to CI

**Phase 5 Gate**:
- [ ] T-108: Governance docs generated from single source
- [ ] T-109: Mirror sync validation passing in CI
- [ ] T-110: Multi-IDE test matrix documented and initial run complete

## Phase 6 — Validation & Cleanup (P2)

### 6.1 Re-Run Full Audit
- [ ] T-111: Execute 8-dimension audit (same methodology as 2026-03-12)
- [ ] T-112: Score must be ≥8.5/10
- [ ] T-113: Document remaining gaps as tracked tech debt in decision-store

### 6.2 Update Contracts
- [ ] T-114: Update `product-contract.md` to reflect v2 capabilities
- [ ] T-115: Update `framework-contract.md` — remove unimplemented claims
- [ ] T-116: Remove phase branching references from framework-contract
- [ ] T-117: Update manifest.yml skill/agent/standard counts

### 6.3 Test Coverage Push
- [ ] T-118: Add integration tests for governance validation paths
- [ ] T-119: Add tests for skill loading and schema validation
- [ ] T-120: Add tests for decision-store CRUD operations
- [ ] T-121: Verify ≥60% meaningful test coverage

### 6.4 Spec Lifecycle Cleanup
- [ ] T-122: Mark stale specs as `stalled` or `closed`
- [ ] T-123: Update `_catalog.md` with final state of all specs
- [ ] T-124: Archive completed work from specs 001-049
- [ ] T-125: Mark spec 050 as `completed`

**Phase 6 Gate**:
- [ ] T-126: Audit score ≥8.5/10
- [ ] T-127: Contracts accurate (zero unimplemented claims)
- [ ] T-128: Test coverage ≥60%
- [ ] T-129: Zero stale specs in catalog
