---
name: ai-autopilot
description: "Use when executing large approved specs autonomously: splits into focused sub-specs, explores deeply, implements with fresh-context agents, verifies anti-hallucination gates, and delivers via PR. Invocation IS approval."
effort: max
argument-hint: "'implement spec-NNN'|--resume|--no-watch"
mode: agent
tags: [orchestration, autonomous, multi-spec, pipeline, execution]
---



# Autopilot

## Purpose

Autonomous execution of large approved specs. Splits a spec with N work units into focused sub-specs, executes each sequentially with fresh-context agents, verifies every increment against anti-hallucination gates, and delivers the full changeset via PR. One invocation, zero interruptions.

## When to Use

- Spec has >5 tasks or touches >10 files
- After `/ai-brainstorm` approval and `/ai-plan` completion
- When manual `/ai-dispatch` would overflow context within a single session
- Multi-phase work that benefits from incremental verify gates

## When NOT to Use

- <5 tasks -- use `/ai-dispatch` directly
- Draft or unapproved spec -- run `/ai-brainstorm` first
- Need human review between phases -- use `/ai-dispatch` with manual checkpoints
- Cross-repo changes -- coordinate manually
- Data migrations with destructive DDL -- require explicit user approval per step

## Process

### Step 0: Load and Validate

1. Read `.ai-engineering/specs/spec.md` -- confirm it is not a placeholder
2. Read `.ai-engineering/specs/plan.md` -- confirm tasks exist
3. Read `.ai-engineering/state/decision-store.json` -- load constraints
4. If spec is placeholder or plan is empty: STOP. Report: "No approved spec. Run `/ai-brainstorm` first."

### Step 1: Split + Explore

Read `handlers/phase-split.md` and execute:

1. Decompose the spec into ordered sub-specs (one concern per sub-spec)
2. Write each to `.ai-engineering/specs/autopilot/sub-NNN.md` with: scope, inputs, outputs, verify checklist
3. Write execution manifest to `.ai-engineering/specs/autopilot/manifest.md`
4. Dispatch parallel Agent(Explore) to map codebase state relevant to each sub-spec
5. Collect findings into `.ai-engineering/specs/autopilot/exploration.md`
6. Update sub-specs with discovered file paths, patterns, and constraints

### Step 2: Execute Loop (sequential, per sub-spec)

For each sub-spec in manifest order:

**2a. Plan + Implement** -- Read `handlers/phase-execute.md` and execute:
- Read the sub-spec and relevant SKILL.md files
- Compose the build prompt with embedded context (file paths, patterns, constraints, acceptance criteria)
- Dispatch Agent(Build) with fresh context -- no carry-over from previous sub-specs
- Build agent receives: sub-spec scope, referenced files, stack standards, verify checklist

**2b. Verify** -- Read `handlers/phase-verify.md` and execute:
- Dispatch Agent(Verify) against the sub-spec's acceptance criteria
- Gate checklist: functional correctness, anti-hallucination (files/functions/imports exist), stack validation (linters/types), no regressions (existing tests pass)
- If verify passes: commit the increment, update manifest.md marking sub-spec complete
- If verify fails: retry implementation ONCE with the failure report embedded in the build prompt
- If second attempt also fails: **STOP the entire pipeline**. Report: what was attempted, what failed, the verify report, and rollback instructions

### Step 3: Final Verification

After all sub-specs complete:

1. Run full test suite: `pytest tests/ -v`
2. Run full lint pass: `ruff check` + `ruff format --check`
3. Run type check: `ty check src/`
4. Dispatch Agent(Verify) on the full changeset against the original spec
5. Confirm no regressions against main branch
6. If final verify fails: escalate -- do not attempt to fix at this stage

### Step 4: PR Pipeline

Read `handlers/phase-pr.md` and execute:

1. Follow `.github/prompts/ai-pr.prompt.md` in full
2. PR body includes: summary of all sub-specs delivered, verify reports as evidence
3. Enable auto-complete with squash merge
4. Enter watch-and-fix loop (unless `--no-watch`)

### Step 5: Cleanup

After PR merges (or immediately if `--no-watch`):

1. Delete `.ai-engineering/specs/autopilot/` directory
2. Clear `specs/spec.md` with placeholder
3. Clear `specs/plan.md` with placeholder
4. Run `/ai-cleanup --all`

## Handler Dispatch Table

