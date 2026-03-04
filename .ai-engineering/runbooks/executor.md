---
name: executor
schedule: "0 * * * *"
environment: worktree
layer: executor
requires: [gh, uv, git]
---

# Issue Executor

## Prompt

Pick the highest-priority `agent-ready` issue and implement it. Create a PR with auto-merge enabled.

1. Fetch candidates: `gh issue list --label agent-ready --state open --json number,title,labels,body --limit 10`.
2. Sort by priority: `p1-critical` > `p2-high` > `p3-normal`, then by creation date (oldest first).
3. Pick the top issue. Skip if:
   - Already has a linked PR (check for branch reference in comments).
   - Labeled `blocked` or `in-progress`.
4. Add label `in-progress` to the selected issue.
5. Create a feature branch: `agent/<issue-number>-<slug>`.
6. Read the issue body for acceptance criteria and context.
7. Execute the build skill: implement the change following all standards.
8. Run quality gates: `ruff check`, `ruff format`, `ty check`, `uv run pytest`.
9. If gates pass:
   - Commit: `fix #<issue-number>: <title>`.
   - Push branch to origin.
   - Create PR: `gh pr create --title "fix #<number>: <title>" --body "Closes #<number>"`.
   - Enable auto-merge: `gh pr merge <pr-number> --auto --squash --delete-branch`.
10. If gates fail:
    - Post a comment on the issue with the failure details.
    - Remove `in-progress` label, add `agent-blocked`.

## Context

- Uses: build agent (full implementation capability).
- Uses: commit skill, pr skill for governed workflow.
- Reads: `.ai-engineering/standards/` for code standards.

## Safety

- Only ONE issue per run. Do not batch.
- Branch MUST be `agent/<issue-number>-<slug>` — never commit to main.
- If tests fail after 3 fix attempts, stop and label `agent-blocked`.
- Do NOT disable or bypass any gate.
- Do NOT use `--no-verify`.
- Auto-merge requires CI to pass — GitHub handles the merge, not the agent.
- Maximum 100 lines changed per run. If the issue requires more, label `too-large` and skip.
