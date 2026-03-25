---
name: ai-dispatch
description: Use when an approved plan exists (plan.md + tasks.md) and you need to execute it. Dispatches subagents per task with two-stage review and progress tracking.
effort: high
argument-hint: "[spec-NNN or --resume]"
mode: agent
---



# Dispatch

## Purpose

Execution engine for approved plans. Reads plan.md and tasks.md, dispatches one subagent per task (fresh context), runs two-stage review on each deliverable, and tracks progress. If stuck: STOP and re-plan.

## When to Use

- After `/ai-plan` produces an approved plan
- To resume execution: `/ai-dispatch --resume`
- Never without an approved plan (run `/ai-plan` first)

## Process

1. **Load plan** -- read `specs/spec.md` -> `specs/plan.md`
2. **Load decisions** -- read `decision-store.json` for constraints
3. **Build DAG** -- parse task dependencies, identify parallel groups
4. **Execute phase by phase** -- for each phase:
   a. Dispatch one subagent per task (fresh context window)
   b. Each subagent receives: task description, file scope, boundaries, constraints
   c. Run two-stage review on deliverable (see below)
   d. Update task status in plan.md
   e. Check phase gate before advancing
5. **Track progress** -- update plan.md checkboxes after each task
6. **Quality check** -- read `handlers/quality.md` and execute: Verify+Review on full changeset, max 2 rounds
7. **Deliver** -- read `handlers/deliver.md` and execute: PR via ai-pr with quality report

## Task Statuses

| Status | Meaning | Action |
|--------|---------|--------|
| `DONE` | Task completed, reviews passed | Check off, advance |
| `DONE_WITH_CONCERNS` | Completed but reviewer flagged issues | Check off, log concerns for follow-up |
| `NEEDS_CONTEXT` | Agent needs information not in the plan | Pause, ask user, then resume |
| `BLOCKED` | Cannot proceed (dependency, access, ambiguity) | STOP execution, re-plan |

## Two-Stage Review (Per-Task)

Every task deliverable goes through two reviews before marking DONE. This is the per-task quality check during Phase 4 execution. A separate full-changeset quality check runs in Phase 6 (see `handlers/quality.md`).

### Stage 1: Spec Compliance

- Does the deliverable match the task description?
- Does it satisfy the acceptance criteria from spec.md?
- Are all file scope boundaries respected (no out-of-scope changes)?

### Stage 2: Code Quality

- Stack validation passes (ruff, tsc, cargo check, etc.)
- No new lint warnings introduced
- Test coverage maintained or improved
- No governance advisory warnings from guard

If either stage fails: fix and re-review (max 2 retries per stage).

## DAG Construction

**Independent** (can run in parallel):
- Different file scopes with no overlap
- No producer-consumer relationship
- Different modules with no shared state

**Dependent** (must serialize):
- Task B reads files Task A creates
- Task B depends on Task A's output
- Both modify governance artifacts (`.ai-engineering/` must serialize)
- Plan explicitly orders them

## Subagent Context

Each subagent receives a focused context window:

```yaml
task: T-2.1
description: "Implement the parse_config function"
agent: ai-build
scope:
  files: ["src/config.py", "tests/test_config.py"]
  boundaries: ["Do NOT modify src/main.py", "Do NOT touch hooks/"]
constraints:
  - "Follow existing ConfigParser pattern in src/base_config.py"
  - "TDD: test files from T-2.0 are IMMUTABLE"
gate:
  post: ["ruff check", "pytest tests/test_config.py"]
```

## Stuck Protocol

If a task fails after 2 retries:

1. Mark task as BLOCKED with reason
2. Check if other tasks in the phase can proceed independently
3. If phase is blocked entirely: STOP execution
4. Report to user: what failed, what was tried, options (re-plan, skip, manual fix)

Never loop silently. Never retry the same approach more than twice.

## Progress Tracking

Update plan.md in real-time:

```markdown
- [x] T-1.1: Create config module @ai-build -- DONE
- [x] T-1.2: Add validation logic @ai-build -- DONE_WITH_CONCERNS (perf warning)
- [ ] T-2.1: Write integration tests @ai-build -- IN PROGRESS
- [ ] T-2.2: Security scan @ai-verify -- PENDING
```

## Resume Protocol

When invoked with `--resume`, read `specs/plan.md` and determine re-entry point:

