#!/usr/bin/env bash
# ai-engineering commit-msg hook (executed by lefthook)
# Enforces conventional commit format.

set -euo pipefail

COMMIT_MSG_FILE="$1"
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Allow merge commits
if echo "$COMMIT_MSG" | grep -qE '^Merge '; then
  exit 0
fi

# Allow revert commits
if echo "$COMMIT_MSG" | grep -qE '^Revert '; then
  exit 0
fi

# Conventional commit pattern: type(scope): description
# type is required, scope is optional
PATTERN='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-zA-Z0-9_-]+\))?: .{1,}'

if ! echo "$COMMIT_MSG" | head -1 | grep -qE "$PATTERN"; then
  echo "FAILED: Commit message does not follow Conventional Commits format."
  echo ""
  echo "Expected format: <type>(<scope>): <description>"
  echo ""
  echo "Types:"
  echo "  feat     — A new feature"
  echo "  fix      — A bug fix"
  echo "  docs     — Documentation changes"
  echo "  style    — Formatting, semicolons, etc. (no code change)"
  echo "  refactor — Code restructuring (no feature/fix)"
  echo "  perf     — Performance improvement"
  echo "  test     — Adding or fixing tests"
  echo "  build    — Build system or dependencies"
  echo "  ci       — CI/CD configuration"
  echo "  chore    — Maintenance tasks"
  echo "  revert   — Reverting a previous commit"
  echo ""
  echo "Examples:"
  echo '  feat(auth): add JWT token refresh'
  echo '  fix: resolve null pointer in user service'
  echo '  docs(api): update endpoint documentation'
  echo ""
  echo "Your message: ${COMMIT_MSG}"
  exit 1
fi

# Check description length (first line should be <= 72 chars)
FIRST_LINE=$(echo "$COMMIT_MSG" | head -1)
if [[ ${#FIRST_LINE} -gt 72 ]]; then
  echo "WARNING: First line of commit message is ${#FIRST_LINE} chars (recommended: ≤72)."
fi

exit 0
