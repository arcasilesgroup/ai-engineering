# Governance Source

Canonical governance document. All IDE-specific instruction files (CLAUDE.md, AGENTS.md, GEMINI.md, .github/copilot-instructions.md) derive from this source. When content diverges, this file is authoritative.

Validate consistency: `ai-eng governance diff`.

## Source of Truth

- Governance rules: `.ai-engineering/context/product/framework-contract.md`
- Product context: `.ai-engineering/context/product/product-contract.md`
- Contract: `.ai-engineering/manifest.yml`

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Load checkpoint** — `ai-eng checkpoint load` for session recovery.
4. **Run cleanup** — sync repo (status, git pull, prune, branch cleanup).
5. **Verify tooling** — ruff, gitleaks, pytest, ty.

Mandatory. Skipping risks stale code, repeated decisions, or merge conflicts.

## Absolute Prohibitions

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip/silence a failing gate — fix root cause.
3. **NEVER** weaken gate severity.
4. **NEVER** modify hook scripts — hash-verified.
5. **NEVER** push to protected branches (main, master).
6. **NEVER** dismiss security findings without `state/decision-store.json` risk acceptance.
7. **NEVER** use destructive git commands unless user explicitly requests.
8. **NEVER** add suppression comments (`# NOSONAR`, `# nosec`, `# type: ignore`, `# pragma: no cover`, `# noqa`, `// nolint`) to bypass static analysis, security scanners, or quality gates. Fix the root cause.

Gate failure: diagnose → fix → retry. Use `ai-eng doctor --fix-tools` or `--fix-hooks`.

## Skills (40)

Path: `.ai-engineering/skills/<name>/SKILL.md` — slash commands: `/ai:<name>`

a11y, api, architecture, build, changelog, cicd, cleanup, cli, code-simplifier, commit, create, db, debug, delete, discover, docs, explain, feature-gap, governance, infra, migrate, observe, perf, plan, pr, product-contract, quality, refactor, release, risk, security, spec, standards, test, work-item

## Agents (10)

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

## On-Demand Context Loading

Before planning or creating specs: read `product-contract.md` §7 (roadmap, KPIs, blockers).
Before governance decisions: read `framework-contract.md` §2-3 (agentic model, ownership).
For skills/agents/CLI reference: read `product-contract.md` §2.2.
For commands/pipelines: read `framework-contract.md` §5.

## Quick Reference

- Skills (40): `.ai-engineering/skills/<name>/SKILL.md` — slash commands: `/ai:<name>`
- Agents (10): `.ai-engineering/agents/<name>.md`
- CLI: `ai-eng <command>` — deterministic tasks, zero AI tokens
- Quality: coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical
- Security: zero medium+ findings, zero leaks, zero dependency vulns
- Tooling: `uv` · `ruff` · `ty` · `pip-audit`

## IDE Projection Map

| IDE | File | Key Additions |
|-----|------|---------------|
| Claude Code | `CLAUDE.md` | .claude/settings.json deny rules, checkpoint load |
| GitHub Copilot | `.github/copilot-instructions.md` | Spec-as-Gate via CLI pipe pattern |
| Gemini CLI | `GEMINI.md` | Full skill/agent tables, progressive disclosure |
| All agents | `AGENTS.md` | Behavior mandates, platform adaptors, runbooks |
