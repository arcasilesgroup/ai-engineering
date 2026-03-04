# CLAUDE.md

Operational guide for assistant sessions. Conflicts with `.ai-engineering/**` → follow `.ai-engineering/**`.

## Source of Truth

- Governance: `.ai-engineering/` — contract: `manifest.yml`, context: `context/**`.

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Load checkpoint** — `ai-eng checkpoint load` for session recovery.
4. **Run cleanup** — `/cleanup` to sync repo.
5. **Verify tooling** — ruff, gitleaks, pytest, ty.

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

| Domain | Skills |
|--------|--------|
| Planning | discover, spec, cleanup, explain |
| Build | build, test, debug, refactor, code-simplifier, api, cli, db, infra, cicd, migrate |
| Scan | security, quality, governance, architecture, perf, a11y, feature-gap |
| Release | commit, pr, release, changelog, work-item |
| Write | docs |
| Observe | observe |
| Governance | risk, standards, create, delete |

Slash commands (`.claude/commands/ai/`): `/ai:<name>` for all skills and agents.

## Agents (6)

Path: `.ai-engineering/agents/<name>.md`

| Agent | Purpose | Scope |
|-------|---------|-------|
| plan | Orchestration, pipeline strategy, session recovery, governance lifecycle | read-write |
| build | Implementation across 20 stacks (ONLY code write agent) | read-write |
| scan | 7-mode assessment: governance, security, quality, perf, a11y, feature, architecture | read-write (work items only) |
| release | ALM lifecycle: commit, PR, release gate, triage, work-items, deploy | read-write |
| write | Documentation (generate/simplify modes) | read-write (docs only) |
| observe | Observability for 3 audiences + DORA metrics + health scoring | read-only |

## Lifecycle

Discovery → Architecture → Planning → Implementation → Scan → Release Gate → Deploy → Observe → Feedback.

## Command Contract

- `/ai:commit` → stage + commit + push
- `/ai:commit --only` → stage + commit
- `/ai:pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/ai:pr --only` → create PR; warn if unpushed, propose auto-push
- `/ai:acho` → stage + commit + push
- `/ai:acho pr` → stage + commit + push + PR + auto-complete

## Pipeline Strategy

Auto-classified from `git diff --stat` + change type. User override: `/ai:plan --pipeline=<type>`.

| Pipeline | When | Steps |
|----------|------|-------|
| full | Features, refactors, >3 files | discover → architecture → risk → spec → dispatch |
| standard | Enhancements, 3-5 files | discover → risk → spec → dispatch |
| hotfix | Bug fixes, <3 files | discover → risk → dispatch |
| trivial | Typos, single-line | dispatch |

## Python CLI (`ai-eng`)

Deterministic tasks run locally without AI tokens (~38% savings):

| Command | What |
|---------|------|
| `ai-eng observe [mode]` | Dashboards: engineer, team, ai, dora, health |
| `ai-eng gate pre-commit\|pre-push` | Run quality gate checks |
| `ai-eng signals emit\|query` | Event store operations |
| `ai-eng checkpoint save\|load` | Session recovery |
| `ai-eng decision list\|expire-check` | Decision store management |

## Progressive Disclosure

Progressive disclosure rules: `standards/framework/core.md`. Token budgets below are quick reference.

| Level | Budget |
|-------|--------|
| Session start | ~500 tokens |
| Single skill | ~2,050 tokens |
| Agent + 2 skills | ~3,200 tokens |
| Platform audit (7 dim) | ~10,500 tokens |

Schema: `.ai-engineering/standards/framework/skills-schema.md`. Organization: flat (no categories).

## Security & Quality

- Mandatory local hooks: `gitleaks`, `semgrep`, dependency checks, stack checks.
- No direct commits to main/master. No protected-branch push.
- Security findings require `state/decision-store.json` risk acceptance.

**Quality**: Coverage 90% (source: `standards/framework/quality/core.md`), duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical, 100% gate pass.

**Security**: Zero medium/high/critical findings, zero leaks, zero dependency vulns, hook hash verification, cross-OS enforcement.

## Tooling

`uv` (runtime) · `ruff` (lint/format) · `ty` (types) · `pip-audit` (deps)
