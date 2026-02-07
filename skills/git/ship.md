# /ai-ship — Unified Ship Workflow

This skill handles the complete shipping workflow: commit, push, and optionally create a pull request with auto-merge. It replaces the separate commit-push and commit-push-pr skills with a single, unified command that supports three modes.

---

## Modes

| Mode                  | Trigger            | What It Does                                      |
| --------------------- | ------------------ | ------------------------------------------------- |
| **Default** (no args) | `/ai-ship`         | Stage → commit → push                             |
| **PR**                | `/ai-ship pr`      | Stage → commit → push → create PR (auto-merge ON) |
| **PR-only**           | `/ai-ship pr-only` | Create PR from current branch (no commit)         |

**Flags:**

- `--no-auto-merge` — Disable auto-merge when creating a PR (applies to `pr` and `pr-only` modes)

---

## Session Preamble (execute silently)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established conventions
3. Read `.ai-engineering/knowledge/anti-patterns.md` — known mistakes to avoid
4. Detect the project stack from package.json, .csproj, pyproject.toml, or equivalent
5. Identify the current branch and working tree state (`git branch --show-current`, `git status --short`)

Do not report this step to the user. Internalize it as context for decision-making.

---

## Trigger

- User invokes `/ai-ship` — default mode (commit + push)
- User invokes `/ai-ship pr` — commit + push + create PR
- User invokes `/ai-ship pr-only` — create PR only (no commit)
- User says "commit and push", "ship it", "commit push and create PR", "create a PR", or similar intent

---

## Mode Detection

Parse the argument to determine the mode:

| Argument          | Mode                                      |
| ----------------- | ----------------------------------------- |
| (none)            | Default — commit + push                   |
| `pr`              | PR — commit + push + create PR            |
| `pr-only`         | PR-only — create PR from current branch   |
| `--no-auto-merge` | Flag — can combine with `pr` or `pr-only` |

If the argument is unrecognized, ask the user which mode they intended.

---

## Specification Gate

BEFORE executing any git operations, present a concise summary to the user:

1. **Mode:** default / pr / pr-only
2. **Branch:** current branch name
3. **Files staged:** list of staged files (categorized: source, tests, config, docs)
4. **Potential commit type:** inferred from the diff (feat/fix/refactor/etc.)
5. **Suggested scope:** inferred from primary directories modified
6. **Breaking change risk:** yes/no based on API surface changes, dependency updates, or config schema changes

For `pr-only` mode, skip items 3-6 and instead show the commit history on the current branch vs. the target branch.

Present this as a quick summary and get user confirmation before proceeding.

---

# Phase 1: Commit + Push (Default and PR modes)

Skip this entire phase for `pr-only` mode — jump directly to Phase 2.

## Step 1: Verify Hooks Are Installed

Check that the enforcement infrastructure is in place:

```bash
# Check lefthook.yml exists
test -f lefthook.yml

# Check lefthook is installed
lefthook version
```

- If `lefthook.yml` does not exist: **STOP**. Inform the user: "lefthook.yml not found. Run `npx ai-engineering init` or `npx ai-engineering update` to generate it."
- If `lefthook` is not installed: **STOP**. Inform the user: "Lefthook not found. Install it: `npm i -D @evilmartians/lefthook && npx lefthook install`"
- If both are present: proceed.

---

## Step 2: Prerequisites

Before starting, verify:

- The current directory is a git repository (`git rev-parse --git-dir`).
- There are staged changes (`git diff --cached --name-only`). If nothing is staged, inform the user and ask what to stage. Do not auto-stage with `git add -A` or `git add .` unless the user explicitly requests it.
- The current branch is not a protected branch (see Protected Branches below). If it is, stop and inform the user.

---

## Step 3: Secrets Scan

Run `gitleaks` on the staged files to detect hardcoded secrets, API keys, tokens, and credentials.

```bash
git diff --cached --name-only -z | xargs -0 gitleaks detect --no-git --verbose -f json --source
```

- If `gitleaks` is not installed, warn the user and recommend installing it. Do not skip this step silently.
- If secrets are detected: **STOP immediately**. Display the findings with file, line number, and rule ID. Do not proceed to commit. Instruct the user to remove the secrets before retrying.
- If no secrets are detected: report "Secrets scan passed" and proceed.

