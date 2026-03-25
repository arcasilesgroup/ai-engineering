---
name: ai-autopilot
description: "Use when executing large approved specs autonomously: decomposes into focused sub-specs, deep-plans each with parallel agents, builds a DAG, implements in waves, runs a quality convergence loop (verify+guard+review x3), and delivers via PR with full integrity report. Invocation IS approval."
effort: max
argument-hint: "'implement spec-NNN'|--resume|--no-watch"
mode: agent
tags: [orchestration, autonomous, multi-spec, pipeline, execution, dag, transparency]
---



# Autopilot v2

## Purpose

Autonomous execution of large approved specs via a 6-phase pipeline. Decomposes a spec into N focused sub-specs, deep-plans each with parallel agents, orchestrates a dependency-aware execution DAG, implements in waves, converges on quality through iterative verify+guard+review loops, and delivers the full changeset via PR with a transparency report. One invocation, zero interruptions, full disclosure.

## When to Use

- Spec has >= 3 independent concerns or touches >= 10 files
- After `/ai-brainstorm` approval (spec.md exists and is not a placeholder)
- When manual `/ai-dispatch` would overflow context within a single session
- Multi-concern work that benefits from parallel intelligence gathering and DAG-driven execution

## When NOT to Use

- < 3 concerns -- use `/ai-dispatch` directly (autopilot overhead not justified)
- Draft or unapproved spec -- run `/ai-brainstorm` first
- Need human review between phases -- use `/ai-dispatch` with manual checkpoints
- Cross-repo changes -- coordinate manually
- Data migrations with destructive DDL -- require explicit user approval per step

## Process

### Step 0: Load and Validate

1. Read `.ai-engineering/specs/spec.md` -- confirm it is not a placeholder
2. Read `.ai-engineering/state/decision-store.json` -- load constraints
3. If spec is placeholder: STOP. Report: "No approved spec. Run `/ai-brainstorm` first."
4. If `--resume` flag: read `specs/autopilot/manifest.md` and jump to the Resume Protocol (Phase 6 handler)
5. Note: plan.md is NOT required. Phase 2 agents generate their own plans (D7).

### Step 1: DECOMPOSE

Read `handlers/phase-decompose.md` and execute:

1. Extract N independent concerns from the spec
2. If N < 3: abort, recommend `/ai-dispatch`
3. Write sub-spec shells to `specs/autopilot/sub-NNN.md`
4. Write execution manifest to `specs/autopilot/manifest.md`

### Step 2: DEEP PLAN

Read `handlers/phase-deep-plan.md` and execute:

1. Dispatch N Agent(Explore+Plan) in parallel -- one per sub-spec
2. Each agent deep-explores the codebase and writes a detailed plan with exports/imports declarations
3. Gate: every sub-spec has enriched Exploration + Plan sections
4. Failed agents retry once, then mark `plan-failed`

### Step 3: ORCHESTRATE

Read `handlers/phase-orchestrate.md` and execute:

1. Analyze all N plans together
2. Build file-overlap matrix and import-chain graph
3. Construct execution DAG with wave assignments
4. Merge sub-specs with unresolvable conflicts

### Step 4: IMPLEMENT

Read `handlers/phase-implement.md` and execute:

1. For each wave in DAG order: dispatch Agent(Build) per sub-spec (parallel within wave)
2. Each agent writes a Self-Report (real/aspirational/stub/failing/invented/hallucinated)
3. Commit per wave, update manifest
4. Cascade-block dependents of failed sub-specs

### Step 5: QUALITY LOOP

Read `handlers/phase-quality.md` and execute:

1. Dispatch Agent(Verify) + Agent(Guard) + Agent(Review) in parallel on full changeset
2. Consolidate findings with unified severity mapping
3. If clean (0 blockers+criticals+highs): proceed to Phase 6
4. If issues remain and round < 3: dispatch fix agents, commit, repeat
5. If round = 3: blockers -> STOP; criticals/highs -> Phase 6 flagged

### Step 6: DELIVER

Read `handlers/phase-deliver.md` and execute:

1. Build Integrity Report from Self-Reports + quality audit
2. Follow `/ai-pr` SKILL.md in full
3. Cleanup: delete autopilot state, clear spec.md + plan.md, verify cleanup
4. Resume Protocol handles mid-pipeline re-entry via `--resume`

## Handler Dispatch Table

| Phase | Handler | Agent Pattern |
|-------|---------|---------------|
| 1. Decompose | `handlers/phase-decompose.md` | Orchestrator (read-only analysis) |
| 2. Deep Plan | `handlers/phase-deep-plan.md` | Explore+Plan x N parallel |
| 3. Orchestrate | `handlers/phase-orchestrate.md` | Orchestrator (DAG construction) |
| 4. Implement | `handlers/phase-implement.md` | Build x N per wave (DAG-driven) |
| 5. Quality Loop | `handlers/phase-quality.md` | Verify + Guard + Review parallel, Build for fixes |
| 6. Deliver | `handlers/phase-deliver.md` | PR pipeline + cleanup |

## Flags

| Flag | Behavior |
|------|----------|
| `--resume` | Read `specs/autopilot/manifest.md`, determine pipeline state, re-enter at the correct phase/wave. Never re-executes completed phases. See Resume Protocol in phase-deliver handler. |
| `--no-watch` | Create PR without the watch-and-fix loop. Useful for draft delivery or when CI is managed externally. |

## Thin Orchestrator Principle

This skill READS other skills' SKILL.md files and EMBEDS their instructions into subagent prompts. It does NOT contain implementation logic. The phases delegate to:

- `.github/prompts/ai-verify.prompt.md` for quality gates (Phase 5)
- `.github/prompts/ai-review.prompt.md` for code review (Phase 5)
- `.github/prompts/ai-pr.prompt.md` for pull request creation and delivery (Phase 6)
- `.github/prompts/ai-commit.prompt.md` for incremental commit protocol (Phase 4, 5)

When those skills improve, autopilot benefits automatically. No duplication, no drift.

## Governance

DEC-023: User invocation of `/ai-autopilot` is the single approval gate. All internal gates (sub-spec validation, DAG verification, quality convergence) are automatic and cannot be bypassed.

State transitions are recorded on disk in `specs/autopilot/manifest.md` -- never in agent memory. Any phase can be audited post-hoc.

D7: plan.md is not required. Phase 2 agents generate their own detailed plans per sub-spec.

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Phase 2 agent fails (timeout, crash) | Retry once. If second attempt fails: mark sub-spec `plan-failed`. Evaluate subset viability. |
| Build agent fails in Phase 4 | Mark sub-spec `blocked`. Cascade-block dependents. Continue with remaining sub-specs in wave. |
| Quality loop exhausted (3 rounds) with blockers | STOP. Do NOT create PR. Report blockers and escalate to user. |
| Quality loop exhausted with only criticals/highs | Proceed to Phase 6. PR created but flagged. Integrity Report documents remaining issues. |
| Mid-pipeline crash | Run `/ai-autopilot --resume`. Reads manifest, continues from last incomplete phase/wave. |
| Final cleanup fails | Warn but do not block -- PR is already delivered. |