| Phase | Handler | Agent Pattern |
|-------|---------|---------------|
| Split + Explore | `handlers/phase-split.md` | Explore x N parallel |
| Execute | `handlers/phase-execute.md` | Plan + Build per sub-spec |
| Verify | `handlers/phase-verify.md` | Verify per sub-spec |
| PR + Deliver | `handlers/phase-pr.md` | PR pipeline |

## Flags

| Flag | Behavior |
|------|----------|
| `--resume` | Read `specs/autopilot/manifest.md`, find last incomplete sub-spec, continue from there. Skip already-completed sub-specs. |
| `--no-watch` | Create PR without the watch-and-fix loop (step 14 of ai-pr). Useful for draft delivery or when CI is managed externally. |

## Thin Orchestrator Principle

This skill READS other skills' SKILL.md files and EMBEDS their instructions into subagent prompts. It does NOT contain implementation logic. The phases delegate to:

- `/ai-dispatch` patterns for task execution
- `/ai-verify` for anti-hallucination gates
- `/ai-pr` for pull request creation and delivery
- `/ai-commit` for incremental commit protocol

When those skills improve, autopilot benefits automatically. No duplication, no drift.

## Governance

DEC-023: User invocation of `/ai-autopilot` is the single approval gate. All internal gates (spec validation, sub-spec review, verify gates) are automatic and cannot be bypassed.

State transitions are recorded on disk in `specs/autopilot/manifest.md` -- never in agent memory. Any phase can be audited post-hoc.

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Verify fails 2x on a sub-spec | Pipeline halts. Report includes: sub-spec, attempts, verify reports, rollback command. |
| Mid-pipeline crash | Run `/ai-autopilot --resume`. Reads manifest.md, continues from last incomplete sub-spec. |
| Final verify fails | Escalate to user. Do not attempt fixes on the assembled changeset. |
| PR watch loop fails 3x | Escalate per ai-pr handler protocol. |

Rollback: `git reset --soft HEAD~N` where N = number of sub-spec commits. Included in failure reports.

## Telemetry

Events emitted at each phase transition via hook system:

| Event | Trigger |
|-------|---------|
| `autopilot.started` | Step 0 completes |
| `autopilot.split_complete` | Step 1 completes |
| `autopilot.subspec_complete` | Each sub-spec passes verify |
| `autopilot.subspec_failed` | Sub-spec fails verify 2x |
| `autopilot.final_verify` | Step 3 completes |
| `autopilot.pr_created` | Step 4 completes |
| `autopilot.done` | Step 5 completes |

## Quick Reference

```
/ai-autopilot "implement spec-062"     # full pipeline
/ai-autopilot --resume                  # continue from failure
/ai-autopilot "spec" --no-watch         # skip PR watch loop
```

## Common Mistakes

- Running on draft or unapproved specs -- brainstorm approval is a hard prerequisite.
- Running on specs with <5 tasks -- use `/ai-dispatch` instead, autopilot overhead is not justified.
- Cross-repo work -- autopilot operates within a single repository.
- Skipping the verify gate -- every sub-spec MUST pass verify before the next begins.
- Carrying context between sub-specs -- each build agent gets fresh context by design.
- Attempting to fix failures after final verify -- escalate, do not compound errors.

## Integration

- **Called by**: user directly (after `/ai-brainstorm` + `/ai-plan` approval)
- **Reads**: `ai-dispatch/SKILL.md`, `ai-verify/SKILL.md`, `ai-pr/SKILL.md`, `ai-commit/SKILL.md`
- **Delegates to**: Agent(Explore) for research, Agent(Build) for implementation, Agent(Verify) for gates
- **Transitions to**: `/ai-cleanup` after merge, or back to user on failure

$ARGUMENTS

---

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

Read `.github/prompts/ai-plan.prompt.md` to load the current planning protocol.

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

Read `.github/prompts/ai-dispatch.prompt.md` to load the current execution protocol.

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

---

# Handler: Deep Explore

## Purpose

Dispatch Agent(Explore) x N in parallel to gather deep codebase context for each sub-spec before implementation begins. Enriches every sub-spec with architectural context so that build agents receive full situational awareness on first attempt.

## Prerequisites

- Phase Split is complete
- Sub-spec files exist at `specs/autopilot/sub-NNN.md`
- Each sub-spec contains a `files:` list and `## Scope` section

## Procedure

### Step 1 -- Load Sub-Specs

1. Glob `specs/autopilot/sub-*.md` to discover all sub-spec files.
2. For each sub-spec, extract:
   - `files:` list (files to create or modify)
   - `## Scope` section content
   - Sub-spec number (NNN from filename)
