# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

## Required References

Read these before any non-trivial work:

- `.ai-engineering/context/product/framework-contract.md` — framework enforcement directives, agentic model, ownership, security/quality contract.
- `.ai-engineering/context/product/product-contract.md` — project goals, KPIs, roadmap, release status, governance surface, architecture snapshot.
- `.ai-engineering/standards/framework/core.md` — governance structure, ownership, lifecycle, skills/agents model.
- `.ai-engineering/standards/framework/stacks/python.md` — Python stack contract, code patterns, testing patterns.
- `.ai-engineering/standards/team/core.md` — team-specific standards.
- `.ai-engineering/context/specs/_active.md` — pointer to active spec.

## Session Start Protocol

Before any non-trivial implementation work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks files.
2. **Read decision store** — `.ai-engineering/state/decision-store.json` to avoid re-asking decided questions.
3. **Run pre-implementation** — execute `/pre-implementation` to sync the repository (git pull, prune, cleanup, create feature branch).
4. **Verify tooling** — confirm ruff, gitleaks, pytest, ty are available.

This protocol is mandatory. Skipping it risks working on stale code, repeating decided questions, or creating merge conflicts.

## Skills

50 procedural skills in `.ai-engineering/skills/<category>/<name>/SKILL.md`.
Categories: `workflows`, `dev`, `review`, `quality`, `govern`, `docs`.
Discover via `ls .ai-engineering/skills/*/` and SKILL.md frontmatter.

## Agents

19 agent personas in `.ai-engineering/agents/<name>.md`.
Discover via `ls .ai-engineering/agents/`.

## Command Contract

- `/commit` -> stage + commit + push
- `/commit --only` -> stage + commit
- `/pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` -> create PR; if branch is unpushed, warn and propose auto-push; if declined, continue with selected mode
- `/acho` -> stage + commit + push
- `/acho pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)

## Non-Negotiables

- Mandatory local gates cannot be bypassed.
- No direct commits to protected branches.
- Update safety must preserve team/project-owned content.
- Security findings cannot be dismissed without risk acceptance in `state/decision-store.json`.

## Validation Reminder

Before proposing merge:

- lint/format (`ruff`),
- tests (`pytest`),
- type checks (`ty`),
- security scans (`gitleaks`, `semgrep`, `pip-audit`).

## Quality Contract

- Coverage: 90%.
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
