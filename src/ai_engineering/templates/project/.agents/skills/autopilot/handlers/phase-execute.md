# Handler: Execute Sub-Spec

## Purpose

Implement one sub-spec by: (1) planning tasks via the ai-plan pattern, (2) dispatching build agents via the ai-dispatch pattern, (3) committing the increment. Called once per sub-spec in the sequential loop from Step 2 of the parent skill.

## Thin Orchestrator Protocol

This handler does NOT contain implementation logic. It reads SKILL.md files from `/ai-dispatch` and `/ai-plan`, then embeds their instructions into subagent prompts. When those skills improve, this handler benefits automatically. No duplication, no drift.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Sub-spec | `.ai-engineering/specs/autopilot/sub-NNN.md` | Yes |
| Exploration context | `.ai-engineering/specs/autopilot/exploration.md` | Yes |
| Manifest | `.ai-engineering/specs/autopilot/manifest.md` | Yes |
| Decision constraints | `.ai-engineering/state/decision-store.json` | Yes |

## Procedure

### Step 1 -- Plan the Sub-Spec

Read `.claude/skills/ai-plan/SKILL.md` to load the current planning protocol.

Dispatch Agent(Plan) with a prompt composed from the plan skill's decomposition rules:

```yaml
agent: plan
context:
  sub_spec: "[contents of specs/autopilot/sub-NNN.md]"
  exploration: "[relevant section from exploration.md]"
  constraints: "[from decision-store.json]"
instructions: |
  Decompose this sub-spec into tasks following the ai-plan protocol:

  1. Each task MUST be bite-sized (2-5 min), single-agent, single-concern
  2. Each task MUST have a verifiable done condition
  3. Dependencies are explicit (T-M.2 blocked by T-M.1)
  4. TDD enforcement: paired RED/GREEN tasks where tests are needed
     - T-N: Write failing tests (RED)
     - T-N+1: Implement to pass tests (GREEN, blocked by T-N)
     - GREEN task constraint: "DO NOT modify test files from T-N"
  5. Assign agents per task: build (code r/w), verify (read-only scan)

  Write the sub-plan to: specs/autopilot/sub-NNN-plan.md

  Format:
    # Sub-Plan: sub-NNN [title]
    ## Tasks: N (build: N, verify: N)
    - T-M.1: [description] (agent: build) -- [done condition]
    - T-M.2: [description] (agent: build, blocked by T-M.1) -- [done condition]
output: "specs/autopilot/sub-NNN-plan.md"
```

Gate: Sub-plan exists and contains at least one task with a done condition.

### Step 2 -- Build the DAG

Read `.claude/skills/ai-dispatch/SKILL.md` to load the current execution protocol.

Parse the sub-plan and classify tasks:

**Independent** (dispatch in parallel):
- Different file scopes with no overlap
- No producer-consumer relationship
- No shared mutable state

**Dependent** (dispatch sequentially):
- Task B reads files Task A creates
- Task B depends on Task A output
- Both modify `.ai-engineering/` artifacts
- Explicit `blocked by` declarations

### Step 3 -- Execute Tasks

For each task (or parallel group), dispatch Agent(Build) with focused context:

```yaml
agent: build
context:
  task: "T-M.N"
  description: "[from sub-plan]"
  scope:
    files: ["[files from sub-spec scope]"]
    boundaries: ["Do NOT modify files outside scope"]
  constraints:
    - "[from decision-store.json]"
    - "[stack standards from contexts/languages/ and contexts/frameworks/]"
    - "[architectural patterns from exploration.md]"
  gate:
    post: ["[stack validation commands for detected stack]"]
instructions: |
  Implement this task following the ai-dispatch execution protocol.

  You receive fresh context -- no carry-over from previous tasks.
  Respect file scope boundaries. Do not modify files outside your scope.
  Follow existing patterns found in the exploration context.
```

After each task completes, run the two-stage review from the dispatch protocol:

**Stage 1 -- Spec Compliance:**
- Deliverable matches the task description
- Acceptance criteria from the sub-spec are satisfied
- No out-of-scope file modifications

**Stage 2 -- Code Quality:**
- Stack validation passes (auto-detected)
- No new lint warnings introduced
- Test coverage maintained or improved

If either stage fails: fix and re-review (max 2 retries per stage). If still failing after 2 retries: mark task BLOCKED, report to parent orchestrator.

Update sub-plan progress after each task:
```
- [x] T-M.1: [description] -- DONE
- [ ] T-M.2: [description] -- IN PROGRESS
```

### Step 4 -- Post-Implementation Validation

After all tasks in the sub-spec complete:

1. **Auto-fix formatting**: `ruff format .`
2. **Auto-fix lint**: `ruff check . --fix`
3. **Check for unfixable issues**: `ruff check .`
   - If unfixable issues remain: report them and mark sub-spec as `needs-attention` in manifest.md
   - Do NOT add suppression comments (`# noqa`, `# type: ignore`) -- fix the code
4. **Run affected tests**: `pytest tests/unit/ -q`
   - If tests fail: analyze failures, attempt fix (1 retry), then escalate

### Step 5 -- Commit the Increment

Stage only files within the sub-spec scope:

```bash
git add [specific files from sub-spec scope]
git commit -m "spec-NNN: sub-spec M -- [sub-spec title]"
```

Post-commit verification:
- `pytest tests/unit/ -q` passes
- `ruff check .` clean
- No untracked files that should have been committed

If post-commit verification fails: diagnose, fix, amend commit (one attempt), then escalate.

## Output

- Sub-plan written to `specs/autopilot/sub-NNN-plan.md`
- Code changes committed to branch
- Task progress updated in sub-plan checkboxes
- Manifest updated: sub-spec marked `complete` or `needs-attention`

## Gate

Sub-spec is complete when ALL hold: (1) all tasks DONE, (2) `ruff check .` clean, (3) `ruff format --check .` clean, (4) `pytest tests/unit/ -q` passes, (5) increment committed with correct message format, (6) manifest updated.

If any gate fails after retry: the parent orchestrator's Step 2b (phase-verify) handles escalation.