3. If no sub-specs found: STOP. Report: "No sub-specs found. Run phase-split first."

### Step 2 -- Dispatch Explorers

For each sub-spec, launch Agent(Explore) with `run_in_background: true` using this prompt:

```
Gather implementation context for sub-spec NNN.

**Files to create/modify:**
{files list from sub-spec}

**Sub-spec scope:**
{scope section from sub-spec}

Explore the codebase to understand:
1. Full context of files that will be modified (read them entirely)
2. Existing patterns for similar functionality nearby
3. Callers and importers of functions that will change
4. Reusable utilities, helpers, and conventions in scope
5. Test patterns used in this area of the codebase

Time-box: 2-3 minutes.

Output: structured context report with absolute file paths and patterns found.
```

All N explorers run in parallel. Do NOT wait for one to finish before launching the next.

### Step 3 -- Collect and Enrich

Wait for all explorers to complete. For each explorer result:

1. Read the explorer output.
2. Append an `## Architectural Context` section to the corresponding sub-spec file containing:
   - **Patterns found**: design patterns, naming conventions, structural idioms in scope
   - **Dependencies mapped**: import chains, coupling points, callers of modified functions
   - **Utilities to reuse**: existing helpers, shared modules, test fixtures available
   - **Key files read**: absolute paths with one-line annotations
3. Write the enriched sub-spec back to disk.

### Step 4 -- Validate Enrichment

For each sub-spec file:

1. Confirm `## Architectural Context` section exists and is non-empty.
2. Reject placeholder content -- if any section contains only "TODO", "TBD", or "N/A", re-dispatch a single explorer for that sub-spec with a narrower prompt.
3. After re-dispatch (max 1 retry per sub-spec), if context is still empty: mark the sub-spec with `context: partial` and proceed. Do not block the pipeline.

## Output

- Every sub-spec file enriched with `## Architectural Context`
- Exploration summary appended to `specs/autopilot/exploration.md`
- Pipeline ready to proceed to Phase 2 (Execute Loop)

## Failure Modes

| Condition | Action |
|-----------|--------|
| Explorer times out | Mark sub-spec `context: partial`, proceed |
| Explorer returns empty output | Retry once with narrower scope |
| All explorers fail | STOP. Report: "Exploration failed for all sub-specs." |
| Sub-spec file missing after split | STOP. Report: "Sub-spec NNN missing. Re-run phase-split." |

---

# Handler: PR + Deliver

## Purpose

Execute the final delivery pipeline: commit gates, push, create PR, optionally watch until merge, and clean up autopilot state. This handler reads ai-pr and ai-commit SKILL.md files and follows their instructions. It does NOT reimplement the PR pipeline.

## Prerequisites

- All sub-specs in `specs/autopilot/manifest.md` marked complete
- Final verification (Step 3 of parent skill) passed
- All sub-spec commits exist on the current branch
- Current branch is NOT main/master

## Procedure

### Step 1 -- Pre-Push Gates

Read `.github/prompts/ai-pr.prompt.md` steps 7-7.5. Execute:

1. `ruff check .` and `ruff format --check .`
2. `gitleaks protect --staged --no-banner`
3. `pytest tests/unit/ -v`
4. `sync_command_mirrors.py --check` (if script exists)

If any check fails: fix and retry once. If still failing: STOP and report which gate failed with full output.

### Step 2 -- Push

1. Confirm current branch is not `main`/`master`. If it is: STOP.
2. `git push -u origin <current-branch>`
3. If push fails (e.g., rejected): report and STOP.

### Step 3 -- Create PR

Read `.github/prompts/ai-pr.prompt.md` steps 10-12.

1. **Detect VCS provider**: check `manifest.yml` -> `providers.vcs.primary`, fallback to `git remote get-url origin`.
2. **Check for existing PR**: `gh pr list --head <branch> --json number --state open`.
3. **Create PR** with structured body:

```markdown
## Summary
- [What the autopilot implemented -- derived from parent spec title and scope]
- [Key architectural decisions or patterns applied]

## Sub-Specs Completed
| # | Title | Status |
|---|-------|--------|
| sub-001 | [title] | VERIFIED |
| sub-002 | [title] | VERIFIED |
| ... | ... | ... |

## Test Plan
- [ ] [Verification results from final verify pass]
- [ ] [Regression check against main]
- [ ] [Lint, type check, secret scan all clean]

## Telemetry
- Sub-specs: N completed, 0 failed
- Duration: Xm (from autopilot start to PR creation)
- Verify passes: N/N
```

