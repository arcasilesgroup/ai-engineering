---
runbook: docs-freshness
version: 1
purpose: "Detect stale documentation, missing coverage for recent features, and doc-vs-code drift"
type: operational
cadence: weekly
hosts:
  - codex-app-automation
  - claude-scheduled-tasks
  - github-agents
  - azure-foundry
provider_scope:
  read: [issues, labels, code, commits]
  write: [comments, work-items, labels]
feature_policy: read-only
hierarchy_policy:
  create: [task]
  mutate: [task]
scan_targets:
  - README.md
  - .ai-engineering/README.md
  - CHANGELOG.md
  - docs/solution-intent.md
  - API documentation
tool_dependencies:
  - gh
  - az
  - git
thresholds:
  staleness_days: 30
  max_findings_per_run: 10
outputs:
  work_items: true
  comments: true
  labels: true
  report: detailed
handoff:
  marker: "docs-stale"
  lifecycle_phase: triage
guardrails:
  max_mutations: 10
  protected_labels: [p1-critical, pinned]
  protected_states: [closed, resolved]
  dry_run_default: true
---

# Docs Freshness

## Purpose

Detect stale documentation, missing coverage for recently shipped features, and drift between documentation claims and actual codebase state. This runbook never modifies documentation -- it reports findings and creates task work items for human authors.

## Procedure

### Step 1 -- Check doc file last-modified dates

For each scan target, retrieve the last commit date and compute days since modification:

```bash
for DOC in README.md .ai-engineering/README.md CHANGELOG.md docs/solution-intent.md; do
  LAST_EPOCH=$(git log -1 --format="%at" -- "$DOC")
  NOW_EPOCH=$(date +%s)
  DAYS_STALE=$(( (NOW_EPOCH - LAST_EPOCH) / 86400 ))
  echo "$DOC | last_modified=$(git log -1 --format='%ai' -- "$DOC") | days_inactive=$DAYS_STALE"
done
```

Any file where `days_inactive >= 30` is flagged as stale.

### Step 2 -- Compare against staleness threshold

For each flagged file, measure how much the codebase changed since the doc was last touched:

```bash
LAST_DOC_SHA=$(git log -1 --format="%H" -- "$DOC")
git diff --stat "$LAST_DOC_SHA"..HEAD -- . ':!*.md'
```

If more than 5 non-doc files changed, the finding severity is elevated from `info` to `warning`.

### Step 3 -- Cross-reference specs with documentation

Detect features that shipped without corresponding doc updates:

```bash
git log --oneline "$LAST_DOC_SHA"..HEAD -- .ai-engineering/specs/_history.md
git show HEAD:.ai-engineering/specs/_history.md | grep -E '^\|.*spec-[0-9]+'
```

For each spec entry that postdates the last doc update, search scan targets for any mention of that feature. A spec with zero doc references is a coverage gap.

### Step 4 -- Verify counts and statistics in READMEs

Check that numeric claims match the actual codebase:

```bash
# Manifest totals
MANIFEST_SKILLS=$(grep -A1 '^skills:' .ai-engineering/manifest.yml | grep 'total:' | awk '{print $2}')
MANIFEST_AGENTS=$(grep -A1 '^agents:' .ai-engineering/manifest.yml | grep 'total:' | awk '{print $2}')

# README claims
grep -nE '[0-9]+ (skills|agents|contexts|stacks)' README.md .ai-engineering/README.md
```

Flag any discrepancy between manifest totals and documented counts. Record the file, line number, claimed value, and actual value.

### Step 5 -- Check CHANGELOG against recent merged PRs

```bash
# GitHub
gh pr list --state merged --limit 20 \
  --json number,title,mergedAt \
  --jq '.[] | select(.mergedAt > (now - 2592000 | strftime("%Y-%m-%dT%H:%M:%SZ"))) | "#\(.number) \(.title)"'

# Azure DevOps
az repos pr list --status completed --top 20 --output json \
  | jq '.[] | select(.closedDate > (now - 2592000 | strftime("%Y-%m-%dT%H:%M:%SZ"))) | "#\(.pullRequestId) \(.title)"'
```

For each merged PR, search `CHANGELOG.md` for the PR number or a keyword match on the title. Missing entries are flagged as coverage gaps.

### Step 6 -- Verify solution-intent architecture alignment

