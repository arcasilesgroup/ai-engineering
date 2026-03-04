---
name: pr-review
schedule: "0 */4 * * *"
environment: worktree
layer: reporting
requires: [gh]
---

# PR Review

## Prompt

Review open PRs that have been waiting for review for more than 4 hours. Post an informative code review comment.

1. Fetch open PRs: `gh pr list --state open --json number,title,createdAt,reviewDecision,labels,additions,deletions,changedFiles --limit 20`.
2. Filter: PRs without any review and created > 4 hours ago.
3. For each qualifying PR:
   - Read the diff: `gh pr diff <number>`.
   - Analyze for:
     - Code quality: complexity, duplication, naming conventions.
     - Security: hardcoded secrets, injection risks, unsafe patterns.
     - Testing: are new functions covered by tests?
     - Standards compliance: does it follow `.ai-engineering/standards/`?
     - Breaking changes: API signature changes, removed exports.
   - Post a review comment with findings organized by category.
   - If no issues found, post an approval comment: "Automated review: no issues found."
   - Do NOT approve or request changes — only post informative comments.
4. Add label `ai-reviewed` after posting the review.

## Context

- Uses: quality skill (review mode).
- Uses: security skill (static mode).
- Reads: `.ai-engineering/standards/` for code standards.

## Safety

- Read-only analysis + comments. Never approve or request changes.
- Do NOT modify PR code or push to PR branches.
- Do NOT merge PRs.
- Maximum 5 reviews per run.
- Skip PRs labeled `skip-ai-review`.
- Skip PRs already labeled `ai-reviewed`.