Rollback: `git reset --soft HEAD~N` where N = number of wave + quality-fix commits. Included in failure reports.

## Telemetry

Events emitted at each phase transition via hook system:

| Event | Trigger |
|-------|---------|
| `autopilot.started` | Step 0 completes |
| `autopilot.decompose_complete` | Phase 1 completes |
| `autopilot.deep_plan_complete` | Phase 2 completes |
| `autopilot.dag_built` | Phase 3 completes |
| `autopilot.subspec_complete` | Each sub-spec passes implementation |
| `autopilot.quality_round` | Each quality loop round completes |
| `autopilot.subspec_failed` | Sub-spec blocked or cascade-blocked |
| `autopilot.final_verify` | Phase 5 completes (pass or exhausted) |
| `autopilot.pr_created` | Phase 6 PR created |
| `autopilot.done` | Phase 6 cleanup completes |

## Quick Reference

```
/ai-autopilot "implement spec-065"     # full 6-phase pipeline
/ai-autopilot --resume                  # continue from failure point
/ai-autopilot "spec" --no-watch         # skip PR watch loop
```

## Common Mistakes

- Running on draft or unapproved specs -- brainstorm approval is a hard prerequisite.
- Running on specs with < 3 concerns -- use `/ai-dispatch` instead, autopilot overhead is not justified.
- Cross-repo work -- autopilot operates within a single repository.
- Expecting plan.md to exist -- v2 does NOT require it. Phase 2 agents plan independently.
- Carrying context between sub-specs -- each build agent gets fresh context by design.
- Attempting to fix failures after quality loop exhaustion with blockers -- escalate, do not compound errors.
- Hand-editing mirrors instead of running `sync_command_mirrors.py` after changes.

## Integration

- **Called by**: user directly (after `/ai-brainstorm` approval)
- **Reads**: `ai-verify/SKILL.md`, `ai-review/SKILL.md`, `ai-pr/SKILL.md`, `ai-commit/SKILL.md`
- **Delegates to**: Agent(Explore) for research, Agent(Build) for implementation, Agent(Verify) for gates, Agent(Guard) for governance advisory, Agent(Review) for code review
- **Transitions to**: `/ai-cleanup` after merge, or back to user on failure

$ARGUMENTS

---

# Handler: Phase 1 -- DECOMPOSE

## Purpose

Take an approved spec and decompose it into N independent concerns, each becoming a sub-spec shell. Fast and shallow -- produces the skeleton that Phase 2 (Deep Plan) enriches. This phase is read-only analysis: no code changes, no builds, no tests.

## Inputs

| Source | What to extract |
|--------|----------------|
| `specs/spec.md` | Full approved spec -- requirements, scope, constraints, acceptance criteria |
| `state/decision-store.json` | Architectural decisions and constraints that bound decomposition |

## Procedure

### Step 1 -- Extract Concerns

Read the spec end-to-end. Identify N independent concerns. A concern is a coherent unit of work: a module, a feature area, a configuration surface, or a data domain.

Heuristics for concern boundaries:
- Different files or directories touched
- Different runtime behavior (CLI vs library vs config)
- Independent testability (can be verified without other concerns)
- Separate domain concepts (auth vs storage vs UI)

Each concern gets a short title (3-6 words) and a 2-3 sentence scope statement extracted from the parent spec.

### Step 2 -- Minimum Concern Guard

If N < 3: **ABORT**. Report to orchestrator:

```
DECOMPOSE ABORTED: Spec has N concerns -- below autopilot threshold (3).
Recommendation: Use /ai-dispatch for direct execution.
```

This is a hard gate. Do not proceed. Do not attempt to split concerns further to meet the threshold -- that produces artificial granularity.

### Step 3 -- Write Sub-Spec Shells

For each concern, write a shell file to `specs/autopilot/sub-NNN.md` using the Shell Schema:

```markdown
---
id: sub-NNN
parent: spec-XXX
title: "Concern title"
files: []  # best guess -- Phase 2 refines
---

# Sub-Spec NNN: [title]

## Scope
[2-3 sentences from parent spec describing this concern]

## Exploration
[EMPTY -- populated by Phase 2]

## Plan
[EMPTY -- populated by Phase 2]

## Self-Report
[EMPTY -- populated by Phase 4]
```

Rules:
- Number sub-specs sequentially: `sub-001`, `sub-002`, ..., `sub-NNN`
- The `files` field is a best guess based on spec mentions and project conventions. Phase 2 agents refine it after codebase exploration.
- The `parent` field references the spec ID (e.g., `spec-065`)
- Scope text must trace back to specific sections of the parent spec. Do not invent requirements.

### Step 4 -- Write Manifest

Write `specs/autopilot/manifest.md` with the full sub-spec list. All statuses start as `planning`.

Format:

```markdown
# Autopilot Manifest: spec-XXX

## Split Strategy
[1 sentence: by-domain, by-layer, by-feature, by-dependency, or hybrid -- explain the rationale]

## Sub-Specs

| # | Title | Status | Depends On | Files (best guess) |
|---|-------|--------|------------|---------------------|
| sub-001 | [title] | planning | None | `path/a`, `path/b` |
| sub-002 | [title] | planning | None | `path/c` |
| sub-003 | [title] | planning | sub-001 | `path/d`, `path/e` |

## Totals
- Sub-specs: N
- Dependency chain depth: M
```

Dependency rules:
- Default to `None` (independent) unless there is an obvious data or API dependency between concerns
- Keep the dependency graph as shallow as possible -- deep chains reduce parallelism in Phase 4
- Dependencies are refined in Phase 3 (Orchestrate) after full plan analysis

### Step 5 -- Validate Coverage

Walk every section and requirement of the parent spec. Confirm each maps to at least one sub-spec scope. Build a traceability check:

```
Spec Section -> Sub-Spec(s)
------------------------------
Section A    -> sub-001, sub-003
Section B    -> sub-002
Section C    -> sub-004
...
```

**Orphan detection**: if any spec section or requirement does not map to a sub-spec, reassign it to the most relevant existing sub-spec. Update that sub-spec's Scope and `files` field.

If orphans remain after 2 reassignment attempts: **STOP**. Report the orphan requirements to the orchestrator for human review.

## Output

Artifacts written:
- N sub-spec shells at `specs/autopilot/sub-001.md` through `specs/autopilot/sub-NNN.md`
- Execution manifest at `specs/autopilot/manifest.md`