Check that `docs/solution-intent.md` references the current directory structure:

```bash
for DIR in $(ls -d */ 2>/dev/null); do
  DIR_NAME=$(basename "$DIR")
  if ! grep -q "$DIR_NAME" docs/solution-intent.md; then
    echo "DRIFT: directory '$DIR_NAME' not referenced in solution-intent.md"
  fi
done
```

Also verify that component names, agent names, and integration points mentioned in the doc still correspond to existing files. Flag references to deleted or renamed components.

### Step 7 -- Create task work items for findings

For each finding (up to `max_findings_per_run` of 10), create a task:

```bash
# GitHub
gh issue create \
  --title "docs-freshness: $DOC is $DAYS_STALE days stale" \
  --body "## Finding
- **File:** \`$DOC\`
- **Days since last update:** $DAYS_STALE
- **Code changes since:** $CHANGED_FILES files
- **Severity:** $SEVERITY

## What changed
$CODE_DIFF_SUMMARY

## Suggested update
$SUGGESTION

<!-- docs-freshness-runbook -->" \
  --label "docs-stale,type/chore"

# Azure DevOps
az boards work-item create --type Task \
  --title "docs-freshness: $DOC is $DAYS_STALE days stale" \
  --description "File: $DOC | Days stale: $DAYS_STALE | Severity: $SEVERITY" \
  --fields "System.Tags=docs-stale"
```

Each work item includes: the file path, what is stale, what changed in code, and a suggested update direction.

### Step 8 -- Generate detailed report

```
=== Docs Freshness Report <DATE> ===
Scan targets checked:    <N>
Stale documents:         <N>
Coverage gaps:           <N>  (specs without doc references)
Count drift:             <N>  (README stats vs manifest)
CHANGELOG gaps:          <N>  (merged PRs without entries)
Architecture drift:      <N>  (solution-intent mismatches)
Work items created:      <N> / 10
Findings by severity:
  warning:               <N>
  info:                  <N>
```

Hosts may route this report to a Slack channel, PR comment, dashboard, or log sink.

## Provider Notes

| Concern | GitHub (`gh`) | Azure DevOps (`az`) |
|---------|---------------|---------------------|
| Merged PRs | `gh pr list --state merged --json` | `az repos pr list --status completed` |
| Create work item | `gh issue create --title --body --label` | `az boards work-item create --type Task` |
| Label finding | `--label "docs-stale"` | `--fields "System.Tags=docs-stale"` |
| Comment | `gh issue comment --body` | `az boards work-item update --discussion` |
| Auth | `GH_TOKEN` or `gh auth login` | `az login` or `AZURE_DEVOPS_EXT_PAT` |

## Host Notes

| Host | Considerations |
|------|---------------|
| `codex-app-automation` | Scheduled Codex task. Auth via `GITHUB_TOKEN` secret. Network sandbox: all API calls through `gh`/`az` CLI. Budget: 10 min. |
| `claude-scheduled-tasks` | Weekly cron. Loads runbook as context. Respect `dry_run_default: true` unless `--live` is passed. Persist report to `state/docs-freshness-report.json` if writable. |
| `github-agents` | GitHub Actions workflow or Copilot agent. Auth: `${{ secrets.GITHUB_TOKEN }}`. Requires `issues: write` permission. Azure DevOps unavailable. |
| `azure-foundry` | Auth via managed identity (`az login --identity`). GitHub PAT from Key Vault. Pre-install: `az extension add --name azure-devops`. |

## Safety

- **Never modifies documentation.** This runbook only reads docs and creates work items. No repository file is written or overwritten.
- **Mutation cap.** Maximum 10 work item creations per run. Excess findings are reported in the summary but not materialized. Remaining findings carry over to the next run.
- **Protected labels.** Work items carrying `p1-critical` or `pinned` are never relabeled or commented on.
- **Protected states.** Items in `closed` or `resolved` state are never reopened or modified.
- **Dry-run default.** All writes are logged to stdout but not executed unless the caller passes `--arm` or sets `DRY_RUN=false`.
- **Idempotent.** Duplicate work items are avoided by searching for existing issues with the `<!-- docs-freshness-runbook -->` marker before creating new ones.
- **No hierarchy escalation.** Creates tasks only. Never creates or mutates features, epics, or user stories.
