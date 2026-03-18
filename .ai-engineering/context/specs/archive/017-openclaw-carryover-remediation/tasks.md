---
spec: "017"
total: 31
completed: 31
last_session: "2026-02-23"
next_session: "CLOSED"
---

# Tasks — Spec-017

## Phase 0: Scaffold + Activation [S]

- [x] 0.1 Create `017-openclaw-carryover-remediation/spec.md`
- [x] 0.2 Create `017-openclaw-carryover-remediation/plan.md`
- [x] 0.3 Create `017-openclaw-carryover-remediation/tasks.md`
- [x] 0.4 Update `_active.md` to spec-017
- [x] 0.5 Update `product-contract.md` Active Spec reference

## Phase 1: Skill Requirements Model Expansion [M]

- [x] 1.1 Extend skill authoring template in `create-skill.md` with `requires.anyBins`, `requires.env`, `requires.config`, `os`
- [x] 1.2 Mirror `create-skill.md` updates to template path
- [x] 1.3 Extend `integrity-check.md` rules for expanded requirement fields
- [x] 1.4 Mirror `integrity-check.md` updates to template path
- [x] 1.5 Implement runtime parsing/evaluation for expanded requirement metadata
- [x] 1.6 Add/adjust tests for expanded requirement validation and backward compatibility

## Phase 2: Skills Status Diagnostics [M]

- [x] 2.1 Design CLI output contract for skill eligibility diagnostics
- [x] 2.2 Implement diagnostics in skills command flow
- [x] 2.3 Add tests for missing-bin, missing-env, missing-config, unsupported-os scenarios
- [x] 2.4 Document diagnostics usage in contributor docs

## Phase 3: CI Security Parity + Workflow Sanity [M]

- [x] 3.1 Add CI `gitleaks` execution path
- [x] 3.2 Add CI `semgrep` execution path
- [x] 3.3 Ensure `pip-audit` remains enforced in CI
- [x] 3.4 Add workflow sanity job (`actionlint` + policy checks)
- [x] 3.5 Add tests/fixtures/scripts needed by workflow sanity policies

## Phase 4: Spec-015 Carryover Completion (Tasks 5.6-5.10) [L]

- [x] 4.1 Implement cross-OS CI matrix coverage for install/doctor/gate/hook flows (015-5.6)
- [x] 4.2 Wire coverage + duplication thresholds into pre-push gate (015-5.7)
- [x] 4.3 Implement `--no-verify` bypass detection with CI verification strategy (015-5.8)
- [x] 4.4 Add hook hash integrity verification via install manifest (015-5.9)
- [x] 4.5 Add integration test that commit with mock secret is blocked by hooks (015-5.10)

## Phase 5: CI Scope Optimization + Install Smoke [M]

- [x] 5.1 Add docs-only/changed-scope routing for heavyweight jobs
- [x] 5.2 Keep baseline security/integrity checks always-on under scope routing
- [x] 5.3 Add install smoke workflow in clean environment
- [x] 5.4 Add test runtime observability artifact for slowest tests

## Phase 6: Spec-014 Closure Reconciliation [S]

- [x] 6.1 Reconcile spec status metadata in `014-dual-vcs-provider/spec.md`
- [x] 6.2 Resolve or formalize skipped verification items in `014-dual-vcs-provider/tasks.md`
- [x] 6.3 Update `014-dual-vcs-provider/done.md` with reconciliation notes and final posture

## Phase 7: Verification [S]

- [x] 7.1 Run targeted unit/integration tests for changed modules
- [x] 7.2 Run lint/type/security checks required by policy
- [x] 7.3 Run `ai-eng validate` and confirm integrity pass

## Phase 8: Close [S]

- [x] 8.1 Create `done.md` for spec-017 with delivered scope and evidence
- [x] 8.2 Update tasks frontmatter (`completed`, `next_session`)
- [x] 8.3 Prepare PR summary with trade-offs and deferred items
