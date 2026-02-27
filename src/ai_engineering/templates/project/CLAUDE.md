# CLAUDE.md

This file is a quick operational guide for assistant sessions in this repo.

## Source of Truth

- Primary governance source: `.ai-engineering/`.
- Canonical contract: `.ai-engineering/manifest.yml`.
- Delivery context: `.ai-engineering/context/**`.

If this file conflicts with `.ai-engineering/**`, follow `.ai-engineering/**`.

## Session Start Protocol

Before any non-trivial implementation work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks files.
2. **Read decision store** — `.ai-engineering/state/decision-store.json` to avoid re-asking decided questions.
3. **Run pre-implementation** — execute `/pre-implementation` to sync the repository (git pull, prune, cleanup, create feature branch).
4. **Verify tooling** — confirm ruff, gitleaks, pytest, ty are available.

This protocol is mandatory. Skipping it risks working on stale code, repeating decided questions, or creating merge conflicts.

## Absolute Prohibitions for AI Agents

The following actions are strictly forbidden. Violating any of these is a governance violation:

1. **NEVER use `--no-verify`** on any git command (commit, push, merge, rebase).
2. **NEVER skip or silence a failing gate check** — fix the root cause instead.
3. **NEVER weaken gate severity** (change required to optional, remove tools from registries).
4. **NEVER modify hook scripts manually** — they are hash-verified.
5. **NEVER push to protected branches** (main, master) directly.
6. **NEVER dismiss security findings** without formal risk acceptance in `state/decision-store.json`.
7. **NEVER disable or modify `.claude/settings.json` deny rules**.
8. **NEVER use destructive git commands** (`git reset --hard`, `git clean -f`, `git push --force`) unless the user explicitly requests it.

If a gate fails: diagnose the root cause, fix it, then retry. Use `ai-eng doctor --fix-tools` or `ai-eng doctor --fix-hooks` for automated remediation.

## Required References

Read these before any non-trivial work:

- `.ai-engineering/context/product/framework-contract.md` — framework identity, personas, roadmap.
- `.ai-engineering/context/product/product-contract.md` — project goals, KPIs, release status.
- `.ai-engineering/standards/framework/core.md` — governance structure, ownership, lifecycle, skills/agents model.
- `.ai-engineering/standards/framework/stacks/python.md` — Python stack contract, code patterns, testing patterns.
- `.ai-engineering/standards/team/core.md` — team-specific standards.
- `.ai-engineering/context/specs/_active.md` — pointer to active spec.

## Skills

Procedural skills in `.ai-engineering/skills/<category>/<name>/SKILL.md`.
Categories: `workflows`, `dev`, `review`, `quality`, `govern`, `docs`.

Key workflow skills:

- `.ai-engineering/skills/workflows/commit/SKILL.md` — governed commit flow.
- `.ai-engineering/skills/workflows/pr/SKILL.md` — governed PR flow.
- `.ai-engineering/skills/workflows/acho/SKILL.md` — `/acho` alias.
- `.ai-engineering/skills/workflows/pre-implementation/SKILL.md` — branch hygiene.
- `.ai-engineering/skills/workflows/cleanup/SKILL.md` — branch cleanup.
- `.ai-engineering/skills/workflows/self-improve/SKILL.md` — iterative improvement loop.

All other skills (44) discoverable via `ls .ai-engineering/skills/*/` and SKILL.md frontmatter.

## Slash Commands

All 50 skills and 19 agents are available as slash commands via `.claude/commands/`. Pattern: `/<category>:<name>` for skills, `/agent:<name>` for agents. Each is a thin wrapper pointing to the canonical source (decision S0-008). Mirrors in `.github/prompts/` and `.github/agents/` are managed by `scripts/sync_command_mirrors.py`.

## Agents

19 agent personas in `.ai-engineering/agents/<name>.md`. Discover via `ls .ai-engineering/agents/`. Activate with `/agent:<name>`.

## Mandatory Lifecycle

Follow this sequence for non-trivial work:

1. Discovery
2. Architecture
3. Planning
4. Implementation
5. Review
6. Verification
7. Testing
8. Iteration

## Command Contract

- `/commit` -> stage + commit + push current branch
- `/commit --only` -> stage + commit
- `/pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` -> create PR; if branch is unpushed, warn and propose auto-push; if declined, continue with selected mode
- `/acho` -> stage + commit + push current branch
- `/acho pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)

## Progressive Disclosure

Skills and agents use a three-level loading model to minimize token overhead:

1. **Metadata** (name + description) — always available. ~50 tokens per skill.
2. **Body** (SKILL.md content) — loaded on-demand when the skill is invoked.
3. **Resources** (scripts/, references/, assets/) — loaded only when the AI needs them during execution.

### Loading Rules

- At session start, load ONLY: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`.
- Do NOT pre-load skill bodies or agent personas at session start.
- Load a skill body when: the user invokes a slash command, OR the agent determines the skill is needed for the current task.
- Load references/ files selectively by section heading — do not load entire reference files.
- Scripts in scripts/ are executed directly, not loaded into context (unless patching is needed).
- Assets in assets/ are copied or modified, never read into context.

### Skill Directory Structure

Each skill is a directory:

```
skills/<category>/<name>/
├── SKILL.md              (instructions with YAML frontmatter)
├── scripts/              (deterministic executable scripts)
├── references/           (on-demand reference docs)
└── assets/               (templates, resources for output)
```

Categories: `workflows`, `dev`, `review`, `quality`, `govern`, `docs`.

### Token Budget Targets

| Level | When Loaded | Budget |
|-------|-------------|--------|
| Session start (spec work) | Always | ~500 tokens |
| Single skill invocation | On-demand | ~2,050 tokens |
| Agent + 2 skills | On-demand | ~3,200 tokens |
| Platform audit (8 dimensions) | Serial on-demand | ~12,950 tokens |

For full schema details: `.ai-engineering/standards/framework/skills-schema.md`.

## Security and Quality Rules

- Local hooks are mandatory in governed flows.
- Required checks: `gitleaks`, `semgrep`, dependency vulnerability checks, and stack checks.
- No direct commits to `main`/`master`.
- No protected-branch push in governed commit flows.
- No unsafe remote execution from skill sources.
- Security findings cannot be dismissed without `state/decision-store.json` risk acceptance.

## Quality Contract

- Coverage: 90% (source of truth: `standards/framework/quality/core.md`).
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

## Tooling Baseline

- Runtime/package tooling: `uv`
- Lint/format: `ruff`
- Type checking: `ty`
- Dependency vulnerability checks: `pip-audit`

## Risk Decision Reuse

- Write accepted risk decisions to `.ai-engineering/state/decision-store.json`.
- Append governance events to `.ai-engineering/state/audit-log.ndjson`.
- Before asking a repeated risk question, read decision-store first.

## Work Logging Requirement

For each execution block, follow active spec via `.ai-engineering/context/specs/_active.md`.

Each governance doc update must include:

- rationale
- expected gain
- potential impact