Report to orchestrator:
```
DECOMPOSE COMPLETE
- Concerns identified: N
- Split strategy: [strategy]
- Coverage validation: PASSED (all spec sections mapped)
- Dependency depth: M
- Ready for Phase 2: DEEP PLAN
```

## Failure Modes

| Condition | Action |
|-----------|--------|
| Spec is placeholder or draft (no real requirements) | STOP. Report: "No approved spec. Run `/ai-brainstorm` first." |
| < 3 concerns extracted | ABORT. Report concern count and recommend `/ai-dispatch`. |
| Orphan requirements after 2 reassignment attempts | STOP. Report orphan list with spec section references for human review. |
| Spec references external systems not in the repo | Flag as constraint in manifest. Do not block -- Phase 2 agents will assess feasibility. |
| Ambiguous scope boundaries between concerns | Prefer larger concerns over artificial splits. Note the ambiguity in the manifest for Phase 3 resolution. |

---

# Handler: Phase 2 -- DEEP PLAN

## Purpose

Dispatch N parallel agents (one per sub-spec) to deep-explore the codebase and write detailed, implementation-ready plans. Each agent enriches its sub-spec with architectural context, ordered tasks, and exports/imports declarations. This is where plan quality is built -- implementation quality depends on it.

## Prerequisites

- Phase 1 (DECOMPOSE) is complete.
- Sub-spec shell files exist at `specs/autopilot/sub-NNN.md` with populated `## Scope` and `files:` frontmatter.
- Manifest exists at `specs/autopilot/manifest.md` with all sub-spec statuses set to `planning`.
- Parent spec is available at `specs/spec.md`.
- Decision store is loaded from `state/decision-store.json`.

## Procedure

### Step 1: Load Sub-Specs

1. Glob `specs/autopilot/sub-*.md`. Collect the full list of sub-spec files.
2. For each sub-spec file, extract:
   - `id` from frontmatter (e.g., `sub-001`)
   - `title` from frontmatter
   - `files:` list from frontmatter (Phase 1 best-guess file list)
   - `## Scope` section content
3. Verify all sub-specs are in `planning` status in the manifest. Skip any that are not.
4. Build a dispatch list: one entry per sub-spec with its content and metadata.

### Step 2: Dispatch Agent(Explore+Plan) Per Sub-Spec

Dispatch all agents in parallel using `run_in_background: true`. Each agent receives a self-contained prompt with:

- The full sub-spec content (frontmatter + scope)
- The parent spec's relevant section for this concern
- Decision-store constraints that apply to this sub-spec's scope
- Stack contexts from `contexts/languages/` and `contexts/frameworks/`

Each agent executes the following five-step procedure:

#### 2a. Deep Explore

Read every file mentioned in the sub-spec's `files:` frontmatter. For each file:

- Summarize current state: key exports, public API surface, line count.
- Map imports: what does this file import, and who imports it.
- Map callers: trace usages from other modules.
- Identify test fixtures that cover this file.

Then read analogous implementations in the codebase -- files that solve a similar problem or follow the pattern this sub-spec should replicate.

#### 2b. Write Exploration Section

Populate `## Exploration` in the sub-spec file with the following required subsections:

```markdown
## Exploration

### Existing Files
[For each file in scope: path, summary of current state, key exports, line count.
If file does not exist yet, note "NEW FILE" with the module it belongs to.]

### Patterns to Follow
[Identify the exemplar file in the codebase that this sub-spec should replicate.
State what pattern to follow and why. Include file path and key structural elements.]

### Dependencies Map
[Import chains relevant to this sub-spec. What this code imports, what imports it.
External dependencies. Shared utilities.]

### Risks
[Discovered constraints, edge cases, or unknowns. Breaking changes to existing callers.
Assumptions that need validation. Missing test coverage.]
```

"Existing Files" and "Patterns to Follow" are mandatory. "Dependencies Map" and "Risks" are mandatory but may be brief if the sub-spec is self-contained.

#### 2c. Write Plan Section

Populate `## Plan` in the sub-spec file with ordered tasks:

```markdown
## Plan

exports: [list of modules/classes/functions this sub-spec creates or exposes]
imports: [list of modules/classes/functions this sub-spec expects from other sub-specs]

### T-N.1: [Task title]
- **Description**: What to implement and why.
- **Files**: List of file paths to create or modify.
- **Done condition**: Observable, verifiable condition that proves this task is complete.

### T-N.2: [Task title]
- **Description**: ...
- **Files**: ...
- **Done condition**: ...
[TDD pair: write test first, then implementation]
```

Requirements for the plan:
- Minimum 2 tasks per sub-spec. No upper limit.
- Every task MUST have explicit file paths and a done condition.
- TDD pairs: where tests are needed, the test task precedes the implementation task.
- `exports:` declares modules, classes, or functions this sub-spec creates that other sub-specs may consume. Phase 3 uses these for DAG construction.
- `imports:` declares what this sub-spec expects from other sub-specs. Can be empty (`imports: []`) if there are no cross-sub-spec dependencies.
- Task IDs use the pattern `T-N.K` where N is the sub-spec number and K is the task sequence (e.g., T-3.1, T-3.2 for sub-003).

#### 2d. Refine File List

Update the sub-spec's `files:` frontmatter with the actual files discovered during exploration. This replaces Phase 1's best-guess list with a verified, complete list. Add files that were discovered during exploration but not in the original list. Remove files that turned out to be irrelevant.

#### 2e. Self-Assess

Append a brief assessment to the sub-spec:

```markdown
### Confidence
- **Level**: high | medium | low
- **Assumptions**: [List any assumptions made during exploration]
- **Unknowns**: [List anything that could not be determined from the codebase]
```

Confidence criteria:
- **high**: all files read, patterns clear, no ambiguity in scope, done conditions are objective.
- **medium**: most files read, some assumptions about behavior or API contracts, minor unknowns.
- **low**: key files missing or inaccessible, significant assumptions, scope may need revision.

### Step 3: Collect Results

Wait for all dispatched agents to complete. For each agent:

1. Verify the sub-spec file was written (non-empty).
2. Read the enriched sub-spec content.
3. Record the outcome: success, timeout, crash, or empty output.

### Step 4: Validate Gate Criteria

For each sub-spec that completed successfully, validate the gate (see Gate section below). Track pass/fail per sub-spec.

If a sub-spec fails gate validation despite the agent completing (e.g., missing required subsections, fewer than 2 tasks, no exports/imports declaration), treat it as a failed agent and proceed to failure handling.

### Step 5: Update Manifest

For each sub-spec:

- If gate passed: update status in manifest to `planned`.
- If gate failed or agent failed: follow Failure Modes procedure. After retries, mark surviving failures as `plan-failed`.

Write a summary line to the manifest:

```markdown
## Deep Plan Summary
- Planned: N of M sub-specs
- Failed: K sub-specs [list IDs]
- Confidence distribution: X high, Y medium, Z low
```

