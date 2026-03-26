# Handler: Phase 5 -- QUALITY LOOP

## Purpose

Converge on quality through iterative assessment and fixing. Dispatch the verify agent + the guard agent + the review agent in parallel on the full changeset, consolidate findings with unified severity mapping, fix issues, and iterate up to 3 rounds. This is where cross-sub-spec integration issues are caught -- the first time all sub-spec changes are evaluated as a single unit.

## Prerequisites

| Condition | Source |
|-----------|--------|
| Phase 4 complete | All waves committed. Manifest updated with per-sub-spec statuses. |
| Sub-spec Self-Reports exist | Each implemented sub-spec has a Self-Report section in its `sub-NNN/plan.md` with classifications (real/aspirational/stub/failing/invented/hallucinated). |
| Manifest has sub-spec statuses | `specs/autopilot/manifest.md` shows `complete` or `blocked` per sub-spec. |

## Thin Orchestrator

This handler does NOT contain verify, guard, or review logic. It reads:

- `.claude/skills/ai-verify/SKILL.md` -- IRRV protocol, 7 scan modes, scan output contract
- `.claude/skills/ai-review/SKILL.md` -- 8-agent parallel review, self-challenge protocol, confidence scoring
- `.claude/skills/ai-governance/SKILL.md` -- advise mode, decision-store lifecycle

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

**The verify agent** -- platform mode:
- Read `.claude/skills/ai-verify/SKILL.md` at dispatch time.
- Embed the IRRV protocol and the Scan Modes table into the agent prompt.
- Run all 7 scan modes (governance, security, quality, performance, a11y, feature, architecture) on the changeset.
- Output: scored verdict with findings per the Scan Output Contract (Score N/100, Verdict, Findings table, Gate Check).

**The guard agent** -- advise mode:
- Read `.claude/skills/ai-governance/SKILL.md` at dispatch time.
- Run governance check against `state/decision-store.json`.
- Check for: expired risk acceptances, ownership violations, framework integrity drift.
- Output: advisory findings with severity levels (concern, warn, info).

**The review agent** -- 8-agent parallel review:
- Read `.claude/skills/ai-review/SKILL.md` at dispatch time.
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

1. **Dispatch the build agent** with focused context:
   - The finding: severity, description, file, line
   - The affected sub-spec context (scope from `sub-NNN/spec.md`, plan from `sub-NNN/plan.md`)
   - The Self-Report entry for that area (so the agent understands what was claimed)

2. **The agent writes the fix** and updates the Self-Report classification:
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
