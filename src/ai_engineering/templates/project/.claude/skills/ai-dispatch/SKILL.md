---
name: ai-dispatch
description: "Use this skill to construct a task dependency DAG from plan.md and dispatch"
---


# Dispatch

## Purpose

Construct a task dependency DAG from plan.md and produce structured dispatch entries for agent assignment. Replaces implicit English-text dispatch ("now run build on these files") with a formal schema that the execute agent can follow deterministically. This skill builds the dispatch plan; the execute agent runs it.

Owned by the **execute agent**. Formalizes the dispatch step that execute performs before coordinating agents.

## Trigger

- Command: `/ai:dispatch`
- Context: an approved plan exists (plan.md + tasks.md) and the execute agent needs a structured dispatch plan before running phases.
- Typically invoked by the execute agent as its first step, or by a human who wants to review the dispatch plan before execution.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"dispatch"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## Procedure

### Step 1 -- Read Plan and Tasks

Load the active spec's execution artifacts:

1. Read `context/specs/_active.md` to identify the current spec.
2. Read `plan.md` for phase ordering, agent assignments, and architecture decisions.
3. Read `tasks.md` for the checkbox task list with phase groupings.
4. Read `decision-store.json` for constraints that affect dispatch (e.g., serialization requirements, blocked paths).

If no active spec exists: STOP. Output: "No active plan found. Run `/ai:plan` first."

### Step 2 -- Parse Task Structure

Extract tasks from tasks.md into a structured list:

- **Task ID**: derived from phase + sequence (e.g., `P1.1`, `P2.3`)
- **Description**: the task text from the checkbox line
- **Phase**: which phase the task belongs to
- **Agent**: assigned agent from plan.md (build, scan, release, write, observe)
- **Status**: `pending`, `in-progress`, or `done` (from checkbox state)
- **File scope**: files or patterns the task will touch (inferred from description and plan architecture)

Skip tasks already marked `[x]` (done). They do not need dispatch.

### Step 3 -- Build Dependency DAG

Determine execution order by analyzing task dependencies:

**Independence test** -- two tasks are independent (parallelizable) when:
- They touch different files or directories
- Neither produces output consumed by the other
- They belong to different modules with no shared state

**Dependency test** -- two tasks are dependent (must serialize) when:
- Task B reads a file that Task A creates or modifies
- Task B depends on Task A's output (e.g., "update config" before "run migration")
- Plan.md explicitly states ordering (e.g., "Phase 2 after Phase 1 gate")
- Both tasks modify the same governance artifact (`.ai-engineering/` files must serialize)

**DAG construction**:
- Group independent tasks into **parallel groups** (can run simultaneously)
- Chain dependent tasks into **serial chains** (must run in order)
- Respect phase boundaries: all tasks in Phase N must complete before Phase N+1 starts

### Step 4 -- Construct Dispatch Entries

For each task (or parallel group), produce a structured dispatch entry:

```yaml
dispatch:
  phase: <phase-id>          # e.g., "P1", "P2"
  agent: <agent-name>        # e.g., "build", "scan", "release"
  tasks: [<task-ids>]        # e.g., ["P1.1", "P1.2"]
  scope:
    files: [<file patterns>] # e.g., ["src/commands/*.py", "tests/test_commands.py"]
    boundaries: [<exclusions>] # e.g., ["Do NOT modify install.sh", "Do NOT touch hooks/"]
  gate:
    pre: [guard.gate]        # gates to pass before starting
    post: [verify.quality]   # gates to pass after completing
  on_failure: escalate | retry | skip_and_log
```

**Field rules**:
- `agent`: must match a known agent from `agents/` directory.
- `scope.files`: be as specific as possible. Glob patterns are acceptable.
- `scope.boundaries`: explicitly state what the agent must NOT touch. Prevents scope creep.
- `gate.pre`: typically `guard.gate` (pre-flight checks). Add `security.scan` for security-sensitive tasks.
- `gate.post`: typically `verify.quality` (lint, type check, tests). Add `verify.coverage` for test tasks.
- `on_failure`: default to `escalate`. Use `retry` only for idempotent tasks. Use `skip_and_log` only for non-blocking tasks explicitly marked optional in the plan.

