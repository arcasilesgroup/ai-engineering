# GEMINI.md — Gemini CLI Overlay

> See [AGENTS.md](AGENTS.md) for the canonical cross-IDE rules (Step 0,
> available skills, agents, and the hard rules that delegate to
> [CONSTITUTION.md](CONSTITUTION.md)). Read those first; this file
> only adds Gemini-CLI-specific specifics.

## FIRST ACTION -- Mandatory

Your first action in every session MUST be to run `/ai-start`.
Do not respond to any user request until `/ai-start` completes.
`/ai-start` and the rest of `/ai-*` are slash commands in the IDE agent surface, not terminal commands.
Do not invent `ai-eng <skill>` equivalents unless the CLI reference explicitly lists them.

> Operating-behaviour rules 1-7 (Plan Mode Default, Subagent Strategy,
> Self-Improvement Loop, Verification Before Done, Demand Elegance,
> Autonomous Bug Fixing, Parallel Execution) live in
> [CONSTITUTION.md → Article XI](CONSTITUTION.md#article-xi--operating-behaviour-cross-ide).
> They apply to **every** supported IDE; do not duplicate them here.

### 8. Context Efficiency

- Never re-read files already in context. Never dump code the user did not ask for
- Use `startLine:endLine:filepath` to cite. Use `// ... existing code ...` for omissions

### 9. Proactive Memory

- Read/write `.ai-engineering/LESSONS.md` to persist learnings across sessions

### 10. Context Loading

Before writing or reviewing code, load the applicable context files:
1. Detect the project's languages from file extensions and build config
2. Read `.ai-engineering/contexts/languages/{language}.md` for each detected language
3. Read `.ai-engineering/contexts/frameworks/{framework}.md` for each detected framework
4. Read shared framework contexts when relevant: `.ai-engineering/contexts/cli-ux.md` for CLI work and `.ai-engineering/contexts/mcp-integrations.md` for MCP/server usage
5. Read `.ai-engineering/contexts/team/*.md` for team conventions
6. Apply loaded standards to all code generation and review

## Task Management

1. **Plan First**: Write plan via `/ai-plan` to `.ai-engineering/specs/plan.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete in `.ai-engineering/specs/plan.md` as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review to the spec tasks file
6. **Capture Lessons**: Update `.ai-engineering/LESSONS.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
- **Cross-Platform**: All generated code, scripts, and paths must work on Windows, macOS, and Linux. Use platform-agnostic idioms. No OS-specific assumptions without explicit fallbacks.

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
| Simplify/refactor code | simplify | direct dispatch |
| Multi-spec autonomous execution | autopilot | `/ai-autopilot` |
| Autonomous backlog execution | run-orchestrator | `/ai-run` |

## Agents (11)

The agents table above lists every agent shipped with the framework. Counts mirror `.ai-engineering/manifest.yml` (`agents.total`).

## Skills (52)

Grouped by type. Invoke as `/ai-<name>`.

__SKILL_GROUPS__

## Effort Levels

Each skill declares `effort` in frontmatter. Assignment by cognitive weight:

| Effort | Count |
|--------|-------|
__EFFORT_ROWS__

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

Telemetry is automatic via hooks and writes only canonical framework events.
- `BeforeAgent(/ai-*)` hook emits `skill_invoked` events
- `AfterTool` agent hooks emit `agent_dispatched` and `ide_hook` events
- Hook, gate, governance, security, and quality outcomes flow to `.ai-engineering/state/framework-events.ndjson`
- Registered skills, agents, contexts, and hooks are catalogued in `.ai-engineering/state/framework-capabilities.json`
- Session discovery and transcript viewing are delegated to separately installed `agentsview`

## Hard Rules

The non-negotiable rules live in [CONSTITUTION.md](CONSTITUTION.md), with the
canonical cross-IDE summary in [AGENTS.md](AGENTS.md). Do not restate them
here — read those first. This overlay only adds Gemini-CLI-specific notes
below.

Gate failure: diagnose, fix, retry. Use `ai-eng doctor --fix` or `ai-eng doctor --fix --phase <name>`.

## Source of Truth

| What | Where |
|------|-------|
| Skills (52) | `.gemini/skills/ai-<name>/SKILL.md` |
| Agents (11) | `.gemini/agents/ai-<name>.md` |
| Config | `.ai-engineering/manifest.yml` |
| Decisions | `.ai-engineering/state/decision-store.json` |
| Active spec | `.ai-engineering/specs/spec.md` |
| Contexts | `.ai-engineering/contexts/languages/`, `frameworks/`, `team/` |
| Lessons | `.ai-engineering/LESSONS.md` |
| CLI | `ai-eng <command>` |