1. **Incomplete tasks remain**: resume at the first incomplete phase. Skip completed tasks.
2. **All tasks DONE but no quality check recorded**: resume at Phase 6 (Quality Check). Read `handlers/quality.md`.
3. **Quality passed but no PR created**: resume at Phase 7 (Deliver). Read `handlers/deliver.md`.
4. **PR exists but not merged**: resume at watch-and-fix loop per `handlers/deliver.md`.

## Handler Dispatch Table

| Phase | Handler | Agent Pattern |
|-------|---------|---------------|
| 6. Quality Check | `handlers/quality.md` | Verify + Review parallel |
| 7. Deliver | `handlers/deliver.md` | PR pipeline + cleanup |

## Common Mistakes

- Dispatching without an approved plan.
- Giving subagents the entire codebase context (scope them tightly).
- Skipping the two-stage review.
- Continuing past a BLOCKED task without user input.
- Modifying test files from a RED phase during a GREEN phase task.
- Skipping the quality check after task execution.

## Integration

- **Called by**: user directly (after `/ai-plan` approval)
- **Calls**: `ai-build` (build tasks), `ai-verify` (scan tasks, quality check), `ai-review` (quality check), `ai-pr` (deliver)
- **Reads**: `ai-verify/SKILL.md`, `ai-review/SKILL.md`, `ai-pr/SKILL.md` (thin orchestrator, embedded at dispatch time)
- **Transitions to**: PR merge (after deliver), or back to `/ai-plan` (if re-plan needed)

$ARGUMENTS

---

# Handler: Phase 4 -- DELIVER

## Purpose

Deliver the dispatch changeset via PR. Build a lightweight Quality Report from Phase 3 results, delegate to ai-pr for the actual PR workflow, clean up spec state, and report completion.

## Prerequisites

- Phase 3 (Quality Check) is complete: either PASS (0 blockers/criticals/highs) or exhausted (max rounds reached with only non-blocking issues remaining).
- All task statuses in `specs/plan.md` are `DONE` or `DONE_WITH_CONCERNS` (no `BLOCKED` tasks that would prevent delivery).
- Branch has commits from per-task execution and per-quality-round fixes.

## Procedure

### Step 1: Build Quality Report

Produce a concise quality summary from Phase 3 results. This is NOT the full Integrity Report from autopilot -- it is a lightweight summary suitable for the PR body.

1. Count quality rounds executed and determine final state (CLEAN or remaining issues with severity breakdown).
2. Run `git diff main...HEAD --stat` to capture the changeset summary.
3. Produce the report:

```markdown
## Quality Report
- Rounds: N/2
- Final: CLEAN | N remaining issues (severity breakdown)
- Changeset: `git diff main...HEAD --stat` summary
```

### Step 2: Deliver PR

This step follows the thin orchestrator principle. Do NOT duplicate PR logic.

1. Read `.github/prompts/ai-pr.prompt.md`.
2. Determine entry point:
   - If unstaged changes exist (e.g., quality report files, late fixes): execute the full ai-pr pipeline starting from Step 0 (commit pipeline through Steps 0-6).
   - If all changes are already committed: **start from Step 7** (pre-push checks). Dispatch already commits per-task and per-quality-round, so this is the normal path.
3. The PR body MUST include the following sections:
   - Standard ai-pr sections: Summary, Test Plan, Work Items, Checklist.
   - The `## Quality Report` from Step 1 as a dedicated section.
4. Enable auto-complete with squash merge per ai-pr Step 13.
5. Enter the watch-and-fix loop per ai-pr Step 14, unless dispatch was invoked with `--no-watch`. If `--no-watch`: skip the loop and proceed directly to Step 3 (Cleanup).

### Step 3: Cleanup

Execute after the PR merges (detected by the watch loop), or immediately after PR creation if `--no-watch` was passed.

1. **Clear `specs/spec.md`** with:
   ```markdown
   # No active spec

   Run /ai-brainstorm to start a new spec.
   ```

2. **Clear `specs/plan.md`** with:
   ```markdown
   # No active plan

   Run /ai-plan after brainstorm approval.
   ```

3. **Add entry to `specs/_history.md`** with the spec ID, title, date, and branch name. If `_history.md` does not exist, create it with this header first:
   ```markdown
   # Spec History

   Completed specs. Details in git history.

   | ID | Title | Status | Created | Branch |
   |----|-------|--------|---------|--------|
   ```
   Then append the new entry row to the table.

