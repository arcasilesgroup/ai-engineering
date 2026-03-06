---
name: ci-fixer
schedule: "*/30 * * * *"
environment: worktree
layer: executor
requires: [gh, uv, git]
---

# CI Fixer

## Prompt

Fix PRs that have failing CI checks. Maximum 3 fix attempts per PR.

1. Fetch PRs: `gh pr list --state open --json number,title,statusCheckRollup,headRefName --limit 10`.
2. For each PR with failing checks:
   - Check if already labeled `ci-fix-attempted-3` → skip (needs human).
   - Checkout the PR branch.
   - Read CI failure logs: `gh pr checks <number> --json name,state,output`.
   - Diagnose the failure:
     - Lint failure → run `ruff format` + `ruff check --fix`.
     - Type error → fix the type annotation.
     - Test failure → read the failing test, understand the assertion, fix the code.
     - Security finding → address the finding per security skill.
   - Run local gates to verify fix.
   - If fixed:
     - Commit: `ci-fix: <description of fix>`.
     - Push to the same branch (PR auto-updates).
     - Add label: `ci-fix-attempted-N` (increment attempt counter).
   - If not fixed after local analysis:
     - Add label `ci-fix-attempted-N`.
     - Post comment explaining what was tried and why it failed.
3. After 3 failed attempts:
   - Add label `needs-human`.
   - Post comment: "CI fix attempts exhausted (3/3). Manual intervention required."

## Context

- Uses: debug skill (diagnose CI failures).
- Uses: build agent (implement fixes).
- Reads: CI logs via GitHub API.

## Safety

- Only push to existing PR branches — never to main.
- Maximum 3 fix attempts per PR.
- If fix changes more than 50 lines, stop and label `needs-human`.
- Do NOT use `--no-verify` on any git command.
- Do NOT modify test assertions to make tests pass (fix the code, not the tests).
- Do NOT revert the original PR changes.
