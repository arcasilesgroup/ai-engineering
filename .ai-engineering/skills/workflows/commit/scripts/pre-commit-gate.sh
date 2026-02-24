#!/usr/bin/env bash
# pre-commit-gate.sh — deterministic pre-commit gate helper
# Usage: ./pre-commit-gate.sh [--staged-only]
# Runs format, lint, and secret detection on staged files.
# Exit 0 = all checks pass, Exit 1 = at least one check failed.
set -euo pipefail

STAGED_ONLY="${1:-}"
EXIT_CODE=0

echo "=== Pre-Commit Gate ==="

# Step 1: Format
echo "[1/3] Running ruff format..."
if command -v ruff >/dev/null 2>&1; then
  ruff format . 2>&1 || true
  echo "  -> format applied"
else
  echo "  -> SKIP: ruff not found (install: uv tool install ruff)"
  EXIT_CODE=1
fi

# Step 2: Lint
echo "[2/3] Running ruff check..."
if command -v ruff >/dev/null 2>&1; then
  if ! ruff check . --fix 2>&1; then
    echo "  -> FAIL: unfixable lint issues found"
    EXIT_CODE=1
  else
    echo "  -> PASS"
  fi
else
  echo "  -> SKIP: ruff not found"
  EXIT_CODE=1
fi

# Step 3: Secret detection
echo "[3/3] Running gitleaks..."
if command -v gitleaks >/dev/null 2>&1; then
  if [ "$STAGED_ONLY" = "--staged-only" ]; then
    if ! gitleaks detect --staged --no-banner 2>&1; then
      echo "  -> FAIL: secrets detected in staged files"
      EXIT_CODE=1
    else
      echo "  -> PASS"
    fi
  else
    if ! gitleaks detect --no-banner 2>&1; then
      echo "  -> FAIL: secrets detected"
      EXIT_CODE=1
    else
      echo "  -> PASS"
    fi
  fi
else
  echo "  -> SKIP: gitleaks not found (install: brew install gitleaks)"
  EXIT_CODE=1
fi

echo "=== Gate Result: $([ $EXIT_CODE -eq 0 ] && echo 'PASS' || echo 'FAIL') ==="
exit $EXIT_CODE
