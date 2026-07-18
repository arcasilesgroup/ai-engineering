---
name: ai-explore
description: "Codebase-only read-only research dispatcher. Thin wrapper around the ai-explore agent for architecture mapping, dependency tracing, pattern identification, and risk surfacing. Trigger for 'explore the codebase', 'where does X live', 'map this module', 'what depends on Y', 'trace this import chain'. Not for external evidence with citations; use /ai-research instead."
effort: cheap
model_tier: haiku
argument-hint: "[question]"
tags: [exploration, research, codebase, architecture, mapping]
---

# Explore

## Quick start

```
/ai-explore "where does the install pipeline run hooks?"
/ai-explore "trace the import chain from cli_factory to the durable repository"
/ai-explore "what files reference the legacy ai_providers schema?"
```

## When to Use

| Use for | Example |
|---------|---------|
| Architecture mapping | "How is the X module structured?" |
| Dependency tracing | "What imports Y? What does Y import?" |
| Pattern identification | "How do we typically handle Z?" |
| Risk surfacing | "What is load-bearing in this code path?" |

Dispatch for any question spanning >= 1 file, module, or import edge.

Not for: external evidence + citations (`/ai-research`); code changes
(`/ai-build`, `/ai-simplify`); LLM-style review (`/ai-review`).

## Workflow

Thin wrapper (D-133-09), §10.1 KISS — fewest moving parts. The
`ai-explore` agent (`.claude/agents/ai-explore.md`) owns file-reading +
grep and the structured findings output.

1. **Capture** — take the entire argument as the question.
2. **Dispatch** — invoke the `ai-explore` agent with the question.
3. **Report** — pass the agent's structured findings through unchanged.

## Output Contract

Agent emits Findings / Dependencies / Risks / Recommendations; the
wrapper returns them verbatim. Pure read-only — never edits code, never
fetches external sources.

## Integration

Called by: user directly. Dispatches: `ai-explore` agent
(`.claude/agents/ai-explore.md`). See also: `/ai-research` (external
evidence), `/ai-review` (LLM review), `/ai-build` (code changes).

$ARGUMENTS
