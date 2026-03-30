---
name: work-item-audit
description: "Audit non-functional work items against repo reality, close invalid noise, and rewrite mixed items before consolidation"
type: operational
cadence: weekly
---

# Work Item Audit

## Objetivo

Audit open non-functional work items before consolidation so the backlog reflects
current repo reality instead of stale findings, false positives, or mixed-signal
aggregates. The runbook supports GitHub Issues and Azure DevOps work items,
analyzes candidates in parallel, auto-closes conclusively invalid items, rewrites
mixed items in place to retain only valid findings, and leaves ambiguous cases open
with an audit rationale.

This runbook is the standard hygiene step that runs before `consolidate`.

## Precondiciones

- Work items provider configured in `manifest.yml` (`github` or `azure_devops`)
- CLI access: `gh` for GitHub, `az` for Azure DevOps
- Repository cloned locally with full access to `src/`, `tests/`,
  `.ai-engineering/specs/`, `.ai-engineering/state/decision-store.json`, and
  `.ai-engineering/CONSTITUTION.md`
- Candidate work items are non-functional findings or maintenance items, not
  normal feature backlog
- Parallel analysis capacity available for bounded batch execution

## Procedimiento

### Step 1 -- Fetch candidate work items

Retrieve open work items from the configured provider, then filter to the default
audit scope: scan findings, audit findings, refinement output, tech debt,
documentation drift, manual-action items, and consolidated maintenance items.
Exclude normal product backlog items by default.

**GitHub:**

```bash
gh issue list --state open --limit 200 \
  --json number,title,body,labels,updatedAt \
  --jq '[.[] | select(
    (.labels | map(.name) | any(
      . == "feature-gap" or
      . == "architecture-drift" or
      . == "security-finding" or
      . == "manual-action" or
      . == "tech-debt" or
      . == "documentation" or
      . == "consolidated"
    )) or
    (.title | startswith("[scan]")) or
    (.title | startswith("[gap]")) or
    (.title | startswith("[consolidated]"))
  )]'
```

**Azure DevOps:**

```bash
az boards query --wiql "SELECT [System.Id], [System.Title], [System.Description], [System.Tags], [System.ChangedDate], [System.State] FROM WorkItems WHERE [System.State] <> 'Closed' AND [System.State] <> 'Removed' ORDER BY [System.ChangedDate] DESC" --output json
```

For Azure DevOps, apply the same candidate filter client-side using tags and title
prefixes analogous to the GitHub labels and prefixes above.

If zero candidates remain after filtering, emit a summary and stop.

### Step 2 -- Partition into bounded parallel batches

Split the candidate set into `N` bounded batches for parallel analysis. Use a
stable shard key so re-runs are deterministic.

Rules:

1. `N` must not exceed 8.
2. Each batch must contain at most 10 items.
3. Analysis may run in parallel, but mutations do not.

Record the shard plan in the summary report:

```
Batch 1: #255 #238 #239 #130 #133
Batch 2: #293 #294 #295 #296 #297
...
```

### Step 3 -- Gather evidence for each item

For every candidate item, collect the full context needed to judge validity.

**3a. Read tracker context**

- Title, body, labels/tags, comments, status/state
- Linked PRs, linked commits, cross-references, and related items
- For consolidated items, read every original linked or referenced item listed in
  the body or comments

**GitHub:**

```bash
gh issue view <NUMBER> --json title,body,labels,comments,timelineItems
```

**Azure DevOps:**

```bash
az boards work-item show --id <ID> --expand all --output json
az boards work-item relation list --id <ID> --output json
```

**3b. Read repo context**

Search the codebase, tests, docs, specs, and decision store for evidence that the
reported problem still exists, has already been fixed, was intentionally accepted,
or is a known false positive.

```bash
git grep -n "<keyword>" -- src/ tests/ .ai-engineering/ docs/
git log --oneline --all --grep="<keyword>" -- src/ tests/ .ai-engineering/
```

Always read:

- `.ai-engineering/CONSTITUTION.md`
- `.ai-engineering/state/decision-store.json`
- `.ai-engineering/specs/_history.md`

**3c. Classify evidence**

Assign one classification:

| Classification | Meaning |
|----------------|---------|
| `valid` | The finding still applies and should remain open |
| `invalid` | The finding is a false positive, duplicate, stale, superseded, or already fixed |
| `mixed` | The item contains both valid and invalid findings |
| `ambiguous` | Evidence is insufficient for safe closure or rewrite |

