---
name: ai-plan
description: "Decomposes an approved spec into a phased execution plan with bite-sized tasks, agent assignments, and gate criteria — the contract /ai-build executes. Trigger for 'break this down', 'create a plan', 'what tasks do we need', 'lets start implementing', 'scope changed re-plan'. Hard gate: user approves before /ai-build can run. Not for ambiguous requirements; use /ai-brainstorm instead. Not for execution; use /ai-build instead."
effort: high
argument-hint: "[spec-NNN or topic]"
model_tier: opus
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-plan/SKILL.md
edit_policy: generated-do-not-edit
---


# Plan

## Quick start

```
/ai-plan                            # plan from approved spec
/ai-plan --pipeline=hotfix          # override classification
/ai-plan --skip-design              # skip design routing
```

## Workflow

Takes an approved spec and produces a phased execution plan — bite-sized tasks, agent assignments, gate criteria. The plan is the contract `/ai-build` executes. **HARD GATE**: operator must approve before `/ai-build` runs (§10.6 SDD).

1. **Read spec** — load `.ai-engineering/specs/spec.md`; flag missing sections per `spec-schema.md`.
2. **Explore codebase** (read-only) — current architecture, patterns, affected files (§10.3 SOLID).
3. **Classify pipeline** — full / standard / hotfix / trivial.
4. **Classify executor route** — write `execution_route` frontmatter: `executor: build` + `safe_next_command: "/ai-build"` for single-concern plans, or `executor: autopilot` + `safe_next_command: "/ai-autopilot"` for multi-concern/large plans. `status` remains the only approval field; draft plans are recommendations only. Emit `framework_operation` detail `operation=execution_routed`.
5. **Design routing** — invoke `handlers/design-routing.md`; capture output at `.ai-engineering/specs/<spec-id>/design-intent.md` under `## Design`. `--skip-design` logs reason and proceeds.
6. **Identify architecture pattern** — read `architecture-patterns.md`; pick a canonical pattern or `ad-hoc`. Record under `## Architecture` BEFORE decomposition.
7. **Decompose into tasks** — bite-sized (2-5 min), single-agent, single-concern, verifiable, ordered. Apply the **exhaustive patch-ready output template** below (D-131-08 / sub-003).
8. **Assign agents** — capability-match (build = code; verify = read-only; guard = advisory).
9. **Order phases** + gate criteria. **TDD pairs** (§10.5): write a RED test task before any GREEN implementation task.
10. **Self-review** (§10.7 Clean Code) — spec-reviewer pattern, max 2 iterations.
11. **Write** to `.ai-engineering/specs/plan.md`, print `safe_next_command`, and **STOP** — operator approves and runs that command.

### Output template — exhaustive patch-ready (D-131-08)

Each task block carries five lines so `/ai-build` can route to the cheap model tier when the work is mechanical:

- `- [ ] T-N — <task title>`
- `- Agent: <build/verify/guard>`
- `- Files: <path/to/file:line>`
- `- Principles applied: §10.x ...` — cite at least one anchor from CANONICAL.md §10 (e.g., §10.3 SOLID, §10.5 TDD, §10.7 Clean Code).
- `- Patch (deterministic):` — include a unified-diff hunk when the edit is mechanical (rename, copy, frontmatter add); omit and add prose only when judgment is required.
- `- Gate: <test/check>`

Patch hunk present → `/ai-build` dispatches `effort: cheap / model_tier: haiku`. Absent patch or synthesis hint → `effort: mid / model_tier: sonnet`. Operator `--max-effort` → `effort: high / model_tier: opus`.

Plan frontmatter MUST include `execution_route.version`, `spec`, `executor`, `automation`, `concern_count`, `estimated_files`, `reason`, and `safe_next_command`. Do not add `approved`/`approval` under `execution_route`; plan `status` is the approval source of truth.

## Dispatch threshold

Dispatch the `ai-plan` agent for any approved spec needing decomposition. Hand off to `/ai-build` only after explicit user approval. The agent file (`.codex/agents/ai-plan.md`) is the interrogator handle; pipeline classification, decomposition rules, and the no-execution protocol live here.

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

## No-Execution Protocol

`/ai-plan` is planning-only. MUST NOT invoke `ai-build agent` or `/ai-build` for task execution; MUST NOT modify source code; MUST NOT check off implementation tasks. MAY write `.ai-engineering/specs/plan.md` and run read-only codebase exploration.

## Common Mistakes

- Tasks too large (>5 min) — split them.
- Missing dependencies between tasks.
- Assigning code-write tasks to verify (verify is read-only).
- Not pairing RED/GREEN tasks for TDD.
- Planning implementation details (plan says WHAT, code says HOW).
- Omitting the `Patch (deterministic):` block when the edit is mechanical — costs `/ai-build` the cheap-tier dispatch.

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
