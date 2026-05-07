---
name: ai-explain
description: Use when a developer asks 'how does this work?', 'why does it do X?', 'trace through this', 'explain this pattern', or needs engineer-grade technical explanations anchored in real codebase examples. 3-tier depth (brief/standard/deep) with ASCII diagrams and execution traces. Not for documentation (/ai-write) or fixing code (/ai-dispatch).
effort: high
argument-hint: "<topic>|--depth brief|standard|deep"
mode: agent
tags: [explanation, teaching, analysis, architecture]
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-explain/SKILL.md
edit_policy: generated-do-not-edit
---



# Explain

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

## Integration

Read-only. Shared by `/ai-guide` for teaching mode. Related: `/ai-verify` (architecture assessment mode).
$ARGUMENTS
