---
description: Stage changes and create a conventional commit with secret scanning
---

## Context

Smart commit workflow that scans for secrets before staging, generates a conventional commit message based on the changes, and commits.

## Inputs

$ARGUMENTS - Optional: specific files to commit, or commit message hint

## Steps

### 1. Scan for Secrets

Before anything else, check staged and unstaged changes for leaked secrets:

- Look for patterns: API keys (`AKIA`, `sk-`, `ghp_`, `xox`), connection strings, private keys, `.env` files
- If `gitleaks` is available, run: `gitleaks detect --source . --no-git --verbose`
- If secrets are found, STOP and report them. Do NOT proceed with the commit.

### 2. Analyze Changes

- Run `git status` to see modified/untracked files
- Run `git diff` for unstaged changes and `git diff --cached` for staged changes
- Run `git log --oneline -5` to see recent commit message style

### 3. Determine What to Stage

- If $ARGUMENTS specifies files, stage those files
- Otherwise, identify logically related changes that form one atomic commit
- NEVER stage: `.env`, `*.key`, `*.pem`, `credentials.*`, `*secret*` files
- Prefer specific `git add <file>` over `git add -A`

### 4. Generate Commit Message

Follow Conventional Commits format:

```
<type>[optional scope]: <description>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

Keep the description under 72 characters. Use imperative mood ("add" not "added").

### 5. Create Commit

- Stage the identified files
- Create the commit with the generated message

### 6. Verify

- Run `git status` to confirm state
- Run `git log --oneline -1` to confirm the commit message

## Verification

- No secrets in the committed files
- Commit message follows conventional format
- Only related changes are in the commit (atomic)
