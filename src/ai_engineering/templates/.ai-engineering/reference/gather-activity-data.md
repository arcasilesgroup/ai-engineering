# Gather Activity Data

Canonical commands for collecting sprint and standup data from git history and work-item providers.
Referenced by: `/ai-standup`, `/ai-sprint`.

## Git Log

```bash
# Commits by author in a date range (no merges)
git log --since="<start>" --until="<end>" --author="<name>" --format="%h|%s|%an" --no-merges

# Recent commits (lookback N days)
git log --since="N days ago" --author="<name>" --format="%h|%s|%an" --no-merges

# Summary stats for a period
git log --since="<start>" --until="<end>" --shortstat --no-merges
```

If `--author` is not specified, resolve from `git config user.name` or `gh api user`.

## GitHub PR Queries

```bash
# All PRs by author (open + closed + merged)
gh pr list --author="<name>" --state=all --json number,title,state,mergedAt,updatedAt,author,url

# Merged PRs in a date range
gh pr list --state merged --json number,title,mergedAt,author

# Issues by team label
gh issue list --label "<team_label>" --state all \
  --json number,title,state,labels,milestone,closedAt,assignees
```

Filter results client-side by date when `gh` does not support `--since`/`--until` flags.

## Azure DevOps PR Queries

```bash
# Completed PRs
az repos pr list --status completed

# Work items by area path and current iteration
az boards query --wiql "SELECT [System.Id], [System.Title], [System.State], \
  [System.AssignedTo], [System.WorkItemType] \
  FROM WorkItems \
  WHERE [System.AreaPath] UNDER '<area_path>' \
  AND [System.IterationPath] = @CurrentIteration" --expand relations
```

## Provider Detection

Read `.ai-engineering/manifest.yml` field `work_items.provider` (`github` or `azure_devops`) before running queries. Use provider-specific config:

- **GitHub**: `work_items.github.team_label`
- **Azure DevOps**: `work_items.azure_devops.area_path`, auto-detect `iteration_path`
