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

## Skills (33)

Path: `.ai-engineering/skills/<name>/SKILL.md` (flat organization, no category subdirectories)

| Skills (alphabetical) |
|-----------------------|
| a11y, api, architecture, build, changelog, cicd, cleanup, cli, code-simplifier, commit, create, db, debug, delete, discover, docs, explain, feature-gap, governance, infra, migrate, observe, perf, pr, quality, refactor, release, risk, security, spec, standards, test, work-item |

## Agents (6)

Path: `.ai-engineering/agents/<name>.md`

| Agent   | Purpose                                                       | Scope                        |
|---------|---------------------------------------------------------------|------------------------------|
| plan    | Orchestration, planning pipeline, dispatch, work-item sync    | read-write                   |
| build   | Implementation across all stacks (ONLY code write agent)      | read-write                   |
| scan    | Assessment: security, quality, governance, architecture, perf | read-write (work items only) |
| release | ALM + GitOps: commit, PR, deploy, triage, changelog           | read-write                   |
| write   | Documentation, changelogs, explanations                       | read-write (docs only)       |
| observe | Observability: engineer, team, AI, DORA, health dashboards    | read-only                    |

Slash commands: `/ai:<name>` for all skills and agents.

## Lifecycle

Discovery → Architecture → Planning → Implementation → Review → Verification → Testing → Iteration.

## Ownership Model

- Framework-managed: `.ai-engineering/standards/framework/**`
- Team-managed: `.ai-engineering/standards/team/**`
- Project-managed: `.ai-engineering/context/**`
- System-managed: `.ai-engineering/state/*.json`, `.ai-engineering/state/*.ndjson`

Never overwrite team/project content during framework updates. Cross-OS enforcement required.

## Command Contract

- `/ai:commit` → stage + commit + push
- `/ai:commit --only` → stage + commit
- `/ai:pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/ai:pr --only` → create PR; warn if unpushed, propose auto-push

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