## Output

- N enriched sub-spec files at `specs/autopilot/sub-NNN.md`, each containing populated `## Exploration`, `## Plan`, and confidence assessment.
- Updated `files:` frontmatter in each sub-spec reflecting actual discovered files.
- Updated manifest with `planned` or `plan-failed` statuses.
- Summary report: N planned, M failed, confidence distribution.

## Gate

All of the following must pass for each sub-spec to be marked `planned`:

1. **Exploration completeness**: `## Exploration` is non-empty and contains at least the "Existing Files" and "Patterns to Follow" subsections with substantive content (not placeholders or TODOs).
2. **Plan minimum tasks**: `## Plan` contains at least 2 tasks (sections matching `### T-N.K`), each with explicit `Files:` paths and a `Done condition:` statement.
3. **Dependency declarations**: the Plan section declares both `exports:` and `imports:`. Either can be an empty list (`[]`) if there are no cross-sub-spec dependencies, but the declaration must be present.

## Failure Modes

### Single Agent Failure (timeout, crash, empty output, gate fail)

1. **First attempt fails**: retry once with a narrower prompt. The retry prompt:
   - Reduces scope to the sub-spec's `## Scope` section only (drops parent spec context).
   - Explicitly names the missing sections: "You must produce ## Exploration with 'Existing Files' and 'Patterns to Follow' subsections, and ## Plan with at least 2 tasks containing file paths and done conditions."
   - Keeps `files:` frontmatter and decision-store constraints.
2. **Second attempt fails**: mark the sub-spec as `plan-failed` in manifest. Do not retry again.

### All Agents Fail

If every sub-spec is `plan-failed` after retries: **halt the pipeline**. Report:

```
HALT: Deep planning failed for all sub-specs.
None of the N agents produced a valid plan.
Pipeline cannot proceed to Phase 3 (Orchestrate).
Review the parent spec for clarity and scope issues.
```

### Partial Failure (some succeed, some fail)

The orchestrator evaluates the failed sub-specs against the parent spec:

1. Read the parent spec's requirements.
2. For each `plan-failed` sub-spec, determine if its scope covers critical or optional requirements.
3. **If failed sub-specs cover critical parent spec requirements**: halt the pipeline. Report which critical scope is unplannable and why.
4. **If failed sub-specs cover only optional or low-priority scope**: proceed to Phase 3 with the successful subset. Report the gap:

```
PARTIAL: N of M sub-specs planned successfully.
Proceeding without: [list of plan-failed sub-spec IDs and titles].
Gap: [description of scope not covered].
```

### Criticality Assessment Criteria

A sub-spec is **critical** if any of the following apply:
- It implements a requirement marked as mandatory or blocking in the parent spec.
- Other sub-specs declare an `imports:` dependency on modules it would `exports:`.
- Its scope covers the primary deliverable of the parent spec.

A sub-spec is **optional** if:
- It covers ancillary concerns (tests-only, docs-only, CI config, mirror updates).
- No other sub-spec depends on its exports.
- The parent spec can be considered partially delivered without it.

---

# Handler: Phase 6 -- DELIVER

## Purpose

Build the Integrity Report from Phase 4 Self-Reports and Phase 5 quality audit, deliver the full changeset via PR following the ai-pr SKILL.md, clean up autopilot state, and provide the Resume Protocol for mid-pipeline recovery.

## Prerequisites

- Phase 5 (QUALITY LOOP) is complete: either PASS (0 blockers/criticals/highs) or exhausted (round 3 reached with only criticals/highs remaining).
- Manifest at `specs/autopilot/manifest.md` has `## Quality Rounds` section with round log.
- Sub-spec files exist at `specs/autopilot/sub-NNN.md` with populated `## Self-Report` sections from Phase 4 implementation agents.
- Parent spec is available at `specs/spec.md`.

## Procedure

### Step 1: Build Transparency Report

1. Glob `specs/autopilot/sub-*.md`. For each sub-spec, read the `## Self-Report` section. Extract per-file/function classifications: real, aspirational, stub, failing, invented, hallucinated.
2. Read the manifest's `## Quality Rounds` section. Extract the consolidated findings from Phase 5: final state (CLEAN or remaining issues with severity breakdown), number of rounds executed, and per-round summaries.
3. If any sub-specs have status `blocked` or `cascade-blocked` in the manifest: collect their ID, title, scope, and blocking reason. These form the "Blocked / Undelivered" section.
4. Aggregate all classifications across sub-specs into totals. Cross-reference against quality findings -- a file classified as "real" in a Self-Report but failing checks in Phase 5 should be reclassified as "failing".
5. Produce the `## Integrity Report` section:

```markdown
## Integrity Report

### Summary
- Real: N files/functions (fully implemented and verified)
- Aspirational: N (implemented, not fully tested)
- Stub: N (placeholder, needs completion)
- Failing: N (implemented but failing checks)
- Invented: N (not in spec, added by agents)
- Hallucinated: N (referenced non-existent things -- fixed or flagged)

### Quality Convergence
- Rounds: N/3
- Final state: CLEAN | N remaining issues (severity breakdown)

### Blocked / Undelivered
[Only present if blocked sub-specs exist]
- sub-NNN: [title] -- blocked: [reason]
- sub-MMM: [title] -- cascade-blocked by sub-NNN

### Details
| File | Function | Classification | Evidence | Notes |
|------|----------|----------------|----------|-------|
| path/to/file.py | ClassName.method | real | tests pass, lint clean | |
| path/to/other.py | helper_func | stub | raises NotImplementedError | Needs real impl |
| path/to/new.py | util | invented | not in spec | Added for DRY |
```

Classification rules:
- **Real**: tests pass AND lint clean AND in spec scope.
- **Aspirational**: implementation exists but test coverage is incomplete or tests are not fully passing.
- **Stub**: placeholder implementation (raises `NotImplementedError`, returns hardcoded values, or contains TODO markers).
- **Failing**: implementation exists but fails lint, type check, or test assertions.
- **Invented**: not traceable to any spec requirement. Added by an agent for utility, DRY, or structural reasons.
- **Hallucinated**: references non-existent modules, functions, or APIs. Fixed during quality loop or flagged for manual resolution.

### Step 2: Deliver PR

This step follows the thin orchestrator principle. Do NOT duplicate PR logic.

1. Read `.github/prompts/ai-pr.prompt.md`. Follow its FULL procedure -- all steps, in order.
2. The PR body MUST include the following sections in addition to the standard ai-pr structure:
   - The `## Integrity Report` from Step 1 as a dedicated section.
   - A `## Sub-Spec Completion` table:
     ```markdown
     ## Sub-Spec Completion
     | # | Title | Status | Wave |
     |---|-------|--------|------|
     | sub-001 | [title] | complete | 1 |
     | sub-002 | [title] | complete | 1 |
     | sub-003 | [title] | blocked | -- |
     ```
   - Standard PR sections (Summary, Test Plan, Checklist) per ai-pr protocol.
