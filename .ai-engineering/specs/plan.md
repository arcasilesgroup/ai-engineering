---
spec: spec-145
title: Standard Flow Executor Routing
status: in-progress
pipeline: standard
phases: 6
total: 26
completed: 25
execution_route:
  version: 1
  spec: spec-145
  executor: build
  automation: hitl
  concern_count: 1
  estimated_files: 8
  reason: "Single-concern framework routing change: choose /ai-build vs /ai-autopilot and remove host-probe admission from the standard flow."
  safe_next_command: "/ai-build"
---

# Plan — spec-145 Standard Flow Executor Routing

## Architecture

**Pattern:** Ports and Adapters.

**Why:** Executor routing is deterministic framework logic consumed by skill/documentation adapters. The core decision is small: classify a plan as `executor: build` or `executor: autopilot`. Skill markdown, mirror surfaces, tests, and docs are adapters around that contract. Host-capacity admission is explicitly out of scope.

**Pipeline classification:** standard. The work touches multiple generated surfaces, but it is one concern: executor routing. It executes through `/ai-build` after approval to avoid the current `/ai-autopilot` host-probe deadlock that this spec removes.

## Gate Strategy

- Plan approved by the operator /ai-build invocation; execution follows the recorded route.
- No host-admission states or host deferral work remain in scope.
- RED/GREEN pairs cover route metadata, no-HITL route refusal, autopilot host-gate removal, and docs/mirror consistency.
- Quality-loop recovery is bounded to one finding-scoped remediation pass for blocker/critical/high findings, followed by terminal reassessment.
- Remediation evidence must use platform-neutral reproducers or report a Windows PowerShell equivalent when a POSIX shell pipeline is unavoidable.
- Canonical `.claude/` skill sources update first; mirrors/templates are regenerated or verified afterward.
- Historical state/audit records remain read-only.

## Phase 1: RED Routing Contract Tests

- [x] T-1.1 — RED: add route metadata lint tests
  - Agent: build
  - Files: tests/unit/test_spec_lint.py:560; tools/spec_lint/checks/plan.py:1
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): add fixtures asserting `execution_route.executor` accepts only `build|autopilot`, `safe_next_command` matches the executor, and approval remains `status` only.
  - Gate: `pytest tests/unit/test_spec_lint.py -q` fails before route metadata validation.

- [x] T-1.2 — RED: add executor routing unit tests
  - Agent: build
  - Files: tests/unit/execution/test_route_classifier.py:new
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): assert single-concern plans route to `build`, multi-concern or large estimated file-count plans route to `autopilot`, and draft plans produce a non-executable recommendation.
  - Gate: `pytest tests/unit/execution/test_route_classifier.py -q` fails before classifier exists.

- [x] T-1.3 — RED: update no-HITL contract tests
  - Agent: build
  - Files: tests/unit/skills/test_build_no_hitl.py:1; tests/unit/skills/test_execution_routing_contract.py:new
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): assert no-HITL reads `execution_route.executor`, refuses `executor: autopilot`, prints `/ai-autopilot`, and keeps no prompts/no fallback/no auto-retry.
  - Gate: `pytest tests/unit/skills/test_build_no_hitl.py tests/unit/skills/test_execution_routing_contract.py -q` fails before docs change.

- [x] T-1.4 — RED: add autopilot no-host-gate contract test
  - Agent: build
  - Files: tests/unit/skills/test_execution_routing_contract.py:new; .claude/skills/ai-autopilot/SKILL.md:42
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): assert autopilot Step 0 does not require `ok_to_dispatch == False` abort wording and does not describe host probe as a hard admission gate.
  - Gate: `pytest tests/unit/skills/test_execution_routing_contract.py -q` fails before autopilot docs change.

## Phase 2: Route Metadata and Classifier

