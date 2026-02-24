---
spec: "021"
total: 91
completed: 91
last_session: "2026-02-24"
next_session: "Spec complete"
---

# Tasks — Governance + CI/CD Evolution

## Phase 0: Scaffold [S]

- [x] 0.1 Create feature branch `feat/governance-cicd-evolution`
- [x] 0.2 Create spec directory `021-governance-cicd-evolution/`
- [x] 0.3 Create `spec.md`, `plan.md`, `tasks.md`
- [x] 0.4 Update `_active.md` to point to spec-021
- [x] 0.5 Update `product-contract.md` active spec reference

## Phase 1: Agent Surface Evolution [L]

- [x] 1.1 Create `agents/orchestrator.md` with scope, capabilities, activation, behavior, references
- [x] 1.2 Create `agents/navigator.md` with 6 strategic capabilities and read-only boundary
- [x] 1.3 Create `agents/devops-engineer.md`
- [x] 1.4 Create `agents/docs-writer.md` with `write` and `simplify` modes
- [x] 1.5 Create `agents/governance-steward.md`
- [x] 1.6 Create `agents/pr-reviewer.md` as headless CI reviewer contract
- [x] 1.7 Update `agents/architect.md` to absorb mapper responsibilities and data-modeling linkage
- [x] 1.8 Update `agents/security-reviewer.md` to include `review/data-security`
- [x] 1.9 Update `agents/quality-auditor.md` to include test-gap mapping explicitly
- [x] 1.10 Update `agents/platform-auditor.md` references for new agent topology
- [x] 1.11 Remove codebase-mapper agent file and clean all references
- [x] 1.12 Add `.claude/commands/agent/orchestrator.md` thin wrapper
- [x] 1.13 Add `.claude/commands/agent/navigator.md` thin wrapper
- [x] 1.14 Add `.claude/commands/agent/devops-engineer.md` thin wrapper
- [x] 1.15 Add `.claude/commands/agent/docs-writer.md` thin wrapper
- [x] 1.16 Add `.claude/commands/agent/governance-steward.md` thin wrapper
- [x] 1.17 Add `.claude/commands/agent/pr-reviewer.md` thin wrapper
- [x] 1.18 Add `.github/agents/orchestrator.md` thin wrapper
- [x] 1.19 Add `.github/agents/navigator.md` thin wrapper
- [x] 1.20 Add `.github/agents/devops-engineer.md` thin wrapper
- [x] 1.21 Add `.github/agents/docs-writer.md` thin wrapper
- [x] 1.22 Add `.github/agents/governance-steward.md` thin wrapper
- [x] 1.23 Add `.github/agents/pr-reviewer.md` thin wrapper
- [x] 1.24 Remove mapper wrappers from `.claude/commands/agent/` and `.github/agents/`

## Phase 2: Skill Surface Evolution [L]

- [x] 2.1 Create `skills/workflows/self-improve/SKILL.md`
- [x] 2.2 Create `skills/dev/data-modeling/SKILL.md`
- [x] 2.3 Create `skills/review/data-security/SKILL.md`
- [x] 2.4 Create `skills/docs/simplify/SKILL.md`
- [x] 2.5 Create `skills/govern/adaptive-standards/SKILL.md`
- [x] 2.6 Update `skills/dev/cicd-generate/SKILL.md` with AI PR review generation step (4b)
- [x] 2.7 Merge the former audit-report output contract into `skills/quality/audit-code/SKILL.md`
- [x] 2.8 Remove the former audit-report skill and clean all references
- [x] 2.9 Remove `skills/patterns/**` category from canonical content
- [x] 2.10 Add equivalent reference docs under consuming skills `references/`
- [x] 2.11 Add Copilot prompt wrappers for new skills
- [x] 2.12 Add Claude command wrappers for new skills
- [x] 2.13 Remove prompt/command wrappers for deleted skills

## Phase 3: Reference Consolidation [M]

- [x] 3.1 Add `references/database-patterns.md` and wire to architect + security-reviewer
- [x] 3.2 Add `references/api-design-patterns.md` and wire to architect + principal-engineer
- [x] 3.3 Add language/framework references (python/typescript/react/nextjs/dotnet/rust)
- [x] 3.4 Add delivery/platform references (azure/azure-devops/infra/cicd/networking)
- [x] 3.5 Wire `git-helpers.md` into workflows and `platform-detect.md` into install-check

## Phase 4: Installer Runtime Expansion [L]