If existing PR found: extend body per ai-pr protocol (append, never overwrite).

### Step 4 -- Auto-Complete

- **GitHub**: `gh pr merge --auto --squash --delete-branch`
- **Azure DevOps**: `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true`

### Step 5 -- Watch (unless --no-watch)

If `--no-watch` flag was passed: skip to Step 6.

Read `.github/prompts/ai-pr.prompt.md` step 14 and execute the full watch-and-fix loop:

- Poll every 60s (active) or 180s (passive)
- Autonomously fix CI failures via commit pipeline (ai-commit steps 0-6)
- Autonomously resolve merge conflicts via rebase with `--force-with-lease`
- Escalate after 3 failed fix attempts on the same check
- Exit on merge, close, or escalation

### Step 6 -- Cleanup

After merge (or immediately if `--no-watch`):

1. Delete `specs/autopilot/` directory entirely: `rm -rf .ai-engineering/specs/autopilot/`
2. Clear `specs/spec.md`:
   ```
   # No active spec

   Run /ai-brainstorm to start a new spec.
   ```
3. Clear `specs/plan.md`:
   ```
   # No active plan

   Run /ai-plan after brainstorm approval.
   ```
4. Stage and commit cleanup: `chore: clear autopilot state after spec-NNN delivery`
5. Run `/ai-cleanup --all` -- switch to default branch, pull, delete merged branch.

### Step 7 -- Final Report

```
Autopilot Complete!

Spec: spec-NNN -- [title]
Sub-specs: N completed, 0 failed
Duration: Xm
PR: #NNN (merged|pending)

Sub-specs delivered:
1. sub-001: [title] -- VERIFIED
2. sub-002: [title] -- VERIFIED
...
```

## Output

- PR created (and merged if watch enabled)
- `specs/autopilot/` cleaned up
- `specs/spec.md` and `specs/plan.md` reset to placeholders
- Repository on default branch, up to date

## Failure Modes

| Condition | Action |
|-----------|--------|
| Pre-push gate fails 2x | STOP. Report gate name and output |
| Push rejected | STOP. Report error |
| PR creation fails | STOP. Report VCS provider error |
| Watch loop escalates (3x same check) | STOP per watch.md protocol |
| Cleanup fails | Warn but do not block -- PR is already delivered |

---

# Handler: Split + Explore

## Purpose

Take a large approved spec and decompose it into N focused sub-specs (max 3-5 tasks each), then enrich each with deep codebase exploration. Every sub-spec must be independently implementable by a fresh-context agent that reads only the sub-spec file and the referenced source files.

## Inputs

- `specs/spec.md` -- the approved parent spec
- `specs/plan.md` -- the task breakdown (if exists)
- `state/decision-store.json` -- active constraints

## Procedure

### Step 1 -- Analyze the Spec

Read `specs/spec.md` end-to-end. Extract:

1. **Work units**: every discrete implementation item (a file to create, a file to modify, a config entry to add, a test to write). Number them sequentially: W-001, W-002, ...
2. **Dependency edges**: for each work unit, note which other work units it reads from, writes to, or imports. Record as `W-003 -> W-007` (003 must complete before 007).
3. **File manifest**: for each work unit, list every file it will create or modify. One work unit may touch multiple files; one file must belong to exactly one work unit.

If `specs/plan.md` exists and has checkable items, cross-reference. Every plan item must map to at least one work unit. Flag orphans.

### Step 2 -- Determine Split Strategy

Evaluate three grouping strategies against the work units:

| Strategy | Rule | Best when |
|----------|------|-----------|
| **By domain** | Group by functional area (contexts, skills, handlers, config, tests) | Spec spans multiple system layers |
| **By dependency** | Group items that form a dependency chain together | Spec has deep sequential dependencies |
| **By file scope** | Group items that touch the same files or directories | Spec modifies many files with clear ownership boundaries |

Choose the strategy that minimizes cross-sub-spec file conflicts. If two strategies tie, prefer by-dependency -- it produces the most predictable execution order.

Document the choice and reasoning in one line:
```
Split strategy: [by-domain|by-dependency|by-file-scope] -- [one sentence why]
```

### Step 3 -- Form Groups

Apply the chosen strategy. Assign each work unit to exactly one group.

