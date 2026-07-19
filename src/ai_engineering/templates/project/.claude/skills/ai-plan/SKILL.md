---
name: ai-plan
description: "Decomposes an approved spec into a phased execution plan with bite-sized tasks, agent assignments, and gate criteria — the contract /ai-build executes. Trigger for 'break this down', 'create a plan', 'what tasks do we need', 'lets start implementing', 'scope changed re-plan'. Hard gate: user approves before /ai-build can run. Not for ambiguous requirements; use /ai-brainstorm instead. Not for execution; use /ai-build instead."
effort: high
argument-hint: "[spec-NNN or topic]"
---

# Plan

Decomposes an approved spec into a phased, patch-ready execution plan — the contract `/ai-build` executes. **HARD GATE**: operator approves before `/ai-build` runs.

```
/ai-plan                    # plan from approved spec
/ai-plan --pipeline=hotfix  # override classification
/ai-plan --skip-design      # skip design routing
```

## Workflow

Principles: §10.6 SDD (approved spec is the contract), §10.3 SOLID (single-concern tasks), §10.5 TDD (RED before GREEN), §10.7 Clean Code (self-review).

1. **Approval gate (HARD STOP, no escape hatch)** — before decomposing, resolve the spec's CANONICAL state. Read `<spec_id>` from `.ai-engineering/specs/spec.md` frontmatter `spec:` (fallback `slug:`); run `python .ai-engineering/scripts/spec_lifecycle.py status <spec_id>`.
   - Sidecar state ≠ `approved` → HARD STOP, write NO `plan.md`, emit exactly:
     ```
     Error: spec-<id> is in '<state>' state.
     Complete /ai-brainstorm approval before running /ai-plan.
     ```
   - No sidecar → fall back to `spec.md` frontmatter `status:`; block (same HARD STOP) unless `status: approved`.
   - Neither resolves → indeterminate plumbing (D-161-03): LOUD warning, proceed (fail-open).
   - Vocab: sidecar `approved` ⇔ frontmatter `status: approved`. The ONLY bypass is approving the spec via `/ai-brainstorm`.
2. **Read spec** — load `spec.md`; flag missing sections per `spec-schema.md`.
3. **Explore** (read-only) — current architecture, patterns, affected files.
4. **Classify pipeline** — full / standard / hotfix / trivial (table below).
5. **Classify executor route** — write `execution_route` frontmatter: `executor: build` + `safe_next_command: "/ai-build"` for single-concern, or `executor: autopilot` + `safe_next_command: "/ai-autopilot"` for multi-concern/large. `status` stays the only approval field; drafts are recommendations. Emit `framework_operation` detail `operation=execution_routed`.
6. **Design routing** — invoke `handlers/design-routing.md`; capture at `.ai-engineering/specs/<spec-id>/design-intent.md` under `## Design`. `--skip-design` logs reason + proceeds.
7. **Identify architecture pattern** — read `architecture-patterns.md`; pick a canonical pattern or `ad-hoc`; record under `## Architecture` BEFORE decomposition.
8. **Decompose into tasks** — bite-sized (2-5 min), single-agent, single-concern, verifiable, ordered; apply the patch-ready template below (D-131-08 / sub-003).
9. **Assign agents** — capability-match (build = code; verify = read-only; guard = advisory).
10. **Order phases + gates** — TDD pairs: a RED test task before any GREEN implementation task.
11. **Self-review** — spec-reviewer pattern, max 2 iterations.
12. **Write + STOP** — write `.ai-engineering/specs/plan.md`, then emit the 6-field value block (Bottom line / Why it matters / What's done / Risk / Next / Details) per `.ai-engineering/reference/value-lens.md` at the resolved audience level (default `full`) alongside the `safe_next_command`, and STOP — operator approves and runs that command. The `safe_next_command` string itself stays a carve-out (exact, machine-runnable).

**Re-plan** (plan failed / scope changed, or `plan.md` holds placeholder content): diff against the existing plan, regenerate affected phases, and preserve completed checkboxes where the task is unchanged.

### Output template — patch-ready (D-131-08)

Each task block carries five lines so `/ai-build` can route mechanical work to the cheap tier:

- `- [ ] T-N — <task title>`
- `- Agent: <build/verify/guard>`
- `- Files: <path/to/file:line>`
- `- Principles applied: §10.x ...` — cite ≥ 1 CANONICAL §10 anchor (e.g. §10.3 SOLID, §10.5 TDD, §10.7 Clean Code).
- `- Patch (deterministic):` — a unified-diff hunk when the edit is mechanical (rename, copy, frontmatter add); omit and add prose only when judgment is required.
- `- Gate: <test/check>`

Routing: patch present → `effort: cheap`; patch absent or synthesis hint → `effort: mid`; operator `--max-effort` → `effort: high`.

Plan frontmatter MUST include `execution_route.version`, `spec`, `executor`, `automation`, `concern_count`, `estimated_files`, `reason`, `safe_next_command`. Do NOT add `approved`/`approval` under `execution_route`; plan `status` is the approval source of truth.

## Pipeline classification

| Pipeline | Trigger | Steps |
| --- | --- | --- |
| `full` | New feature, refactor, >5 files | discover, architecture, risk, test-plan, spec, dispatch |
| `standard` | Enhancement, 3-5 files | discover, risk, spec, dispatch |
| `hotfix` | Bug fix, security patch, <3 files | discover, risk, spec, dispatch |
| `trivial` | Typo, comment, single-line | spec, dispatch |

## No-execution protocol

`/ai-plan` is planning-only. MUST NOT invoke `ai-build` / `/ai-build`, modify source, or check off implementation tasks. MAY write `plan.md` and run read-only exploration. Dispatch the `ai-plan` agent (`.claude/agents/ai-plan.md`, the interrogator handle) for any approved spec needing decomposition; hand off to `/ai-build` only after explicit approval.

## Common mistakes

- Planning HOW instead of WHAT.
- Omitting the `Patch (deterministic):` block on mechanical edits — costs `/ai-build` the cheap-tier dispatch.

## Examples

User: "the spec is approved, break it down into a phased plan"

```
/ai-plan
```

Reads `spec.md`, runs read-only exploration, decomposes into phases with agent assignments + gates, writes `plan.md`, emits the value block, and STOPs for approval.

## Integration

Called by: user directly, post-`/ai-brainstorm` approval. Calls: `ai-explore` agent (codebase context). Transitions to: `/ai-build` (only after user approves). See also: `/ai-brainstorm`, `/ai-build`, `/ai-autopilot` (multi-concern alternative).

$ARGUMENTS
