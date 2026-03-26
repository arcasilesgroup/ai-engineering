# Handler: Phase 4 -- IMPLEMENT

## Purpose

Execute the implementation plan following the DAG. For each wave, dispatch the build agent per sub-spec in parallel. Each agent receives full context (sub-spec content, decision-store constraints, stack standards) and writes a Self-Report classifying every piece of work using the Transparency Protocol. Commits are made per wave. Failed sub-specs cascade-block their dependents in later waves.

## Prerequisites

- Phase 3 (Orchestrate) complete.
- Manifest at `specs/autopilot/manifest.md` contains a `## Execution DAG` section with wave assignments.
- All sub-specs targeted for implementation have enriched Exploration, Plan, and file ownership sections (populated by Phase 2 and refined by Phase 3).
- Decision-store at `state/decision-store.json` is readable (constraints apply to all agents).

## Procedure

### Step 1 -- Parse Execution DAG

Read `specs/autopilot/manifest.md`. Extract the `## Execution DAG` section. Parse:

- Wave numbers (Wave 1, Wave 2, ..., Wave N) in execution order.
- Sub-spec assignments per wave (which sub-specs execute in each wave).
- Dependency edges (which sub-specs depend on which -- used for cascade blocking in Step 5).
- Current status of each sub-spec (`planned`, `blocked`, `cascade-blocked`, `implemented`).

Build an in-memory wave execution plan:

```
Wave 1: [sub-001, sub-003]  (no dependencies)
Wave 2: [sub-002, sub-004]  (sub-002 depends on sub-001)
Wave 3: [sub-005]           (depends on sub-002, sub-004)
```

### Step 2 -- Execute Wave

For each wave in DAG order (Wave 1 first, then Wave 2, etc.):

#### 2a -- Skip Cascade-Blocked Sub-Specs

Check every sub-spec assigned to this wave. If a sub-spec has status `blocked` or `cascade-blocked`, skip it. Log the skip:

```
WAVE W: Skipping sub-NNN (cascade-blocked by sub-XXX)
```

If all sub-specs in the wave are blocked, the wave is empty. Log and proceed to the next wave -- cascade blocking in Step 5 will handle downstream effects.

#### 2b -- Dispatch the Build Agent Per Sub-Spec (Parallel)

For each non-blocked sub-spec in the wave, dispatch the build agent with a fresh context containing:

1. **Sub-spec scope and exploration** -- from `specs/autopilot/sub-NNN/spec.md` (Scope, Exploration, file ownership).
1b. **Sub-spec plan** -- from `specs/autopilot/sub-NNN/plan.md` (task checkboxes).
2. **Decision-store constraints** -- relevant entries from `state/decision-store.json` that apply to this sub-spec's domain.
3. **Stack standards** -- loaded from `contexts/languages/` and `contexts/frameworks/` matching the detected stack.
4. **File boundary enforcement** -- explicit instruction embedded in the agent prompt:

```
HARD BOUNDARY: You may ONLY modify these files:
  - [list of files from sub-NNN/spec.md frontmatter files: field]

Do NOT create, modify, or delete any file outside this list.
If your plan requires touching a file outside scope, STOP and
report the conflict. Do not proceed.
```

All agents in the wave dispatch in parallel. They do not share context with each other.

#### 2c -- Agent Executes Plan Tasks

Each build agent executes the plan tasks listed in its sub-spec's `plan.md`, in order. The agent follows standard build procedures:

- Write code following stack standards loaded from contexts.
- Run post-edit validation per the stack (ruff, tsc, cargo check, etc.).
- Fix validation failures (max 3 attempts per file, then report failure).
- Respect quality gates: no suppression comments, no weakened thresholds.

After completing task T-N.K, edit `specs/autopilot/sub-NNN/plan.md` to change `- [ ] T-N.K` to `- [x] T-N.K`.

#### 2d -- Agent Writes Self-Report

After completing (or failing) its plan tasks, each agent appends a `## Self-Report` section to `specs/autopilot/sub-NNN/plan.md` using the Transparency Protocol:

```markdown
## Self-Report

| File/Function | Classification | Notes |
|---------------|----------------|-------|
| phases/detect.py:DetectPhase | real | Full implementation with tests |
| phases/tools.py:check_auth() | stub | Returns True always, needs real impl |
| merge.py:validate_schema() | invented | Not in spec, added for safety |
| utils.py:format_output() | aspirational | Implemented but no tests yet |
```

**Classifications** (every item of work MUST be classified):

| Classification | Meaning |
|----------------|---------|
| `real` | Implemented and verified -- backed by passing tests or concrete evidence |
| `aspirational` | Implemented but not fully tested, or relying on unverified assumptions |
| `stub` | Placeholder only -- marked with `TODO` or raises `NotImplementedError` |
| `failing` | Implemented but tests, lint, or type checks fail on it |
| `invented` | Agent created something not in the spec (new helper, utility, pattern) |
| `hallucinated` | Agent referenced something that does not exist (phantom import, non-existent API, missing module) |

