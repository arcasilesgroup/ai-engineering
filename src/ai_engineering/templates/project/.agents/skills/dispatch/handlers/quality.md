# Handler: Phase 3 -- QUALITY CHECK

## Purpose

Evaluate the full changeset as a unit after all dispatch tasks complete. Dispatch the verify agent and the review agent in parallel, consolidate findings with unified severity mapping, fix issues, and iterate up to 2 rounds. This is where cross-task integration issues are caught -- the first time all task changes are evaluated as a single unit. Proportionate to dispatch scale (typically < 3 concerns, < 10 files).

## Prerequisites

| Condition | Source |
|-----------|--------|
| All tasks complete | Every task in `plan.md` marked `[x]`. |
| No blocked tasks | Zero tasks in BLOCKED state. |

## Thin Orchestrator

This handler does NOT contain verify or review logic. It reads:

- `.agents/skills/verify/SKILL.md` -- IRRV protocol, 7 scan modes, scan output contract
- `.agents/skills/review/SKILL.md` -- 8-agent parallel review, self-challenge protocol, confidence scoring

These protocols are embedded verbatim into subagent prompts at dispatch time. When those skills improve, this handler benefits automatically.

## Procedure

### Step 1 -- Scope the Changeset

Compute the changeset diff: `git diff main...HEAD` -- this is the input for both assessment agents.

### Step 2 -- Iterative Assessment and Fix (round 1 to 2)

Repeat the following cycle. Track the current round number (R = 1 or 2).

#### Step 2a -- Assess (2 agents in parallel)

Dispatch two assessment agents simultaneously. Each gets fresh context.

**The verify agent** -- platform mode:
- Read `.agents/skills/verify/SKILL.md` at dispatch time.
- Embed the IRRV protocol and the Scan Modes table into the agent prompt.
- Run all 7 scan modes (governance, security, quality, performance, a11y, feature, architecture) on the changeset.
- Output: scored verdict with findings per the Scan Output Contract (Score N/100, Verdict, Findings table, Gate Check).

**The review agent** -- 8-agent parallel review:
- Read `.agents/skills/review/SKILL.md` at dispatch time.
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

1. **Dispatch the build agent** with focused context:
   - The finding: severity, description, file, line
   - The affected task context from `plan.md`

2. **The build agent writes the fix**.

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

## Governance Gate

For governance-sensitive specs (frontmatter `regulated: true`, or spec body mentions compliance/audit/risk acceptance), run `/ai-governance` on the changeset **before** proceeding to dispatch tasks.

- **Advisory** (medium severity): logged to `plan.md` under `## Governance Findings` -- does not block dispatch.
- **Blocking** (high/critical severity): must be resolved before implementation begins.

This gate is fail-closed for blocking findings -- dispatch halts until resolved.

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
