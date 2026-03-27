---
name: ai-instinct
description: "Use when you want to see what the AI has learned about your project's workflow patterns, when session context feels stale, or when enough activity has accumulated to consolidate observations. Trigger for 'what has the AI learned?', 'refresh the instinct context', 'show instinct status', 'consolidate observations'. Two modes: status (inspect current state) and review (consolidate new observations into project-local instincts)."
effort: medium
argument-hint: "[status|review]"
mode: agent
tags: [meta, learning, continuous-improvement]
---


# ai-instinct

Project-local instinct review for `ai-engineering` v1. This skill keeps instinct learning intentionally small: capture bounded observations automatically, consolidate them into one project store, and load only a short derived context at session start.

## Artifact Set

| Artifact | Purpose |
|----------|---------|
| `.ai-engineering/state/instinct-observations.ndjson` | Sanitized append-only observation stream. Retain only the last 30 days. |
| `.ai-engineering/instincts/instincts.yml` | Canonical project-local instinct store. |
| `.ai-engineering/instincts/context.md` | Bounded context derived from the canonical store. |
| `.ai-engineering/instincts/meta.json` | Checkpoints and thresholds for consolidation. |

## Supported Pattern Families

The canonical store supports only these sections:

- `toolSequences`
- `errorRecoveries`
- `skillAgentPreferences`

Anything outside those families is out of scope for v1.

## Scope And Guardrails

- Project-local only. No global instinct scope.
- One canonical `instincts.yml`, not one file per instinct.
- No confidence scores, promotion, evolve, export, or import flows.
- No daemons, background observers, or periodic workers.
- Never store transcripts, prompts, responses, or raw tool payloads.
- `context.md` must stay bounded and should contain only the most relevant 3-5 bullets.

## Commands

| Command | Description |
|---------|-------------|
| `/ai-instinct status` | Inspect the current instinct store, context freshness, and consolidation metadata. |
| `/ai-instinct review` | Consolidate recent observation delta into the canonical store and regenerate bounded context when needed. |

### `/ai-instinct status`

Read the four instinct artifacts and report:

- whether instinct learning is initialized
- how many entries exist in each supported section
- when extraction last ran
- when context was last generated
- whether context refresh is pending
- whether the current context appears fresh or stale

Use this mode when the user wants to understand what the project has already learned.

### `/ai-instinct review`

This is the only consolidation flow for v1. It is normally triggered from `/ai-onboard`, but it can also be run manually when the user wants to inspect or normalize the current state.

Procedure:

1. Read `.ai-engineering/instincts/meta.json` to determine the last checkpoint and refresh thresholds.
2. Read only the recent delta from `.ai-engineering/state/instinct-observations.ndjson`.
3. Read the current `.ai-engineering/instincts/instincts.yml`.
4. If needed for `skillAgentPreferences`, inspect the correlated recent slice of `.ai-engineering/state/framework-events.ndjson`.
5. Normalize the delta into only the supported families:
   - common tool sequences
   - common error recovery paths
   - common `skill -> agent` preferences
6. Merge duplicate or near-duplicate patterns into the canonical store.
7. Drop noise that lacks meaningful repetition or does not improve future guidance.
8. Regenerate `.ai-engineering/instincts/context.md` as a bounded context for future sessions.
9. Update `.ai-engineering/instincts/meta.json` with the new checkpoint and refresh state.

If there is no meaningful delta and the context is still fresh, report that no consolidation was needed.

## Output Expectations

`status` should stay concise and operational. Prefer counts, timestamps, and freshness signals over raw dumps.

`review` should summarize:

- what delta was reviewed
- which sections changed
- which noisy or duplicate entries were merged or ignored
- whether `context.md` was regenerated

## Scripts

- `scripts/consolidate.py [--context PATH] [--observations PATH]` -- read instinct context and report observation counts per pattern family

## Boundaries

- Do not create instincts outside `.ai-engineering/instincts/`.
- Do not recreate ECC-style project/global trees.
- Do not invent unsupported pattern types.
- Do not load raw observations directly into the prompt when `context.md` is available.
- Do not claim the system supports promotion, evolution, or global libraries.

$ARGUMENTS