3. Enable auto-complete with squash merge per ai-pr Step 13.
4. Enter the watch-and-fix loop per ai-pr Step 14, unless `--no-watch` flag was passed. If `--no-watch`: skip the loop and proceed directly to Step 3 (Cleanup).

### Step 3: Cleanup

Execute after the PR merges (detected by the watch loop), or immediately after PR creation if `--no-watch` was passed.

1. **Delete autopilot directory**:
   ```
   rm -rf .ai-engineering/specs/autopilot/
   ```

2. **Clear `specs/spec.md`** with:
   ```markdown
   # No active spec

   Run /ai-brainstorm to start a new spec.
   ```

3. **Clear `specs/plan.md`** with:
   ```markdown
   # No active plan

   Run /ai-plan after brainstorm approval.
   ```

4. **Add entry to `specs/_history.md`** with the spec ID, title, date, and PR number. If `_history.md` does not exist, create it with this header first:
   ```markdown
   # Spec History

   Completed specs. Details in git history.

   | ID | Title | Status | Created | Branch |
   |----|-------|--------|---------|--------|
   ```
   Then append the new entry row to the table.

5. **Verify cleanup** (lesson from spec-056): re-read `specs/spec.md` and `specs/plan.md` after clearing. If either file still contains old spec content (anything other than the placeholder text), clear it again. This is a hard verification -- do not trust the write succeeded without reading back.

6. **Stage and commit** all cleanup changes:
   ```
   chore: clear autopilot state after spec-NNN delivery
   ```

### Step 4: Final Report

Print the completion summary to the user:

```
Autopilot Complete!

Spec: spec-NNN -- [title]
Sub-specs: N completed, M blocked
Waves: W executed
Quality rounds: R/3
PR: #NNN (merged|pending)
Integrity: N real, N aspirational, N stub, N failing, N invented, N hallucinated
```

Field sources:
- **Spec**: from `specs/spec.md` frontmatter (read before cleanup clears it).
- **Sub-specs**: count from manifest. "completed" = status `complete`. "blocked" = status `blocked` or `cascade-blocked`.
- **Waves**: count from manifest's `## Execution DAG` section.
- **Quality rounds**: from manifest's `## Quality Rounds` section.
- **PR**: number from the PR creation step. State is "merged" if watch loop confirmed merge, "pending" if `--no-watch` was used.
- **Integrity**: totals from the Integrity Report built in Step 1.

## Resume Protocol

When the autopilot is invoked with `--resume`, read `specs/autopilot/manifest.md` and re-enter the pipeline at the correct phase. Resume NEVER re-executes completed phases. The manifest is the single source of truth for all resume decisions.

### Resume Decision Logic

Read the manifest. Inspect sub-spec statuses, section presence, and wave completion state. Apply the first matching rule:

1. **All sub-specs are `planning`**: Phase 2 (DEEP PLAN) never completed. Re-enter at Phase 2 by reading `handlers/phase-deep-plan.md` and executing from the start.

2. **`## Execution DAG` section is missing**: Phase 3 (ORCHESTRATE) never completed. Re-enter at Phase 3 by reading `handlers/phase-orchestrate.md` and executing from the start.

3. **Some waves are `implemented` and others are not**: Phase 4 (IMPLEMENT) was interrupted mid-execution. Identify the first incomplete wave (a wave where not all sub-specs are `complete`, `blocked`, or `cascade-blocked`). Re-enter Phase 4 at that wave. Skip all completed waves -- do not re-dispatch their agents.

4. **All waves are `implemented` but `## Quality Rounds` section is absent**: Phase 5 (QUALITY LOOP) never started. Re-enter at Phase 5 by reading `handlers/phase-quality.md` and executing from the start.

5. **`## Quality Rounds` exists but pipeline stopped** (e.g., blockers after round 3 that have since been manually resolved, or a crash during the quality loop): Re-enter at Phase 5 for another attempt. Reset the round counter to 0. The quality loop starts fresh but operates on the current state of the codebase.

6. **Quality passed but PR not created**: Phase 6 delivery was interrupted before the PR was created. Re-enter at Phase 6 Step 2 (Deliver PR). Skip the Integrity Report build only if `## Integrity Report` already exists in the manifest -- otherwise, start from Step 1.

### Resume Safeguards

- Never re-execute a phase whose artifacts are already complete and valid.
- If the manifest is missing or corrupted (unparseable): STOP. Report: "Manifest is missing or corrupted. Cannot resume. Inspect `specs/autopilot/manifest.md` manually."
- If the manifest exists but no sub-specs files are found: STOP. Report: "Manifest exists but sub-spec files are missing. Pipeline state is inconsistent."
- After determining the re-entry point, report to the user before proceeding:
  ```
  Resume: re-entering at Phase N ([phase name]).
  Reason: [why this phase was selected].
  Completed phases: [list of phases that will be skipped].
  ```

## Output

- PR created with Integrity Report, Sub-Spec Completion table, and standard ai-pr sections.
- Autopilot state cleaned: `specs/autopilot/` deleted, `specs/spec.md` and `specs/plan.md` cleared.
- Entry added to `specs/_history.md`.
- Final report printed to user.

## Failure Modes

| Condition | Action |
|-----------|--------|
| PR creation fails (VCS error, auth failure, network) | STOP and report the error. Do NOT retry PR creation -- VCS errors require user diagnosis. The Integrity Report and changeset are preserved in the branch. |
| Watch loop escalates (same check fails 3 times) | STOP per ai-pr handler protocol (Step 14 / `handlers/watch.md`). Report which check is failing and the 3 attempts made. PR remains open for manual intervention. |
| Cleanup fails (file write error, permission denied) | Warn but do NOT block. The PR is already delivered -- cleanup is best-effort. Report which cleanup step failed so the user can run it manually. |
| `_history.md` does not exist | Create it with the standard header (see Step 3.4), then add the entry. This is not a failure -- it is expected on first autopilot delivery. |
| Manifest missing or corrupted on `--resume` | STOP. Report: "Manifest is missing or corrupted. Cannot resume." Do not guess pipeline state. |
| Sub-spec files missing on `--resume` | STOP. Report: "Sub-spec files missing. Pipeline state inconsistent." Do not proceed with partial data. |
| Integrity Report aggregation finds zero Self-Reports | STOP. Phase 4 did not complete properly. Report: "No Self-Reports found in sub-specs. Phase 4 may not have completed. Run `--resume` to re-evaluate pipeline state." |

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

# Handler: Phase 4 -- IMPLEMENT

## Purpose