- [x] 4.1 Add `installer/tools.py` for OS-aware installation attempts (`winget`, `brew`, `apt`)
- [x] 4.2 Add `installer/auth.py` for provider auth checks and guidance
- [x] 4.2a Ensure provider-aware VCS tool install path (`gh` for GitHub, `az` for Azure DevOps)
- [x] 4.2b Implement CLI-unavailable fallback to API-direct mode and persist mode in manifest/state
- [x] 4.3 Add `installer/cicd.py` for stack-aware pipeline generation
- [x] 4.4 Add `installer/branch_policy.py` for API apply + manual guide fallback
- [x] 4.5 Expand `installer/service.py` to include phases 2-5 after existing bootstrap
- [x] 4.6 Update install result model/output to include readiness outcome and manual-step flags
- [x] 4.7 Add templates for GitHub pipelines (`ci.yml`, `ai-pr-review.yml`, `ai-eng-gate.yml`, optional `security.yml`)
- [x] 4.8 Add templates for Azure DevOps pipelines (`ci.yml`, `ai-pr-review.yml`, `ai-eng-gate.yml`)
- [x] 4.9 Add manual guide templates for branch policy setup (GitHub + Azure DevOps)

## Phase 5: VCS + Pipeline Enforcement [L]

- [x] 5.1 Extend `vcs/protocol.py` with branch policy, auth scope, and PR review methods
- [x] 5.2 Implement GitHub branch protection apply + PR review posting
- [x] 5.3 Implement Azure DevOps policy/build validation apply + PR review posting
- [x] 5.4 Add API fallback providers for environments without `gh`/`az` CLI installs
- [x] 5.5 Update `vcs/factory.py` to resolve CLI vs API mode from manifest/runtime
- [x] 5.6 Expand `pipeline/injector.py` from snippet-only behavior to generation support
- [x] 5.7 Expand `pipeline/compliance.py` to verify AI PR review and gate pipeline presence
- [x] 5.8 Ensure high/critical findings map to merge-blocking status outcomes

## Phase 6: CLI + State Integration [M]

- [x] 6.1 Add `cli_commands/review.py` with `ai-eng review pr`
- [x] 6.2 Register new review command group in `cli_factory.py`
- [x] 6.2a Add `cli_commands/cicd.py` with `ai-eng cicd regenerate`
- [x] 6.2b Register `cicd` command group in `cli_factory.py`
- [x] 6.3 Extend `state/models.py` InstallManifest for auth/policy/cicd state
- [x] 6.4 Update readiness checks to include auth, generated pipelines, and policy readiness
- [x] 6.5 Update `doctor/service.py` with new diagnostics and fix guidance

## Phase 6.5: Surface Consistency + Map Validation [M]

- [x] 6.6 Validate final governance counts: 14 agents, 44 skills, 6 categories, no `patterns/` category
- [x] 6.7 Build and document agent→skill map and verify 0 orphan skills
- [x] 6.8 Assign `docs/prompt-design` to `docs-writer` and verify orphan count remains 0
- [x] 6.9 Ensure `navigator` uses existing artifacts only (no new runtime artifact outputs)
- [x] 6.10 Ensure `workflows/self-improve` codifies analyze→plan→execute→verify→learn handoff

## Phase 7: Documentation + Pointer Synchronization [M]

- [x] 7.1 Update `manifest.yml` registrations/counters and enforcement sections
- [x] 7.2 Update `AGENTS.md` agent inventory and references
- [x] 7.3 Update `CLAUDE.md` agent inventory and references
- [x] 7.4 Update `codex.md` agent inventory and references
- [x] 7.5 Update `.github/copilot-instructions.md` agent inventory and references
- [x] 7.6 Sync template mirror under `src/ai_engineering/templates/.ai-engineering/**`
- [x] 7.7 Sync template project wrappers under `src/ai_engineering/templates/project/**`

## Phase 8: Verify + Close [M]

- [x] 8.1 Add/adjust unit tests for installer phases, vcs policy methods, and review command
- [x] 8.2 Add/adjust integration tests for install-to-operational flows (GitHub/Azure + fallback)
- [x] 8.3 Add/adjust tests for `ai-eng cicd regenerate` behavior on stack changes
- [x] 8.4 Run `ruff`, `pytest`, `ty`, `pip-audit` and ensure gates pass
- [x] 8.5 Run integrity-check for `.ai-engineering/` consistency
- [x] 8.6 Verify acceptance criteria and create `done.md`
