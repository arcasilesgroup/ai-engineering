---
name: ai-plan
description: "Decomposes an approved spec into a phased execution plan with bite-sized tasks, agent assignments, and gate criteria — the contract /ai-build executes. Trigger for 'break this down', 'create a plan', 'what tasks do we need', 'lets start implementing', 'scope changed re-plan'. Hard gate: user approves before /ai-build can run. Not for ambiguous requirements; use /ai-brainstorm instead. Not for execution; use /ai-build instead."
effort: high
argument-hint: "[spec-NNN or topic]"
---


# Plan

## Quick start

```
/ai-plan                            # plan from approved spec
/ai-plan --pipeline=hotfix          # override classification
/ai-plan --skip-design              # skip design routing
```

## Workflow

Implementation planning. Takes an approved spec (from `/ai-brainstorm` or manual creation) and produces a phased execution plan with bite-sized tasks, agent assignments, and gate criteria. The plan is the contract that `/ai-build` executes.

**HARD GATE**: user must approve the plan before `/ai-build` can run.

1. **Read spec** — load `.ai-engineering/specs/spec.md`; flag missing sections per `.ai-engineering/contexts/spec-schema.md`.
2. **Explore codebase** (read-only) — understand current architecture, patterns, and affected files.
3. **Classify pipeline** — full / standard / hotfix / trivial.
4. **Design routing** — invoke `handlers/design-routing.md`; if routed, capture `/ai-design` output at `.ai-engineering/specs/<spec-id>/design-intent.md` and link it under `## Design`. `--skip-design` logs reason and proceeds.
5. **Identify architecture pattern** — read `.ai-engineering/contexts/architecture-patterns.md`. Pick a canonical pattern (layered, hexagonal, CQRS, event-sourcing, ports-and-adapters, clean-architecture, pipes-and-filters, repository, unit-of-work, microservices, modular-monolith) or `ad-hoc`. Record under `## Architecture` with one-paragraph justification BEFORE task decomposition.
6. **Decompose into tasks** — bite-sized (2-5 min), single-agent, single-concern, verifiable, ordered.
7. **Assign agents** — capability-match (build = code; verify = read-only scan; guard = advisory).
8. **Order phases** + gate criteria.
9. **Self-review** (spec-reviewer pattern, max 2 iterations).
10. **Write** to `.ai-engineering/specs/plan.md`.
11. **STOP** — present plan; user runs `/ai-build`.

## Dispatch threshold

Dispatch the `ai-plan` agent for any approved spec needing decomposition. Hand off to `/ai-build` only after explicit user approval. The agent file (`.claude/agents/ai-plan.md`) is the interrogator handle; pipeline classification, decomposition rules, and the no-execution protocol live here.

## When to Use

- After `/ai-brainstorm` produces an approved spec.
- When a spec exists but plan.md has placeholder content.
- When re-planning is needed (plan failed, scope changed).

## Pipeline Classification

| Pipeline | Trigger | Steps |
| --- | --- | --- |
| `full` | New feature, refactor, >5 files | discover, architecture, risk, test-plan, spec, dispatch |
| `standard` | Enhancement, 3-5 files | discover, risk, spec, dispatch |
| `hotfix` | Bug fix, security patch, <3 files | discover, risk, spec, dispatch |
| `trivial` | Typo, comment, single-line | spec, dispatch |

## Task Decomposition Rules

Each task: bite-sized (2-5 min), single-agent (build / verify / guard), single-concern, verifiable (clear done condition), ordered (explicit dependencies).

**TDD enforcement**: for features needing tests, paired tasks:

- `T-N: Write failing tests for [feature]` (RED) — build/test mode.
- `T-N+1: Implement [feature] to pass tests` (GREEN, blocked by T-N) — build/code mode, constraint: "DO NOT modify test files from T-N".

## No-Execution Protocol

`/ai-plan` is planning-only. MUST NOT invoke `ai-build agent` or `/ai-build` for task execution; MUST NOT modify source code; MUST NOT check off implementation tasks. MAY write `.ai-engineering/specs/plan.md` and run read-only codebase exploration.

## Common Mistakes

- Tasks too large (>5 min) — split them.
- Missing dependencies between tasks.
- Assigning code-write tasks to verify (verify is read-only).
- Not pairing RED/GREEN tasks for TDD.
- Planning implementation details (plan says WHAT, code says HOW).
- Skipping the review step.

## Examples

### Example 1 — plan from an approved spec

User: "the spec is approved, break it down into a phased plan"

```
/ai-plan
```

Reads `.ai-engineering/specs/spec.md`, runs read-only exploration, decomposes into phases with task assignments + gates, writes `plan.md`, presents for approval.

### Example 2 — re-plan after scope change

User: "scope changed — re-plan from the updated spec"

```
/ai-plan
```

Diffs against the existing plan, regenerates affected phases, preserves completed checkboxes where the task is unchanged.

## Integration

Called by: user directly, post-`/ai-brainstorm` approval. Calls: `ai-explore` agent (codebase context). Transitions to: `/ai-build` (only after user approves). See also: `/ai-brainstorm`, `/ai-build`, `/ai-autopilot` (multi-concern alternative).

$ARGUMENTS
