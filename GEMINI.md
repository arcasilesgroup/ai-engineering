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

## Skills (34)

Path: `.ai-engineering/skills/<name>/SKILL.md` (flat organization, no category subdirectories)

| Skills (alphabetical) |
|-----------------------|
| a11y, api, architecture, build, changelog, cicd, cleanup, cli, code-simplifier, commit, create, db, debug, delete, discover, docs, explain, feature-gap, governance, infra, migrate, observe, perf, plan, pr, quality, refactor, release, risk, security, spec, standards, test, work-item |

## Agents (7)

Path: `.ai-engineering/agents/<name>.md`

| Agent | Purpose | Scope |
|-------|---------|-------|
| plan | Planning pipeline, spec creation, execution plan — stops before execution | read-write |
| execute | Read approved plan, dispatch agents, coordinate, checkpoint, report | read-write |
| build | Implementation across all stacks (ONLY code write agent) | read-write |
| scan | 7-mode assessment: governance, security, quality, perf, a11y, feature, architecture | read-write (work items only) |
| release | ALM lifecycle: commit, PR, release gate, triage, work-items, deploy | read-write |
| write | Documentation (generate/simplify modes) | read-write (docs only) |
| observe | Observability: 5 modes across 4 audience tiers + DORA metrics + health scoring | read-only |

## Lifecycle

Discovery → Architecture → Planning → Implementation → Scan → Release Gate → Deploy → Observe → Feedback.

## Command Contract

- `/ai:plan` → planning pipeline (classify → discover → risk → spec → execution plan → STOP)
- `/ai:execute` → read approved plan, dispatch agents, coordinate, report
- `/ai:commit` → stage + commit + push
- `/ai:commit --only` → stage + commit
- `/ai:pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/ai:pr --only` → create PR; warn if unpushed, propose auto-push

## Progressive Disclosure

Three-level loading: **Metadata** (always, ~50 tok/skill) → **Body** (on-demand) → **Resources** (on-demand).

Session start loads ONLY: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`. Do NOT pre-load skills or agents.

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
