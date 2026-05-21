# Handler: Phase 5 -- QUALITY LOOP

**Contract**: single round, fail-loud with one bounded
quality-remediation pass -- spec-131 D-131-05 as amended by spec-145.

## Purpose

Converge on quality through one initial assessment, one optional bounded
remediation pass, and one terminal final reassessment. Dispatch the
verify agent + the guard agent + the review agent in parallel on the
full changeset, consolidate findings with unified severity mapping, and
allow exactly **one bounded quality-remediation pass** for
blocker/critical/high findings that are attributable to the autopilot
changeset and safe to patch without new operator decisions. Remaining
blocker/critical/high findings after final reassessment STOP and
escalate. This is where cross-sub-spec integration issues are caught --
the first time all sub-spec changes are evaluated as a single unit.

## Prerequisites

| Condition | Source |
|-----------|--------|
| Phase 4 complete | All waves committed. Manifest updated with per-sub-spec statuses. |
| Sub-spec Self-Reports exist | Each implemented sub-spec has a Self-Report section in its `sub-NNN/plan.md` with classifications (real/aspirational/stub/failing/invented/hallucinated). |
| Manifest has sub-spec statuses | `.ai-engineering/runtime/autopilot/manifest.md` shows `complete` or `blocked` per sub-spec. |
| Remediation budget unused | Manifest does not record `quality_remediation.used: true`. |

## Thin Orchestrator

This handler does NOT contain verify, guard, or review logic. It reads:

- `.claude/skills/ai-verify/SKILL.md` -- IRRV protocol, 7 scan modes,
  scan output contract
- `.claude/skills/ai-review/SKILL.md` -- 8-agent parallel review,
  self-challenge protocol, confidence scoring
- `.claude/skills/ai-governance/SKILL.md` -- advise mode,
  decision-store lifecycle

These protocols are embedded verbatim into subagent prompts at dispatch
time. When those skills improve, this handler benefits automatically.

**Token efficiency**: All three skill files are read ONCE at quality
loop entry (before Step 2 begins). The changeset diff and Self-Reports
are also computed/read once.

## Procedure

### Step 1 -- Scope the Changeset

Check `.ai-engineering/runtime/autopilot/manifest.md` for blocked or
cascade-blocked sub-specs.

- If all sub-specs are `complete`: quality loop covers the full
  changeset.
- If partial (some sub-specs `blocked`): note which scope was not
  delivered. The quality loop verifies only the implemented subset.
  Record the gap:

```text
Quality Scope: partial (sub-003, sub-007 blocked)
Verified subset: sub-001, sub-002, sub-004, sub-005, sub-006
```

Compute the changeset diff: `git diff main...HEAD` -- this is the input
for all assessment agents.

### Step 1b -- Pre-load Shared Context

Read the following files ONCE and cache their content for the quality
loop:

1. **Skill files**: `.claude/skills/ai-verify/SKILL.md`,
   `.claude/skills/ai-review/SKILL.md`,
   `.claude/skills/ai-governance/SKILL.md`
2. **Self-Reports**: glob
   `.ai-engineering/runtime/autopilot/sub-*/plan.md`, extract `##
   Self-Report` sections from each
3. **Changeset diff**: the `git diff main...HEAD` computed in Step 1

### Step 2 -- Initial Assessment

Run once. Track this pass as `initial_assessment`, not as a numbered
retry loop.

#### Step 2a -- Assess (3 agents in parallel)

**Concurrency cap (spec-139 M1)**: `cap = min(3,
AIENG_MAX_QUALITY_AGENTS)`.

The quality cap is intentionally low because the three assessment agents
(verify, guard, review) are each multi-tool orchestrators rather than
lightweight workers. `AIENG_MAX_QUALITY_AGENTS` can only *lower* the cap
(and the `performance.concurrency.max_quality_agents` manifest knob
behaves the same way) -- it never raises the cap above the default of
`3`. The framework default is `cap = 3`, so all three agents run in
parallel unless the operator has explicitly capped further (for example
`AIENG_MAX_QUALITY_AGENTS=1` for a memory-constrained host).

Dispatch up to `cap` assessment agents simultaneously. Each gets fresh
context. Use the pre-loaded skill files and diff from Step 1b -- do NOT
re-read them from disk.

**The verify agent** -- platform mode:

- Use the cached `ai-verify/SKILL.md` content.
- Embed the IRRV protocol and the Scan Modes table into the agent prompt.
- Run all 7 scan modes (governance, security, quality, performance,
  a11y, feature, architecture) on the changeset.
- Output: scored verdict with findings per the Scan Output Contract
  (Score N/100, Verdict, Findings table, Gate Check).