- [x] T-2.1 — GREEN: implement a small route classifier
  - Agent: build
  - Files: src/ai_engineering/execution/__init__.py:new; src/ai_engineering/execution/route.py:new; tests/unit/execution/test_route_classifier.py:1
  - Principles applied: §10.1 KISS, §10.5 TDD, §10.8 Hexagonal Architecture
  - Patch (deterministic): define a pure classifier that returns `executor`, `concern_count`, `estimated_files`, `reason`, and `safe_next_command`; no host probe imports.
  - Gate: `pytest tests/unit/execution/test_route_classifier.py -q` passes.

- [x] T-2.2 — GREEN: update plan schema docs
  - Agent: build
  - Files: .ai-engineering/reference/plan-schema.md:8; src/ai_engineering/templates/.ai-engineering/reference/plan-schema.md:8
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): document `execution_route` fields and explicitly state that host capacity is not plan metadata.
  - Gate: `pytest tests/docs/test_links.py tests/unit/test_spec_lint.py -q` passes.

- [x] T-2.3 — GREEN: validate route metadata in plan lint
  - Agent: build
  - Files: tools/spec_lint/checks/plan.py:1; tests/unit/test_spec_lint.py:560
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): extend the lightweight frontmatter parser enough to validate the nested `execution_route` block without adding PyYAML.
  - Gate: `pytest tests/unit/test_spec_lint.py -q` passes.

- [x] T-2.4 — GREEN: expose route classification to `/ai-plan`
  - Agent: build
  - Files: .claude/skills/ai-plan/SKILL.md:19; .codex/skills/ai-plan/SKILL.md:19; .gemini/skills/ai-plan/SKILL.md:19; .github/skills/ai-plan/SKILL.md:19
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): add a route-classification step that writes `execution_route` and prints `/ai-build` or `/ai-autopilot` at exit.
  - Gate: `pytest tests/unit/skills/test_execution_routing_contract.py -q` passes.

## Phase 3: Build and Autopilot Skill Contracts

- [x] T-3.1 — GREEN: update no-HITL route gate
  - Agent: build
  - Files: .claude/skills/ai-build/handlers/no-hitl.md:18; .codex/skills/ai-build/handlers/no-hitl.md:18; .gemini/skills/ai-build/handlers/no-hitl.md:18; .github/skills/ai-build/handlers/no-hitl.md:18
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): make `execution_route.executor == build` authoritative for new plans; keep heading-count only as legacy fallback.
  - Gate: `pytest tests/unit/skills/test_build_no_hitl.py tests/unit/skills/test_execution_routing_contract.py -q` passes.

- [x] T-3.2 — GREEN: update `/ai-build` routing preflight wording
  - Agent: build
  - Files: .claude/skills/ai-build/SKILL.md:19; .codex/skills/ai-build/SKILL.md:19; .gemini/skills/ai-build/SKILL.md:19; .github/skills/ai-build/SKILL.md:19
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): document that `/ai-build` reads `execution_route.executor` and refuses `autopilot` plans with the safe next command.
  - Gate: `pytest tests/unit/skills/test_execution_routing_contract.py -q` passes.

- [x] T-3.3 — GREEN: remove autopilot host-probe hard gate
  - Agent: build
  - Files: .claude/skills/ai-autopilot/SKILL.md:42; .codex/skills/ai-autopilot/SKILL.md:39; .gemini/skills/ai-autopilot/SKILL.md:39; .github/skills/ai-autopilot/SKILL.md:40
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): remove Step 0 abort on `ok_to_dispatch == False`; if host probe remains mentioned, it is diagnostic/advisory only and cannot block the standard flow.
  - Gate: `pytest tests/unit/skills/test_execution_routing_contract.py -q` passes.

- [x] T-3.4 — GREEN: update autopilot examples and integration text
  - Agent: build
  - Files: .claude/skills/ai-autopilot/references/examples.md:1; .codex/skills/ai-autopilot/references/examples.md:1
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): document that executor routing comes from `plan.md`; remove host-admission recovery examples.
  - Gate: `pytest tests/unit/skills/test_execution_routing_contract.py -q` passes.

