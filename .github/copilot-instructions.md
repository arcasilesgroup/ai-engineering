# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Run cleanup** — sync repo (status, git pull, prune, branch cleanup).
4. **Verify tooling** — ruff, gitleaks, pytest, ty.

## Skills (47)

Path: `.ai-engineering/skills/<name>/SKILL.md` (flat organization)

| Skills (alphabetical) |
|-----------------------|
| a11y, agent-card, agent-lifecycle, api, arch-review, audit, changelog, cicd, cleanup, cli, code-review, commit, compliance, data-model, db, debug, deps, discover, docs, docs-audit, explain, improve, infra, install, integrity, migrate, multi-agent, ownership, perf-review, pr, prompt, refactor, release, risk, sbom, sec-deep, sec-review, simplify, skill-lifecycle, sonar, spec, standards, test-gap, test-plan, test-run, triage, work-item |

## Agents (6)

Path: `.ai-engineering/agents/<name>.md`

| Agent | Purpose | Scope |
|-------|---------|-------|
| plan | Orchestration, planning pipeline, dispatch, work-item sync | read-write |
| build | Implementation across all stacks (ONLY code write agent) | read-write |
| review | All reviews, security, quality, governance (individual modes) | read-only |
| scan | Spec-vs-code gap analysis, architecture drift detection | read-only |
| write | Documentation, changelogs, explanations | read-write (docs only) |
| triage | Auto-prioritize work items, backlog grooming | read-write (work items only) |

## Command Contract

- `/commit` → stage + commit + push
- `/commit --only` → stage + commit
- `/pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` → create PR; warn if unpushed, propose auto-push
- `/acho` → stage + commit + push
- `/acho pr` → stage + commit + push + PR + auto-complete

## Quality Contract

Coverage 90%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical, 100% gate pass.

## Security Contract

Zero medium/high/critical findings, zero leaks, zero dependency vulns, hook hash verification, cross-OS enforcement.
