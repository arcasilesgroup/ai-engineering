# CLAUDE.md

Multi-IDE instruction file. Consumed by Claude Code, GitHub Copilot, Codex, Gemini CLI, and other AI coding assistants.
This file is self-contained -- no other instruction files are required.

## Workflow Orchestration

Read the active spec before touching code: `.ai-engineering/specs/spec.md` and `.ai-engineering/specs/plan.md`.
Read the decision store to avoid repeating settled questions: `.ai-engineering/state/decision-store.json`.

### 1. Plan Mode Default

- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately -- don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity via `/ai-brainstorm`

### 2. Subagent Strategy

- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution
- Never have a subagent do two unrelated things

### 3. Self-Improvement Loop

- After ANY correction from the user: update `.ai-engineering/contexts/team/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start: read `.ai-engineering/contexts/team/lessons.md` proactively

### 4. Verification Before Done

- Never mark a task complete without proving it works
- Run the tests. Run the linter. Check the output
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"

### 5. Demand Elegance (Balanced)

- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes -- don't over-engineer
- Clever is bad. Simple and clear is elegant

### 6. Autonomous Bug Fixing

- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -- then resolve them
- If you see a bug while working on something else -- fix it and mention it in the commit
- Zero context switching required from the user

### 7. Parallel Execution

- Batch independent operations into simultaneous tool calls
- Never go sequential when you can go parallel

### 8. Context Efficiency

- Never re-read files already in context. Never dump code the user did not ask for
- Use `startLine:endLine:filepath` to cite. Use `// ... existing code ...` for omissions

### 9. Proactive Memory

- Read/write `.ai-engineering/contexts/team/lessons.md` to persist learnings across sessions

## Task Management

1. **Plan First**: Write plan via `/ai-plan` to `.ai-engineering/specs/plan.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete in `.ai-engineering/specs/plan.md` as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review to the spec tasks file
6. **Capture Lessons**: Update `.ai-engineering/contexts/team/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

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
| Multi-spec autonomous execution | autopilot | `/ai-autopilot` |

## Platform Mirrors

Each IDE has its own skill and agent files. Same content, platform-native format.

| Platform | Skills | Agents |
|----------|--------|--------|
| Claude Code | `.claude/skills/ai-*/SKILL.md` | `.claude/agents/ai-*.md` |
| GitHub Copilot | `.github/skills/ai-*/SKILL.md` | `.github/agents/*.agent.md` |
| Codex / Gemini | `.agents/skills/*/SKILL.md` | `.agents/agents/ai-*.md` |

## Skills (37)

Grouped by type. Invoke as `/ai-<name>`.

**Workflow:** brainstorm, plan, dispatch, test, debug, verify, review, eval
**Delivery:** commit, pr, release, cleanup
**Enterprise:** security, governance, pipeline, schema, solution-intent
**Teaching:** explain, guide, write, slides, media, video-editing
**SDLC:** note, standup, sprint, sprint-review, postmortem, support, resolve-conflicts
**Meta:** create, learn, prompt, onboard, analyze-permissions, instinct, autopilot

## Effort Levels

Each skill declares `effort` in frontmatter. Assignment by cognitive weight:

| Effort | Count |
|--------|-------|
| max | 11 (brainstorm, plan, review, verify, security, debug, governance, schema, instinct, eval, autopilot) |
| high | 15 (dispatch, test, write, explain, guide, pr, solution-intent, support, postmortem, pipeline, create, prompt, slides, media, video-editing) |
| medium | 11 (commit, cleanup, standup, note, onboard, release, resolve-conflicts, sprint, sprint-review, learn, analyze-permissions) |

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
- `UserPromptSubmit(/ai-*)` hook emits `skill_invoked` events
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

Gate failure: diagnose, fix, retry. Use `ai-eng doctor --fix` or `ai-eng doctor --fix --phase <name>`.

## Source of Truth

| What | Where |
|------|-------|
| Skills (37) | `.claude/skills/ai-<name>/SKILL.md` |
| Agents (9) | `.claude/agents/ai-<name>.md` |
| Config | `.ai-engineering/manifest.yml` |
| Decisions | `.ai-engineering/state/decision-store.json` |
| Active spec | `.ai-engineering/specs/spec.md` |
| Contexts | `.ai-engineering/contexts/languages/`, `frameworks/`, `team/` |
| Lessons | `.ai-engineering/contexts/team/lessons.md` |
| CLI | `ai-eng <command>` |
