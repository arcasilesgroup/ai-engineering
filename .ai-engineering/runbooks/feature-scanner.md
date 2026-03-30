---
name: feature-scanner
description: "Scan last 24h commits and PRs against spec history to detect unimplemented features, uncovered acceptance criteria, and spec-vs-code regressions"
type: operational
cadence: daily
---

# Feature Scanner

## Objetivo

Detect unimplemented features, uncovered acceptance criteria, and spec-vs-code regressions by cross-referencing recent commits and merged PRs against completed spec history. Runs daily on a 24-hour lookback window and produces task work items for every verified gap.

## Precondiciones

- Git repository with commit history accessible via `git log`.
- `.ai-engineering/specs/_history.md` exists with at least one spec in `done` status.
- Work item provider configured in `manifest.yml` field `work_items.provider` (GitHub or Azure DevOps).
- CLI tools available: `gh` (GitHub) or `az` (Azure DevOps) authenticated for the target repository.

## Procedimiento

### Step 1 -- Collect recent commits

```bash
git log --since="24 hours ago" --format="%H %s" --no-merges
```

Store the output as the change ledger. If no commits exist, skip to Step 9 and report "no changes in window."

### Step 2 -- Collect merged PRs

```bash
# GitHub
SINCE=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S 2>/dev/null \
     || date -u -v-24H +%Y-%m-%dT%H:%M:%S)
gh pr list --state merged --json number,title,mergedAt,body \
  --jq "[.[] | select(.mergedAt >= \"$SINCE\")]"

# Azure DevOps (when provider is azure_devops)
az repos pr list --status completed \
  --query "[?closedDate >= '$SINCE']" -o json
```

Record each PR number, title, body, and changed files (`gh pr diff <number> --name-only`).

### Step 3 -- Load spec history

```bash
cat .ai-engineering/specs/_history.md
```

Extract the last 5 specs with status `done`. Record spec ID, title, and branch name.

### Step 4 -- Extract acceptance criteria from spec archive

For each spec, recover content from git history. Criteria appear under `## Acceptance Criteria` or `## Goals`.

```bash
SPEC_BRANCH="spec/080-standards-engine-delivery-intelligence"
COMMIT_HASH=$(git log --all --format="%H" --grep="$SPEC_BRANCH" \
  -- .ai-engineering/specs/spec.md | head -1)
git show "$COMMIT_HASH:.ai-engineering/specs/spec.md"
```

Parse each criterion into `{spec_id, criterion_text, keywords[]}`. Keywords are nouns and verbs that drive codebase searches (function names, routes, CLI commands, config keys).

### Step 5 -- Search for implementation evidence

For each criterion, search for matching tests and implementation files.

```bash
# Test files
git grep -l "<keyword>" -- "tests/" "test/" "**/*_test.*" "**/*.test.*"
# Implementation files
git grep -l "<keyword>" -- "src/" "lib/" "scripts/" "*.py" "*.ts"
# CLI commands
git grep -l "<keyword>" -- "**/*cli*" "**/*command*"
```

Mark each criterion: `covered` (evidence found), `partial` (some keywords match), or `gap` (no match).

### Step 6 -- Identify gaps

Compile every `gap` or `partial` criterion. For each, record: spec ID, criterion text, unmatched keywords, what is missing (tests, implementation, or both). Severity: `gap` = high, `partial` = medium.

### Step 7 -- Check for regressions

```bash
# Files changed in recent commits
git diff --name-only HEAD~10..HEAD
# File scope of each recent spec
SPEC_BRANCH="spec/080-standards-engine-delivery-intelligence"
git diff --name-only main..."$SPEC_BRANCH" 2>/dev/null
```

When overlap exists, re-run evidence search from Step 5 against the current tree. Any criterion that was `covered` but now has no match is a regression.

### Step 8 -- Map findings and deduplicate via handler

Map each gap or regression to the Finding contract and route through the shared dedup handler.

**Finding mapping:**

```yaml
domain_label: "feature-gap"
title: "[feature-gap] spec-$SPEC_ID: $CRITERION_SUMMARY"
file_path: $AFFECTED_FILES (first file)
rule_id: "spec-$SPEC_ID"
symbol: null
severity: gap = high, partial = medium, regression = high
body: |
  **Spec:** $SPEC_ID - $SPEC_TITLE
  **Criterion:** $CRITERION_TEXT
  **Status:** gap | partial | regression
  **Missing:** implementation | tests | both
  **Affected files:**
  $FILE_LIST

  **Detected by:** feature-scanner runbook ($RUN_DATE)
```

Follow `handlers/dedup-check.md` to process all findings through the dedup cascade (max 20 per run).

For regressions, also comment on the source PR:

```bash
gh pr comment <pr_number> \
  --body "feature-scanner: regression detected for spec-$SPEC_ID criterion '$CRITERION_TEXT'"
```

### Step 9 -- Generate summary report

```
=== Feature Scanner Report ===
Window:        <start> to <end>
Commits:       12    Merged PRs: 3    Specs checked: 5
Gaps:          2 (1 high, 1 medium)
Regressions:   1
Items created: 3

  [gap/high]    spec-080 | "CLI --format flag" | no implementation
  [gap/medium]  spec-079 | "Hooks relocate"    | partial test coverage
  [regression]  spec-077 | "Prompts migration" | broken by a1b2c3d
```

## Output

Summary report to stdout. Work items created for unimplemented features and regressions. No local files are written.

## Guardrails

1. **Mutations enabled by default.** Work items are created automatically for all gaps and regressions.
2. **Never modifies code.** Inspects the repo and creates task items only. No commits, pushes, or merges.
3. **Explicit criteria only.** Gaps are reported only for acceptance criteria stated verbatim in the spec. No inferred or speculated requirements.
4. **Bounded mutations.** Maximum 20 items per run. Overflow is noted in the report.
5. **Protected states.** Items in `closed`/`resolved` are never modified. Labels `p1-critical` and `pinned` are never removed.
6. **Idempotent.** Deduplication is delegated to the shared handler (`handlers/dedup-check.md`), which checks consolidated issues first, then individual issues, before creating new items.
