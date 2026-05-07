# AGENTS.md — Canonical Cross-IDE Rulebook

> Hard rules live in [CONSTITUTION.md](CONSTITUTION.md). This file is
> the canonical multi-IDE entry point and shared runtime contract for
> root IDE behavior. Canonical skills and agents live under `.claude/`;
> IDE-specific overlays (CLAUDE.md, GEMINI.md,
> .github/copilot-instructions.md) delegate to this file.

## Step 0 — First Action

Every session, the first action is:

1. Read [CONSTITUTION.md](CONSTITUTION.md) (non-negotiable rules).
2. Read `.ai-engineering/manifest.yml` (configuration source of truth).
3. Query `.ai-engineering/state/state.db` `decisions` table (active decisions and risk posture).
4. No implementation without an approved spec — invoke `/ai-brainstorm`
   first when a task has no spec.

## Workflow

Implementation is spec-gated by default:

1. `/ai-brainstorm` produces or refines the approved spec when scope is unclear or missing.
2. `/ai-plan` decomposes the approved spec into concrete tasks without writing production code.
3. `/ai-dispatch` executes the approved plan for standard scoped work.
4. `/ai-autopilot` executes the approved spec autonomously for large multi-concern work.
5. If no approved spec exists, stop and return to `/ai-brainstorm` before implementation.

## Skills (50)

The full registry is in `.ai-engineering/manifest.yml` under
`skills.registry`. Canonical skill definitions live under
`.claude/skills/ai-<name>/SKILL.md`; other IDE skill surfaces are
generated mirrors.

Invoke skills via `/ai-<name>` in the IDE agent surface (slash command).
Do not invent `ai-eng <skill>` terminal equivalents unless the CLI
reference explicitly lists them.

## Agents (10)

The 10 first-class agents are listed in
`.ai-engineering/manifest.yml` under `agents.registry` and documented at
`.claude/agents/ai-<name>.md`. Other IDE agent surfaces are generated
mirrors; each runs in its own context window, so offload research and
parallel analysis to them.

## Hard Rules

The non-negotiable rules are in [CONSTITUTION.md](CONSTITUTION.md).
Read them before any commit, push, or risk-acceptance decision. Gate
failure: diagnose, fix, retry. Use `ai-eng doctor --fix` when needed.

## Observability

Hook, gate, governance, security, and quality outcomes flow to
`.ai-engineering/state/framework-events.ndjson` (audit chain). Registered
skills, agents, contexts, and hooks are catalogued in
`.ai-engineering/state/state.db` `tool_capabilities` table. Session discovery
and transcript viewing are delegated to the separately installed
`agentsview` companion tool.

## Source of Truth

| What | Where |
|------|-------|
| Skills (50) | `.claude/skills/ai-<name>/SKILL.md` |
| Agents (10) | `.claude/agents/ai-<name>.md` |
| Placement contract | `.ai-engineering/contexts/knowledge-placement.md` |
| Config | `.ai-engineering/manifest.yml` |
| Decisions | `.ai-engineering/state/state.db` `decisions` table |
| Audit chain | `.ai-engineering/state/framework-events.ndjson` |
| Constitution | [CONSTITUTION.md](CONSTITUTION.md) |
