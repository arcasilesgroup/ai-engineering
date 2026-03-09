# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Run cleanup** — sync repo (status, git pull, prune, branch cleanup).
4. **Verify tooling** — ruff, gitleaks, pytest, ty.

## Skills (35)

Path: `.ai-engineering/skills/<name>/SKILL.md` (flat organization)

| Skills (alphabetical) |
|-----------------------|
| a11y, api, architecture, build, changelog, cicd, cleanup, cli, code-simplifier, commit, create, db, debug, delete, discover, docs, explain, feature-gap, governance, infra, migrate, observe, perf, plan, pr, product-contract, quality, refactor, release, risk, security, spec, standards, test, work-item |

## Agents (7)

Path: `.ai-engineering/agents/<name>.md`

| Agent   | Purpose                                                       | Scope                        |
|---------|---------------------------------------------------------------|------------------------------|
| plan    | Planning pipeline, spec creation, execution plan — STOPS before execution | read-write |
| execute | Read approved plan, dispatch agents, coordinate, checkpoint, report | read-write |
| build   | Implementation across all stacks (ONLY code write agent)      | read-write                   |
| scan    | Assessment: security, quality, governance, architecture, perf | read-write (work items only) |
| release | ALM + GitOps: commit, PR, deploy, triage, changelog           | read-write                   |
| write   | Documentation, changelogs, explanations                       | read-write (docs only)       |
| observe | Observability: engineer, team, AI, DORA, health dashboards    | read-only                    |

## Command Contract

- `/ai:plan` → planning pipeline (classify → discover → risk → spec → execution plan → STOP)
- `/ai:plan --plan-only` → advisory only (discover → risk → recommend, zero writes)
- `/ai:execute` → read approved plan, dispatch agents, coordinate, report
- `/ai:commit` → stage + commit + push
- `/ai:commit --only` → stage + commit
- `/ai:pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/ai:pr --only` → create PR; warn if unpushed, propose auto-push

## Quality Contract

Coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical, 100% gate pass.

## Security Contract

Zero medium/high/critical findings, zero leaks, zero dependency vulns, hook hash verification, cross-OS enforcement.