**The guard agent** -- advise mode:

- Use the cached `ai-governance/SKILL.md` content.
- Run governance check against `state/decision-store.json`.
- Check for: expired risk acceptances, ownership violations, framework
  integrity drift.
- Output: advisory findings with severity levels (concern, warn, info).

**The review agent** -- 8-agent parallel review:

- Use the cached `ai-review/SKILL.md` content.
- Embed the 8 Review Agents table, self-challenge protocol, and
  confidence scoring rules into the agent prompt.
- Run the full review protocol on the cached changeset diff.
- Output: findings with severity, confidence score, and corroboration
  status.

If all 3 assessment agents fail to RUN in this assessment (operational
failure -- agent timeout / crash / missing skill file / dispatch error),
retry the dispatch once. If the second dispatch attempt also fails to
RUN: **STOP**. Report the failure and escalate to user. This is
OPERATIONAL retry of the assessment dispatch itself, not a
quality-remediation pass.

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

Deduplicate findings that appear in multiple sources. When two or more
agents flag the same file and line with the same category, merge into a
single finding and note corroboration (increases confidence).

**Cross-reference against Self-Reports**: use the cached Self-Report
data from Step 1b. For each finding, check the corresponding sub-spec
Self-Report from Phase 4.

- If Self-Report classifies a test as `real` but Verify finds it
  failing: flag the discrepancy as a blocker. The Self-Report was
  inaccurate.
- If Self-Report classifies something as `aspirational` or `stub` and
  Verify confirms it: not a discrepancy -- the gap was declared.

Produce a consolidated findings list:

```text
Consolidated Findings:
| # | Unified Severity | Source(s) | Category | Description | File:Line | Self-Report Match | Owner |
```

#### Step 2c -- Evaluate

Count the consolidated findings by unified severity:

- **Blockers**: count
- **Criticals**: count
- **Highs**: count

Decision matrix:

| Condition | Action |
|-----------|--------|
| 0 blockers + 0 criticals + 0 highs | **PASS**. Proceed to Phase 6. |
| Any blocker/critical/high and remediation budget unused | Enter Phase 5b bounded remediation pass. |
| Any blocker/critical/high and remediation budget already used | **STOP**. Do NOT proceed to Phase 6. Do NOT create PR. Emit `autopilot.quality_loop_blocked` and escalate. |

Medium/low findings are documented in the Integrity Report but do not
trigger remediation.

### Phase 5b -- Bounded Remediation Pass

Run **one bounded quality-remediation pass** only for eligible
blocker/critical/high findings.

Eligibility for remediation:

1. The finding is attributable to the implemented autopilot changeset,
   a sub-spec Self-Report discrepancy, or a gate-owned artifact required
   for the current source-tree gate.
2. The finding maps to an owning sub-spec, wave, integration step, or
   explicitly shared file.
3. The finding has concrete evidence: file/path, command, failing test,
   policy rule, or review location.
4. The fix is mechanical and localized: it does NOT require new
   decomposition, deep-planning, product approval, architecture redesign,
   destructive migration, cross-repo edits, or baseline cleanup.

**Advisory + conservative (D-149-04).** Condition 4 is a judgment call, so
it is biased to the safe side: when eligibility under it is uncertain,
treat the finding as INELIGIBLE and escalate. It may only escalate — it can
never silently auto-pass a finding — so the same changeset yields the same
STOP verdict (the verdict is a deterministic count of remaining
blocker/critical/high findings).

Ineligible findings STOP immediately with the escalation report from
Step 2f.

Persist the attempt before editing:

```yaml
quality_remediation:
  max_attempts: 1
  used: true
  findings_fixed: []
  final_reassessment: pending
```

For each eligible finding:

1. Assign an owner: `sub-NNN`, `integration`, or `shared`.
2. Patch only the finding-scoped files.
3. Run the narrowest reproducer that proves the finding is fixed.
4. Append the finding id, owner, reproducer, and result to
   `quality_remediation.findings_fixed`.

##### Cross-platform reproducers

Reproducer commands must be platform-neutral where practical:

- Prefer Python entry points, `pytest` node IDs, `uv run ...`, or
  `ai-eng ...` commands over shell-specific glue.
- Do not rely on a POSIX shell pipeline for required evidence unless a
  Windows PowerShell equivalent is provided in the manifest or
  escalation report.
- Use repository-relative paths in reports; never record
  machine-specific absolute paths.

Do NOT re-decompose. Do NOT re-run Phase 2 deep-planning. Do NOT reopen
all waves. Do NOT perform a second remediation pass.

