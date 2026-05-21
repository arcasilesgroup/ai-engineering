---
name: ai-explore
description: Codebase-only read-only research dispatcher. Thin wrapper around the ai-explore agent for architecture mapping, dependency tracing, pattern identification, and risk surfacing. Trigger for 'explore the codebase', 'where does X live', 'map this module', 'what depends on Y', 'trace this import chain'. Not for external evidence with citations; use /ai-research instead.
effort: cheap
argument-hint: "[question]"
tags: [exploration, research, codebase, architecture, mapping]
model_tier: haiku
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-explore/SKILL.md
edit_policy: generated-do-not-edit
---


# Explore

## Quick start

```
/ai-explore "where does the install pipeline run hooks?"
/ai-explore "trace the import chain from cli_factory to the durable repository"
/ai-explore "what files reference the legacy ai_providers schema?"
```

## When to Use

- Architecture mapping: "How is the X module structured?"
- Dependency tracing: "What imports Y? What does Y import?"
- Pattern identification: "How do we typically handle Z?"
- Risk surfacing: "What's load-bearing in this code path?"

## When NOT to Use

- External evidence + citations needed -> use `/ai-research` instead.
- Code change needed -> use `/ai-build` or `/ai-simplify` instead.
- LLM-style code review -> use `/ai-review` instead.

## Process

Per D-133-09 this is a thin wrapper: dispatches the existing
`ai-explore` agent (`.codex/agents/ai-explore.md`) with the user's
question. The agent owns the heavy lifting (file-reading + grep tools
structured findings output).

1. **Capture the question.** Take the entire argument as the question.
2. **Dispatch agent.** Invoke `ai-explore` agent with the question.
3. **Report.** Return the agent's structured findings to the user.

## Output Contract

The agent emits structured Findings / Dependencies / Risks /
Recommendations sections. Wrapper passes them through unchanged.

## Common Mistakes

- Treating this skill as an external-research tool. It is codebase-only.
- Asking it to make changes. Pure read-only.
