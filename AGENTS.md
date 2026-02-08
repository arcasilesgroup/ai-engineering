# AGENTS.md

## Purpose

Operational contract for AI agents working in this repository.

## Canonical Governance Source

- `.ai-engineering/` is the single source of truth for governance and context.
- Agents must treat `.ai-engineering/manifest.yml` and `.ai-engineering/context/**` as authoritative.

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

## Command Contract

- `/commit` -> stage + commit + push current branch
- `/commit --only` -> stage + commit
- `/pr` -> stage + commit + push + create PR
- `/pr --only` -> create PR; if branch is unpushed, warn and propose auto-push; continue via selected mode if declined
- `/acho` -> stage + commit + push current branch
- `/acho pr` -> stage + commit + push + create PR

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
- Update `.ai-engineering/context/delivery/implementation.md` and `.ai-engineering/context/backlog/tasks.md` on each phase execution block.
- Include rationale, expected gain, and potential impact in governance document updates.
