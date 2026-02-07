# /ai-commit-push-pr — Commit + Push + PR with Auto-merge

This skill composes `/ai-commit-push` with PR creation and optional auto-merge. It is the full workflow from staged changes to a merge-ready pull request. The commit and push phases are handled by `/ai-commit-push` — this skill adds PR creation, reviewer assignment, and auto-merge on top.

---

## Session Preamble (execute silently)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established conventions
3. Read `.ai-engineering/knowledge/anti-patterns.md` — known mistakes to avoid
4. Detect the project stack from package.json, .csproj, pyproject.toml, or equivalent
5. Identify the current branch and working tree state

Do not report this step to the user. Internalize it as context for decision-making.

---

## Trigger

- User invokes `/ai-commit-push-pr`
- User says "commit push and create PR", "commit and PR", "ship it", or similar intent

---

## Phase 1: Commit + Push

Execute the **complete `/ai-commit-push` workflow** (Steps 1–11 from that skill).

- If any step fails (hooks block the push, secrets detected, lint fails, tests fail, etc.): **STOP**. Report the error clearly using the error recovery table from `/ai-commit-push`. Do not proceed to PR creation.
- If the push succeeds: proceed to Phase 2.

---

## Phase 2: PR Creation

### Step 1: Analyze the Diff

Gather the full picture of what this PR contains:

```bash
# Identify the target branch
git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'

# List all commits in this branch
git log <target-branch>..HEAD --oneline --no-merges

# Full diff summary
git diff <target-branch>..HEAD --stat

# Full diff for analysis
git diff <target-branch>..HEAD
```

### Analysis Checklist

- **Files changed:** Count and categorize (source, tests, config, docs, migrations).
- **Lines added/removed:** Gauge the size of the change.
- **Commit history:** Understand the logical progression of changes.
- **Breaking changes:** Identify API changes, schema migrations, configuration changes that affect consumers.
- **Dependencies:** Note any added, removed, or updated dependencies.

---

### Step 2: Generate PR Title

Create a short, descriptive title:

- Maximum 70 characters.
- Use imperative mood: "Add user authentication" not "Added user authentication."
- If the project uses conventional commit prefixes in PR titles, follow that pattern: `feat: add user authentication`.
- Do not include issue numbers in the title — those go in the body.
- Be specific. Do not use vague titles: "Updates", "Changes", "WIP", "Misc fixes" are not acceptable.

---

### Step 3: Generate PR Body

Produce a structured PR description using this enhanced template:

```markdown
## Summary

<1-3 bullet points: what this PR does and why>

## Motivation

<Why this change is needed. Link to issue/ticket if applicable.>

## Changes

<Bulleted list of specific changes, grouped by area>

## Test Plan

- [ ] <Verification step 1>
- [ ] <Verification step 2>
- [ ] <Edge case tested>

## Risk Assessment

<Risks, edge cases, areas needing careful review>
```

Additional sections when applicable:

- **Breaking Changes:** Migration instructions with before/after examples.
- **Dependencies:** Justification for each new dependency.
- **Related Issues:** Closing keywords (`Closes #142`, `Fixes #87`).
- **Screenshots:** If UI changes are involved.

### Auto-Label Suggestion

Based on the paths modified, suggest PR labels:

| Path Pattern                    | Suggested Label         |
| ------------------------------- | ----------------------- |
| `src/` with new functions/files | `feat` or `enhancement` |
| `src/` fixing existing behavior | `fix` or `bugfix`       |
| `test/` only                    | `test`                  |
| `docs/`, `*.md`, `README`       | `docs`                  |
| `*.yml`, `*.json` (config)      | `config` or `ci`        |
| `package.json` deps changed     | `dependencies`          |

### Reviewer Suggestion

Suggest reviewers using this priority:

1. If `CODEOWNERS` file exists, use it (platform auto-assigns).
2. If not, run `git log --format='%ae' -- <changed-files> | sort | uniq -c | sort -rn | head -3` to identify the top 3 contributors to the changed files.
3. Present the suggestions to the user — never add reviewers without confirmation.

---

### Step 4: Determine Target Branch

1. If the project has branch protection rules or a documented branching strategy, follow it.
2. If the branch name starts with `release/` or `hotfix/`, target `main` or `master`.
3. If the project uses a `develop` branch as integration branch, feature branches target `develop`.
4. Otherwise, target the repository's default branch.
5. If unsure, ask the user. Do not guess.