### Step 5 -- Validate Dispatch Plan

Before presenting the dispatch plan, validate it:

1. **Capability match**: verify each agent has the capabilities required by its assigned tasks. Cross-reference against the agent's `capabilities` list in its frontmatter. Flag mismatches.
2. **Coverage check**: every pending task in tasks.md must appear in exactly one dispatch entry. No task left unassigned, no task assigned twice.
3. **Cycle detection**: verify the DAG has no circular dependencies. If cycles are found, report the cycle and ask the human to resolve the ordering.
4. **Boundary conflicts**: verify no two parallel tasks have overlapping file scopes. If overlap is found, serialize them.

### Step 6 -- Present Dispatch Plan

Output the complete dispatch plan as YAML, with a summary header:

```markdown
## Dispatch Plan: spec-NNN

**Tasks**: X pending (Y parallel groups, Z serial chains)
**Agents**: [list of agents involved]
**Estimated phases**: N
**Validation**: PASS | FAIL (with details)

### Phase 1: <phase name>

[Dispatch entries for Phase 1 as YAML blocks]

### Phase 2: <phase name>

[Dispatch entries for Phase 2 as YAML blocks]
```

The execute agent reads this plan and coordinates agent dispatch accordingly.

## Output

- Structured dispatch plan (YAML blocks in markdown)
- Presented in conversation for human review, or written to plan.md as an appendix if the human approves
- The execute agent uses this as its coordination blueprint

## Limitations

- This skill formalizes the **human's dispatch experience** -- it structures what execute already does implicitly.
- True programmatic dispatch (machine-readable DAG with automated agent invocation) is aspirational and tracked as spec-052.
- Dispatch entries are consumed by the execute agent within a single Claude Code session. Cross-session dispatch requires checkpoint recovery.
- The skill cannot validate that agents will succeed -- it only validates that the plan is structurally sound.

## When NOT to Use

- **No plan exists** -- use `/ai:plan` first to create plan.md and tasks.md.
- **Trivial changes** -- single-task changes do not need a DAG. Execute directly.
- **Active execution** -- do not re-dispatch mid-execution. Complete or checkpoint the current plan first.

## Examples

### Example 1: Multi-phase feature spec

Active spec has 3 phases, 8 tasks, 2 agents (build + scan).

1. **Parse**: 8 tasks extracted, 2 already done, 6 pending.
2. **DAG**: Phase 2 has 3 independent build tasks (different files) -> parallel group. Phase 3 has scan depending on all builds -> serial after Phase 2.
3. **Dispatch**: 2 parallel build entries for Phase 2, 1 scan entry for Phase 3.
4. **Validate**: all agents have required capabilities, no file overlaps in parallel group.
5. **Output**: structured plan with 2 phases, 3 dispatch entries.

### Example 2: Governance change requiring serialization

Active spec modifies 3 governance files in `.ai-engineering/`.

1. **Parse**: 3 tasks, all touching `.ai-engineering/` directory.
2. **DAG**: governance files must serialize (framework rule). All 3 tasks become a serial chain.
3. **Dispatch**: 3 sequential dispatch entries, each with `gate.post: [verify.integrity]`.
4. **Validate**: no parallel groups (correct for governance changes).

## References

- `.claude/skills/ai-plan/SKILL.md` -- produces the plan.md that dispatch reads.
- `.claude/agents/ai-build.md` -- primary dispatch target for implementation tasks.
- `.claude/agents/ai-verify.md` -- dispatch target for quality and security validation.
- `standards/framework/core.md` -- governance rules for serialization requirements.
$ARGUMENTS
