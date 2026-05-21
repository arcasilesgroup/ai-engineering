# Handler: Phase 3 -- QUALITY CHECK

## Purpose

Evaluate the full changeset as a unit after all dispatch tasks complete.
Dispatch the verify agent and the review agent in parallel, consolidate
findings with unified severity mapping, and run **one bounded
quality-remediation pass** when the first assessment finds blocker /
critical / high issues that are safe to fix without new product or
architecture decisions. **Contract**: single round, fail-loud with one
bounded remediation pass (spec-131 D-131-05 as amended by spec-145).
Clean -> exit with PASS. Blocker / critical / high findings may be
remediated once; the final reassessment is terminal. Remaining blocker /
critical / high findings STOP + escalate. This is where cross-task
integration issues are caught -- the first time all task changes are
evaluated as a single unit. Proportionate to dispatch scale (typically <
3 concerns, < 10 files).

## Prerequisites

| Condition | Source |
|-----------|--------|
| All tasks complete | Every task in `plan.md` marked `[x]`. |
| No blocked tasks | Zero tasks in BLOCKED state. |
| Remediation budget unused | `plan.md` does not record `quality_remediation.used: true`. |

## Thin Orchestrator

This handler does NOT contain verify or review logic. It reads:

- `.claude/skills/ai-verify/SKILL.md` -- IRRV protocol, 7 scan modes,
  scan output contract
- `.claude/skills/ai-review/SKILL.md` -- 8-agent parallel review,
  self-challenge protocol, confidence scoring

These protocols are embedded verbatim into subagent prompts at dispatch
time. When those skills improve, this handler benefits automatically.

## Procedure

### Step 1 -- Scope the Changeset

Compute the changeset diff: `git diff main...HEAD` -- this is the input
for both assessment agents.

### Step 2 -- Initial Assessment

Run once on the full changeset. Track the pass as `initial_assessment`,
not as a numbered retry loop.

#### Step 2a -- Assess (2 agents in parallel)

Dispatch two assessment agents simultaneously. Each gets fresh context.

**The verify agent** -- platform mode:

- Read `.claude/skills/ai-verify/SKILL.md` at dispatch time.
- Embed the IRRV protocol and the Scan Modes table into the agent prompt.
- Run all 7 scan modes (governance, security, quality, performance,
  a11y, feature, architecture) on the changeset.
- Output: scored verdict with findings per the Scan Output Contract
  (Score N/100, Verdict, Findings table, Gate Check).

**The review agent** -- 8-agent parallel review:

- Read `.claude/skills/ai-review/SKILL.md` at dispatch time.
- Embed the 8 Review Agents table, self-challenge protocol, and
  confidence scoring rules into the agent prompt.
- Run the full review protocol on `git diff main...HEAD`.
- Output: findings with severity, confidence score, and corroboration
  status.

If both assessment agents fail to RUN (timeout / crash / missing skill
file / dispatch error), retry that operational dispatch once. If the
second dispatch attempt also fails to RUN: **STOP**. Report the
operational failure and escalate to the user. This is not a
quality-remediation pass.

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

Deduplicate findings that appear in both sources. When both agents flag
the same file and line with the same category, merge into a single
finding and note corroboration (increases confidence).

Produce a consolidated findings list:

```text
Consolidated Findings:
| # | Unified Severity | Source(s) | Category | Description | File:Line | Reproducer |
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
| Any blocker/critical/high and remediation budget unused | Enter Step 2d bounded remediation pass. |
| Any blocker/critical/high and remediation budget already used | **STOP**. Do NOT proceed to `/ai-pr`. Emit `quality_loop_blocked` event and escalate. |

Medium/low findings are recorded in the PR body but do not trigger
remediation.

#### Step 2d -- Bounded Remediation Pass

Run **one bounded quality-remediation pass** only when every selected
finding is eligible.

Eligibility for remediation:

1. Severity is blocker, critical, or high.
2. The finding has concrete evidence: file/path, command, failing test,
   or policy rule.
3. The fix is localized to the current changeset or to a gate-owned
   artifact required for the current source-tree gate (for example a
   verifier false positive, lockfile vulnerability pin, or allowlist
   entry that does not store secret-shaped literals).
4. The fix is mechanical: it does NOT require a product decision,
   architecture redesign, destructive migration, cross-repo edit, or
   baseline cleanup campaign.

**Advisory + conservative (D-149-04).** Condition 4 is a judgment call, so
it is biased to the safe side: when eligibility under it is uncertain,
treat the finding as INELIGIBLE and escalate (Step 2f). Condition 4 may
only escalate — it can never silently auto-pass a finding (deem eligible →
remediate → PASS) on an optimistic read. The STOP/PASS verdict (Steps 2c /
2e) is a **deterministic count of remaining blocker/critical/high**
findings, so the same diff yields the same STOP verdict.

Ineligible findings STOP immediately with the escalation report from
Step 2f.

For each eligible finding:

1. Record `quality_remediation.used: true` in `plan.md` before editing.
2. Assign the affected task context from `plan.md`.
3. Patch only the finding-scoped files.
4. Run the narrowest reproducer that proves the finding is fixed.
5. Record the reproducer command and result under `## Quality
   Remediation` in `plan.md`.

##### Cross-platform reproducers

Reproducer commands must be platform-neutral where practical:

- Prefer Python entry points, `pytest` node IDs, `uv run ...`, or
  `ai-eng ...` commands over shell-specific glue.
- Do not rely on a POSIX shell pipeline for required evidence unless a
  Windows PowerShell equivalent is provided in the report.
- Use repository-relative paths in reports; never record
  machine-specific absolute paths.

### Step 2e -- Final Reassessment

After the remediation pass, run verify + review once more on the full
changeset using the same Step 2a/2b assessment protocol. This is the
**final reassessment**.

Decision matrix:

| Condition | Action |
|-----------|--------|
| 0 blockers + 0 criticals + 0 highs | **PASS**. Proceed to Phase 4 (Deliver). |
| Any blocker/critical/high remains | **STOP**. Do NOT proceed to `/ai-pr`. Emit `quality_loop_blocked` event and escalate. |

Do NOT perform a second remediation pass. Do NOT widen scope beyond the
consolidated findings. Do NOT continue patching after final reassessment.

### Step 2f -- Escalate (on terminal blocker)

For each remaining blocker/critical/high finding, emit a structured
escalation report containing:

1. **Finding**: severity, description, file, line.
2. **Source**: which assessment agent flagged it (verify, review, or
   both -- corroboration boosts confidence).
3. **Affected task context** from `plan.md`.
4. **Remediation status**: not attempted, fixed but still failing, or
   ineligible.
5. **Recommended next step**: typically `/ai-debug`, `/ai-plan`
   revision, or operator decision.

Emit a `quality_loop_blocked` framework event with the finding payload
and STOP. The operator is responsible for resolution; re-dispatching
`/ai-build` is the explicit retry path after human decision.

### Step 3 -- Record Quality Outcome

After Step 2 completes (PASS or STOP), write a single outcome to
`plan.md` under `## Quality Outcome` and, if used, `## Quality
Remediation`.

PASS example:

```markdown
## Quality Outcome

Final: 0 blockers, 0 criticals, 0 highs -> PASS

## Quality Remediation

used: true
max_attempts: 1
final_reassessment: pass
```

Blocked example:

```markdown
## Quality Outcome

Final: 1 blocker, 0 criticals, 1 high -> STOP (escalated to user)

## Quality Remediation

used: true
max_attempts: 1
final_reassessment: blocked
```

## Governance Gate

For governance-sensitive specs (frontmatter `regulated: true`, or spec
body mentions compliance/audit/risk acceptance), run `/ai-governance` on
the changeset **before** proceeding to dispatch tasks.

- **Advisory** (medium severity): logged to `plan.md` under `##
  Governance Findings` -- does not block dispatch.
- **Blocking** (high/critical severity): must be resolved before
  implementation begins.

This gate is fail-closed for blocking findings -- dispatch halts until
resolved.

## Gate

**Pass condition**: 0 blockers + 0 criticals + 0 highs after initial
assessment or after the one bounded remediation pass and final
reassessment.

**Exit condition**: PASS achieved OR blocker/critical/high found after
the remediation budget is consumed.

**Hard stop**: any blocker/critical/high after final reassessment
prevents Phase 4 entry. No exceptions. No second remediation pass.

## Failure Modes

| Condition | Action |
|-----------|--------|
| Both assessment agents fail to RUN | Retry the operational dispatch once. If second attempt also fails: STOP and escalate. |
| Single assessment agent fails but the other succeeds | Use available findings. Log the missing assessment. Do not retry the entire assessment for a single agent failure. |
| Finding lacks a concrete reproducer or scoped fix | STOP and escalate; do not guess. |
| Remediation pass used and findings remain | STOP and escalate; user decides whether to re-plan or re-run manually. |

## Behavioral Negatives

The following actions are prohibited during this phase:

- **Do NOT** weaken severity mappings to force a pass.
- **Do NOT** skip either assessment agent (Verify, Review). Both run.
- **Do NOT** proceed to Phase 4 with known blocker/critical/high
  findings remaining.
- **Do NOT** perform a second remediation pass.
- **Do NOT** broaden the fix beyond quality-loop findings.
- **Do NOT** launch long full-suite gates after targeted reproducers
  without reporting the expected cost and receiving operator approval,
  unless the plan explicitly names that full-suite gate.
- **Do NOT** modify assessment agent findings to make them less severe.
- **Do NOT** use forbidden language in status reports: "should work",
  "looks good", "probably fine", "seems to", "I think", "most likely".
- **Do NOT** merge findings in a way that loses information. Every
  finding must be traceable to its source agent.
