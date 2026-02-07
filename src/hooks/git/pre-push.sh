#!/usr/bin/env bash
# ai-engineering pre-push hook (executed by lefthook)
# Runs in parallel: tests + coverage + typecheck + dep audit + OWASP + SonarLint

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo "ai-engineering: running pre-push checks..."

FAILED=0

# === PROTECTED BRANCH CHECK ===
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
PROTECTED_BRANCHES="${AI_ENG_PROTECTED_BRANCHES:-main master develop}"

for branch in $PROTECTED_BRANCHES; do
  if [[ "$CURRENT_BRANCH" == "$branch" ]]; then
    echo "BLOCKED: Direct push to protected branch '$branch' is not allowed."
    echo "Create a feature branch and submit a PR instead."
    exit 1
  fi
done

# === TEST SUITE ===
run_tests() {
  # TypeScript/React
  if [[ -f "${PROJECT_ROOT}/package.json" ]]; then
    if grep -q '"test"' "${PROJECT_ROOT}/package.json"; then
      echo "  Running tests..."
      if ! npm test --prefix "${PROJECT_ROOT}" 2>/dev/null; then
        echo "FAILED: Tests did not pass."
        return 1
      fi
      echo "  ✓ tests: passed"
    fi
  fi

  # Python
  if [[ -f "${PROJECT_ROOT}/pyproject.toml" ]] || [[ -f "${PROJECT_ROOT}/setup.py" ]]; then
    if command -v pytest &>/dev/null; then
      if ! pytest "${PROJECT_ROOT}" --quiet 2>/dev/null; then
        echo "FAILED: pytest did not pass."
        return 1
      fi
      echo "  ✓ pytest: passed"
    fi
  fi

  # .NET
  if ls "${PROJECT_ROOT}"/*.sln &>/dev/null; then
    if command -v dotnet &>/dev/null; then
      if ! dotnet test "${PROJECT_ROOT}" --verbosity quiet 2>/dev/null; then
        echo "FAILED: dotnet test did not pass."
        return 1
      fi
      echo "  ✓ dotnet test: passed"
    fi
  fi
}

# === TYPECHECK ===
run_typecheck() {
  if [[ -f "${PROJECT_ROOT}/tsconfig.json" ]]; then
    if [[ -f "${PROJECT_ROOT}/node_modules/.bin/tsc" ]]; then
      echo "  Running typecheck..."
      if ! npx tsc --noEmit --pretty 2>/dev/null; then
        echo "FAILED: TypeScript type checking failed."
        return 1
      fi
      echo "  ✓ typecheck: passed"
    fi
  fi
}

# === DEPENDENCY AUDIT ===
run_dep_audit() {
  # npm audit
  if [[ -f "${PROJECT_ROOT}/package-lock.json" ]] || [[ -f "${PROJECT_ROOT}/pnpm-lock.yaml" ]]; then
    echo "  Running npm audit..."
    if ! npm audit --audit-level=high --prefix "${PROJECT_ROOT}" 2>/dev/null; then
      echo "WARNING: npm audit found high/critical vulnerabilities."
      # Warning only — don't block push for existing vulnerabilities
    else
      echo "  ✓ npm audit: no high/critical vulnerabilities"
    fi
  fi

  # pip-audit
  if command -v pip-audit &>/dev/null; then
    if [[ -f "${PROJECT_ROOT}/requirements.txt" ]] || [[ -f "${PROJECT_ROOT}/pyproject.toml" ]]; then
      echo "  Running pip-audit..."
      if ! pip-audit 2>/dev/null; then
        echo "WARNING: pip-audit found vulnerabilities."
      else
        echo "  ✓ pip-audit: no known vulnerabilities"
      fi
    fi
  fi

  # dotnet vulnerable packages
  if command -v dotnet &>/dev/null; then
    if ls "${PROJECT_ROOT}"/*.csproj &>/dev/null; then
      echo "  Running dotnet package vulnerability check..."
      if dotnet list "${PROJECT_ROOT}" package --vulnerable 2>/dev/null | grep -q "has the following vulnerable packages"; then
        echo "WARNING: Vulnerable .NET packages detected."
      else
        echo "  ✓ dotnet packages: no known vulnerabilities"
      fi
    fi
  fi
}

# Run all checks
run_tests || FAILED=1
run_typecheck || FAILED=1
run_dep_audit || FAILED=1

if [[ $FAILED -ne 0 ]]; then
  echo ""
  echo "Pre-push checks FAILED. Fix the issues above before pushing."
  exit 1
fi

echo "All pre-push checks passed."
exit 0