**Hard rule:** Never commit files that contain secrets, API keys, passwords, tokens, or credentials. Never override this check.

---

## Step 4: Lint

Run the stack-appropriate linter on the staged files. Detect the stack from the project context:

| Stack                | Linter Command                           |
| -------------------- | ---------------------------------------- |
| Node.js / TypeScript | `npx eslint --fix <staged-files>`        |
| .NET / C#            | `dotnet format --include <staged-files>` |
| Python               | `ruff check --fix <staged-files>`        |

- Run the linter with auto-fix enabled where supported.
- If the linter produces errors that cannot be auto-fixed: display the errors with file, line, and rule. Ask the user whether to proceed with warnings or stop to fix.
- If the linter auto-fixed files: re-stage the fixed files (`git add <fixed-files>`) and inform the user what was changed.
- If no linter is detected or configured: warn the user that no linter ran. Do not silently skip.

---

## Step 5: Format

Run the stack-appropriate formatter on the staged files:

| Stack                | Formatter Command                                      |
| -------------------- | ------------------------------------------------------ |
| Node.js / TypeScript | `npx prettier --write <staged-files>`                  |
| .NET / C#            | `dotnet format --include <staged-files>`               |
| Python               | `black <staged-files>` or `ruff format <staged-files>` |

- Formatting is always auto-applied. The formatter is authoritative.
- After formatting, re-stage any modified files (`git add <formatted-files>`).
- Report which files were reformatted. If no files changed, report "Formatting check passed — no changes needed."
- If the formatter is not installed or configured: warn the user. Do not silently skip.

---

## Step 6: Conventional Commit Validation

Ensure the commit message will follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Valid Types

| Type       | Usage                                                |
| ---------- | ---------------------------------------------------- |
| `feat`     | A new feature or user-facing capability              |
| `fix`      | A bug fix                                            |
| `docs`     | Documentation-only changes                           |
| `style`    | Formatting, whitespace, semicolons — no logic change |
| `refactor` | Code restructuring with no behavior change           |
| `perf`     | Performance improvement                              |
| `test`     | Adding or updating tests                             |
| `build`    | Build system or dependency changes                   |
| `ci`       | CI/CD configuration changes                          |
| `chore`    | Maintenance tasks that do not modify src or test     |
| `revert`   | Reverts a previous commit                            |

### Rules

- Type is mandatory and must be lowercase.
- Scope is optional but recommended. It should identify the module, component, or area affected.
- Description is mandatory, lowercase (except proper nouns), imperative mood ("add" not "added"), and no trailing period.
- Description must not exceed 72 characters (type + scope + description combined).
- If breaking changes are introduced, the footer must include `BREAKING CHANGE:` or the type must be suffixed with `!`.

---

## Step 7: Generate Commit Message

Analyze the staged diff to generate a commit message:

```bash
git diff --cached --stat
git diff --cached
```

### Analysis Process

1. **Identify the type:** What kind of change is this? New feature, bug fix, refactor, test, docs, etc.
2. **Identify the scope:** Which module, component, or area is primarily affected?
3. **Summarize the change:** What does this change do, in imperative mood, in one line?
4. **Assess body need:** If the change is non-trivial (more than 3 files, complex logic, or behavioral change), draft a body explaining the motivation and approach.
5. **Check for breaking changes:** Does this change break existing APIs, configurations, or contracts?

---

## Step 8: Present for Approval

Present the generated commit message to the user:

```
Proposed commit message:
───────────────────────
feat(auth): add JWT token refresh endpoint

Add automatic token refresh when access tokens expire within 5 minutes
of a request. Refresh tokens are rotated on each use to prevent replay.

Closes #142
───────────────────────

Options:
  1. Commit and push with this message
  2. Edit the message
  3. Abort
```

- If the user chooses to edit: accept their revised message and re-validate it against conventional commit rules (Step 6).
- If the user aborts: stop the workflow cleanly. Do not commit anything.
- Do not commit without explicit user approval.

---

## Step 9: Execute Commit

Run the commit command:

```bash
git commit -m "<approved-message>"
```

