# /ai-pr — Pull Request Creation Workflow

This skill defines the step-by-step workflow for creating a well-structured, standards-compliant pull request. Every PR is analyzed for completeness, quality, and risk before submission. The goal is a PR that a reviewer can understand and evaluate in minutes, not hours.

---

## Trigger

- User invokes `/ai-pr`
- User says "create a PR", "open a pull request", "submit PR", or similar intent

---

## Prerequisites

Before starting, verify the following:

- The current directory is a git repository.
- The current branch is not the default branch (`main`, `master`, or project-configured default). You cannot create a PR from the default branch to itself.
- There are commits on the current branch that are not on the target branch (`git log <target>..<current> --oneline`). If there are no commits, inform the user and stop.
- The CLI tool is available: `gh` (GitHub) or `az repos` (Azure DevOps). If neither is installed, inform the user and stop.
- The user is authenticated with the CLI tool (`gh auth status` or `az account show`).

---

## Step 1: Analyze the Diff

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

## Step 2: Generate PR Title

Create a short, descriptive title that follows the project conventions:

### Rules

- Maximum 70 characters.
- Use imperative mood: "Add user authentication" not "Added user authentication."
- If the project uses conventional commit prefixes in PR titles, follow that pattern: `feat: add user authentication`.
- Do not include issue numbers in the title — those go in the body.
- Be specific: "Fix race condition in session cleanup" is better than "Fix bug."
- Do not use vague titles: "Updates", "Changes", "WIP", "Misc fixes" are not acceptable.

---

## Step 3: Generate PR Body

Produce a structured PR description with the following sections:

### Summary

A 1-3 sentence overview of what this PR does and why. This is the first thing a reviewer reads — make it count.

- What problem does this solve?
- What approach was taken?
- What is the user-visible impact?

### Changes

A bulleted list of the specific changes, grouped by area:

```markdown
## Changes

### Authentication
- Add JWT refresh token endpoint at `POST /auth/refresh`
- Implement automatic token rotation on refresh
- Add refresh token revocation on logout

### Database
- Add `refresh_tokens` table migration
- Add index on `refresh_tokens.user_id`

### Tests
- Add integration tests for token refresh flow
- Add unit tests for token rotation logic
```

### Testing

Describe how this was tested and how a reviewer can verify it:

```markdown
## Testing

- [ ] Unit tests pass (`npm test`)
- [ ] Integration tests pass (`npm run test:integration`)
- [ ] Manual testing: login, wait for token expiry, verify automatic refresh
- [ ] Tested with expired refresh token — confirms 401 response
```

### Risk Assessment

Identify risks, edge cases, and areas that need careful review:

```markdown
## Risk Assessment

- **Medium:** Database migration adds a new table. Rollback migration included.
- **Low:** New endpoint follows existing auth patterns. No changes to existing endpoints.
- **Note:** Refresh token rotation means concurrent requests during refresh may fail. Documented in ADR-027.
```

### Additional Sections (When Applicable)

- **Breaking Changes:** If any, list them explicitly with migration instructions.
- **Dependencies:** If new dependencies were added, justify each one.
- **Screenshots:** If there are UI changes, include before/after screenshots.
- **Related Issues:** Link to issues, tickets, or design documents. Use closing keywords where appropriate (`Closes #142`, `Fixes #87`).

---

## Step 4: Determine Target Branch

Identify the correct target branch for this PR:

### Default Logic

1. If the project has branch protection rules or a documented branching strategy, follow it.
2. If the branch name starts with `release/` or `hotfix/`, the target is typically `main` or `master`.
3. If the project uses a `develop` branch as integration branch, feature branches target `develop`.
4. Otherwise, target the repository's default branch.

### Compliance Branch Rules

- Feature branches (`feature/*`, `feat/*`) target the integration branch (`develop` or `main`).
- Release branches (`release/*`) target `main` or `master`.
- Hotfix branches (`hotfix/*`) target `main` or `master` (and may also need to be merged into `develop`).
- If unsure, ask the user which branch to target. Do not guess.

```bash
# Check if the branch already has an upstream tracking reference
git config --get branch.<current-branch>.merge
```

---

## Step 5: Check for Missing Tests

Analyze the diff to identify untested changes:

### Detection Criteria

- **New functions or methods** in source files that have no corresponding test additions.
- **New API endpoints** without integration or e2e tests.
- **Modified business logic** without updated test assertions.
- **New error handling paths** without tests that trigger those paths.
- **Edge cases** visible in the code (null checks, boundary conditions, empty arrays) without test coverage.

### Report Format

If missing tests are detected:

```
Missing test coverage detected:
  - src/auth/refresh.ts: refreshToken() — no test covers the expired refresh token path
  - src/auth/refresh.ts: rotateToken() — no test for concurrent rotation attempts

Recommendation: Add tests before creating the PR. Proceed anyway? [y/N]
```

- If the user chooses to proceed: include a note in the PR body under "Known Gaps."
- Do not silently ignore missing tests.

---

## Step 6: Run Quality Checks

Run the project's quality verification suite before creating the PR:

```bash
# Detect and run appropriate commands
# Lint
npx eslint . / dotnet format --verify-no-changes / ruff check .

# Type check
npx tsc --noEmit / dotnet build / mypy .

# Tests
npm test / dotnet test / pytest

# Build (if applicable)
npm run build / dotnet build / cargo build
```

### Handling Failures

- **Lint failures:** Display the errors. Ask the user to fix or proceed with a note in the PR body.
- **Type check failures:** Display the errors. These should be fixed before creating a PR. Recommend stopping to fix.
- **Test failures:** Display the failing tests. Strongly recommend fixing before creating the PR. If the user insists on proceeding, add a "Known Failing Tests" section to the PR body.
- **Build failures:** Stop. A PR that does not build should not be created.

---

## Step 7: Present for Approval

Display the complete PR details for user review:

```
Pull Request Preview:
─────────────────────
Title: feat: add JWT token refresh endpoint

Target: main ← feature/token-refresh
Commits: 4
Files changed: 8 (+342, -12)

Body:
[full PR body as generated in Step 3]

─────────────────────
Options:
  1. Create this PR
  2. Edit title or body
  3. Change target branch
  4. Abort
```

- If the user edits: accept their changes and re-validate the title length and format.
- If the user aborts: stop cleanly. Do not create the PR.
- Do not create a PR without explicit user approval.

---

## Step 8: Create the PR

Push the branch and create the PR using the appropriate CLI:

### GitHub (gh)

```bash
# Ensure branch is pushed
git push -u origin HEAD

# Create PR
gh pr create \
  --title "<approved-title>" \
  --body "<approved-body>" \
  --base <target-branch> \
  --head <current-branch>
```

### Azure DevOps (az)

```bash
# Ensure branch is pushed
git push -u origin HEAD

# Create PR
az repos pr create \
  --title "<approved-title>" \
  --description "<approved-body>" \
  --source-branch <current-branch> \
  --target-branch <target-branch>
```

### Post-Creation

- Capture and display the PR URL.
- Report the PR number/ID.
- Confirm the PR was created successfully.

---

## Step 9: Add Reviewers

If the project has configured reviewers or code owners:

### GitHub

```bash
# Add reviewers
gh pr edit <pr-number> --add-reviewer <reviewer1>,<reviewer2>

# Add labels if configured
gh pr edit <pr-number> --add-label "<label>"
```

### Azure DevOps

```bash
# Add reviewers
az repos pr update --id <pr-id> --reviewers <reviewer1> <reviewer2>
```

### Reviewer Selection Logic

1. If `CODEOWNERS` file exists, the platform auto-assigns. Report who was auto-assigned.
2. If the project configuration specifies default reviewers, add them.
3. If no reviewers are configured, inform the user: "No default reviewers configured. Add reviewers manually or configure them in the project settings."
4. Never add reviewers that are not configured. Do not guess who should review.

---

## Final Output

After successful PR creation, display:

```
Pull request created successfully:
  PR #143: feat: add JWT token refresh endpoint
  URL: https://github.com/org/repo/pull/143
  Target: main ← feature/token-refresh
  Reviewers: @alice, @bob (from CODEOWNERS)
  Status: Open, checks pending
```

---

## Error Recovery

| Failure | Action |
|---|---|
| Not a git repo | Stop. Inform the user. |
| No commits to submit | Stop. Inform the user there is nothing to create a PR for. |
| CLI not installed | Stop. Provide installation instructions for `gh` or `az`. |
| Not authenticated | Stop. Provide auth instructions (`gh auth login` or `az login`). |
| Push fails | Display error. Common causes: no remote, auth failure, branch protection. |
| PR creation fails | Display error. Common causes: PR already exists, branch not pushed, permission denied. |
| Build/tests fail | Warn. Recommend fixing before creating PR. Allow user override with documentation. |

---

## What This Skill Does NOT Do

- It does not merge the PR. Merging is a separate action performed after review.
- It does not resolve review comments. That is a manual process.
- It does not rebase or squash commits. The user should do that before invoking `/ai-pr` if desired.
- It does not create branches. The user must be on the correct branch before invoking.
- It does not run CI pipelines. CI is triggered automatically by the PR creation.
