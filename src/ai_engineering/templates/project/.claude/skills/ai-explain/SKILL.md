---
name: ai-explain
description: "Explains code, concepts, patterns, and architecture with engineer-grade depth: 3-tier control (brief/standard/deep), ASCII diagrams, execution traces, anchored to real file:line references. Trigger for 'how does this work', 'why does it do X', 'trace through this', 'explain this pattern', 'walk me through'. Not for documentation artifacts; use /ai-prose or /ai-docs instead. Not for fixing code; use /ai-debug or /ai-build instead."
effort: mid
argument-hint: "[topic]|--depth brief|standard|deep"
tags: [explanation, teaching, analysis, architecture]
---

# Explain

Explains code, concepts, patterns, and architecture with engineer-grade depth — 3-tier control (brief/standard/deep), ASCII diagrams, and execution traces anchored to real `file:line` references. Use it for "how does this work", "why does it do X", "trace through this", or "walk me through" — not for producing docs (`/ai-prose`, `/ai-docs`) or fixing code (`/ai-debug`, `/ai-build`).

## Quick start

```
/ai-explain "how does the audit chain work" --depth brief
/ai-explain auth-handler.ts:42-90 --depth standard
/ai-explain "spec lifecycle FSM" --depth deep
```

## Workflow

Read-only; §10.7 Clean Code — clarity over cleverness.

1. **Identify subject** — classify into Code / Concept / Pattern /
   Architecture / Error / Difference. If ambiguous, ask ONE question.
2. **Search codebase** — search the tree for real instances; `file:line` refs
   are primary evidence. If none, use a generic stack example and say so.
3. **Select depth** (per cue table) and deliver only that depth's sections.
4. **Follow-up** — "what about X?" extend at depth; "go deeper" +1 level,
   only new sections; "trace a different path" re-run Trace; "show me in
   my code" search the codebase for the concept.

| Depth | Cues | Sections |
|-------|------|----------|
| Brief | "TL;DR", "brief", "short" | Summary + Walkthrough (3-5 steps) |
| Standard (default) | general question | + Diagram + Gotchas + Trace |
| Deep | "deep dive", "everything", "teach me" | + Context Map + Complexity Notes |

Section contract:

- **Summary** — 1-2 technical sentences: what it does + why it exists.
- **Walkthrough** — numbered `file:line` steps in execution order.
- **Diagram** — ASCII (data flow / call chain / state machine / sequence),
  width < 70 chars, no Mermaid.
- **Gotchas** — specific edge cases / perf traps / concurrency hazards in
  THIS code, not generic advice.
- **Trace It** — execution trace of a concrete scenario; show data
  transformation per step, highlight decision points.
- **Context Map** — when to use / when NOT / alternatives with tradeoffs.
- **Complexity Notes** — cyclomatic complexity, nesting, time/space of hot
  paths, concurrency assessment.

Pitfalls: don't over-explain standard concepts (assume competence); no
generic gotchas; avoid "basically" / "simply" / "just".

## Examples

### Example — quick orientation on an unfamiliar pattern

User: "how does the audit chain work in this repo?"

```
/ai-explain "audit chain" --depth brief
```

Anchors to `framework-events.ndjson`; emits a 3-paragraph overview with a
small ASCII flow.

## Integration

Called by: user directly, `/ai-onboard` (teaching mode). Read-only. See
also: `/ai-debug`, `/ai-prose content blog`, `/ai-verify` (architecture
assessment).

$ARGUMENTS
