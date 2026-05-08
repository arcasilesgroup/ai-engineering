---
name: ai-explain
description: "Explains code, concepts, patterns, and architecture with engineer-grade depth: 3-tier control (brief/standard/deep), ASCII diagrams, execution traces, anchored to real file:line references. Trigger for 'how does this work', 'why does it do X', 'trace through this', 'explain this pattern', 'walk me through'. Not for documentation artifacts; use /ai-write or /ai-docs instead. Not for fixing code; use /ai-debug or /ai-dispatch instead."
effort: high
argument-hint: "[topic]|--depth brief|standard|deep"
tags: [explanation, teaching, analysis, architecture]
---


# Explain

## Quick start

```
/ai-explain "how does the audit chain work" --depth brief
/ai-explain auth-handler.ts:42-90 --depth standard
/ai-explain "spec lifecycle FSM" --depth deep
```

Engineer-grade technical explanations of code, concepts, patterns, and architecture. 3-tier depth control scales detail to what the developer needs. Anchored in the actual codebase with `file:line` references, ASCII diagrams, and execution traces.

## When to Use

- "How does this work?", "What is this?", "Why does this do X?", "Trace this."
- NOT for generating documentation -- use `/ai-write`.
- NOT for writing/fixing code -- use `/ai-dispatch` or `/ai-debug`.

## Process

### 1. Identify subject

Classify into: Code, Concept, Pattern, Architecture, Error, or Difference. If ambiguous, ask ONE clarifying question.

### 2. Search codebase

Use Grep/Glob to find real instances. Codebase examples with `file:line` references are primary evidence. If not found, use generic example in project's stack and note it.

### 3. Select depth

| Depth | Trigger cues | Sections |
|-------|-------------|----------|
| Brief | "TL;DR", "brief", "short" | Summary + Walkthrough (3-5 steps) |
| Standard | General question (DEFAULT) | Summary + Walkthrough + Diagram + Gotchas + Trace |
| Deep | "deep dive", "everything", "teach me" | All above + Context Map + Complexity Notes |

### 4. Deliver explanation

Sections (depth selection per step 3 table):

- **Summary**: 1-2 technical sentences -- what it does and why it exists.
- **Walkthrough**: numbered steps with `file:line` references, following execution order. Brief: 3-5 steps max.
- **Diagram**: ASCII art reflecting actual code structure. Choose type: data flow, call chain, state machine, sequence. Width under 70 chars. No Mermaid.
- **Gotchas**: specific pitfalls in this code -- edge cases, performance traps, concurrency hazards. Not generic advice.
- **Trace It**: execution trace through a concrete scenario. Show data transformation at each step, highlight decision points.
- **Context Map**: when to use, when NOT to use, alternatives with tradeoff comparison.
- **Complexity Notes**: cyclomatic complexity, nesting depth, time/space complexity of hot paths, concurrency assessment.

### 5. Follow-up

- "What about X?" -- extend at same depth.
- "Go deeper" -- increase one level, deliver only new sections.
- "Trace a different path" -- re-run Trace with different scenario.
- "Show me in my code" -- find the concept via Grep/Glob.

## Quick Reference

```
/ai-explain <topic>                  # standard depth (default)
/ai-explain <topic> --depth brief
/ai-explain <topic> --depth deep
```
Sections per depth: see step 3 table.

## Common Mistakes

- Over-explaining standard concepts -- assume technical competence.
- Generic gotchas ("be careful with null") -- must be specific to the code under review.
- Using "basically", "simply", "just" -- these minimize real complexity.

## Examples

### Example 1 — quick orientation on an unfamiliar pattern

User: "how does the audit chain work in this repo?"

```
/ai-explain "audit chain" --depth brief
```

Anchors to `framework-events.ndjson`, the audit indexer, and the projection schema; emits a 3-paragraph overview with a small ASCII flow.

### Example 2 — deep walk-through of a tricky function

User: "trace through how spec_lifecycle.start_new handles the FSM"

```
/ai-explain spec_lifecycle.py:start_new --depth deep
```

Reads the function, produces an execution trace per state transition, calls out the atomic-write boundary, references tests that exercise each branch.

## Integration

Called by: user directly, `/ai-guide` (teaching mode). Read-only. See also: `/ai-debug`, `/ai-write content blog`, `/ai-verify` (architecture assessment).

$ARGUMENTS
