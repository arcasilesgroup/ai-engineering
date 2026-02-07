#!/usr/bin/env bash
# ai-engineering pre-commit hook (executed by lefthook)
# Runs in parallel: gitleaks + lint + format check

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
CONFIG_FILE="${PROJECT_ROOT}/.ai-engineering/config.yml"

echo "ai-engineering: running pre-commit checks..."

# === GITLEAKS — Secret Scanning ===
gitleaks_check() {
  if command -v gitleaks &>/dev/null; then
    if ! gitleaks protect --staged --no-banner 2>/dev/null; then
      echo "FAILED: gitleaks detected potential secrets in staged files."
      echo "Review staged changes and remove any secrets before committing."
      return 1
    fi
    echo "  ✓ gitleaks: no secrets detected"
  else
    echo "  ⚠ gitleaks not installed, skipping secret scan"
  fi
}

# === LINT CHECK ===
lint_check() {
  # TypeScript/React
  if [[ -f "${PROJECT_ROOT}/package.json" ]]; then
    if [[ -f "${PROJECT_ROOT}/node_modules/.bin/eslint" ]]; then
      STAGED_TS=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx|js|jsx)$' || true)
      if [[ -n "$STAGED_TS" ]]; then
        if ! echo "$STAGED_TS" | xargs npx eslint --quiet 2>/dev/null; then
          echo "FAILED: ESLint found errors in staged files."
          return 1
        fi
        echo "  ✓ eslint: passed"
      fi
    fi
  fi

  # Python
  if [[ -f "${PROJECT_ROOT}/pyproject.toml" ]] || [[ -f "${PROJECT_ROOT}/setup.py" ]]; then
    if command -v ruff &>/dev/null; then
      STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' || true)
      if [[ -n "$STAGED_PY" ]]; then
        if ! echo "$STAGED_PY" | xargs ruff check 2>/dev/null; then
          echo "FAILED: Ruff found errors in staged files."
          return 1
        fi
        echo "  ✓ ruff: passed"
      fi
    fi
  fi

  # .NET
  if ls "${PROJECT_ROOT}"/*.csproj &>/dev/null || ls "${PROJECT_ROOT}"/*.sln &>/dev/null; then
    if command -v dotnet &>/dev/null; then
      if ! dotnet format --verify-no-changes --verbosity quiet 2>/dev/null; then
        echo "FAILED: dotnet format found formatting issues."
        return 1
      fi
      echo "  ✓ dotnet format: passed"
    fi
  fi
}

# === FORMAT CHECK ===
format_check() {
  if [[ -f "${PROJECT_ROOT}/node_modules/.bin/prettier" ]]; then
    STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx|js|jsx|json|md|yml|yaml|css|scss)$' || true)
    if [[ -n "$STAGED_FILES" ]]; then
      if ! echo "$STAGED_FILES" | xargs npx prettier --check 2>/dev/null; then
        echo "FAILED: Prettier found formatting issues. Run: npx prettier --write <files>"
        return 1
      fi
      echo "  ✓ prettier: formatted correctly"
    fi
  fi

  if command -v black &>/dev/null; then
    STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' || true)
    if [[ -n "$STAGED_PY" ]]; then
      if ! echo "$STAGED_PY" | xargs black --check --quiet 2>/dev/null; then
        echo "FAILED: Black found formatting issues. Run: black <files>"
        return 1
      fi
      echo "  ✓ black: formatted correctly"
    fi
  fi
}

# Run all checks
FAILED=0
gitleaks_check || FAILED=1
lint_check || FAILED=1
format_check || FAILED=1

if [[ $FAILED -ne 0 ]]; then
  echo ""
  echo "Pre-commit checks FAILED. Fix the issues above before committing."
  exit 1
fi

echo "All pre-commit checks passed."
exit 0
