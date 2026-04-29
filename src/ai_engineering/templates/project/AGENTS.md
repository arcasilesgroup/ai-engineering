# AGENTS.md — Canonical Cross-IDE Rulebook

> Hard rules live in [CONSTITUTION.md](CONSTITUTION.md). This file is
> the canonical multi-IDE entry point and source of truth for skills,
> agents, and IDE surfaces. IDE-specific overlays (CLAUDE.md,
> GEMINI.md, .github/copilot-instructions.md) delegate to this file.

## Step 0 — First Action

Every session, the first action is:

1. Read [CONSTITUTION.md](CONSTITUTION.md) (non-negotiable rules).
2. Read `.ai-engineering/manifest.yml` (configuration source of truth).
3. No implementation without an approved spec — invoke `/ai-brainstorm`
   first when a task has no spec.

## Skills (49)

The full registry is in `.ai-engineering/manifest.yml` under
`skills.registry`. Each skill is documented at
`.codex/skills/ai-<name>/SKILL.md` and mirrored to other IDE surfaces.

Invoke skills via `/ai-<name>` in the IDE agent surface (slash command).
Do not invent `ai-eng <skill>` terminal equivalents unless the CLI
reference explicitly lists them.

## Agents (10)

The 10 first-class agents are listed in
`.ai-engineering/manifest.yml` under `agents.registry` and documented at
`.codex/agents/ai-<name>.md`. Each runs in its own context window;
offload research and parallel analysis to them.

## Hard Rules

The non-negotiable rules are in [CONSTITUTION.md](CONSTITUTION.md).
Read them before any commit, push, or risk-acceptance decision. Gate
failure: diagnose, fix, retry. Use `ai-eng doctor --fix` when needed.

## Observability

Hook, gate, governance, security, and quality outcomes flow to
`.ai-engineering/state/framework-events.ndjson` (audit chain). Registered
skills, agents, contexts, and hooks are catalogued in
`.ai-engineering/state/framework-capabilities.json`. Session discovery
and transcript viewing are delegated to the separately installed
`agentsview` companion tool.

## Source of Truth

| What | Where |
|------|-------|
| Skills (49) | `.codex/skills/ai-<name>/SKILL.md` |
| Agents (10) | `.codex/agents/ai-<name>.md` |
| Config | `.ai-engineering/manifest.yml` |
| Decisions | `.ai-engineering/state/decision-store.json` |
| Audit chain | `.ai-engineering/state/framework-events.ndjson` |
| Constitution | [CONSTITUTION.md](CONSTITUTION.md) |
