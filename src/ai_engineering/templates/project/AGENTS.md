# CLAUDE.md — Claude Code Overlay

> See [AGENTS.md](./AGENTS.md) for the canonical cross-IDE rules (Step 0,
> available skills, agents, and the hard rules that delegate to
> [CONSTITUTION.md](./CONSTITUTION.md)). Read those first; this file
> only adds Claude-Code-specific specifics.

## Native Surface

- **Slash commands** — invoke skills via `/ai-<name>` in the Claude Code agent
  surface. Do not invent `ai-eng <skill>` terminal equivalents that are not
  listed in the CLI reference.
- **Skill location** — Claude Code project-scope skills live under
  `.codex/skills/` (one directory per skill, `SKILL.md` inside). User-scope
  copies live under `~/.codex/skills/` and are loaded as a fallback. The
  authoritative path is the one referenced from
  [AGENTS.md → Skills Available](./AGENTS.md#skills-available); see
  Article V of [CONSTITUTION.md](./CONSTITUTION.md) for the SSOT contract.
- **Subagents** — the dispatch surface is the 10 first-class agents listed in
  [AGENTS.md → Agents Available](./AGENTS.md#agents-available). Each runs in
  its own context window; offload research and parallel analysis to them.

## Hooks Configuration

Claude Code reads its hook wiring from `.claude/settings.json`:

- `UserPromptSubmit` runs the `/ai-*` dispatcher and emits `skill_invoked`
  telemetry events.
- `PostToolUse` runs the agent observability hooks (`agent_dispatched`,
  `ide_hook` events).
- All hook outcomes flow to `.ai-engineering/state/framework-events.ndjson`
  for the audit chain.

Hook scripts are hash-verified and the deny rules in `.claude/settings.json`
are tracked in source control — treat both as read-only at the IDE layer.

## Hot-Path Discipline

Claude Code triggers pre-commit and pre-push hooks on every save/commit, so
the local critical path must stay fast:

- **Pre-commit budget**: under 1 second wall-clock for the deterministic
  Layer-1 gate (lint, format check, secret scan on staged hunks only).
- **Pre-push budget**: under 5 seconds for the residual checks before the
  push pipeline takes over.
- Anything heavier (full test suite, dependency audit, governance
  evaluation) belongs in CI, not on the local hot path.

If a check exceeds budget, profile it and move work off the hot path before
adding new logic to the hook.

## Token Efficiency Tips

- Use `/clear` when context is no longer load-bearing rather than letting
  the conversation balloon — Claude Code keeps the full transcript in
  context until cleared.
- For deep codebase research, dispatch the `ai-explore` agent (read-only,
  fresh context) instead of having the main thread read the whole tree.
- Cite files with `startLine:endLine:filepath`; never paste large code
  blocks the user did not ask for.
- Treat `/ai-start` as the session bootstrap — it loads only what the
  current task needs and avoids re-reading already-loaded context.

## Observability

Telemetry is automatic — refer to
[AGENTS.md → Skills Available → `/ai-start`](./AGENTS.md#skills-available)
for the bootstrap that registers hooks. Session discovery and transcript
viewing are delegated to the separately installed `agentsview` companion
tool.