Execute the implementation plan following the DAG. For each wave, dispatch Agent(Build) per sub-spec in parallel. Each agent receives full context (sub-spec content, decision-store constraints, stack standards) and writes a Self-Report classifying every piece of work using the Transparency Protocol. Commits are made per wave. Failed sub-specs cascade-block their dependents in later waves.

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

#### 2b -- Dispatch Agent(Build) Per Sub-Spec (Parallel)

For each non-blocked sub-spec in the wave, dispatch an Agent(Build) with a fresh context containing:

1. **Sub-spec content** -- the full `specs/autopilot/sub-NNN.md` file (Scope, Exploration, Plan, file list).
2. **Decision-store constraints** -- relevant entries from `state/decision-store.json` that apply to this sub-spec's domain.
3. **Stack standards** -- loaded from `contexts/languages/` and `contexts/frameworks/` matching the detected stack.
4. **File boundary enforcement** -- explicit instruction embedded in the agent prompt:

```
HARD BOUNDARY: You may ONLY modify these files:
  - [list of files from sub-spec file ownership]

Do NOT create, modify, or delete any file outside this list.
If your plan requires touching a file outside scope, STOP and
report the conflict. Do not proceed.
```

All agents in the wave dispatch in parallel. They do not share context with each other.

#### 2c -- Agent Executes Plan Tasks

Each Agent(Build) executes the plan tasks listed in its sub-spec, in order. The agent follows standard build procedures:

- Write code following stack standards loaded from contexts.
- Run post-edit validation per the stack (ruff, tsc, cargo check, etc.).
- Fix validation failures (max 3 attempts per file, then report failure).
- Respect quality gates: no suppression comments, no weakened thresholds.

#### 2d -- Agent Writes Self-Report

After completing (or failing) its plan tasks, each agent appends a `## Self-Report` section to the end of its sub-spec file (`specs/autopilot/sub-NNN.md`) using the Transparency Protocol:

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
- Self-Reports -- appended to each sub-spec file (`specs/autopilot/sub-NNN.md`).
- Updated manifest -- `specs/autopilot/manifest.md` with `implemented`, `blocked`, or `cascade-blocked` statuses per sub-spec, plus wave commit hashes.

## Gate

A wave is complete when ALL of the following hold:

1. Every non-blocked sub-spec in the wave has a Self-Report written in its sub-spec file.
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
| Agent violates file boundary | Agent MUST stop immediately and report the conflict. Do not commit boundary-violating changes. Mark the sub-spec `blocked` and cascade-block dependents. |
| Agent produces `hallucinated` classification | Not a blocking failure during Phase 4. The Self-Report flags it. Phase 5 (Quality Loop) will detect and address phantom references. |
| Agent exceeds 3 validation fix attempts on a file | Mark that file's work as `failing` in the Self-Report. Continue with remaining plan tasks. Do not block the entire sub-spec for a single file failure. |
| Manifest write fails (disk error, permissions) | STOP. Cannot proceed without persistent state. Escalate immediately -- pipeline integrity depends on manifest accuracy. |

---

# Handler: Phase 3 -- ORCHESTRATE

## Purpose

Analyze all N enriched sub-spec plans together, detect file overlaps and import dependencies, construct an execution DAG with wave assignments, and resolve conflicts. This phase prevents merge conflicts during Phase 4 and ensures correct execution ordering. It is read-only analysis on sub-spec files -- no code changes, no builds.

## Prerequisites

Phase 2 (Deep Plan) complete. All non-failed sub-specs have enriched `## Exploration` and `## Plan` sections. Each plan declares `exports:` and `imports:` lists -- Phase 3 uses these structured declarations for DAG construction, not code analysis.

Required state:
- `specs/autopilot/manifest.md` exists with sub-spec list and statuses
- Non-failed sub-specs (`planning` or `planned`) have non-empty `## Plan` sections
- Sub-specs marked `plan-failed` are excluded from DAG construction

## Procedure

### Step 1 -- Extract Declarations

Read all non-failed sub-spec files from `specs/autopilot/`. For each sub-spec, extract:

1. **files**: the `files:` list from frontmatter (refined by Phase 2)
2. **exports**: the `exports:` declarations from `## Plan` (modules, classes, or functions this sub-spec creates)
3. **imports**: the `imports:` declarations from `## Plan` (modules, classes, or functions this sub-spec expects from other sub-specs)

Build a lookup table:

```
sub-001: files=[a.py, b.py], exports=[ModuleA, func_x], imports=[]
sub-002: files=[c.py, d.py], exports=[ServiceB],        imports=[ModuleA]
sub-003: files=[e.py],       exports=[HelperC],          imports=[]
```

**Missing declarations**: if a sub-spec lacks `exports:` or `imports:` declarations, treat it as having no cross-sub-spec dependencies (isolated). Log a warning:

```
WARNING: sub-NNN missing exports/imports declarations -- treated as isolated.
```

### Step 2 -- Build File-Overlap Matrix

For each pair of sub-specs (i, j) where i < j, check if they share any file paths. A file path is shared when both sub-specs list it in their `files:` frontmatter (create or modify the same path).

Record overlaps as undirected edges:

```
File Overlaps:
  sub-001 <-> sub-004  (shared: src/installer/service.py)
  sub-002 <-> sub-005  (shared: src/installer/merge.py, src/installer/phases/__init__.py)
```

Sub-spec pairs with zero shared files have no file-overlap edge.

### Step 3 -- Build Import-Chain Graph

Using declared `exports:` and `imports:`, check if sub-spec A exports a symbol that sub-spec B imports. This uses the structured declarations from Phase 2 -- it does NOT parse or analyze source code.

Record import dependencies as directed edges (A -> B means B depends on A, so A must complete before B):

```
Import Chains:
  sub-001 -> sub-002  (sub-002 imports ModuleA from sub-001)
  sub-001 -> sub-005  (sub-005 imports func_x from sub-001)
```

If sub-spec B imports a symbol not exported by any sub-spec, it is an external dependency (outside autopilot scope). Ignore it -- no edge created.

### Step 4 -- Construct DAG

Combine file-overlap edges and import-chain edges into a single dependency graph. Apply topological sort to assign wave numbers:

**Rules**:
- Sub-specs with zero file overlaps AND zero import chains with each other can be assigned to the same wave (parallel execution is safe).
- Sub-specs with a file overlap or import dependency must be serialized (the dependent waits for the dependency to complete).
- For file overlaps (undirected), serialize by sub-spec number (lower number goes first).
- For import chains (directed), the exporter executes before the importer.

**Wave assignment via topological sort**:
- Wave 1: sub-specs with zero incoming edges (no dependencies on other sub-specs)
- Wave 2: sub-specs whose dependencies are all in Wave 1
- Wave 3: sub-specs whose dependencies are all in Wave 1 or Wave 2
- Continue until all sub-specs are assigned.

### Step 5 -- Handle Unresolvable Conflicts