Self-Report rules:
- Every file touched or created by the agent MUST appear in the report.
- Every public function or class added MUST have its own row.
- The `hallucinated` classification is a signal for Phase 5 to investigate -- it means the agent may have written code that cannot compile or run.
- Agents MUST NOT classify their own work as `real` unless tests exist and pass. Untested code is `aspirational` at best.

### Step 3 -- Commit the Wave

After all agents in the wave complete (success or failure), commit the wave's changes:

```bash
git add [files from all sub-specs in this wave]
git commit -m "spec-NNN: wave W -- [comma-separated sub-spec titles]"
```

Commit scope:
- Include only files owned by sub-specs in this wave.
- Do not include manifest updates in the wave commit (those happen in Step 4).
- If a sub-spec agent failed, its partial changes are still committed (the Self-Report documents what is incomplete).

### Step 4 -- Update Manifest

After the wave commit, update `specs/autopilot/manifest.md`:

- Mark each successfully completed sub-spec in the wave as `implemented`.
- Mark each failed sub-spec (agent could not complete its plan) as `blocked`.
- Record the wave commit hash for traceability.

### Step 5 -- Cascade Blocking

For every sub-spec marked `blocked` in this wave:

1. Walk the DAG edges forward -- find all sub-specs in later waves that depend (directly or transitively) on the blocked sub-spec.
2. Mark each dependent as `cascade-blocked` in the manifest.
3. Record the blocking chain:

```
sub-004 cascade-blocked by sub-002 (blocked in Wave 2)
sub-006 cascade-blocked by sub-004 (cascade-blocked by sub-002)
```

Cascade-blocked sub-specs are never attempted. They appear in the Integrity Report (Phase 6) under a "Blocked / Undelivered" section with the full blocking chain.

Do NOT attempt to rescue cascade-blocked sub-specs by re-planning or re-scoping. That decision belongs to the user after reviewing the Integrity Report.

### Step 6 -- Proceed to Next Wave

Return to Step 2 with the next wave. Repeat until all waves are exhausted.

After the final wave, report to the orchestrator:

```
IMPLEMENT COMPLETE
- Waves executed: W
- Sub-specs implemented: X / N
- Sub-specs blocked: Y
- Sub-specs cascade-blocked: Z
- Wave commits: [list of commit hashes]
- Ready for Phase 5: QUALITY LOOP
```

## Output

Artifacts produced:
- Committed waves -- one commit per wave with implementation changes.
- Self-Reports -- appended to each `specs/autopilot/sub-NNN/plan.md`.
- Updated manifest -- `specs/autopilot/manifest.md` with `implemented`, `blocked`, or `cascade-blocked` statuses per sub-spec, plus wave commit hashes.

## Gate

A wave is complete when ALL of the following hold:

1. Every non-blocked sub-spec in the wave has a Self-Report written in its `plan.md`.
2. Every non-blocked sub-spec's changed files are committed.
3. The manifest is updated with statuses for all sub-specs in the wave.
4. Cascade blocking has been applied for any newly blocked sub-specs.

The phase is complete when all waves have been processed and the orchestrator report is emitted.

## Failure Modes

| Condition | Action |
|-----------|--------|
| Build agent fails (cannot complete plan tasks) | Mark sub-spec `blocked` in manifest. Write a partial Self-Report documenting what was completed and what failed. Continue with remaining sub-specs in the wave. |
| All sub-specs in a wave are blocked or cascade-blocked | Wave is empty. Log it. Proceed to the next wave. Cascade blocking propagates to dependents automatically. |
| Commit fails (pre-commit hook rejects) | Diagnose the failure. Apply automated fixes: `ruff format .`, `ruff check --fix .` for Python; equivalent for other stacks. Retry commit once. If second commit fails, report the hook failure and escalate to the orchestrator. |
| Agent violates file boundary (declared in `sub-NNN/spec.md` frontmatter `files:` field) | Agent MUST stop immediately and report the conflict. Do not commit boundary-violating changes. Mark the sub-spec `blocked` and cascade-block dependents. |
| Agent produces `hallucinated` classification | Not a blocking failure during Phase 4. The Self-Report flags it. Phase 5 (Quality Loop) will detect and address phantom references. |
| Agent exceeds 3 validation fix attempts on a file | Mark that file's work as `failing` in the Self-Report. Continue with remaining plan tasks. Do not block the entire sub-spec for a single file failure. |
| Manifest write fails (disk error, permissions) | STOP. Cannot proceed without persistent state. Escalate immediately -- pipeline integrity depends on manifest accuracy. |
