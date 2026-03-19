# CLAUDE.md

Operational guide for Claude Code sessions. Conflicts with `.ai-engineering/**` → follow `.ai-engineering/**`.

## Source of Truth

- Governance rules: `.ai-engineering/context/product/framework-contract.md`
- Product context: `.ai-engineering/context/product/product-contract.md`
- Contract: `.ai-engineering/manifest.yml`

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/specs/_active.md` and linked spec/plan/tasks.
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
9. **NEVER** add suppression comments (`# NOSONAR`, `# nosec`, `# type: ignore`, `# pragma: no cover`, `# noqa`, `// nolint`) to bypass static analysis, security scanners, or quality gates. Fix the root cause. If a finding is a false positive, refactor the code to satisfy the analyzer or escalate to the user with a full explanation of why it fails and why it's safe.

Gate failure: diagnose → fix → retry. Use `ai-eng doctor --fix-tools` or `--fix-hooks`.

## On-Demand Context Loading

Before planning or creating specs: read `product-contract.md` §7 (roadmap, KPIs, blockers).
Before governance decisions: read `framework-contract.md` §2-3 (agentic model, ownership).
For skills/agents/CLI reference: read `product-contract.md` §2.2.
For commands/pipelines: read `framework-contract.md` §5.

## Observability

Telemetry is **automatic via hooks** — no manual `ai-eng signals emit` needed in Claude Code.
- `PostToolUse(Skill)` hook emits `skill_invoked` events automatically
- `Stop` hook emits `session_end` events automatically
- All events → `.ai-engineering/state/audit-log.ndjson`
- Dashboards: `ai-eng observe [engineer|team|ai|dora|health]`

## Quick Reference

- Skills (34): `.claude/skills/ai-<name>/SKILL.md` — slash commands: `/ai-<name>`
- Agents (8): `.claude/agents/ai-<name>.md`
- CLI: `ai-eng <command>` — see `product-contract.md` §2.2 for full table
- Quality: coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15, zero blocker/critical
- Security: zero medium+ findings, zero leaks, zero dependency vulns
- Tooling: `uv` · `ruff` · `ty` · `pip-audit`
