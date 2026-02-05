# Git Hooks

> Git hooks that run during git operations.

## pre-push Hook

**Trigger:** Before `git push`
**Purpose:** Block pushes with critical dependency vulnerabilities.

### How It Works

1. Runs before `git push`
2. Checks npm dependencies (if `package.json` exists)
3. Checks pip dependencies (if `requirements.txt` exists)
4. **CRITICAL vulnerabilities** → Blocks push
5. **HIGH vulnerabilities** → Warns but allows

### Installation

#### Via Install Script

```bash
scripts/install.sh --name "MyProject" --stacks dotnet --install-tools
```

#### Manual Installation

```bash
cp scripts/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### Script Source

```bash
#!/usr/bin/env bash
# .git/hooks/pre-push

set -euo pipefail

echo "Running pre-push vulnerability check..."

CRITICAL=0
HIGH=0

# Check npm if package.json exists
if [[ -f "package.json" ]] && command -v npm >/dev/null; then
  echo "Checking npm dependencies..."

  # Run audit and capture output
  AUDIT_OUTPUT=$(npm audit --json 2>/dev/null || true)

  if [[ -n "$AUDIT_OUTPUT" ]]; then
    CRITICAL=$(echo "$AUDIT_OUTPUT" | jq -r '.metadata.vulnerabilities.critical // 0')
    HIGH=$(echo "$AUDIT_OUTPUT" | jq -r '.metadata.vulnerabilities.high // 0')
  fi
fi

# Check pip if requirements.txt exists
if [[ -f "requirements.txt" ]] && command -v pip-audit >/dev/null; then
  echo "Checking pip dependencies..."

  PIP_OUTPUT=$(pip-audit --format=json 2>/dev/null || true)

  if [[ -n "$PIP_OUTPUT" ]]; then
    PIP_CRITICAL=$(echo "$PIP_OUTPUT" | jq '[.[] | select(.severity == "CRITICAL")] | length')
    PIP_HIGH=$(echo "$PIP_OUTPUT" | jq '[.[] | select(.severity == "HIGH")] | length')
    CRITICAL=$((CRITICAL + PIP_CRITICAL))
    HIGH=$((HIGH + PIP_HIGH))
  fi
fi

# Report findings
if [[ $CRITICAL -gt 0 ]]; then
  echo ""
  echo "=========================================="
  echo "BLOCKED: $CRITICAL critical vulnerabilities found"
  echo "=========================================="
  echo ""
  echo "Run 'npm audit' or 'pip-audit' for details."
  echo "Fix critical vulnerabilities before pushing."
  echo ""
  echo "To bypass (not recommended): git push --no-verify"
  exit 1
fi

if [[ $HIGH -gt 0 ]]; then
  echo ""
  echo "WARNING: $HIGH high severity vulnerabilities found"
  echo "Consider fixing before merging."
  echo ""
fi

echo "Pre-push check passed."
exit 0
```

### Vulnerability Levels

| Level | Action | Rationale |
|-------|--------|-----------|
| CRITICAL | Block push | Active exploits, immediate risk |
| HIGH | Warn | Serious risk, fix soon |
| MEDIUM | Ignore | Plan to fix |
| LOW | Ignore | Low priority |

### Bypassing

If you must push with vulnerabilities (emergency only):

```bash
git push --no-verify
```

**Warning:** This skips ALL pre-push hooks. Document why you bypassed.

### Example Output

```
$ git push origin feature/new-login

Running pre-push vulnerability check...
Checking npm dependencies...

==========================================
BLOCKED: 2 critical vulnerabilities found
==========================================

Run 'npm audit' for details.
Fix critical vulnerabilities before pushing.

To bypass (not recommended): git push --no-verify
```

---

## Other Git Hooks (Not Included)

The framework focuses on pre-push, but you can add others:

### pre-commit

Run before each commit:

```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit

# Run gitleaks on staged files
gitleaks detect --source . --no-git --staged-only

# Run linter
npm run lint --quiet
```

### commit-msg

Validate commit messages:

```bash
#!/usr/bin/env bash
# .git/hooks/commit-msg

COMMIT_MSG_FILE=$1
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Require conventional commit format
if ! echo "$COMMIT_MSG" | grep -qE "^(feat|fix|docs|refactor|test|chore|ci)(\(.+\))?!?: .+"; then
  echo "ERROR: Commit message must follow Conventional Commits format"
  echo "Example: feat(auth): add login endpoint"
  exit 1
fi
```

### pre-rebase

Prevent rebasing shared branches:

```bash
#!/usr/bin/env bash
# .git/hooks/pre-rebase

BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)

if [[ "$BRANCH" == "main" || "$BRANCH" == "master" || "$BRANCH" == "develop" ]]; then
  echo "ERROR: Cannot rebase protected branch: $BRANCH"
  exit 1
fi
```

---

## Managing Git Hooks

### Location

Git hooks live in `.git/hooks/` (not committed) or use a tool to manage them:

### Using husky (npm projects)

```bash
npm install --save-dev husky
npx husky install
npx husky add .husky/pre-push "scripts/hooks/pre-push"
```

### Using pre-commit (Python projects)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: vulnerability-check
        name: Vulnerability Check
        entry: scripts/hooks/pre-push
        language: script
        stages: [push]
```

---
**See also:** [Hooks Overview](Hooks-Overview) | [Tool Installation](Installation-Tool-Installation)