## Phase 4: Mirrors, Templates, and Docs

- [x] T-4.1 — GREEN: propagate skill changes to installer templates
  - Agent: build
  - Files: src/ai_engineering/templates/project/.claude/skills/ai-plan/SKILL.md:19; src/ai_engineering/templates/project/.claude/skills/ai-build/SKILL.md:19; src/ai_engineering/templates/project/.claude/skills/ai-autopilot/SKILL.md:42; src/ai_engineering/templates/project/.codex/skills/:all; src/ai_engineering/templates/project/.gemini/skills/:all; src/ai_engineering/templates/project/.github/skills/:all; src/ai_engineering/templates/project/.cursor/skills/:all; src/ai_engineering/templates/project/.opencode/skills/:all; src/ai_engineering/templates/project/.agent/skills/:all
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Patch (deterministic): run the repository mirror/template sync command and inspect generated changes.
  - Gate: `ai-eng dev sync --check` passes.

- [x] T-4.2 — GREEN: update canonical chain wording minimally
  - Agent: build
  - Files: src/ai_engineering/templates/project/CANONICAL.md:47; AGENTS.md:47; CLAUDE.md:47; GEMINI.md:47; .github/copilot-instructions.md:47
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): keep the public chain unchanged while clarifying that `/ai-plan` recommends `/ai-build` or `/ai-autopilot`.
  - Gate: `pytest tests/unit/specs/test_active_workflow_compliance.py -q` passes.

- [x] T-4.3 — GREEN: update CHANGELOG and lesson-linked docs
  - Agent: build
  - Files: CHANGELOG.md:1; .ai-engineering/LESSONS.md:1
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): add `[Unreleased]` Changed entry for route-only standard-flow simplification; keep the LESSONS entry added during replanning.
  - Gate: `pytest tests/docs/test_links.py -q` passes.

- [x] T-4.4 — VERIFY: active host-admission terms are gone from the standard flow
  - Agent: verify
  - Files: .claude/skills/:all; .codex/skills/:all; .gemini/skills/:all; .github/skills/:all; src/ai_engineering/templates/project/:all; .ai-engineering/reference/:all
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): read-only grep with archive/history allowlist.
  - Gate: `rg --hidden -n "host_admission|fanout|serial|deferred|ok_to_fanout" .claude .codex .gemini .github src/ai_engineering/templates/project .ai-engineering/reference | grep -v archive` returns no standard-flow hits except unrelated prose explicitly allowed by tests.

## Phase 5: Final Verification and Handoff

- [x] T-5.1 — VERIFY: run route and spec lint suites
  - Agent: verify
  - Files: tests/unit/execution/:all; tests/unit/test_spec_lint.py:560; tools/spec_lint/checks/plan.py:1
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/unit/execution tests/unit/test_spec_lint.py -q` passes.

- [x] T-5.2 — VERIFY: run skill contract tests
  - Agent: verify
  - Files: tests/unit/skills/:all; .claude/skills/:all
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/unit/skills -q` passes.

