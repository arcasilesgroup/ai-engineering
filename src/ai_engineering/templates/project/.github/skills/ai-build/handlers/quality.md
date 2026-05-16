# Handler: Phase 3 -- QUALITY CHECK

## Purpose

Evaluate the full changeset as a unit after all dispatch tasks complete. Dispatch the verify agent and the review agent in parallel, consolidate findings with unified severity mapping. **Contract**: single round, fail-loud (spec-131 D-131-05). Clean → exit with PASS. Blockers → STOP + escalate (no auto-retry). This is where cross-task integration issues are caught -- the first time all task changes are evaluated as a single unit. Proportionate to dispatch scale (typically < 3 concerns, < 10 files).

## Prerequisites

| Condition | Source |
|-----------|--------|
| All tasks complete | Every task in `plan.md` marked `[x]`. |
| No blocked tasks | Zero tasks in BLOCKED state. |

## Thin Orchestrator

This handler does NOT contain verify or review logic. It reads:

- `.github/skills/ai-verify/SKILL.md` -- IRRV protocol, 7 scan modes, scan output contract
- `.github/skills/ai-review/SKILL.md` -- 8-agent parallel review, self-challenge protocol, confidence scoring

These protocols are embedded verbatim into subagent prompts at dispatch time. When those skills improve, this handler benefits automatically.

## Procedure

### Step 1 -- Scope the Changeset

Compute the changeset diff: `git diff main...HEAD` -- this is the input for both assessment agents.

### Step 2 -- Final Assessment (single round, fail-loud)

Run **once** on the full changeset. Track no round number. Clean → exit with PASS. Any blocker → STOP, do not proceed to `/ai-pr`, emit escalation report.

#### Step 2a -- Assess (2 agents in parallel)

Dispatch two assessment agents simultaneously. Each gets fresh context.

**The verify agent** -- platform mode:
- Read `.github/skills/ai-verify/SKILL.md` at dispatch time.
- Embed the IRRV protocol and the Scan Modes table into the agent prompt.
- Run all 7 scan modes (governance, security, quality, performance, a11y, feature, architecture) on the changeset.
- Output: scored verdict with findings per the Scan Output Contract (Score N/100, Verdict, Findings table, Gate Check).

**The review agent** -- 8-agent parallel review:
- Read `.github/skills/ai-review/SKILL.md` at dispatch time.
- Embed the 8 Review Agents table, self-challenge protocol, and confidence scoring rules into the agent prompt.
- Run the full review protocol on `git diff main...HEAD`.
- Output: findings with severity, confidence score, and corroboration status.

If both assessment agents fail: retry the round once. If the second attempt also fails: **STOP**. Report the failure and escalate to user. Do not proceed.

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
Consolidated Findings:
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
| 0 blockers + 0 criticals + 0 highs | **PASS**. Proceed to Phase 4 (Deliver). |
| Any blocker | **STOP**. Do NOT proceed to `/ai-pr`. Emit `quality_loop_blocked` event. Report all blockers with evidence and escalate to user. |
| 0 blockers + criticals/highs present | Proceed to Phase 4 with issues documented in the PR body. |

#### Step 2d -- Escalate (on blocker)

For each finding at blocker severity, emit a structured escalation report containing:

1. **Finding**: severity, description, file, line.
2. **Source**: which assessment agent flagged it (verify, review, or both -- corroboration boosts confidence).
3. **Affected task context** from `plan.md`.
4. **Recommended next step**: typically `/ai-debug` or operator decision; the agent does NOT auto-retry.

Emit a `quality_loop_blocked` framework event with the finding payload and STOP. The operator is responsible for resolution; `/ai-build --rerun-quality-loop` (or re-dispatching `/ai-build`) is the explicit retry path.

### Step 3 -- Record Quality Outcome

After Step 2 completes (PASS or STOP), write a single-row outcome to `plan.md` under a `## Quality Outcome` section:

```markdown
## Quality Outcome

Final: 0 blockers, 0 criticals, 0 highs -> PASS
```

Or if blocked:

```markdown
## Quality Outcome

Final: 1 blocker, 0 criticals, 1 high -> STOP (escalated to user)
```

## Governance Gate

For governance-sensitive specs (frontmatter `regulated: true`, or spec body mentions compliance/audit/risk acceptance), run `/ai-governance` on the changeset **before** proceeding to dispatch tasks.

- **Advisory** (medium severity): logged to `plan.md` under `## Governance Findings` -- does not block dispatch.
- **Blocking** (high/critical severity): must be resolved before implementation begins.

This gate is fail-closed for blocking findings -- dispatch halts until resolved.

## Gate

**Pass condition**: 0 blockers + 0 criticals + 0 highs after assessment.

**Exit condition**: PASS achieved (clean) OR blocker found (STOP, escalate).

**Hard stop**: any blocker prevents Phase 4 entry. No exceptions, no retries.

## Failure Modes

| Condition | Action |
|-----------|--------|
| Both assessment agents fail in the round | Retry the round once. If second attempt also fails: STOP and escalate to user. |
| Single assessment agent fails but the other succeeds | Use available findings. Log the missing assessment. Do not retry the entire round for a single agent failure -- only retry when both fail. |
| Operator wants to re-attempt after fix | Operator re-invokes `/ai-build` (or `/ai-build --rerun-quality-loop`); the handler does NOT auto-retry. |

## Behavioral Negatives

The following actions are prohibited during this phase:

- **Do NOT** weaken severity mappings to force a pass.
- **Do NOT** skip either assessment agent (Verify, Review). Both run.
- **Do NOT** proceed to Phase 4 with known blockers remaining.
- **Do NOT** loop or auto-retry. Single round is the contract; blockers stop the pipeline (spec-131 D-131-05).
- **Do NOT** modify assessment agent findings to make them less severe.
- **Do NOT** use forbidden language in status reports: "should work", "looks good", "probably fine", "seems to", "I think", "most likely".
- **Do NOT** merge findings in a way that loses information. Every finding must be traceable to its source agent.
