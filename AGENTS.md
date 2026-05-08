# AGENTS.md — Canonical Cross-IDE Rulebook

> Hard rules live in [CONSTITUTION.md](CONSTITUTION.md). This file is the
> canonical multi-IDE entry point. IDE overlays (CLAUDE.md, GEMINI.md,
> .github/copilot-instructions.md) delegate to this file.

## Step 0 — First Action

Every session, do these four things first:

1. Read [CONSTITUTION.md](CONSTITUTION.md) — non-negotiable rules.
2. Read `.ai-engineering/manifest.yml` — configuration source of truth.
3. Query `.ai-engineering/state/state.db` `decisions` table — active risk posture.
4. No implementation without an approved spec — invoke `/ai-brainstorm` first.

## Workflow — the seven-step chain

The canonical chain is verbatim:
**/ai-brainstorm → /ai-plan → /ai-build → /ai-verify → /ai-review → /ai-commit → /ai-pr**

`/ai-brainstorm` produces the spec; `/ai-plan` decomposes; `/ai-build` is
the multi-stack implementation gateway; `/ai-verify` runs deterministic
gates; `/ai-review` runs reviewer agents in parallel; `/ai-commit` stages
the signed commit; `/ai-pr` creates the PR. No approved spec? Stop and
return to `/ai-brainstorm`.

## Two-file state pattern

Each spec carries two source-of-truth files:

- `plan.md` — task ledger; checkbox-flips on completion; living state.
- `LESSONS.md` — append-only retro per spec; never auto-rewritten.

The harness keeps both in lock-step; humans review both at PR time.

## Skills (50)

Registry: `.ai-engineering/manifest.yml` `skills.registry`. Canonical
definitions: `.claude/skills/ai-<name>/SKILL.md`. Other IDE surfaces are
generated mirrors. Invoke via `/ai-<name>` in the agent surface.

## Agents (10)

The agents are listed in `.ai-engineering/manifest.yml` under
`agents.registry` and documented at `.claude/agents/ai-<name>.md`. Each
agent runs in its own context window — offload research and parallel
analysis aggressively.

## Hard Rules

Non-negotiable rules live in [CONSTITUTION.md](CONSTITUTION.md). Read them
before any commit, push, or risk-acceptance decision. Gate failure:
diagnose, fix, retry. Use `ai-eng doctor --fix` when needed.

## Spec lifecycle

`/ai-brainstorm` calls `spec_lifecycle.py start_new`; `/ai-pr` calls
`mark_shipped` post-merge; `/ai-cleanup --specs` calls `sweep` (DRAFT >14d
→ ABANDONED). All fail-open. State at `.ai-engineering/state/specs/<id>.json`;
projection at `.ai-engineering/specs/_history.md` (7-col canonical).

## Observability

Hook, gate, governance, and quality outcomes flow to
`.ai-engineering/state/framework-events.ndjson` (audit chain). Registered
skills, agents, contexts, and hooks are catalogued in
`.ai-engineering/state/state.db` `tool_capabilities` table. Session
discovery is delegated to the separately installed `agentsview` companion.

## Source of Truth

| What | Where |
|------|-------|
| Skills | `.claude/skills/ai-<name>/SKILL.md` |
| Agents | `.claude/agents/ai-<name>.md` |
| Placement contract | `.ai-engineering/contexts/knowledge-placement.md` |
| Config | `.ai-engineering/manifest.yml` |
| Decisions | `.ai-engineering/state/state.db` `decisions` table |
| Audit chain | `.ai-engineering/state/framework-events.ndjson` |
| Constitution | [CONSTITUTION.md](CONSTITUTION.md) |
