# GEMINI.md — Gemini CLI Overlay

> See [AGENTS.md](AGENTS.md) for the canonical cross-IDE rules (Step 0,
> available skills, agents, hard rules, quality gates, observability,
> source of truth, and operating-behaviour rules). Read those first;
> this file only adds Gemini-CLI-specific specifics. The non-negotiable
> rules live in [CONSTITUTION.md](CONSTITUTION.md).

## FIRST ACTION — Mandatory

Your first action in every session MUST be to run `/ai-start`. Do not
respond to any user request until `/ai-start` completes. `/ai-*` are
slash commands in the IDE agent surface, not `ai-eng` CLI subcommands.

## Hooks Wiring (Gemini-specific)

Gemini CLI hook configuration lives in `.gemini/settings.json`. Hook
event mapping (canonical Python script in
`.ai-engineering/scripts/hooks/`):

| Cross-IDE primitive          | Gemini event |
|------------------------------|--------------|
| Progressive disclosure       | `BeforeAgent` |
| Tool offload + loop detect   | `AfterTool` |
| Checkpoint + Ralph Loop      | `AfterAgent` |

Compaction events (PreCompact / PostCompact) are not surfaced by
Gemini CLI; the snapshot primitive degrades gracefully.

## Surface Pointers

| What | Where |
|------|-------|
| Skills (__SKILL_COUNT__) | `.gemini/skills/ai-<name>/SKILL.md` |
| Agents (__AGENT_COUNT__) | `.gemini/agents/ai-<name>.md` |
| Hook scripts | `.ai-engineering/scripts/hooks/` (shared) |
| CLI | `ai-eng <command>` |

All other content (skill list, agent list, quality gates, hard rules,
observability stanza, telemetry default, source-of-truth table) is
defined once in [AGENTS.md](AGENTS.md). Do not duplicate.

## Skills

See [AGENTS.md → Skills](AGENTS.md#skills-__SKILL_COUNT__) for the
canonical skill list and dispatch surface. The Gemini surface mirrors
that registry under `.gemini/skills/`.

## Observability

See [AGENTS.md → Observability](AGENTS.md#observability) for the
canonical telemetry posture and audit chain wiring. Gemini-specific
hook events are listed under `Hooks Wiring (Gemini-specific)` above.

## Source of Truth

See [AGENTS.md → Source of Truth](AGENTS.md#source-of-truth) for the
canonical source-of-truth table covering CONSTITUTION.md, AGENTS.md,
and the per-IDE overlay charters.