**Hard constraints:**
- Each group has 3-5 work units (split large groups, merge small ones)
- No file appears in more than one group
- Dependency edges between groups flow in one direction (no cycles)
- Groups are numbered in execution order: group 1 has no dependencies on later groups

**Soft preferences:**
- Keep related tests in the same group as their implementation
- Keep config/registry updates in the group that creates the thing being registered
- If a file is read by multiple groups but written by one, assign it to the writer

### Step 4 -- Generate Sub-Specs

Create `specs/autopilot/` directory. For each group, write `specs/autopilot/sub-NNN.md`:

```markdown
---
id: sub-NNN
parent: spec-XXX
title: "Sub-spec title"
status: pending
files:
  - path/to/file-1.ext
  - path/to/file-2.ext
depends_on: []
---

# Sub-Spec NNN: [title]

## Scope

[2-3 sentences: what this sub-spec implements from the parent spec. Reference parent spec sections by name.]

## Work Units

- W-XXX: [description]
- W-YYY: [description]

## Files

| Action | Path | Notes |
|--------|------|-------|
| create | path/to/new-file.ext | [what it contains] |
| modify | path/to/existing.ext | [what changes] |

## Acceptance Criteria

- [ ] [Testable criterion -- one per work unit minimum]
- [ ] [Additional criteria from parent spec that apply to this sub-spec]

## Dependencies

[Which sub-specs must complete before this one, or "None -- first in sequence."]

## Architectural Context

[Populated by Step 5. Left blank during generation.]
```

Number sub-specs with zero-padded three-digit IDs: sub-001, sub-002, ... sub-NNN.

### Step 5 -- Deep Explore

For each sub-spec, dispatch an Agent(Explore) in parallel. Each explorer receives:

**Prompt**: "Read sub-spec `specs/autopilot/sub-NNN.md`. For every file listed in the Files table:"

1. **If the file exists**: read it. Summarize its current structure (exports, classes, key functions). Note the patterns it follows (naming conventions, import style, error handling).
2. **If the file will be created**: find the closest existing analog in the codebase. Read it. Document the pattern to replicate.
3. **Map dependencies**: for each file, find who imports it (`Grep` for the module name) and what it imports. List direct dependents.
4. **Identify patterns**: read one existing file of the same type (e.g., if creating a handler, read an existing handler). Extract the template: frontmatter schema, section order, tone, line count range.
5. **Check for conflicts**: verify no other sub-spec lists the same files. If conflict found, report it -- do not resolve.

Each explorer appends its findings to the sub-spec's `## Architectural Context` section:

```markdown
## Architectural Context

### Existing Files
- `path/to/file.ext`: [summary of current state, key exports, line count]

### Patterns to Follow
- [Pattern name]: [file that exemplifies it] -- [what to replicate]

### Dependencies Map
- `module.name` imported by: [list of importers]
- `module.name` imports: [list of dependencies]

### Risks
- [Any discovered constraint or conflict]
```

### Step 6 -- Validate

Run these checks. All must pass before proceeding.

1. **Existence**: every `specs/autopilot/sub-NNN.md` file exists and has >30 lines
2. **Coverage**: every work unit (W-XXX) from Step 1 appears in exactly one sub-spec
3. **No overlap**: no file path appears in the Files table of more than one sub-spec
4. **Valid DAG**: sub-spec dependency order contains no cycles (if sub-002 depends on sub-001, sub-001 must not depend on sub-002 or any successor of sub-002)
5. **Enriched**: every sub-spec has a non-empty `## Architectural Context` section

If any check fails:
- Overlap or coverage gap: reassign the conflicting work unit and regenerate affected sub-specs
- Cycle: reorder groups to break the cycle
- Missing context: re-run the explorer for that sub-spec
- Max 2 fix attempts. If still failing after 2: STOP and report the validation failures to the orchestrator

## Output

```
specs/autopilot/sub-001.md
specs/autopilot/sub-002.md
...
specs/autopilot/sub-NNN.md
```

Report to orchestrator:
```
Split complete.
- Strategy: [chosen strategy]
- Sub-specs: N
- Work units: M (distributed across N sub-specs)
- Estimated complexity: [low|medium|high] per sub-spec
- Dependency chain depth: D (longest path through the DAG)
- Validation: all 5 checks passed
```

## Anti-Patterns

