# CLAUDE.md

Operational guide for assistant sessions. Conflicts with `.ai-engineering/**` → follow `.ai-engineering/**`.

## Source of Truth

- Governance: `.ai-engineering/` — contract: `manifest.yml`, context: `context/**`.

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Run cleanup** — `/cleanup` to sync repo.
4. **Verify tooling** — ruff, gitleaks, pytest, ty.

Mandatory. Skipping risks stale code, repeated decisions, or merge conflicts.

## Absolute Prohibitions

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip/silence a failing gate — fix root cause.
3. **NEVER** weaken gate severity.
4. **NEVER** modify hook scripts — hash-verified.
5. **NEVER** push to protected branches (main, master).
6. **NEVER** dismiss security findings without `state/decision-store.json` risk acceptance.
7. **NEVER** disable/modify `.claude/settings.json` deny rules.
8. **NEVER** use destructive git commands unless user explicitly requests.

Gate failure: diagnose → fix → retry. Use `ai-eng doctor --fix-tools` or `--fix-hooks`.

## Skills (33)

Path: `.ai-engineering/skills/<name>/SKILL.md` (flat organization, no category subdirectories)

| Skills (alphabetical) |
|-----------------------|
| a11y, api, architecture, build, changelog, cicd, cleanup, cli, code-simplifier, commit, create, db, debug, delete, discover, docs, explain, feature-gap, governance, infra, migrate, observe, perf, pr, quality, refactor, release, risk, security, spec, standards, test, work-item |

Slash commands (`.claude/commands/ai/`): `/ai:<name>` for all skills and agents.

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

## Lifecycle

Discovery → Architecture → Planning → Implementation → Review → Verification → Testing → Iteration.

## Command Contract

- `/ai:commit` → stage + commit + push
- `/ai:commit --only` → stage + commit
- `/ai:pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/ai:pr --only` → create PR; warn if unpushed, propose auto-push
- `/ai:acho` → stage + commit + push
- `/ai:acho pr` → stage + commit + push + PR + auto-complete

## Progressive Disclosure

Progressive disclosure rules: `standards/framework/core.md`. Token budgets below are quick reference.

| Level | Budget |
|-------|--------|
| Session start | ~500 tokens |
| Single skill | ~2,050 tokens |
| Agent + 2 skills | ~3,200 tokens |
| Platform audit (8 dim) | ~12,950 tokens |

Schema: `.ai-engineering/standards/framework/skills-schema.md`. Organization: flat (no categories).

## Security & Quality

- Mandatory local hooks: `gitleaks`, `semgrep`, dependency checks, stack checks.
- No direct commits to main/master. No protected-branch push.
- Security findings require `state/decision-store.json` risk acceptance.

**Quality**: Coverage 90% (source: `standards/framework/quality/core.md`), duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical, 100% gate pass.

**Security**: Zero medium/high/critical findings, zero leaks, zero dependency vulns, hook hash verification, cross-OS enforcement.

## Tooling

`uv` (runtime) · `ruff` (lint/format) · `ty` (types) · `pip-audit` (deps)