**Hard rules:**

- Never use `--no-verify`. The pre-commit hooks exist for a reason.
- Never use `--amend` unless the user explicitly requests it.
- Never use `--allow-empty` unless the user explicitly requests it.
- If the commit fails due to a pre-commit hook: report the failure, display the hook output, and ask the user how to proceed. Do not automatically retry or bypass.

---

## Step 10: Push to Remote

Push the branch to the remote. Use the Git Helpers utility for remote tracking detection:

```bash
# Check if current branch tracks a remote (see Git Helpers — Remote Tracking)
UPSTREAM="$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "")"

if [[ -z "$UPSTREAM" ]]; then
  git push -u origin HEAD
else
  git push
fi
```

This triggers **pre-push hooks automatically** via lefthook:

- Full project lint
- TypeScript type checking
- All tests
- Build verification
- Gitleaks branch-diff scan
- Dependency audit
- Semgrep OWASP SAST scan

**Do NOT duplicate these checks in the skill** — the hooks handle them.

---

## Step 11: Verify Push

After the push completes, verify:

```bash
git log --oneline -1
git status
```

Report the result:

```
Commit + push successful:
  abc1234 feat(auth): add JWT token refresh endpoint
  Branch: feature/token-refresh → origin/feature/token-refresh
  Working tree: clean
```

- **If mode is default:** The workflow is complete. Produce the final report (see Final Report section).
- **If mode is PR:** Proceed to Phase 2.

---

# Phase 2: PR Creation (PR and PR-only modes)

Skip this entire phase for default mode.

## Step 12: Detect Platform

Use the Platform Detection utility (see Shared Utilities — Platform Detection) to determine the git hosting platform and available CLI:

```bash
# Detect platform from remote URL
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo "")"

PLATFORM="unknown"
if echo "$REMOTE_URL" | grep -qE 'github\.com'; then
  PLATFORM="github"
elif echo "$REMOTE_URL" | grep -qE 'dev\.azure\.com|visualstudio\.com'; then
  PLATFORM="azdo"
fi

# Verify CLI availability
if [[ "$PLATFORM" == "github" ]]; then
  if ! command -v gh &>/dev/null || ! gh auth status &>/dev/null 2>&1; then
    echo "GitHub CLI not available or not authenticated. Run: gh auth login"
    exit 1
  fi
elif [[ "$PLATFORM" == "azdo" ]]; then
  if ! command -v az &>/dev/null || ! az account show &>/dev/null 2>&1; then
    echo "Azure CLI not available or not authenticated. Run: az login"
    exit 1
  fi
fi
```

If the platform cannot be detected or the CLI is not available, **STOP** and provide installation instructions.

---

## Step 13: Determine Target Branch

Use the Git Helpers utility (see Shared Utilities — Default Branch Detection) to find the target branch:

```bash
# 3-tier fallback for default branch detection
DEFAULT_BRANCH="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || true)"

if [[ -z "$DEFAULT_BRANCH" ]]; then
  if git show-ref --verify --quiet refs/remotes/origin/main 2>/dev/null; then
    DEFAULT_BRANCH="main"
  elif git show-ref --verify --quiet refs/remotes/origin/master 2>/dev/null; then
    DEFAULT_BRANCH="master"
  fi
fi

if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="main"
fi
```

Override logic:

1. If the branch name starts with `release/` or `hotfix/`, target `main` or `master`.
2. If the project uses a `develop` branch as integration branch, feature branches target `develop`.
3. Otherwise, target the detected default branch.
4. If unsure, ask the user. Do not guess.

---

## Step 14: Analyze the Diff

Gather the full picture of what this PR contains:

```bash
# List all commits in this branch
git log $DEFAULT_BRANCH..HEAD --oneline --no-merges

# Full diff summary
git diff $DEFAULT_BRANCH..HEAD --stat

# Full diff for analysis
git diff $DEFAULT_BRANCH..HEAD
```

### Analysis Checklist