### Step 4 -- Decide the mutation plan

After all batches complete, merge their findings into one centralized mutation
plan. Each item gets exactly one planned action:

| Classification | Action |
|----------------|--------|
| `valid` | Keep open, optionally normalize title/body if clearly stale |
| `invalid` | Comment rationale and close automatically |
| `mixed` | Rewrite title/body in place to keep only valid findings, comment the delta, keep open |
| `ambiguous` | Comment what is unclear, keep open, add clarification marker if available |

Evidence is considered conclusive when at least one of these is true:

1. The code or docs now contradict the original claim directly.
2. A later commit, spec, PR, or decision explicitly resolved or superseded it.
3. A related item already tracks the same valid work and this item is pure duplicate
   or redundant residue.
4. The item depends on manual external review that has already been completed.

### Step 5 -- Apply tracker mutations

Apply mutations centrally and sequentially after synthesis.

**For invalid items -- GitHub:**

```bash
gh issue comment "$NUMBER" --body "Closing after work-item audit: this item is no longer valid.

- Classification: invalid
- Reason: <false positive | duplicate | already fixed | superseded | stale>
- Evidence: <repo file / PR / decision / related item>

If new evidence appears, reopen the item.

<!-- work-item-audit:closed -->"

gh issue close "$NUMBER" --reason "not planned"
```

**For invalid items -- Azure DevOps:**

```bash
az boards work-item update --id "$ID" \
  --state Closed \
  --discussion "Closing after work-item audit: this item is no longer valid.

- Classification: invalid
- Reason: <false positive | duplicate | already fixed | superseded | stale>
- Evidence: <repo file / PR / decision / related item>

Reopen if new evidence appears."
```

**For mixed items -- GitHub:**

```bash
gh issue edit "$NUMBER" --title "<rewritten title>" --body "<rewritten body with only valid findings>"

gh issue comment "$NUMBER" --body "work-item-audit rewrote this item in place.

- Removed as invalid: <list>
- Kept as valid: <list>
- Evidence reviewed: <related items, repo paths, decisions>

<!-- work-item-audit:rewritten -->"
```

**For mixed items -- Azure DevOps:**

```bash
az boards work-item update --id "$ID" \
  --title "<rewritten title>" \
  --description "<rewritten body with only valid findings>" \
  --discussion "work-item-audit rewrote this item in place.

- Removed as invalid: <list>
- Kept as valid: <list>
- Evidence reviewed: <related items, repo paths, decisions>"
```

**For ambiguous items:**

Post a comment explaining what is missing and keep the item open.

### Step 6 -- Emit summary report

Produce a summary to stdout:

```
=== Work Item Audit Report ===
Date:                 2026-03-30T00:00:00Z
Provider:             github
Candidates scanned:   38
Parallel batches:     4
Valid kept:           12
Invalid closed:       9
Mixed rewritten:      5
Ambiguous kept:       4
Skipped:              8
Mutations used:       23 / 30

Closed:
  - #238 false positive duplicate of #239
  - #255 superseded by decision update

Rewritten:
  - #305 retained 6 valid gaps, removed 3 resolved sub-findings

Ambiguous:
  - #130 requires refreshed SonarCloud evidence
```

The summary is the only local output. No files are written.

## Output

Summary report to stdout. Tracker mutations are the primary output: comments,
title/body rewrites, and closures. No local files are written.

## Guardrails

1. **Mutations enabled by default for conclusive cases.** Invalid items are closed automatically when the evidence is conclusive.
2. **Centralized mutation phase only.** Parallel workers may analyze, but only the merged mutation plan may edit or close items.
3. **Never touches code.** This runbook audits tracker state only. No source edits, branches, commits, or pull requests.
4. **Always reads related context before closing.** If an item references or depends on other items, those related items must be reviewed first.
5. **Edit mixed items in place.** It does not split mixed items into new work items by default.
6. **Normal feature backlog is out of scope by default.** Human-authored product work is excluded unless explicitly included by the operator.
7. **Bounded mutations.** Maximum 30 mutations per run. Remaining items are reported and deferred.
8. **Idempotent.** Re-running the same day must not duplicate comments, rewrites, or closures for unchanged evidence.
9. **Protected labels are not absolute shields.** `security`, `p1-critical`, `manual-action`, and `consolidated` items may still be closed when evidence is conclusive.
