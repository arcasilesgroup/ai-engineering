# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

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

## Command Contract

- `/commit` -> stage + commit + push
- `/commit --only` -> stage + commit
- `/pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` -> create PR; if branch is unpushed, warn and propose auto-push; if declined, continue with selected mode
- `/acho` -> stage + commit + push
- `/acho pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)

## Non-Negotiables

- Mandatory local gates cannot be bypassed.
- No direct commits to protected branches.
- Update safety must preserve team/project-owned content.
- Security findings cannot be dismissed without risk acceptance in `state/decision-store.json`.

## Validation Reminder

Before proposing merge:

- lint/format (`ruff`),
- tests (`pytest`),
- type checks (`ty`),
- security scans (`gitleaks`, `semgrep`, `pip-audit`).

## Quality Contract

- Coverage ≥ 80% (≥ 90% governance-critical).
- Duplication ≤ 3%.
- Cyclomatic complexity ≤ 10.
- Cognitive complexity ≤ 15.
- No blocker/critical issues.
