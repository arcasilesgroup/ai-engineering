# GEMINI.md

Operational guide for Gemini assistant sessions. Conflicts with `.ai-engineering/**` → follow `.ai-engineering/**`.

## Source of Truth

- Governance: `.ai-engineering/` — contract: `manifest.yml`, context: `context/**`.

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Run cleanup** — cleanup workflow to sync repo.
4. **Verify tooling** — ruff, gitleaks, pytest, ty.

Mandatory. Skipping risks stale code, repeated decisions, or merge conflicts.

## Absolute Prohibitions

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip/silence a failing gate — fix root cause.
3. **NEVER** weaken gate severity.
4. **NEVER** modify hook scripts — hash-verified.
5. **NEVER** push to protected branches (main, master).
6. **NEVER** dismiss security findings without `state/decision-store.json` risk acceptance.
7. **NEVER** use destructive git commands unless user explicitly requests.

Gate failure: diagnose → fix → retry. Use `ai-eng doctor --fix-tools` or `--fix-hooks`.

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

## Lifecycle

Discovery → Architecture → Planning → Implementation → Review → Verification → Testing → Iteration.

## Progressive Disclosure

Three-level loading: **Metadata** (always) → **Body** (on-demand) → **Resources** (on-demand).

Session start loads ONLY: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`. Do NOT pre-load skills or agents.

## Security & Quality

- Mandatory local hooks: `gitleaks`, `semgrep`, dependency checks, stack checks.
- No direct commits to main/master. No protected-branch push.
- Security findings require `state/decision-store.json` risk acceptance.

**Quality**: Coverage 90% (source: `standards/framework/quality/core.md`), duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical, 100% gate pass.

**Security**: Zero medium/high/critical findings, zero leaks, zero dependency vulns, hook hash verification, cross-OS enforcement.

## Tooling

`uv` (runtime) · `ruff` (lint/format) · `ty` (types) · `pip-audit` (deps)