### Step 2e -- Final Reassessment

After Phase 5b, run verify + guard + review once more on the full
implemented changeset using the same Step 2a/2b assessment protocol.
This is the terminal **final reassessment**.

Decision matrix:

| Condition | Action |
|-----------|--------|
| 0 blockers + 0 criticals + 0 highs | **PASS**. Proceed to Phase 6. |
| Any blocker/critical/high remains | **STOP**. Do NOT proceed to Phase 6. Do NOT create PR. Emit `autopilot.quality_loop_blocked` and escalate. |

Update manifest:

```yaml
quality_remediation:
  max_attempts: 1
  used: true
  final_reassessment: pass|blocked
```

### Step 2f -- Escalation Report

For each remaining blocker/critical/high finding:

1. Capture the finding: severity, description, file, line.
2. Capture the affected sub-spec context (scope from `sub-NNN/spec.md`,
   plan from `sub-NNN/plan.md`).
3. Capture the Self-Report entry for that area (so the operator
   understands what was claimed).
4. Capture remediation status: ineligible, attempted, fixed-but-still
   failing, or not attempted because the budget was consumed.
5. Emit STOP + write blocker findings to the manifest under `##
   Blocker Findings`.

The operator is responsible for resolution; `/ai-autopilot --resume`
after manual fix is the explicit retry path. The handler does not keep
patching after final reassessment.

### Step 3 -- Record Quality Outcome

After Step 2 completes (PASS or STOP), write a single-row outcome to
`.ai-engineering/runtime/autopilot/manifest.md` under a `## Quality
Outcome` section:

```markdown
## Quality Outcome

Final: 0 blockers, 0 criticals, 0 highs -> PASS
```

Or if blocked:

```markdown
## Quality Outcome

Final: 1 blocker, 0 criticals, 1 high -> STOP (blockers remain, escalated)
```

## Output

Report to orchestrator upon completion:

**If PASS:**

```text
QUALITY LOOP COMPLETE
- Assessment: initial or final reassessment
- Final: 0 blockers, 0 criticals, 0 highs
- Remediation used: true|false
- Changeset scope: full | partial (list blocked sub-specs)
- Self-Report discrepancies found: N
- Ready for Phase 6: DELIVER
```

**If blocker found:**

```text
QUALITY LOOP BLOCKED
- Assessment: final reassessment
- Remaining: B blockers, C criticals, H highs
- Blocker details:
  1. [severity] [category] [file:line] -- [description]
  2. ...
- ACTION REQUIRED: User must resolve blockers before delivery.
- Rollback hint: git reset --soft HEAD~N (N = wave + quality-fix commits)
```

## Gate

**Pass condition**: 0 blockers + 0 criticals + 0 highs after the initial
assessment or after the one bounded remediation pass and final
reassessment.

**Exit condition**: PASS achieved OR blocker/critical/high remains after
the remediation budget is consumed.

**Hard stop**: any blocker/critical/high after final reassessment
prevents Phase 6 entry. No exceptions. No second remediation pass.

## Failure Modes

| Condition | Action |
|-----------|--------|
| All 3 assessment agents fail to RUN (operational failure: timeout/crash/missing skill file/dispatch error) | Retry the dispatch once. If second attempt also fails to RUN: STOP and escalate. |
| Partial changeset (blocked sub-specs from Phase 4) | Verify only implemented files. Note gaps in the consolidated findings and the manifest. |
| Self-Report discrepancy (claimed `real`, found failing) | Reclassify as blocker; eligible for the one bounded remediation pass if the fix is localized. |
| Single assessment agent fails but others succeed | Use available findings. Log the missing assessment. Do not retry the entire assessment for a single agent failure. |
| Remediation pass used and blocker/critical/high findings remain | STOP and escalate; user decides whether to re-plan or resume manually. |

## Behavioral Negatives

The following actions are prohibited during this phase:

- **Do NOT** weaken severity mappings to force a pass.
- **Do NOT** skip any of the 3 assessment agents (Verify, Guard,
  Review). All three run.
- **Do NOT** proceed to Phase 6 with known blocker/critical/high
  findings remaining.
- **Do NOT** retry the quality loop indefinitely. The only allowed
  quality-finding recovery is one bounded remediation pass followed by
  final reassessment.
- **Do NOT** perform a second remediation pass.
- **Do NOT** modify assessment agent findings to make them less severe.
- **Do NOT** use forbidden language in status reports: "should work",
  "looks good", "probably fine", "seems to", "I think", "most likely".
- **Do NOT** merge findings in a way that loses information. Every
  finding must be traceable to its source agent.
