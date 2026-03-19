# Handler: Find Reviews

## Purpose

Find and summarize existing review comments on a PR or in the codebase. Useful for understanding prior feedback before starting a new review.

## Procedure

### Step 1 -- Identify Source

Determine where to look for reviews:

- **PR number provided**: use `gh api repos/{owner}/{repo}/pulls/{number}/comments` to fetch PR comments
- **No PR number**: check `git log --format='%H %s' -20` for recent review-related commits
- **File paths provided**: search for TODO/FIXME/HACK/REVIEW comments in those files

### Step 2 -- Collect Comments

For PR comments:
1. Fetch all review comments via GitHub API
2. Group by file and line number
3. Classify: approved, changes-requested, comment-only

For inline comments in code:
1. Grep for review markers: `TODO`, `FIXME`, `HACK`, `REVIEW`, `XXX`
2. Include surrounding context (3 lines before/after)
3. Check git blame for age and author

### Step 3 -- Summarize

Produce a summary grouped by theme:

```markdown
## Review Comments Summary

### Open Issues (N)
- [file:line] [severity] [comment summary]

### Resolved (N)
- [file:line] [what was resolved]

### Patterns
- [recurring themes across comments]
```

### Step 4 -- Feed Forward

If transitioning to a new review (`/ai-review review`), carry forward:
- Unresolved issues from prior reviews (check if they still apply)
- Recurring patterns (things this codebase gets wrong repeatedly)