A conflict is unresolvable when two sub-specs must modify the same function within the same file -- not just the same file, but the same logical unit. Ordering alone cannot prevent a merge conflict at the function level.

**Resolution**: merge the conflicting sub-specs into a single sub-spec.

1. Create a new sub-spec that combines the scopes, plans, and file lists of both
2. Preserve the lower sub-spec number (e.g., merge sub-003 into sub-001 -> result is sub-001)
3. Remove the higher-numbered sub-spec from the manifest
4. Update the merged sub-spec file with combined `## Scope`, `## Exploration`, `## Plan`, and `files:` frontmatter
5. Re-check the DAG edges for the merged sub-spec (it inherits all edges of both originals)
6. Log the merge with rationale:

```
MERGE: sub-003 merged into sub-001
Reason: both modify detect_phase() in src/installer/phases/detect.py
Combined work units: 7
```

If a merge produces a sub-spec with more than 7 work units, consider splitting differently: extract the conflicting function into its own sub-spec, or reorder tasks so the conflict is localized. Max 2 attempts at resolution before escalating to the orchestrator.

### Step 6 -- Write DAG to Manifest

Append the `## Execution DAG` section to `specs/autopilot/manifest.md`:

```markdown
## Execution DAG

Wave 1 (parallel): sub-001, sub-003, sub-005
Wave 2 (parallel, after Wave 1): sub-002, sub-004
Wave 3 (serial, after Wave 2): sub-006

### Dependency Edges
- sub-001 -> sub-002 (imports: ModuleA)
- sub-001 -> sub-004 (file overlap: service.py)
- sub-003 -> sub-006 (imports: HelperC)
```

Wave labels:
- `(parallel)` when the wave contains 2+ sub-specs
- `(serial, after Wave N)` when the wave contains exactly 1 sub-spec
- `(parallel, after Wave N)` when the wave contains 2+ sub-specs and follows another wave

### Step 7 -- Validate DAG

Run two validation checks:

1. **Acyclicity**: verify the DAG has no cycles. A cycle means A depends on B and B depends on A (directly or transitively). If a cycle is detected, see Failure Modes below.

2. **Complete coverage**: every non-failed sub-spec must have a wave assignment. If any sub-spec is unassigned, it was missed during graph construction -- reassign it. Sub-specs with no edges default to Wave 1.

## Output

Artifacts written:
- Updated `specs/autopilot/manifest.md` with `## Execution DAG` section
- Updated sub-spec files (only if merges occurred in Step 5)

Report to orchestrator:

```
ORCHESTRATE COMPLETE
- Sub-specs analyzed: N (M excluded as plan-failed)
- File overlaps detected: X pairs
- Import chains detected: Y edges
- Merges performed: Z (details: ...)
- DAG waves: W
- Wave distribution: Wave 1 = A sub-specs, Wave 2 = B sub-specs, ...
- Fully serial: yes/no
- Ready for Phase 4: IMPLEMENT
```

## Failure Modes

| Condition | Action |
|-----------|--------|
| Cyclic dependency detected | Attempt to break by merging the cycle participants into one sub-spec. If the merged sub-spec exceeds 7 work units, split differently and rebuild the DAG. Max 2 attempts. If unresolved, escalate to user with the cycle graph. |
| Sub-spec missing `exports:`/`imports:` declarations | Treat as isolated (no cross-sub-spec dependencies). Log warning. Do not block. |
| All sub-specs must be serial (fully serial DAG) | Proceed normally. This is an expected DAG shape for tightly coupled specs, not a failure. Phase 2 deep-plan work is still valuable even without parallelism. |
| Merge produces sub-spec with >7 work units | Attempt to split the conflicting function into its own sub-spec (max 2 attempts). If still >7, proceed with the large sub-spec and note it in the report. |
| No sub-specs remain after excluding `plan-failed` | STOP. Report: "All sub-specs failed planning. Pipeline cannot continue." Escalate to user. |
| File overlap between 3+ sub-specs on the same path | Merge all sub-specs that share that file into one. Apply the same merge protocol as Step 5. |

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

# Handler: Phase 5 -- QUALITY LOOP

## Purpose

Converge on quality through iterative assessment and fixing. Dispatch Agent(Verify) + Agent(Guard) + Agent(Review) in parallel on the full changeset, consolidate findings with unified severity mapping, fix issues, and iterate up to 3 rounds. This is where cross-sub-spec integration issues are caught -- the first time all sub-spec changes are evaluated as a single unit.

## Prerequisites

| Condition | Source |
|-----------|--------|
| Phase 4 complete | All waves committed. Manifest updated with per-sub-spec statuses. |
| Sub-spec Self-Reports exist | Each implemented sub-spec has a Self-Report section in its `sub-NNN.md` with classifications (real/aspirational/stub/failing/invented/hallucinated). |
| Manifest has sub-spec statuses | `specs/autopilot/manifest.md` shows `complete` or `blocked` per sub-spec. |

## Thin Orchestrator

This handler does NOT contain verify, guard, or review logic. It reads:

- `.github/prompts/ai-verify.prompt.md` -- IRRV protocol, 7 scan modes, scan output contract
- `.github/prompts/ai-review.prompt.md` -- 8-agent parallel review, self-challenge protocol, confidence scoring
- `.github/prompts/ai-governance.prompt.md` -- advise mode, decision-store lifecycle

These protocols are embedded verbatim into subagent prompts at dispatch time. When those skills improve, this handler benefits automatically.

## Procedure

### Step 1 -- Scope the Changeset

Check `specs/autopilot/manifest.md` for blocked or cascade-blocked sub-specs.

- If all sub-specs are `complete`: quality loop covers the full changeset.
- If partial (some sub-specs `blocked`): note which scope was not delivered. The quality loop verifies only the implemented subset. Record the gap:

```
Quality Scope: partial (sub-003, sub-007 blocked)
Verified subset: sub-001, sub-002, sub-004, sub-005, sub-006
```

Compute the changeset diff: `git diff main...HEAD` -- this is the input for all assessment agents.

### Step 2 -- Iterative Assessment and Fix (round 1 to 3)

Repeat the following cycle. Track the current round number (R = 1, 2, or 3).

#### Step 2a -- Assess (3 agents in parallel)

Dispatch three assessment agents simultaneously. Each gets fresh context.

**Agent(Verify)** -- platform mode:
- Read `.github/prompts/ai-verify.prompt.md` at dispatch time.
- Embed the IRRV protocol and the Scan Modes table into the agent prompt.
- Run all 7 scan modes (governance, security, quality, performance, a11y, feature, architecture) on the changeset.
- Output: scored verdict with findings per the Scan Output Contract (Score N/100, Verdict, Findings table, Gate Check).

**Agent(Guard)** -- advise mode:
- Read `.github/prompts/ai-governance.prompt.md` at dispatch time.
- Run governance check against `state/decision-store.json`.
- Check for: expired risk acceptances, ownership violations, framework integrity drift.
- Output: advisory findings with severity levels (concern, warn, info).

