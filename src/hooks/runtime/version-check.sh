#!/usr/bin/env bash
# ai-engineering version check hook
# Runs at session start to check for framework updates.
# Uses 24h cache to avoid hammering npm registry.

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
AI_ENG_DIR="${PROJECT_ROOT}/.ai-engineering"
CACHE_FILE="${AI_ENG_DIR}/.update-cache"
VERSION_FILE="${AI_ENG_DIR}/.version"
CACHE_TTL=86400  # 24 hours in seconds

# Read current version
if [[ ! -f "$VERSION_FILE" ]]; then
  exit 0
fi
CURRENT_VERSION=$(head -1 "$VERSION_FILE" | tr -d '[:space:]')

# Check cache
if [[ -f "$CACHE_FILE" ]]; then
  CACHE_TIME=$(stat -f '%m' "$CACHE_FILE" 2>/dev/null || stat -c '%Y' "$CACHE_FILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  ELAPSED=$(( NOW - CACHE_TIME ))

  if [[ $ELAPSED -lt $CACHE_TTL ]]; then
    # Cache is fresh, read cached result
    CACHED_VERSION=$(cat "$CACHE_FILE")
    if [[ "$CACHED_VERSION" != "$CURRENT_VERSION" && -n "$CACHED_VERSION" ]]; then
      echo "ai-engineering update available: ${CURRENT_VERSION} → ${CACHED_VERSION}"
      echo "Run: npx ai-engineering update"
    fi
    exit 0
  fi
fi

# Cache expired or missing — check npm registry
LATEST_VERSION=$(npm view ai-engineering version 2>/dev/null || echo "")

if [[ -z "$LATEST_VERSION" ]]; then
  # Can't reach registry, skip silently
  exit 0
fi

# Update cache
echo "$LATEST_VERSION" > "$CACHE_FILE"

# Notify if update available
if [[ "$LATEST_VERSION" != "$CURRENT_VERSION" ]]; then
  echo "ai-engineering update available: ${CURRENT_VERSION} → ${LATEST_VERSION}"
  echo "Run: npx ai-engineering update"
fi

exit 0
