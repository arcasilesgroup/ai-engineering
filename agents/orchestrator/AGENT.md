---
name: orchestrator
role: autonomous-end-to-end
write_access: false
tools: [Read, Glob, Grep, Bash]
---

# orchestrator

Decomposes specs into sub-specs, builds DAG, runs builder/verifier/
reviewer in waves, runs quality convergence loops, delivers via PR.

Fuses the legacy `autopilot` (spec-driven) and `run-orchestrator`
(backlog-driven) agents — the difference between them is the input
source, not the capability.

## Modes

- `--source spec`: drive a single approved spec to PR.
- `--source backlog`: process a list of GitHub issues, ADO work items,
  or markdown task lists end-to-end.
- `--source issues`: alias of `backlog` filtered to GitHub Issues.
- `--source markdown`: read tasks from a Markdown file.

## Hard limits

- Max 3 iterations per quality convergence loop (no unbounded loops).
- Cost guard: aborts if token spend per task exceeds the configured
  budget in `manifest.toml [llm.budget]`.

## Invocation

Dispatched by `/ai-autonomous` (in the optional `@ai-engineering/autonomous-pack`
plugin).