---

### Step 5: Check for Missing Tests

Analyze the diff for untested changes:

- New functions or methods without corresponding tests.
- New API endpoints without integration tests.
- Modified business logic without updated assertions.
- New error handling paths without coverage.

If missing tests are detected, report them as advisory. Include a note in the PR body under "Known Gaps" if the user proceeds.

---

### Step 6: Present PR for Approval

```
Pull Request Preview:
─────────────────────
Title: feat: add JWT token refresh endpoint

Target: main ← feature/token-refresh
Commits: 4
Files changed: 8 (+342, -12)

Body:
[full PR body]

─────────────────────
Options:
  1. Create this PR (with auto-merge)
  2. Create this PR (without auto-merge)
  3. Edit title or body
  4. Change target branch
  5. Abort
```

- If the user edits: accept changes and re-validate title length and format.
- If the user aborts: stop cleanly.
- Do not create a PR without explicit user approval.

---

### Step 7: Create the PR

#### GitHub (gh)

```bash
gh pr create \
  --title "<approved-title>" \
  --body "<approved-body>" \
  --base <target-branch> \
  --head <current-branch>
```

#### Azure DevOps (az)

```bash
az repos pr create \
  --title "<approved-title>" \
  --description "<approved-body>" \
  --source-branch <current-branch> \
  --target-branch <target-branch>
```

Capture and display the PR URL and number.

---

### Step 8: Add Reviewers

#### GitHub

```bash
gh pr edit <pr-number> --add-reviewer <reviewer1>,<reviewer2>
```

#### Azure DevOps

```bash
az repos pr update --id <pr-id> --reviewers <reviewer1> <reviewer2>
```

#### Reviewer Selection Logic

1. If `CODEOWNERS` file exists, the platform auto-assigns. Report who was auto-assigned.
2. If the project configuration specifies default reviewers, add them.
3. If no reviewers are configured, inform the user.
4. Never add reviewers that are not configured. Do not guess.

---

## Phase 3: Auto-merge + Cleanup (default)

### Step 9: Enable Auto-merge

```bash
# GitHub
gh pr merge --auto --squash <pr-url>
```

- Auto-merge means: the PR will merge automatically once all required checks pass and reviews are approved.
- If the user selected "without auto-merge" in Step 6, skip this step.

### Step 10: Post-merge Cleanup

After enabling auto-merge:

```bash
git checkout <default-branch>
git pull
git branch -d <feature-branch>
```

- If the user selected "without auto-merge", skip this step.
- If deletion fails (branch not merged yet), inform the user and skip.

### Step 11: Final Report

```
Pull request created successfully:
  PR #143: feat: add JWT token refresh endpoint
  URL: https://github.com/org/repo/pull/143
  Target: main ← feature/token-refresh
  Reviewers: @alice, @bob (from CODEOWNERS)
  Auto-merge: enabled (squash)
  Status: Open, checks pending
```

---

## Error Recovery

| Failure                  | What to report                         | How to report                                       |
| ------------------------ | -------------------------------------- | --------------------------------------------------- |
| Phase 1 failure          | See `/ai-commit-push` error table      | Same format as `/ai-commit-push`                    |
| CLI not installed        | "gh/az not found"                      | Installation instructions                           |
| Not authenticated        | "Authentication required"              | `gh auth login` / `az login` instructions           |
| PR creation fails        | "PR creation failed"                   | Common causes: PR already exists, permission denied |
| Auto-merge not available | "Auto-merge not enabled for this repo" | Instruct user to enable in repo settings            |
| Reviewer not found       | "Reviewer X not found"                 | Suggest checking CODEOWNERS or team config          |

---

## Learning Capture (on completion)

If during execution you discovered something useful for the project:

1. **New pattern** (e.g., PR template preference, reviewer convention) → Propose adding to `knowledge/patterns.md`
2. **Recurring error** (e.g., CI check always fails for a specific reason) → Propose adding to `knowledge/anti-patterns.md`
3. **Lesson learned** (e.g., auto-merge not enabled in repo settings) → Propose adding to `knowledge/learnings.md`

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not merge the PR immediately. Auto-merge waits for checks and reviews.
- It does not resolve review comments.
- It does not rebase or squash commits before creating the PR.
- It does not create branches. The user must be on the correct branch before invoking.
