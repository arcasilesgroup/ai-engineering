# AGENTS.md

Operational contract for AI agents. Consumed by GitHub Copilot, Claude Code, Gemini CLI, Codex, and other AI coding agents.

## Canonical Governance Source

- `.ai-engineering/` is the single source of truth — contract: `manifest.yml`, context: `context/**`.

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Run cleanup** — sync repo (status, git pull, prune, branch cleanup).
4. **Verify tooling** — ruff, gitleaks, pytest, ty.

Mandatory. Skipping risks stale code, repeated decisions, or merge conflicts.

## Agent Behavior Mandates

1. **The `<think>` Protocol** — Before complex git operations, broad changes, or task conclusion: use internal reasoning to plan. Verify all context is discovered.
2. **Parallel Execution** — Batch independent operations into simultaneous tool calls. Never sequential when parallelizable.
3. **Context Efficiency** — Never re-read files already in context window.
4. **Code Citing** — Use `startLine:endLine:filepath` format. Never output code unless requested. Use `// ... existing code ...` for omissions.
5. **Proactive Memory** — Read/write `state/decision-store.json` to persist learnings and avoid repeated questions.

## Skills (44)

Path: `.ai-engineering/skills/<category>/<name>/SKILL.md`

| Category | Count | Skills |
|----------|-------|--------|
| workflows | 4 | commit, pr, cleanup, self-improve |
| dev | 16 | debug, refactor, code-review, data-modeling, test-runner, test-strategy, migration, deps-update, cicd-generate, cli-ux, multi-agent, api-design, infrastructure, database-ops, sonar-gate, discovery-interrogation |
| review | 5 | architecture, performance, security, specialized-security, accessibility |
| docs | 5 | changelog, explain, writer, simplify, prompt-design |
| govern | 8 | integrity-check, contract-compliance, ownership-audit, adaptive-standards, create-spec, agent-lifecycle, skill-lifecycle, risk-lifecycle |
| quality | 6 | audit-code, docs-audit, install-check, release-gate, test-gap-analysis, sbom |

## Agents (19)

Path: `.ai-engineering/agents/<name>.md`

| Agent | Purpose |
|-------|---------|
| principal-engineer | Code review |
| debugger | Bug diagnosis |
| architect | Architecture analysis |
| quality-auditor | Quality gate enforcement |
| security-reviewer | Security assessment |
| orchestrator | Multi-phase execution |
| navigator | Strategic spec analysis |
| devops-engineer | CI/CD automation |
| test-master | Testing specialist |
| docs-writer | Documentation |
| governance-steward | Governance lifecycle |
| pr-reviewer | Headless CI review |
| code-simplifier | Complexity reduction |
| platform-auditor | Full-spectrum audit |
| verify-app | E2E verification |
| infrastructure-engineer | IaC provisioning |
| database-engineer | Database engineering |
| frontend-specialist | Frontend/UI architecture |
| api-designer | Contract-first API design |

Slash commands: see `CLAUDE.md`.

## Lifecycle

Discovery → Architecture → Planning → Implementation → Review → Verification → Testing → Iteration.

## Ownership Model

- Framework-managed: `.ai-engineering/standards/framework/**`
- Team-managed: `.ai-engineering/standards/team/**`
- Project-managed: `.ai-engineering/context/**`
- System-managed: `.ai-engineering/state/*.json`, `.ai-engineering/state/*.ndjson`

Never overwrite team/project content during framework updates. Cross-OS enforcement required.

## Command Contract

- `/commit` → stage + commit + push
- `/commit --only` → stage + commit
- `/pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` → create PR; warn if unpushed, propose auto-push
- `/acho` → stage + commit + push
- `/acho pr` → stage + commit + push + PR + auto-complete

## Non-Negotiables

- Mandatory local gates cannot be bypassed.
- No direct commits to protected branches.
- Update safety must preserve team/project-owned content.
- Security findings require `state/decision-store.json` risk acceptance.

## Progressive Disclosure

Three-level loading: **Metadata** (always) → **Body** (on-demand) → **Resources** (on-demand).

Session start loads ONLY: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`. Do NOT pre-load skills or agents.

## Quality Contract

Coverage 90%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical, 100% gate pass.

## Security Contract

Zero medium/high/critical findings, zero leaks, zero dependency vulns, hook hash verification, cross-OS enforcement.

## Tooling

`uv` (runtime) · `ruff` (lint/format) · `ty` (types) · `pip-audit` (deps)

## Validation Reminder

Before merge: `ruff`, `pytest`, `ty`, `gitleaks`, `semgrep`, `pip-audit`.
