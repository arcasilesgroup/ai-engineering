---
name: commit-push
description: Stage changes, create a conventional commit with secret scanning, and push to remote
disable-model-invocation: true
---

## Context

Smart commit workflow that scans for secrets before staging, generates a conventional commit message based on the changes, commits, and pushes to the remote branch.

## Inputs

$ARGUMENTS - Optional: specific files to commit, or commit message hint

## Steps

### 1. Analyze Changes

- Run `git status` to see modified/untracked files
- Run `git diff` for unstaged changes and `git diff --cached` for staged changes
- Run `git log --oneline -5` to see recent commit message style

### 2. Determine What to Stage

- If $ARGUMENTS specifies files, stage those files
- Otherwise, identify logically related changes that form one atomic commit
- NEVER stage: `.env`, `*.key`, `*.pem`, `credentials.*`, `*secret*` files
- Prefer specific `git add <file>` over `git add -A`

### 3. Stage Files

- Stage the identified files with `git add <file>`

### 4. Scan Staged Changes for Secrets

After staging, scan **only the staged changes** (not the whole repo):

- If `gitleaks` is available, run: `gitleaks protect --staged --verbose`
- This scans only the content being committed, not the entire repository
- If secrets are found, unstage the files (`git restore --staged <files>`) and STOP. Do NOT proceed with the commit.
- If `gitleaks` is not available, manually review staged diffs for patterns: API keys (`AKIA`, `sk-`, `ghp_`, `xox`), connection strings, private keys

### 5. Generate Commit Message

Follow Conventional Commits format:

```
<type>[optional scope]: <description>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

Keep the description under 72 characters. Use imperative mood ("add" not "added").

### 6. Create Commit

- Create the commit with the generated message

### 7. Push to Remote

- Determine current branch: `git branch --show-current`
- Push with tracking: `git push -u origin <branch>`
- If push fails due to upstream changes, inform the user and suggest `git pull --rebase`

### 8. Verify

- Run `git status` to confirm state
- Run `git log --oneline -1` to confirm the commit message
- Confirm push succeeded

## Verification

- No secrets in the committed changes
- Commit message follows conventional format
- Only related changes are in the commit (atomic)
- Changes are pushed to remote