- [x] T-5.3 — VERIFY: run docs and mirror gates
  - Agent: verify
  - Files: README.md:1; AGENTS.md:1; CLAUDE.md:1; GEMINI.md:1; .github/copilot-instructions.md:1
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/docs/test_links.py tests/unit/specs/test_active_workflow_compliance.py -q && ai-eng dev sync --check` passes.

- [x] T-5.4 — VERIFY: run framework verification
  - Agent: verify
  - Files: .ai-engineering/specs/spec.md:1; .ai-engineering/specs/plan.md:1
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): read-only verification.
  - Gate: `ai-eng spec verify --sections .ai-engineering/specs/spec.md && ai-eng spec verify && uv run ai-eng verify` pass.
  - Result: PASS. `.venv/bin/python -m spec_lint --check` returned 6/6 checks with zero blockers/advisories, `.venv/bin/ai-eng dev sync --check` reported mirrors in sync, and `uv run ai-eng verify` returned 100/100.

- [ ] T-5.5 — VERIFY: run full test suite
  - Agent: verify
  - Files: tests/:all; src/:all; tools/:all
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `pytest -q` passes.

## Phase 6: Bounded Quality Remediation Contract Extension

- [x] T-6.1 — RED: add bounded quality-remediation contract tests
  - Agent: build
  - Files: tests/unit/skills/test_quality_remediation_contract.py:new
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): assert `/ai-build` and `/ai-autopilot` expose one bounded remediation pass, final reassessment, cross-platform reproducers, and mirror/template propagation.
  - Gate: `pytest tests/unit/skills/test_quality_remediation_contract.py -q` fails before skill changes.

- [x] T-6.2 — GREEN: update `/ai-build` quality remediation contract
  - Agent: build
  - Files: .claude/skills/ai-build/handlers/quality.md:1; .claude/skills/ai-build/SKILL.md:1
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): add one bounded quality-remediation pass for blocker/critical/high findings, final reassessment, no second pass, and operator approval before long full-suite gates.
  - Gate: `pytest tests/unit/skills/test_quality_remediation_contract.py -q` passes for build assertions.

- [x] T-6.3 — GREEN: update `/ai-autopilot` Phase 5b remediation contract
  - Agent: build
  - Files: .claude/skills/ai-autopilot/handlers/phase-quality.md:1; .claude/skills/ai-autopilot/SKILL.md:1; .claude/skills/ai-autopilot/references/examples.md:1
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Patch (deterministic): add manifest-aware `quality_remediation.max_attempts: 1`, owner mapping (`sub-NNN`/`integration`/`shared`), no re-decompose/no re-plan/no second pass.
  - Gate: `pytest tests/unit/skills/test_quality_remediation_contract.py -q` passes for autopilot assertions.

- [x] T-6.4 — GREEN: propagate quality remediation to multi-IDE surfaces
  - Agent: build
  - Files: .codex/skills/:all; .gemini/skills/:all; .github/skills/:all; src/ai_engineering/templates/project/:all
  - Principles applied: §10.4 DRY, §10.6 SDD
  - Patch (deterministic): run `.venv/bin/ai-eng dev sync` after canonical `.claude/` edits.
  - Gate: `pytest tests/unit/skills/test_quality_remediation_contract.py -q` passes mirror/template assertions.

- [x] T-6.5 — VERIFY: run focused quality-remediation gates
  - Agent: verify
  - Files: tests/unit/skills/test_quality_remediation_contract.py:1; tests/unit/test_phase_quality_single_round.py:1; tests/architecture/test_agent_description_contract.py:1
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): read-only verification.
  - Gate: `pytest tests/unit/skills/test_quality_remediation_contract.py tests/unit/test_phase_quality_single_round.py tests/architecture/test_agent_description_contract.py -q` passes.
  - Result: PASS as part of the 38-test focused quality-contract slice.

## Approval Gate

This revised plan was approved by the operator /ai-build invocation. Execution is in progress through /ai-build.


## Quality Rounds

Round 1: BLOCKED. `ai-eng spec verify --sections` and `ai-eng spec verify` passed; `ai-eng verify` failed with Security/Architecture findings (`idna` CVE-2026-45409, historical gitleaks examples, and internal import-cycle false positives). Per the pre-remediation single-round fail-loud policy, delivery stopped for operator direction.

Round 2 (operator requested remediation): PASS. Resolved the verifier false positives, dependency blocker, historical gitleaks findings, spec lint shape, canonical specs directory shape, and the new bounded quality-remediation contract. The focused 38-test quality-contract slice passed, docs/mirror checks passed (`358 passed, 3 skipped`), mirror sync passed, and `uv run ai-eng verify` returned 100/100. Full `pytest -q` remains intentionally pending until the operator approves the long-running gate.
