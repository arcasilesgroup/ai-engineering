# AGENTS.md

Multi-IDE instruction file. Consumed by GitHub Copilot, Codex, Gemini CLI, and other AI coding assistants.
This file is self-contained -- no other instruction files are required.

## Source of Truth

Config: `.ai-engineering/manifest.yml`. Decisions: `.ai-engineering/state/decision-store.json`.
Contexts: `.ai-engineering/contexts/` (languages, frameworks, team).

## Before You Start

1. Read the active spec: `.ai-engineering/specs/_active.md` and linked plan/tasks.
2. Read the decision store: `.ai-engineering/state/decision-store.json`.
3. Load checkpoint if resuming: `ai-eng checkpoint load`.
4. Verify tooling is available: ruff, gitleaks, pytest, ty.

## Workflow Orchestration

Enter plan mode for any non-trivial task (3+ steps). Think before you build.

Read the active spec before touching code: `.ai-engineering/specs/_active.md` and linked plan/tasks.
Read the decision store to avoid repeating settled questions: `.ai-engineering/state/decision-store.json`.

If something goes sideways -- stop, re-read context, re-plan. Do not push through a broken approach.

**Subagent strategy.** Offload research to subagents. One task per subagent, clear deliverable.
Never have a subagent do two unrelated things.

**Self-improvement loop.** After ANY correction from the user -- whether about code style, architecture,
process, or tooling -- update `tasks/lessons.md` immediately. Same mistake twice is unacceptable.

**Verification before done.** Run the tests. Run the linter. Check the output.
Prove it works before claiming "done." If you cannot prove it, say so.

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

## Platform Mirrors

Each IDE has its own skill and agent files. Same content, platform-native format.

| Platform | Skills | Agents |
|----------|--------|--------|
| Claude Code | `.claude/skills/ai-*/SKILL.md` | `.claude/agents/ai-*.md` |
| GitHub Copilot | `.github/prompts/ai-*.prompt.md` | `.github/agents/*.agent.md` |
| Codex / Gemini | `.agents/skills/*/SKILL.md` | `.agents/agents/ai-*.md` |

## Skills (34)

Grouped by workflow phase. Invoke as `/ai-<name>`.

**Plan:** plan, spec, architecture, contract, schema
**Build:** code, api, infra, pipeline, migrate, refactor, simplify
**Test:** test, debug, gap, performance, accessibility
**Ship:** commit, pr, release, lifecycle
**Observe:** dashboard, ops, triage, integrity, evolve
**Govern:** governance, guard, security, verify, quality
**Learn:** document, explain, dispatch, cleanup

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
