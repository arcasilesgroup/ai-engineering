# Codex Project Instructions

Operational contract for OpenAI Codex working in this repository.

## Canonical Governance Source

- `.ai-engineering/` is the single source of truth for governance and context.
- Agents must treat `.ai-engineering/manifest.yml` and `.ai-engineering/context/**` as authoritative.

## Session Start Protocol

Before any non-trivial implementation work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks files.
2. **Read decision store** — `.ai-engineering/state/decision-store.json` to avoid re-asking decided questions.
3. **Run pre-implementation** — execute `/pre-implementation` to sync the repository (git pull, prune, cleanup, create feature branch).
4. **Verify tooling** — confirm ruff, gitleaks, pytest, ty are available.

This protocol is mandatory. Skipping it risks working on stale code, repeating decided questions, or creating merge conflicts.

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

- `.ai-engineering/skills/workflows/commit/SKILL.md` — `/commit` flow.
- `.ai-engineering/skills/workflows/pr/SKILL.md` — `/pr` flow.
- `.ai-engineering/skills/workflows/acho/SKILL.md` — `/acho` alias.
- `.ai-engineering/skills/workflows/pre-implementation/SKILL.md` — branch hygiene before implementation.
- `.ai-engineering/skills/workflows/cleanup/SKILL.md` — branch cleanup and stale branch removal.
- `.ai-engineering/skills/workflows/self-improve/SKILL.md` — iterative analyze→plan→execute→verify→learn loop.

### Dev Skills

- `.ai-engineering/skills/dev/debug/SKILL.md` — systematic diagnosis.
- `.ai-engineering/skills/dev/refactor/SKILL.md` — safe refactoring.
- `.ai-engineering/skills/dev/code-review/SKILL.md` — code review checklist.
- `.ai-engineering/skills/dev/data-modeling/SKILL.md` — data modeling and migration safety.
- `.ai-engineering/skills/dev/test-strategy/SKILL.md` — test design.
- `.ai-engineering/skills/dev/migration/SKILL.md` — migration planning.
- `.ai-engineering/skills/dev/deps-update/SKILL.md` — dependency management.
- `.ai-engineering/skills/dev/cicd-generate/SKILL.md` — CI/CD workflow generation.
- `.ai-engineering/skills/dev/multi-agent/SKILL.md` — multi-agent orchestration patterns.

### Review Skills

- `.ai-engineering/skills/review/architecture/SKILL.md` — architecture review.
- `.ai-engineering/skills/review/performance/SKILL.md` — performance review.
- `.ai-engineering/skills/review/security/SKILL.md` — security assessment.
- `.ai-engineering/skills/review/data-security/SKILL.md` — data security posture review.
- `.ai-engineering/skills/review/dast/SKILL.md` — dynamic application security testing.
- `.ai-engineering/skills/review/container-security/SKILL.md` — container image scanning.

### Docs Skills

- `.ai-engineering/skills/docs/changelog/SKILL.md` — changelog documentation.
- `.ai-engineering/skills/docs/explain/SKILL.md` — Feynman-style code and concept explanations.
- `.ai-engineering/skills/docs/writer/SKILL.md` — open-source documentation generation.
- `.ai-engineering/skills/docs/simplify/SKILL.md` — clarity-first simplification workflow.
- `.ai-engineering/skills/docs/prompt-design/SKILL.md` — prompt engineering frameworks.

### Govern Skills

- `.ai-engineering/skills/govern/integrity-check/SKILL.md` — governance content validation (7-category check).
- `.ai-engineering/skills/govern/contract-compliance/SKILL.md` — clause-by-clause contract validation.
- `.ai-engineering/skills/govern/ownership-audit/SKILL.md` — ownership boundary and updater safety validation.
- `.ai-engineering/skills/govern/adaptive-standards/SKILL.md` — standards evolution with compatibility checks.
- `.ai-engineering/skills/govern/create-agent/SKILL.md` — agent authoring and registration procedure.
- `.ai-engineering/skills/govern/create-skill/SKILL.md` — skill authoring and registration procedure.
- `.ai-engineering/skills/govern/create-spec/SKILL.md` — spec creation with branch-first workflow.
- `.ai-engineering/skills/govern/delete-agent/SKILL.md` — safe agent removal with dependency checks.
- `.ai-engineering/skills/govern/delete-skill/SKILL.md` — safe skill removal with dependency checks.
- `.ai-engineering/skills/govern/accept-risk/SKILL.md` — risk acceptance with severity-based expiry.
- `.ai-engineering/skills/govern/resolve-risk/SKILL.md` — risk remediation and closure.
- `.ai-engineering/skills/govern/renew-risk/SKILL.md` — time-limited risk renewal (max 2).

### Quality Skills

- `.ai-engineering/skills/quality/audit-code/SKILL.md` — quality gate assessment.
- `.ai-engineering/skills/quality/docs-audit/SKILL.md` — documentation and content quality audit.
- `.ai-engineering/skills/quality/install-check/SKILL.md` — installation readiness check.
- `.ai-engineering/skills/quality/release-gate/SKILL.md` — aggregated release readiness gate.
- `.ai-engineering/skills/quality/test-gap-analysis/SKILL.md` — capability-to-test risk mapping.
- `.ai-engineering/skills/quality/sbom/SKILL.md` — software bill of materials generation.

## Agents

Agent definitions provide personas for complex multi-step tasks. Activate the relevant agent:

- `.ai-engineering/agents/principal-engineer.md` — principal-level code review.
- `.ai-engineering/agents/debugger.md` — systematic bug diagnosis.
- `.ai-engineering/agents/architect.md` — architecture analysis.
- `.ai-engineering/agents/quality-auditor.md` — quality gate enforcement.
- `.ai-engineering/agents/security-reviewer.md` — security assessment.
- `.ai-engineering/agents/orchestrator.md` — multi-phase execution orchestration.
- `.ai-engineering/agents/navigator.md` — strategic next-spec analysis.
- `.ai-engineering/agents/devops-engineer.md` — CI/CD and delivery automation.
- `.ai-engineering/agents/docs-writer.md` — documentation authoring and simplification.
- `.ai-engineering/agents/governance-steward.md` — governance lifecycle stewardship.
- `.ai-engineering/agents/pr-reviewer.md` — headless CI pull request review.
- `.ai-engineering/agents/code-simplifier.md` — complexity reduction.
- `.ai-engineering/agents/platform-auditor.md` — full-spectrum audit orchestration.
- `.ai-engineering/agents/verify-app.md` — end-to-end verification.

## Copilot Integration

GitHub Copilot prompt files (`.github/prompts/`) and custom agents (`.github/agents/`) are thin wrappers deployed alongside Claude Code commands. They point to the same canonical skill and agent files.

- `/commit`, `/pr`, `/cleanup`, etc. — workflow prompts.
- `/dev-debug`, `/dev-refactor`, etc. — dev skill prompts.
- `@debugger`, `@security-reviewer`, etc. — agent personas.

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

- Coverage: 100%.
- Duplication ≤ 3%.
- Cyclomatic complexity ≤ 10.
- Cognitive complexity ≤ 15.
- No blocker/critical issues.
- Quality gate pass rate: 100% on all governed operations.

## Security Contract

- Security scan pass rate: 100% — zero medium/high/critical findings.
- Secret detection: zero leaks (blocker severity).
- Dependency vulnerabilities: zero known (blocker severity).
- SAST findings (medium+): zero — remediate or risk-accept.
- Tamper resistance: hook hash verification + `--no-verify` bypass detection mandatory.
- Cross-OS enforcement: all gates must pass on Ubuntu, Windows, and macOS.

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