4. **Verify cleanup**: re-read `specs/spec.md` and `specs/plan.md` after clearing. If either file still contains old spec content (anything other than the placeholder text), clear it again. Do not trust the write succeeded without reading back.

5. **Stage and commit** all cleanup changes:
   ```
   chore: clear spec state after dispatch delivery
   ```

### Step 4: Final Report

Print the completion summary to the user:

```
Dispatch Complete!

Spec: spec-NNN -- [title]
Tasks: N completed, M with concerns
Quality rounds: R/2
PR: #NNN (merged|pending)
```

Field sources:
- **Spec**: from `specs/spec.md` frontmatter (read before cleanup clears it).
- **Tasks**: count from `specs/plan.md`. "completed" = status `DONE`. "with concerns" = status `DONE_WITH_CONCERNS`.
- **Quality rounds**: from Phase 3 execution log.
- **PR**: number from the PR creation step. State is "merged" if watch loop confirmed merge, "pending" if `--no-watch` was used.

## Resume Protocol

When dispatch is invoked with `--resume` and the pipeline is at the deliver phase:

1. **PR exists**: check for an open PR on the current branch.
   - If found: enter the watch-and-fix loop (ai-pr Step 14). Skip Steps 1-2.
   - If merged: proceed to Step 3 (Cleanup).
2. **PR does not exist**: start from Step 1 (Build Quality Report) and execute the full deliver procedure.

Resume NEVER re-executes completed phases. The plan.md task statuses are the source of truth for resume decisions.

## Failure Modes

| Condition | Action |
|-----------|--------|
| PR creation fails (VCS error, auth failure, network) | STOP and report the error. Do NOT retry PR creation -- VCS errors require user diagnosis. The changeset is preserved in the branch. |
| Watch loop escalates (same check fails 3 times) | STOP per ai-pr handler protocol (Step 14). Report which check is failing and the 3 attempts made. PR remains open for manual intervention. |
| Cleanup fails (file write error, permission denied) | Warn but do NOT block. The PR is already delivered -- cleanup is best-effort. Report which cleanup step failed so the user can run it manually. |
| `_history.md` does not exist | Create it with the standard header (see Step 3.3), then add the entry. This is expected on first dispatch delivery. |
| Pre-push checks fail (Step 7 via ai-pr) | STOP and report. Quality issues that slip past Phase 3 must be resolved before delivery. Do not force-push or skip checks. |

---

# Handler: Phase 3 -- QUALITY CHECK

## Purpose

Evaluate the full changeset as a unit after all dispatch tasks complete. Dispatch Agent(Verify) + Agent(Review) in parallel, consolidate findings with unified severity mapping, fix issues, and iterate up to 2 rounds. This is where cross-task integration issues are caught -- the first time all task changes are evaluated as a single unit. Proportionate to dispatch scale (typically < 3 concerns, < 10 files).

## Prerequisites

| Condition | Source |
|-----------|--------|
| All tasks complete | Every task in `plan.md` marked `[x]`. |
| No blocked tasks | Zero tasks in BLOCKED state. |

## Thin Orchestrator

This handler does NOT contain verify or review logic. It reads:

- `.github/prompts/ai-verify.prompt.md` -- IRRV protocol, 7 scan modes, scan output contract
- `.github/prompts/ai-review.prompt.md` -- 8-agent parallel review, self-challenge protocol, confidence scoring

These protocols are embedded verbatim into subagent prompts at dispatch time. When those skills improve, this handler benefits automatically.

## Procedure

### Step 1 -- Scope the Changeset

Compute the changeset diff: `git diff main...HEAD` -- this is the input for both assessment agents.

### Step 2 -- Iterative Assessment and Fix (round 1 to 2)

Repeat the following cycle. Track the current round number (R = 1 or 2).

#### Step 2a -- Assess (2 agents in parallel)

Dispatch two assessment agents simultaneously. Each gets fresh context.

**Agent(Verify)** -- platform mode:
- Read `.github/prompts/ai-verify.prompt.md` at dispatch time.
- Embed the IRRV protocol and the Scan Modes table into the agent prompt.
- Run all 7 scan modes (governance, security, quality, performance, a11y, feature, architecture) on the changeset.
- Output: scored verdict with findings per the Scan Output Contract (Score N/100, Verdict, Findings table, Gate Check).