**Agent(Review)** -- 8-agent parallel review:
- Read `.github/prompts/ai-review.prompt.md` at dispatch time.
- Embed the 8 Review Agents table, self-challenge protocol, and confidence scoring rules into the agent prompt.
- Run the full review protocol on `git diff main...HEAD`.
- Output: findings with severity, confidence score, and corroboration status.

If all 3 assessment agents fail in this round: retry the round once. If the second attempt also fails: **STOP**. Report the failure and escalate to user. Do not proceed.

#### Step 2b -- Consolidate Findings

Map all findings from the three sources to a unified severity scale:

| Source | Source Severity | Unified Severity |
|--------|----------------|------------------|
| Verify | blocker | blocker |
| Verify | critical | critical |
| Verify | high | high |
| Verify | medium | medium |
| Verify | low | low |
| Guard | concern | high |
| Guard | warn | medium |
| Guard | info | low |
| Review | (uses same scale) | as-is |

Deduplicate findings that appear in multiple sources. When two or more agents flag the same file and line with the same category, merge into a single finding and note corroboration (increases confidence).

**Cross-reference against Self-Reports**: for each finding, check the corresponding sub-spec Self-Report from Phase 4.

- If Self-Report classifies a test as `real` but Verify finds it failing: flag the discrepancy as a blocker. The Self-Report was inaccurate.
- If Self-Report classifies something as `aspirational` or `stub` and Verify confirms it: not a discrepancy -- the gap was declared.
- If Self-Report classifies something as `failing` and the fix round resolved it: update the Self-Report entry.

Produce a consolidated findings list:

```
Consolidated Findings (Round R):
| # | Unified Severity | Source(s) | Category | Description | File:Line | Self-Report Match |
```

#### Step 2c -- Evaluate

Count the consolidated findings by unified severity:

- **Blockers**: count
- **Criticals**: count
- **Highs**: count

Decision matrix:

| Condition | Action |
|-----------|--------|
| 0 blockers + 0 criticals + 0 highs | **PASS**. Exit loop. Proceed to Phase 6. |
| Issues remain AND round < 3 | Proceed to Step 2d (fix). |
| Round = 3 AND blockers remain | **STOP**. Do NOT proceed to Phase 6. Do NOT create PR. Report all blockers with evidence and escalate to user. |
| Round = 3 AND only criticals/highs remain (0 blockers) | Proceed to Phase 6 with issues documented. PR is created but flagged in the Integrity Report. |

#### Step 2d -- Fix

For each finding at blocker, critical, or high unified severity:

1. **Dispatch Agent(Build)** with focused context:
   - The finding: severity, description, file, line
   - The affected sub-spec context (scope + plan from `sub-NNN.md`)
   - The Self-Report entry for that area (so the agent understands what was claimed)

2. **Agent writes the fix** and updates the Self-Report classification:
   - `failing` -> `real` (if the fix makes a test pass)
   - `aspirational` -> `real` (if the fix implements the missing behavior)
   - `stub` -> `real` (if the fix replaces the stub with real logic)

3. **Commit fixes** with message format:
   ```
   spec-NNN: quality round R -- fix [category]
   ```
   Where `[category]` is the finding category (e.g., security, performance, correctness).

4. **Return to Step 2a** for the next round.

### Step 3 -- Record Quality Rounds

After the loop completes (pass or exhausted), write the quality rounds log to `specs/autopilot/manifest.md` under a `## Quality Rounds` section:

```markdown
## Quality Rounds

Round 1: 3 blockers, 5 criticals, 12 highs -> FIX
Round 2: 0 blockers, 1 critical, 4 highs -> FIX
Round 3: 0 blockers, 0 criticals, 0 highs -> PASS
```

Or if exhausted with remaining issues:

```markdown
## Quality Rounds

Round 1: 2 blockers, 3 criticals, 8 highs -> FIX
Round 2: 1 blocker, 1 critical, 3 highs -> FIX
Round 3: 1 blocker, 0 criticals, 1 high -> STOP (blockers remain)
```

## Output

Report to orchestrator upon completion:

**If PASS:**
```
QUALITY LOOP COMPLETE
- Rounds: R
- Final: 0 blockers, 0 criticals, 0 highs
- Changeset scope: full | partial (list blocked sub-specs)
- Self-Report discrepancies found: N (all resolved)
- Ready for Phase 6: DELIVER
```

**If exhausted with blockers:**
```
QUALITY LOOP EXHAUSTED -- BLOCKERS REMAIN
- Rounds: 3
- Remaining: B blockers, C criticals, H highs
- Blocker details:
  1. [severity] [category] [file:line] -- [description]
  2. ...
- ACTION REQUIRED: User must resolve blockers before delivery.
- Rollback hint: git reset --soft HEAD~N (N = wave + fix commits)
```

**If exhausted without blockers:**
```
QUALITY LOOP EXHAUSTED -- FLAGGED
- Rounds: 3
- Remaining: 0 blockers, C criticals, H highs
- Flagged issues documented in manifest for Integrity Report.
- Proceeding to Phase 6: DELIVER (with flags)
```

## Gate

**Pass condition**: 0 blockers + 0 criticals + 0 highs after assessment.

**Exit condition**: pass achieved OR 3 rounds exhausted.

**Hard stop**: blockers remaining after round 3 prevent Phase 6 entry. No exceptions.

## Failure Modes

| Condition | Action |
|-----------|--------|
| All 3 assessment agents fail in a round | Retry the round once. If second attempt also fails: STOP and escalate to user. |
| Fix agent introduces new issues | Next assessment round catches them. The loop either converges or exhausts at round 3. |
| Partial changeset (blocked sub-specs from Phase 4) | Verify only implemented files. Note gaps in the consolidated findings and the manifest. |
| Self-Report discrepancy (claimed `real`, found failing) | Reclassify as blocker. Fix agent must resolve in the next fix cycle. |
| Single assessment agent fails but others succeed | Use available findings. Log the missing assessment. Do not retry the entire round for a single agent failure -- only retry when all 3 fail. |

## Behavioral Negatives

The following actions are prohibited during this phase:

- **Do NOT** weaken severity mappings to force a pass.
- **Do NOT** skip any of the 3 assessment agents (Verify, Guard, Review). All three run every round.
- **Do NOT** proceed to Phase 6 with known blockers remaining.
- **Do NOT** retry more than 3 rounds. 3 is the hard ceiling.
- **Do NOT** modify assessment agent findings to make them less severe.
- **Do NOT** use forbidden language in status reports: "should work", "looks good", "probably fine", "seems to", "I think", "most likely".
- **Do NOT** merge findings in a way that loses information. Every finding must be traceable to its source agent.

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
