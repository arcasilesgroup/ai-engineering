#!/usr/bin/env bash
# Smoke-test the `ai-eng install` flow on clean Linux distributions using Docker.
#
# Validates spec-101 goals (G-2, G-3, G-11) on distributions beyond `ubuntu-latest`:
# does the installer succeed user-scope, are required tools provisioned, and does
# `git commit` work right after install on a minimal base image?
#
# Usage:
#   scripts/clean-install-test.sh                 # all default distros
#   scripts/clean-install-test.sh debian:12-slim  # subset (positional args)
#   KEEP_LOGS=1 scripts/clean-install-test.sh     # keep per-distro logs
#
# Requires: Docker Desktop running, repo checkout (this script reads its own repo).

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
LOG_DIR="${TMPDIR:-/tmp}/ai-eng-smoke-$$"
PER_DISTRO_TIMEOUT="${PER_DISTRO_TIMEOUT:-900}"
DEFAULT_DISTROS=(
  "debian:12-slim"
  "ubuntu:22.04"
  "redhat/ubi9-minimal"
  "alpine:3.19"
)

if [ "$#" -gt 0 ]; then
  DISTROS=("$@")
else
  DISTROS=("${DEFAULT_DISTROS[@]}")
fi

mkdir -p "$LOG_DIR"
echo "Logs: $LOG_DIR"
echo "Repo: $REPO_ROOT"
echo "Distros: ${DISTROS[*]}"

# Pick a timeout helper if available. macOS ships without GNU coreutils, so
# `timeout` is missing unless `brew install coreutils` was run (giving `gtimeout`).
# Falling back to no timeout is fine; the user can Ctrl+C if needed.
TIMEOUT_CMD=()
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD=(timeout "$PER_DISTRO_TIMEOUT")
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD=(gtimeout "$PER_DISTRO_TIMEOUT")
else
  echo "(timeout command not found; running without per-distro time limit)"
fi
echo

# Script that runs INSIDE each container. Heredoc kept literal (no expansion here).
INNER_SCRIPT=$(cat <<'INNER'
set -e
export DEBIAN_FRONTEND=noninteractive
export PIP_BREAK_SYSTEM_PACKAGES=1

# 1. Install minimal prereqs (python3, pip, git) per package manager.
if [ -f /etc/debian_version ]; then
  apt-get update -qq
  apt-get install -qq -y --no-install-recommends \
    git ca-certificates python3 python3-pip python3-venv
elif command -v microdnf >/dev/null 2>&1; then
  microdnf install -y --nodocs git ca-certificates python3 python3-pip >/dev/null
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y --setopt=install_weak_deps=False git ca-certificates python3 python3-pip >/dev/null
elif [ -f /etc/alpine-release ]; then
  apk add --no-cache git ca-certificates python3 py3-pip bash >/dev/null
else
  echo "ERROR: unsupported distro (no apt/dnf/apk found)" >&2
  exit 2
fi

# 2. Install uv from PyPI (pre-built wheels for manylinux + musllinux).
#    Avoids the curl|sh idiom that the project sentinel blocks.
python3 -m pip install --quiet --user uv
export PATH="$HOME/.local/bin:$PATH"
uv --version

# 3. Stage a writable copy of the repo (bind mount is read-only) and install ai-engineering.
cp -r /src /tmp/ai-engineering
cd /tmp/ai-engineering
uv tool install --quiet . 2>&1 | tail -3
hash -r
command -v ai-eng >/dev/null || { echo "ai-eng not on PATH after uv tool install"; exit 3; }
ai-eng --help >/dev/null || { echo "ai-eng --help failed"; exit 3; }

# 4. Apply ai-eng install to a fresh empty project; this is the real test.
mkdir -p /tmp/demo
cd /tmp/demo
git init -q
git config user.email "smoke@test.local"
git config user.name "Smoke Test"
git config commit.gpgsign false
ai-eng install . 2>&1 | tail -25

# 5. Validate hooks accept a trivial commit (proves required tools are runnable).
git commit --allow-empty -m "smoke-test commit" 2>&1 | tail -10

echo "---SMOKE-PASS---"
INNER
)

declare -A RESULTS
declare -A DURATIONS
OVERALL_RC=0

for IMG in "${DISTROS[@]}"; do
  SAFE_NAME="${IMG//[:\/]/-}"
  LOG_FILE="$LOG_DIR/${SAFE_NAME}.log"
  printf "── %-28s " "$IMG"

  START_TS=$SECONDS
  if "${TIMEOUT_CMD[@]}" docker run --rm \
      -v "$REPO_ROOT:/src:ro" \
      -e HOME=/root \
      "$IMG" \
      sh -c "$INNER_SCRIPT" >"$LOG_FILE" 2>&1; then
    if grep -q '^---SMOKE-PASS---$' "$LOG_FILE"; then
      RESULTS[$IMG]="PASS"
    else
      RESULTS[$IMG]="UNKNOWN (no PASS marker)"
      OVERALL_RC=1
    fi
  else
    RC=$?
    if [ "$RC" -eq 124 ]; then
      RESULTS[$IMG]="TIMEOUT (>${PER_DISTRO_TIMEOUT}s)"
    else
      RESULTS[$IMG]="FAIL (exit $RC)"
    fi
    OVERALL_RC=1
  fi
  DURATIONS[$IMG]=$((SECONDS - START_TS))
  printf "%-25s  %4ds  %s\n" "${RESULTS[$IMG]}" "${DURATIONS[$IMG]}" "$LOG_FILE"
done

echo
echo "════════════════════════ Resumen ════════════════════════"
printf "%-28s %-25s %s\n" "Imagen" "Resultado" "Tiempo"
for IMG in "${DISTROS[@]}"; do
  printf "%-28s %-25s %ds\n" "$IMG" "${RESULTS[$IMG]}" "${DURATIONS[$IMG]}"
done
echo
if [ "$OVERALL_RC" -eq 0 ]; then
  echo "✓ Todas las distros pasaron."
else
  echo "✗ Hubo fallos. Revisa los logs en $LOG_DIR/"
fi

if [ -z "${KEEP_LOGS:-}" ] && [ "$OVERALL_RC" -eq 0 ]; then
  rm -rf "$LOG_DIR"
  echo "(logs limpiados; usa KEEP_LOGS=1 para mantenerlos)"
fi

exit "$OVERALL_RC"
