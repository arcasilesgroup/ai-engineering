---
name: ai-explore
description: "Codebase-only read-only research dispatcher. Thin wrapper around the ai-explore agent for architecture mapping, dependency tracing, pattern identification, and risk surfacing — dispatch for any question spanning >= 1 file, module, or import edge. Trigger for 'explore the codebase', 'where does X live', 'map this module', 'what depends on Y', 'trace this import chain'. Not for external evidence with citations; use /ai-research instead."
effort: cheap
argument-hint: "[question]"
tags: [exploration, research, codebase, architecture, mapping]
mirror_family: antigravity-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-explore/SKILL.md
edit_policy: generated-do-not-edit
---


# Explore

Read-only codebase research dispatcher: a thin wrapper around the
`ai-explore` agent for architecture mapping, dependency tracing, pattern
identification, and risk surfacing. Use it for any question spanning one
or more files, modules, or import edges.

## Quick start

```
/ai-explore "where does the install pipeline run hooks?"
/ai-explore "trace the import chain from cli_factory to the durable repository"
/ai-explore "what files reference the legacy ai_providers schema?"
```

## Workflow

Thin wrapper (D-133-09), §10.1 KISS — fewest moving parts. The
`ai-explore` agent (`.agents/agents/ai-explore.md`) owns file-reading +
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
(`.agents/agents/ai-explore.md`). See also: `/ai-research` (external
evidence), `/ai-review` (LLM review), `/ai-build` (code changes).

**Inline fallback** — subagent dispatch is the primary path. On a host without a subagent primitive, execute this skill by reading `.agents/agents/ai-explore.md` inline and answering in-context, sequentially, under the same read-only scope; inline-sequential is the floor, not an alternate behaviour.

$ARGUMENTS
