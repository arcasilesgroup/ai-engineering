#!/usr/bin/env bash
# sonar-pre-gate.sh — Run SonarQube/SonarCloud analysis with quality gate wait.
#
# Usage:
#   ./sonar-pre-gate.sh [--skip-if-unconfigured]
#
# Prerequisites:
#   - sonar-scanner on PATH
#   - SONAR_TOKEN environment variable or keyring entry
#   - sonar-project.properties in project root
#
# Exit codes:
#   0 — quality gate passed (or skipped when unconfigured)
#   1 — quality gate failed
#   2 — configuration error (missing scanner, missing properties)

set -euo pipefail

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------

SKIP_IF_UNCONFIGURED="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-.}"
PROPS_FILE="${PROJECT_ROOT}/sonar-project.properties"

# ---------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------

# Check sonar-scanner is available.
if ! command -v sonar-scanner &>/dev/null; then
    echo "SKIP: sonar-scanner not found on PATH" >&2
    if [[ "$SKIP_IF_UNCONFIGURED" == "--skip-if-unconfigured" ]]; then
        exit 0
    fi
    exit 2
fi

# Check sonar-project.properties exists.
if [[ ! -f "$PROPS_FILE" ]]; then
    echo "SKIP: sonar-project.properties not found" >&2
    if [[ "$SKIP_IF_UNCONFIGURED" == "--skip-if-unconfigured" ]]; then
        exit 0
    fi
    exit 2
fi

# Check SONAR_TOKEN is set.
if [[ -z "${SONAR_TOKEN:-}" ]]; then
    echo "SKIP: SONAR_TOKEN not set" >&2
    if [[ "$SKIP_IF_UNCONFIGURED" == "--skip-if-unconfigured" ]]; then
        exit 0
    fi
    exit 2
fi

# ---------------------------------------------------------------
# Execute Sonar analysis
# ---------------------------------------------------------------

echo "Running Sonar analysis..."
sonar-scanner \
    -Dsonar.qualitygate.wait=true \
    -Dsonar.token="${SONAR_TOKEN}" \
    -Dproject.settings="${PROPS_FILE}"

EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "PASS: Sonar quality gate passed"
else
    echo "FAIL: Sonar quality gate failed (exit code: $EXIT_CODE)" >&2
fi

exit $EXIT_CODE