- Generating sub-specs without reading the parent spec first (always start from spec.md)
- Splitting too fine (1-2 work units per sub-spec creates overhead without value)
- Splitting too coarse (6+ work units defeats the purpose of splitting)
- Assigning the same file to multiple sub-specs (guaranteed merge conflicts)
- Skipping the explore phase (agents without context hallucinate file paths and APIs)
- Hand-waving acceptance criteria (every criterion must be verifiable by a command or assertion)
- Creating circular dependencies between sub-specs (makes sequential execution impossible)

---

# Handler: Verify Sub-Spec (Anti-Hallucination Gate)

## Purpose

Verify that a sub-spec implementation is real and functional -- not hallucinated, incomplete, or disconnected. This is the quality gate between sub-specs.

## Why This Exists

AI agents can:
- Create files that exist but are never imported or called (dead code)
- Write functions with correct signatures but wrong behavior
- Reference modules that do not exist (phantom imports)
- Mark tasks DONE without the code actually working

This gate catches those failures BEFORE moving to the next sub-spec.

## Procedure

### Step 1 -- Read Verify Pattern

Read `.github/prompts/ai-verify.prompt.md`. Use the IRRV protocol (Identify, Run, Read, Verify) as the foundation for every check below. No claim without evidence.

### Step 2 -- Collect Evidence

Get the list of files changed in this sub-spec:

```bash
git diff HEAD~1 --name-only
```

Load the sub-spec from `.ai-engineering/specs/autopilot/sub-NNN.md` and extract its `files:` list and acceptance criteria.

### Step 3 -- Dispatch Verify Agent

Dispatch Agent(Verify) with the changed files and this five-level checklist.

**Level 1: Existence**
- [ ] Every file listed in sub-spec `files:` exists on disk
- [ ] No file is empty (>10 lines of actual content, not just headers)
- [ ] File extensions match expected types

**Level 2: Syntax**
- [ ] `ruff check .` passes with zero errors
- [ ] `ruff format --check .` reports no changes needed
- [ ] For YAML files: valid YAML (`python -c "import yaml; yaml.safe_load(open(f))"`)
- [ ] For JSON files: valid JSON (`python -c "import json; json.load(open(f))"`)

**Level 3: Integration**
- [ ] No phantom imports: for each `import X` or `from X import Y` in new code, verify X exists
- [ ] No dead code: every new function/class is referenced from at least one other file
- [ ] For skills: routing table references match handler files on disk
- [ ] For handlers: cross-references to other handlers/skills resolve
- [ ] `sync_command_mirrors.py --check` reports zero drift (if applicable)

**Level 4: Functional**
- [ ] `pytest tests/unit/ -q` passes
- [ ] If new test files were created: they run and pass
- [ ] Sub-spec acceptance criteria from `sub-NNN.md` are met

**Level 5: Consistency**
- [ ] `scripts/check_test_mapping.py` passes (new tests mapped)
- [ ] Manifest counts match disk reality
- [ ] No CLAUDE.md/AGENTS.md counter drift

### Step 4 -- Evaluate Results

**ALL PASS**: Mark sub-spec as VERIFIED in `specs/autopilot/manifest.md`, continue to next.

**Level 1-2 failures** (auto-fixable):
1. Run `ruff check . --fix` and `ruff format .`
2. Re-check once
3. If still failing: treat as Level 3-5 failure

**Level 3-5 failures** (structural):
1. Report findings with evidence: which check failed, file path, line number, error message
2. If first failure for this sub-spec: retry the execute phase with the failure report embedded in the build prompt
3. If second failure: STOP the autopilot pipeline. Report to user with:
   - Sub-spec identifier
   - Both verify reports (attempt 1 and attempt 2)
   - Specific checks that failed and why
   - Rollback command: `git reset --soft HEAD~N`

## Output

```
--- Verify: sub-NNN ---
Level 1 (Existence):  PASS | FAIL (details)
Level 2 (Syntax):     PASS | FAIL (details)
Level 3 (Integration): PASS | FAIL (details)
Level 4 (Functional): PASS | FAIL (details)
Level 5 (Consistency): PASS | FAIL (details)
Verdict: VERIFIED | RETRY (attempt 1/2) | FAILED (pipeline halted)
---
```

## Behavioral Negatives (Must NOT)

- Weaken or skip any check level to force a pass
- Modify test assertions to make tests pass
- Claim VERIFIED without running every applicable check
- Use forbidden words: "should work", "looks good", "probably fine"
- Proceed to the next sub-spec on a FAILED verdict
- Retry more than once (2 total attempts max, then escalate)
