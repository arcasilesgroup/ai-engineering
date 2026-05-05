---
name: ai-plan
description: "Use when an approved spec exists and needs a phased execution plan: task decomposition, agent assignments, and gate criteria. Trigger for 'break this down', 'create a plan', 'what tasks do we need', 'let's start implementing', or when plan.md has placeholder content. Also for re-planning: 'scope changed', 'plan failed'. Not for ambiguous requirements — use /ai-brainstorm first."
effort: high
argument-hint: "[spec-NNN or topic]"
---


# Plan

## Purpose

Implementation planning skill. Takes an approved spec (from `/ai-brainstorm` or manual creation) and produces a phased execution plan with bite-sized tasks, agent assignments, and gate criteria. The plan is the contract that `/ai-dispatch` executes.

HARD GATE: user must approve the plan before `/ai-dispatch` can run.

## When to Use

- After `/ai-brainstorm` produces an approved spec
- When a spec exists but plan.md has placeholder content
- When re-planning is needed (plan failed, scope changed)

## Process

1. **Read spec** -- load `.ai-engineering/specs/spec.md`. If spec.md does not conform to `.ai-engineering/contexts/spec-schema.md`, flag missing sections before proceeding.
2. **Explore codebase** -- understand current architecture, patterns, and affected files
3. **Classify pipeline** -- select full/standard/hotfix/trivial based on change scope
4. **Design routing** -- read `.ai-engineering/specs/spec.md` body. Invoke `handlers/design-routing.md` to detect UI keywords. If routing decision is `routed`, ensure `/ai-design` output is captured at `.ai-engineering/specs/<spec-id>/design-intent.md` and link it from `plan.md` under the `## Design` section. If `--skip-design` was passed by the user, log skip reason and proceed.
5. **Identify architecture pattern** -- read `.ai-engineering/contexts/architecture-patterns.md`. Identify the fitting pattern for this spec (layered, hexagonal, CQRS, event-sourcing, ports-and-adapters, clean-architecture, pipes-and-filters, repository, unit-of-work, microservices, modular-monolith, or another canonical pattern documented in the context). Record it in `plan.md` under a `## Architecture` section with a one-paragraph justification tying the pattern's "When to use" criteria to the spec's domain. If no canonical pattern fits, write `ad-hoc` under `## Architecture` with a one-paragraph explanation of why no pattern applies and what structural choice the implementation will make instead. This step happens BEFORE task decomposition so downstream agents inherit the architectural intent.
6. **Decompose into tasks** -- bite-sized (2-5 min each), single-agent, single-concern
7. **Assign agents** -- capability-match each task to the right agent
8. **Order phases** -- define phase boundaries and gate criteria
9. **Review plan** -- self-review with spec-reviewer pattern (max 2 iterations)
10. **Write artifacts** -- persist the plan to `.ai-engineering/specs/plan.md`
11. **STOP** -- present plan. User runs `/ai-dispatch` to execute.

## Pipeline Classification

| Pipeline | Trigger | Steps |
|----------|---------|-------|
| `full` | New feature, refactor, >5 files | discover, architecture, risk, test-plan, spec, dispatch |
| `standard` | Enhancement, 3-5 files | discover, risk, spec, dispatch |
| `hotfix` | Bug fix, security patch, <3 files | discover, risk, spec, dispatch |
| `trivial` | Typo, comment, single-line | spec, dispatch |

Override: `/ai-plan --pipeline=hotfix`.

## Task Decomposition Rules

Each task MUST be:

- **Bite-sized**: completable in 2-5 minutes by an agent
- **Single-agent**: assigned to exactly one agent (build, verify, guard)
- **Single-concern**: does one thing (not "implement feature AND write tests")
- **Verifiable**: has a clear done condition (test passes, lint clean, file exists)
- **Ordered**: dependencies are explicit (T-3 blocked by T-2)

**TDD enforcement**: for features needing tests, always produce paired tasks:
- `T-N: Write failing tests for [feature]` (RED) -- assigned to build/test mode
- `T-N+1: Implement [feature] to pass tests` (GREEN, blocked by T-N) -- assigned to build/code mode, constraint: "DO NOT modify test files from T-N"

## Agent Assignment

| Agent | Capabilities | Assign when... |
|-------|-------------|----------------|
| `build` | Code read-write, tests, debug | Implementation, test writing, bug fixes |
| `verify` | Read-only scanning, 7 modes | Quality checks, security scans, gap analysis |
| `guard` | Advisory, drift detection | Pre-dispatch governance checks |

## Plan Artifacts

### plan.md

```markdown
# Plan: spec-NNN [title]

## Pipeline: [full|standard|hotfix|trivial]
## Phases: N
## Tasks: N (build: N, verify: N, guard: N)

### Phase 1: [name]
**Gate**: [what must be true before Phase 2 starts]
- [ ] T-1.1: [task description] (agent: build)
- [ ] T-1.2: [task description] (agent: build)

### Phase 2: [name]
**Gate**: [what must be true before Phase 3 starts]
...
```

## Common Mistakes

- Tasks too large (> 5 min). Split them.
- Missing dependencies between tasks.
- Assigning code-write tasks to verify (verify is read-only).
- Not pairing RED/GREEN tasks for TDD.
- Planning implementation details (plan says WHAT, code says HOW).
- Skipping the review step.

## No-Execution Protocol

`/ai-plan` is planning-only. It MUST NOT:
- Invoke `ai-build agent` or `/ai-dispatch` for task execution
- Modify source code
- Check off implementation tasks as completed

It MAY:
- Write the plan to `.ai-engineering/specs/plan.md`
- Run codebase exploration (read-only)

## Integration

- **Called by**: user directly, or after `/ai-brainstorm` approval
- **Calls**: Explore agent (`ai-explore`) for codebase context, write (artifact creation)
- **Transitions to**: `/ai-dispatch` (ONLY -- user must invoke explicitly)

$ARGUMENTS