- **Files changed:** Count and categorize (source, tests, config, docs, migrations).
- **Lines added/removed:** Gauge the size of the change.
- **Commit history:** Understand the logical progression of changes.
- **Breaking changes:** Identify API changes, schema migrations, configuration changes that affect consumers.
- **Dependencies:** Note any added, removed, or updated dependencies.
- **Work items:** Extract linked issues from branch name and commit messages (see Git Helpers — Work Item Extraction).

---

## Step 15: Generate PR Title

Create a short, descriptive title:

- Maximum 70 characters.
- Use imperative mood: "Add user authentication" not "Added user authentication."
- If the project uses conventional commit prefixes in PR titles, follow that pattern: `feat: add user authentication`.
- Do not include issue numbers in the title — those go in the body.
- Be specific. Do not use vague titles: "Updates", "Changes", "WIP", "Misc fixes" are not acceptable.

---

## Step 16: Generate PR Body

Produce a structured PR description:

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
- **Related Issues:** Closing keywords (`Closes #142`, `Fixes #87`, or `AB#123` for Azure DevOps).
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

## Step 17: Present PR for Approval

```
Pull Request Preview:
─────────────────────
Title: feat: add JWT token refresh endpoint

Target: main ← feature/token-refresh
Commits: 4
Files changed: 8 (+342, -12)
Auto-merge: enabled (use --no-auto-merge to disable)

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

- If `--no-auto-merge` flag was provided, default to option 2.
- If the user edits: accept changes and re-validate title length and format.
- If the user aborts: stop cleanly.
- Do not create a PR without explicit user approval.

---

## Step 18: Create the PR

### GitHub

```bash
gh pr create \
  --title "<approved-title>" \
  --body "<approved-body>" \
  --base <target-branch> \
  --head <current-branch>
```

### Azure DevOps

```bash
# Extract work item IDs from branch name (see Git Helpers — Work Item Extraction)
WORK_ITEMS="$(echo "$CURRENT_BRANCH" | grep -oE 'AB#[0-9]+' | sed 's/AB#//' | tr '\n' ',' | sed 's/,$//' || true)"

az repos pr create \
  --title "<approved-title>" \
  --description "<approved-body>" \
  --source-branch <current-branch> \
  --target-branch <target-branch> \
  ${WORK_ITEMS:+--work-items "$WORK_ITEMS"}
```

Capture and display the PR URL and number.

---

## Step 19: Add Reviewers

### GitHub

```bash
gh pr edit <pr-number> --add-reviewer <reviewer1>,<reviewer2>
```

### Azure DevOps

```bash
az repos pr update --id <pr-id> --reviewers <reviewer1> <reviewer2>
```

### Reviewer Selection Logic

1. If `CODEOWNERS` file exists, the platform auto-assigns. Report who was auto-assigned.
2. If the project configuration specifies default reviewers, add them.
3. If no reviewers are configured, inform the user.
4. Never add reviewers that are not configured. Do not guess.

---

## Step 20: Enable Auto-merge (default ON)

If the user selected auto-merge (or did not explicitly disable it):

### GitHub

```bash
gh pr merge --auto --squash <pr-number>
```

### Azure DevOps

```bash
az repos pr update --id <pr-id> --auto-complete true --merge-strategy squash
```

- Auto-merge means: the PR will merge automatically once all required checks pass and reviews are approved.
- If `--no-auto-merge` flag was provided or the user selected "without auto-merge", skip this step.
- If auto-merge is not available for the repository, inform the user and continue.

---

# Final Report

Produce the appropriate report based on the mode:

### Default Mode Report

```
Ship complete (commit + push):
  abc1234 feat(auth): add JWT token refresh endpoint
  Branch: feature/token-refresh → origin/feature/token-refresh
  Working tree: clean
```

### PR Mode Report

```
Ship complete (commit + push + PR):
  Commit: abc1234 feat(auth): add JWT token refresh endpoint
  PR #143: feat: add JWT token refresh endpoint
  URL: https://github.com/org/repo/pull/143
  Target: main ← feature/token-refresh
  Reviewers: @alice, @bob (from CODEOWNERS)
  Auto-merge: enabled (squash)
  Status: Open, checks pending
