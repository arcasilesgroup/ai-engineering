# CLAUDE.md

## Workflow Orchestration

Enter plan mode for any non-trivial task (3+ steps). Think before you build.

Read the active spec before touching code: `.ai-engineering/context/specs/_active.md` and linked plan/tasks.
Read the decision store to avoid repeating settled questions: `.ai-engineering/state/decision-store.json`.

If something goes sideways -- stop, re-read context, re-plan. Do not push through a broken approach.

**Subagent strategy.** Offload research to subagents. One task per subagent, clear deliverable.
Never have a subagent do two unrelated things.

**Self-improvement loop.** After ANY correction from the user -- whether about code style, architecture,
process, or tooling -- update `tasks/lessons.md` immediately. Same mistake twice is unacceptable.

**Verification before done.** Run the tests. Run the linter. Check the output.
Prove it works before claiming "done." If you cannot prove it, say so.

**Demand elegance.** For non-trivial changes, ask yourself: "is there a more elegant way?"
Clever is bad. Simple and clear is elegant.

**Autonomous bug fixing.** If you see a bug while working on something else -- fix it.
No hand-holding, no "I noticed a potential issue." Just fix it and mention it in the commit.

**Parallel execution.** Batch independent operations into simultaneous tool calls.
Never go sequential when you can go parallel.

**Context efficiency.** Never re-read files already in context. Never dump code the user did not ask for.
Use `startLine:endLine:filepath` to cite. Use `// ... existing code ...` for omissions.

**Proactive memory.** Read/write `state/decision-store.json` to persist learnings across sessions.

## Agent Selection

| Task | Agent | Invoke |
|------|-------|--------|
| Planning, specs, architecture | plan | `/ai-brainstorm` |
| Writing/editing code | build | `/ai-dispatch` (after plan) |
| Quality + security scanning | verify | `/ai-verify` |
| Governance, compliance | guard | `/ai-governance` |
| Code review (parallel agents) | review | `/ai-review` |
| Deep codebase research | explore | direct dispatch |
| Onboarding, teaching | guide | `/ai-guide` |
| Simplify/refactor code | simplify | `/ai-simplify` |

## Core Skills

These auto-trigger in the standard workflow. You rarely invoke them directly.

| Skill | Triggers when |
|-------|---------------|
| `/ai-plan` | Any task requiring architecture or multi-step coordination |
| `/ai-dispatch` | Approved plan ready for execution |
| `/ai-commit` | Code changes ready to stage and commit |
| `/ai-pr` | Branch ready for pull request |
| `/ai-guard` | Pre-commit governance check (automatic via hooks) |
| `/ai-test` | Implementation complete, needs verification |
| `/ai-verify` | Quality/security scanning before merge |

Full skill catalog: `.claude/skills/ai-<name>/SKILL.md` -- 34 framework skills + repo-specific extras.

## Task Management

Track progress in `tasks/todo.md`. Mark items done as you complete them.
Record learnings in `tasks/lessons.md` -- especially corrections, gotchas, and patterns.
These files are your working memory across sessions.

## Don't

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip or silence a failing gate -- fix the root cause.
3. **NEVER** weaken gate severity or coverage thresholds.
4. **NEVER** modify hook scripts -- they are hash-verified.
5. **NEVER** push to protected branches (main, master).
6. **NEVER** dismiss security findings without `state/decision-store.json` risk acceptance.
7. **NEVER** disable or modify `.claude/settings.json` deny rules.
8. **NEVER** add suppression comments (`# noqa`, `# nosec`, `# type: ignore`, `# pragma: no cover`, `# NOSONAR`, `// nolint`) to bypass quality gates. Fix the code. If it is a false positive, refactor to satisfy the analyzer or escalate with a full explanation.

Gate failure: diagnose, fix, retry. Use `ai-eng doctor --fix-tools` or `--fix-hooks`.

## Quality Gates

| Metric | Threshold |
|--------|-----------|
| Test coverage | >= 80% |
| Code duplication | <= 3% |
| Cyclomatic complexity | <= 10 per function |
| Cognitive complexity | <= 15 per function |
| Blocker/critical issues | 0 |
| Security findings (medium+) | 0 |
| Secret leaks | 0 |
| Dependency vulnerabilities | 0 |

Tooling: `ruff` + `ty` (lint/format), `pytest` (test), `gitleaks` (secrets), `pip-audit` (deps).

## Observability

Telemetry is automatic via hooks -- no manual `ai-eng signals emit` needed.
- `PostToolUse(Skill)` hook emits `skill_invoked` events
- `Stop` hook emits `session_end` events
- All events flow to `.ai-engineering/state/audit-log.ndjson`
- Dashboards: `ai-eng observe [engineer|team|ai|dora|health]`

## Source of Truth

| What | Where |
|------|-------|
| Skills (34+) | `.claude/skills/ai-<name>/SKILL.md` |
| Agents (8) | `.claude/agents/ai-<name>.md` |
| Config | `.ai-engineering/manifest.yml` |
| Governance | `.ai-engineering/context/product/framework-contract.md` |
| Product context | `.ai-engineering/context/product/product-contract.md` |
| CLI | `ai-eng <command>` -- see `product-contract.md` section 2.2 |
