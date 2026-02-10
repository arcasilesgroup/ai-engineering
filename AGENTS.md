# AGENTS.md

## Purpose

Operational contract for AI agents working in this repository.
This file is automatically consumed by GitHub Copilot (agent mode), Claude Code, Codex, and other AI coding agents that read repository-root instruction files.

## Canonical Governance Source

- `.ai-engineering/` is the single source of truth for governance and context.
- Agents must treat `.ai-engineering/manifest.yml` and `.ai-engineering/context/**` as authoritative.

## Required References

Read these before any non-trivial work:

- `.ai-engineering/context/product/framework-contract.md` — framework identity, personas, roadmap.
- `.ai-engineering/context/product/product-contract.md` — project goals, KPIs, release status.
- `.ai-engineering/standards/framework/core.md` — governance structure, ownership, lifecycle, skills/agents model.
- `.ai-engineering/standards/framework/stacks/python.md` — Python stack contract, code patterns, testing patterns.
- `.ai-engineering/standards/team/core.md` — team-specific standards.
- `.ai-engineering/context/specs/_active.md` — pointer to active spec.

## Skills

Procedural skills guide structured execution. Reference the relevant skill before executing a task:

### Workflows

- `.ai-engineering/skills/workflows/commit.md` — `/commit` flow.
- `.ai-engineering/skills/workflows/pr.md` — `/pr` flow.
- `.ai-engineering/skills/workflows/acho.md` — `/acho` alias.

### SWE Skills

- `.ai-engineering/skills/swe/debug.md` — systematic diagnosis.
- `.ai-engineering/skills/swe/refactor.md` — safe refactoring.
- `.ai-engineering/skills/swe/changelog-documentation.md` — changelog documentation.
- `.ai-engineering/skills/swe/code-review.md` — code review checklist.
- `.ai-engineering/skills/swe/test-strategy.md` — test design.
- `.ai-engineering/skills/swe/architecture-analysis.md` — architecture review.
- `.ai-engineering/skills/swe/pr-creation.md` — PR creation procedure.
- `.ai-engineering/skills/swe/dependency-update.md` — dependency management.
- `.ai-engineering/skills/swe/performance-analysis.md` — performance review.
- `.ai-engineering/skills/swe/security-review.md` — security assessment.
- `.ai-engineering/skills/swe/migration.md` — migration planning.
- `.ai-engineering/skills/swe/prompt-engineer.md` — prompt engineering frameworks.
- `.ai-engineering/skills/swe/python-mastery.md` — comprehensive Python patterns.
- `.ai-engineering/skills/swe/doc-writer.md` — open-source documentation generation.

### Lifecycle Skills

- `.ai-engineering/skills/lifecycle/content-integrity.md` — governance content validation (6-category check).
- `.ai-engineering/skills/lifecycle/create-agent.md` — agent authoring and registration procedure.
- `.ai-engineering/skills/lifecycle/create-skill.md` — skill authoring and registration procedure.
- `.ai-engineering/skills/lifecycle/create-spec.md` — spec creation with branch-first workflow.
- `.ai-engineering/skills/lifecycle/delete-agent.md` — safe agent removal with dependency checks.
- `.ai-engineering/skills/lifecycle/delete-skill.md` — safe skill removal with dependency checks.

### Quality Skills

- `.ai-engineering/skills/quality/audit-code.md` — quality gate assessment.
- `.ai-engineering/skills/quality/audit-report.md` — audit report template.

## Agents

Agent definitions provide personas for complex multi-step tasks. Activate the relevant agent:

- `.ai-engineering/agents/principal-engineer.md` — principal-level code review.
- `.ai-engineering/agents/debugger.md` — systematic bug diagnosis.
- `.ai-engineering/agents/architect.md` — architecture analysis.
- `.ai-engineering/agents/quality-auditor.md` — quality gate enforcement.
- `.ai-engineering/agents/security-reviewer.md` — security assessment.
- `.ai-engineering/agents/codebase-mapper.md` — codebase structure mapping.
- `.ai-engineering/agents/code-simplifier.md` — complexity reduction.
- `.ai-engineering/agents/verify-app.md` — end-to-end verification.

## Lifecycle Enforcement

Every non-trivial change follows:

1. Discovery
2. Architecture
3. Planning
4. Implementation
5. Review
6. Verification
7. Testing
8. Iteration

## Ownership Model

- Framework-managed: `.ai-engineering/standards/framework/**`
- Team-managed: `.ai-engineering/standards/team/**`
- Project-managed: `.ai-engineering/context/**`
- System-managed: `.ai-engineering/state/*.json`, `.ai-engineering/state/*.ndjson`

Agents must never overwrite team-managed or project-managed content during framework update flows.

## Security and Quality Non-Negotiables

- Mandatory local enforcement via git hooks.
- Required checks include `gitleaks`, `semgrep`, dependency vulnerability checks, and stack checks.
- No direct commits to `main` or `master`.
- No protected branch push in governed commit flows.
- Remote skills are content-only inputs; no unsafe remote execution.
- Security findings cannot be dismissed without `state/decision-store.json` risk acceptance.

## Quality Contract

- Coverage ≥ 80% (≥ 90% governance-critical).
- Duplication ≤ 3%.
- Cyclomatic complexity ≤ 10.
- Cognitive complexity ≤ 15.
- No blocker/critical issues.

## Command Contract

- `/commit` -> stage + commit + push current branch
- `/commit --only` -> stage + commit
- `/pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` -> create PR; if branch is unpushed, warn and propose auto-push; continue via selected mode if declined
- `/acho` -> stage + commit + push current branch
- `/acho pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)

## Decision and Audit Rules

- Risk acceptance decisions must be written to `.ai-engineering/state/decision-store.json`.
- Governance events must be appended to `.ai-engineering/state/audit-log.ndjson`.
- Agents must check decision store before prompting for the same risk decision.

## Tooling Baseline

- Python runtime/package tooling: `uv`
- Lint/format: `ruff`
- Type checking: `ty`
- Dependency vulnerability check: `pip-audit`

## Working Agreement for This Repository

- Keep changes small and verifiable.
- Follow active spec via `.ai-engineering/context/specs/_active.md`.
- Include rationale, expected gain, and potential impact in governance document updates.