```

### PR-only Mode Report

```
Ship complete (PR created):
  PR #143: feat: add JWT token refresh endpoint
  URL: https://github.com/org/repo/pull/143
  Target: main ← feature/token-refresh
  Commits: 4
  Reviewers: @alice, @bob (from CODEOWNERS)
  Auto-merge: enabled (squash)
  Status: Open, checks pending
```

---

## Protected Branches

The following branches are protected by default. Never commit directly to them:

- `main`
- `master`
- `production`
- `release/*`

If the project defines additional protected branches in its configuration (e.g., `develop`, `staging`), respect those as well.

If the user is on a protected branch:

1. Stop before committing.
2. Inform the user: "You are on a protected branch (`main`). Direct commits are not allowed."
3. Suggest creating a feature branch: `git checkout -b <branch-name>`

---

## Blocklist — Files That Must Never Be Committed

The following file patterns must never be included in a commit, regardless of user intent:

- `.env`, `.env.*` (environment files with secrets)
- `*.pem`, `*.key`, `*.p12`, `*.pfx` (private keys and certificates)
- `credentials.json`, `service-account.json`, `secrets.yaml`, `secrets.json`
- `**/node_modules/**`, `**/.venv/**`, `**/bin/Debug/**`, `**/bin/Release/**` (dependency/build artifacts)
- `*.sqlite`, `*.db` (local databases with potential PII)

If any staged file matches these patterns:

1. Warn the user with the specific file names.
2. Recommend unstaging them: `git reset HEAD <file>`.
3. Do not proceed until the user resolves the issue.

---

## Error Recovery

| Failure                    | What to report                      | How to report                                       |
| -------------------------- | ----------------------------------- | --------------------------------------------------- |
| Hooks not installed        | "lefthook not detected"             | Exact installation instructions                     |
| Pre-commit hook fails      | Which hook failed + full output     | File, line, rule violated                           |
| Push blocked by lint hook  | "Full project lint failed" + errors | List each error with file:line:rule                 |
| Push blocked by typecheck  | "TypeScript compilation failed"     | Show type errors with location                      |
| Push blocked by test hook  | "Tests failed" + test names         | Show failing tests and assertions                   |
| Push blocked by build hook | "Build failed"                      | Show compilation error                              |
| Push blocked by gitleaks   | "Secrets detected in branch"        | Show file, line, type of secret                     |
| Push blocked by audit      | "Vulnerable dependencies"           | List package, CVE, severity, fix available          |
| Push blocked by semgrep    | "OWASP security issue detected"     | Show OWASP rule, file, line, explanation            |
| Push auth failure          | "Authentication failed"             | Instructions: `gh auth login` / `az login`          |
| Push branch protection     | "Direct push to X blocked"          | Suggest creating feature branch                     |
| On protected branch        | "Direct commits not allowed"        | Suggest: `git checkout -b <branch-name>`            |
| Blocked file staged        | "Prohibited file in staging"        | List files, recommend unstaging                     |
| No staged changes          | "Nothing to commit"                 | Ask what to stage                                   |
| CLI not installed          | "gh/az not found"                   | Installation instructions                           |
| Not authenticated          | "Authentication required"           | `gh auth login` / `az login` instructions           |
| PR creation fails          | "PR creation failed"                | Common causes: PR already exists, permission denied |
| Auto-merge not available   | "Auto-merge not enabled for repo"   | Instruct user to enable in repo settings            |
| Reviewer not found         | "Reviewer X not found"              | Suggest checking CODEOWNERS or team config          |

---

## Learning Capture (on completion)

If during execution you discovered something useful for the project:

1. **New pattern** (e.g., recurring commit scope, PR template preference, reviewer convention) → Propose adding to `knowledge/patterns.md`
2. **Recurring error** (e.g., hook always fails on a specific check, CI issue) → Propose adding to `knowledge/anti-patterns.md`
3. **Lesson learned** (e.g., dependency that breaks lint, auto-merge not enabled) → Propose adding to `knowledge/learnings.md`

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not create branches. The user must be on the correct branch before invoking.
- It does not squash or rebase. Those are separate operations.
- It does not modify unstaged files. Only staged changes are processed (in default and PR modes).
- It does not merge the PR immediately. Auto-merge waits for checks and reviews.
- It does not resolve review comments.
- It does not rebase or squash commits before creating the PR.
