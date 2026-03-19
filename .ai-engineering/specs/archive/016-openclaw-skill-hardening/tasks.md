---
spec: "016"
total: 35
completed: 35
last_session: "2026-02-23"
next_session: "none — spec complete"
---

# Tasks — OpenClaw-Inspired Skill & Standards Hardening

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec directory and spec.md
- [x] 0.2 Create plan.md
- [x] 0.3 Create tasks.md
- [x] 0.4 Update _active.md to point to spec-016
- [x] 0.5 Atomic commit: scaffold

## Phase 1: YAML Frontmatter [L]

- [x] 1.1 Define frontmatter schema (name, version, category, requires, tags)
- [x] 1.2 Add frontmatter to workflow skills (4 skills: commit, pr, acho, pre-implementation)
- [x] 1.3 Add frontmatter to dev skills (7 skills: code-review, debug, refactor, test-strategy, migration, deps-update, cicd-generate)
- [x] 1.4 Add frontmatter to review skills (5 skills: architecture, security, performance, dast, container-security)
- [x] 1.5 Add frontmatter to docs skills (4 skills: changelog, explain, writer, prompt-design)
- [x] 1.6 Add frontmatter to govern skills (11 skills: create-spec, create-skill, create-agent, delete-skill, delete-agent, integrity-check, contract-compliance, ownership-audit, accept-risk, resolve-risk, renew-risk)
- [x] 1.7 Add frontmatter to quality skills (7 skills: audit-code, audit-report, test-gap-analysis, install-check, release-gate, sbom, docs-audit)
- [x] 1.8 Add frontmatter to utils skills (5 skills: git-helpers, platform-detect, python-patterns, dotnet-patterns, nextjs-patterns)

## Phase 2: Anti-patterns [M]

- [x] 2.1 Add "When NOT to Use" to skills/review/security.md
- [x] 2.2 Add "When NOT to Use" to skills/review/architecture.md
- [x] 2.3 Add "When NOT to Use" to skills/dev/code-review.md
- [x] 2.4 Add "When NOT to Use" to skills/dev/refactor.md
- [x] 2.5 Add "When NOT to Use" to skills/quality/audit-code.md
- [x] 2.6 Add "When NOT to Use" to skills/govern/integrity-check.md

## Phase 3: Test Tiers [M]

- [x] 3.1 Add Test Tiers section to standards/framework/stacks/python.md
- [x] 3.2 Map test tiers to gate stages in standards/framework/quality/core.md
- [x] 3.3 Update skills/dev/test-strategy.md with tier classification

## Phase 4: Doctor Skill [M]

- [x] 4.1 Create skills/utils/doctor.md following skill template
- [x] 4.2 Create .claude/commands/utils/doctor.md slash command wrapper
- [x] 4.3 Update manifest.yml with doctor skill registration
- [x] 4.4 Update CLAUDE.md with doctor skill reference

## Phase 5: Multi-Agent Skill [M]

- [x] 5.1 Create skills/dev/multi-agent.md following skill template
- [x] 5.2 Create .claude/commands/dev/multi-agent.md slash command wrapper
- [x] 5.3 Update manifest.yml with multi-agent skill registration
- [x] 5.4 Update CLAUDE.md with multi-agent skill reference
- [x] 5.5 Update agents/platform-auditor.md to reference multi-agent skill

## Phase 6: Install Gating [M]

- [x] 6.1 Add requires.bins to skills/review/security.md (gitleaks, semgrep)
- [x] 6.2 Add requires.bins to skills/review/dast.md (zap-cli, nuclei)
- [x] 6.3 Add requires.bins to skills/review/container-security.md (trivy)
- [x] 6.4 Add requires.bins to skills/quality/audit-code.md (ruff, ty)
- [x] 6.5 Add requires.bins to skills/quality/sbom.md (pip-audit)
- [x] 6.6 Add requires.bins to skills/dev/deps-update.md (pip-audit)
- [x] 6.7 Add requires.bins to skills/workflows/commit.md (gitleaks, ruff)

## Phase 7: Governance Updates [S]

- [x] 7.1 Update skills/govern/integrity-check.md — add frontmatter validation
- [x] 7.2 Update skills/govern/create-skill.md — include frontmatter in template

## Phase 8: Cross-References [S]

- [x] 8.1 Update product-contract.md — active spec, skill counter (43 to 45)
- [x] 8.2 Update instruction files — CLAUDE.md, AGENTS.md skill lists

## Phase 9: Close [S]

- [x] 9.1 Run integrity-check — verify zero violations
- [x] 9.2 Create done.md
- [x] 9.3 Update tasks.md frontmatter — completed = total
- [x] 9.4 Create PR