**Agent(Review)** -- 8-agent parallel review:
- Read `.github/prompts/ai-review.prompt.md` at dispatch time.
- Embed the 8 Review Agents table, self-challenge protocol, and confidence scoring rules into the agent prompt.
- Run the full review protocol on `git diff main...HEAD`.
- Output: findings with severity, confidence score, and corroboration status.

If both assessment agents fail in this round: retry the round once. If the second attempt also fails: **STOP**. Report the failure and escalate to user. Do not proceed.

#### Step 2b -- Consolidate Findings

Map all findings from both sources to a unified severity scale:

| Source | Source Severity | Unified Severity |
|--------|----------------|------------------|
| Verify | blocker | blocker |
| Verify | critical | critical |
| Verify | high | high |
| Verify | medium | medium |
| Verify | low | low |
| Review | (uses same scale) | as-is |

Deduplicate findings that appear in both sources. When both agents flag the same file and line with the same category, merge into a single finding and note corroboration (increases confidence).

Produce a consolidated findings list:

```
Consolidated Findings (Round R):
| # | Unified Severity | Source(s) | Category | Description | File:Line |
```

#### Step 2c -- Evaluate

Count the consolidated findings by unified severity:

- **Blockers**: count
- **Criticals**: count
- **Highs**: count

Decision matrix:

| Condition | Action |
|-----------|--------|
| 0 blockers + 0 criticals + 0 highs | **PASS**. Exit loop. Proceed to Phase 4. |
| Issues remain AND round < 2 | Proceed to Step 2d (fix). |
| Round = 2 AND blockers remain | **STOP**. Do NOT proceed to Phase 4. Report all blockers with evidence and escalate to user. |
| Round = 2 AND only criticals/highs remain (0 blockers) | Proceed to Phase 4 with issues documented. |

#### Step 2d -- Fix

For each finding at blocker, critical, or high unified severity:

1. **Dispatch Agent(Build)** with focused context:
   - The finding: severity, description, file, line
   - The affected task context from `plan.md`

2. **Agent writes the fix**.

3. **Commit fixes** with message format:
   ```
   quality round R -- fix [category]
   ```
   Where `[category]` is the finding category (e.g., security, performance, correctness).

4. **Return to Step 2a** for the next round.

### Step 3 -- Record Quality Rounds

After the loop completes (pass or exhausted), write the quality rounds log to `plan.md` under a `## Quality Rounds` section:

```markdown
## Quality Rounds

Round 1: 2 blockers, 3 criticals, 5 highs -> FIX
Round 2: 0 blockers, 0 criticals, 0 highs -> PASS
```

Or if exhausted with remaining issues:

```markdown
## Quality Rounds

Round 1: 2 blockers, 3 criticals, 5 highs -> FIX
Round 2: 1 blocker, 0 criticals, 1 high -> STOP (blockers remain)
```

## Dispatch Quality Does NOT Check

This handler intentionally omits governance concerns. The following are outside its scope:

- Decision-store constraint violations (no Agent(Guard))
- Expired risk acceptances
- Ownership model violations
- Framework integrity drift

Users working on governance-sensitive changes must run `/ai-governance` separately.

## Gate

**Pass condition**: 0 blockers + 0 criticals + 0 highs after assessment.

**Exit condition**: pass achieved OR 2 rounds exhausted.

**Hard stop**: blockers remaining after round 2 prevent Phase 4 entry. No exceptions.

## Failure Modes

| Condition | Action |
|-----------|--------|
| Both assessment agents fail in a round | Retry the round once. If second attempt also fails: STOP and escalate to user. |
| Fix agent introduces new issues | Next assessment round catches them. The loop either converges or exhausts at round 2. |
| Single assessment agent fails but the other succeeds | Use available findings. Log the missing assessment. Do not retry the entire round for a single agent failure -- only retry when both fail. |

## Behavioral Negatives

The following actions are prohibited during this phase:

- **Do NOT** weaken severity mappings to force a pass.
- **Do NOT** skip either assessment agent (Verify, Review). Both run every round.
- **Do NOT** proceed to Phase 4 with known blockers remaining.
- **Do NOT** retry more than 2 rounds. 2 is the hard ceiling.
- **Do NOT** modify assessment agent findings to make them less severe.
- **Do NOT** use forbidden language in status reports: "should work", "looks good", "probably fine", "seems to", "I think", "most likely".
- **Do NOT** merge findings in a way that loses information. Every finding must be traceable to its source agent.
