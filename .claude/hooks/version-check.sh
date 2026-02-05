#!/usr/bin/env bash
# =============================================================================
# Version Check Hook
# =============================================================================
# Checks for AI Engineering Framework updates on session start.
# Uses a 24-hour cache to avoid repeated network calls.
#
# Fallback chain: gh api → git ls-remote → curl VERSION
#
# Exit: Always 0 (informational only, never blocks)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CACHE_FILE="${HOME}/.ai-engineering-version-cache"
CACHE_TTL=86400  # 24 hours in seconds
# Detect repo owner/name from git remote, with fallback
_remote_url="$(cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" && git config --get remote.origin.url 2>/dev/null || echo "")"
if [[ "$_remote_url" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
    REPO_OWNER="${BASH_REMATCH[1]}"
    REPO_NAME="${BASH_REMATCH[2]}"
else
    REPO_OWNER="arcasilesgroup"
    REPO_NAME="ai-engineering"
fi
DEPRECATIONS_FILE="${CLAUDE_PROJECT_DIR:-$(pwd)}/DEPRECATIONS.json"
LOCAL_VERSION_FILE="${CLAUDE_PROJECT_DIR:-$(pwd)}/.ai-version"

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
log_info() {
    echo "[AI Framework] $1" >&2
}

log_warn() {
    echo "[AI Framework] ⚠️  $1" >&2
}

get_local_version() {
    if [[ -f "$LOCAL_VERSION_FILE" ]]; then
        cat "$LOCAL_VERSION_FILE" | tr -d '[:space:]'
    else
        echo ""
    fi
}

# Compare semver: returns 0 if $1 < $2, 1 if $1 >= $2
version_lt() {
    local v1="$1" v2="$2"
    # Strip 'v' prefix if present
    v1="${v1#v}"
    v2="${v2#v}"

    # Use sort -V for version comparison
    if [[ "$(printf '%s\n%s' "$v1" "$v2" | sort -V | head -n1)" == "$v1" && "$v1" != "$v2" ]]; then
        return 0  # v1 < v2
    else
        return 1  # v1 >= v2
    fi
}

is_cache_valid() {
    if [[ ! -f "$CACHE_FILE" ]]; then
        return 1
    fi

    local cache_time
    cache_time=$(head -1 "$CACHE_FILE" 2>/dev/null || echo "0")
    local current_time
    current_time=$(date +%s)
    local age=$((current_time - cache_time))

    if [[ $age -lt $CACHE_TTL ]]; then
        return 0
    fi
    return 1
}

read_cache() {
    if [[ -f "$CACHE_FILE" ]]; then
        tail -n +2 "$CACHE_FILE" | head -1
    fi
}

write_cache() {
    local version="$1"
    local timestamp
    timestamp=$(date +%s)
    echo "$timestamp" > "$CACHE_FILE"
    echo "$version" >> "$CACHE_FILE"
}

# ---------------------------------------------------------------------------
# Version Fetching (fallback chain)
# ---------------------------------------------------------------------------
fetch_latest_version() {
    local version=""

    # Method 1: GitHub API via gh CLI
    if command -v gh &>/dev/null; then
        version=$(gh api "repos/${REPO_OWNER}/${REPO_NAME}/releases/latest" --jq '.tag_name' 2>/dev/null || true)
        version="${version#v}"  # Strip 'v' prefix
        if [[ -n "$version" ]]; then
            echo "$version"
            return 0
        fi
    fi

    # Method 2: git ls-remote for tags
    version=$(git ls-remote --tags "https://github.com/${REPO_OWNER}/${REPO_NAME}.git" 2>/dev/null \
        | grep -o 'refs/tags/v[0-9]*\.[0-9]*\.[0-9]*$' \
        | sed 's|refs/tags/v||' \
        | sort -V \
        | tail -1 || true)
    if [[ -n "$version" ]]; then
        echo "$version"
        return 0
    fi

    # Method 3: curl VERSION file from raw.githubusercontent.com
    version=$(curl -s --connect-timeout 5 "https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/VERSION" 2>/dev/null | tr -d '[:space:]' || true)
    if [[ -n "$version" ]]; then
        echo "$version"
        return 0
    fi

    # All methods failed
    return 1
}

# ---------------------------------------------------------------------------
# Deprecation Check
# ---------------------------------------------------------------------------
check_deprecation() {
    local version="$1"

    if [[ ! -f "$DEPRECATIONS_FILE" ]]; then
        return 0
    fi

    # Check if version is in deprecated list
    local deprecated_info
    deprecated_info=$(grep -o "\"$version\"[^}]*}" "$DEPRECATIONS_FILE" 2>/dev/null || true)

    if [[ -n "$deprecated_info" ]]; then
        local reason
        reason=$(echo "$deprecated_info" | grep -o '"reason"\s*:\s*"[^"]*"' | sed 's/.*:.*"\(.*\)"/\1/' || echo "This version has known issues")
        log_warn "Your version ($version) is deprecated"
        log_warn "Reason: $reason. Update recommended."
        return 1
    fi

    # Check if version is below minimum supported
    local min_supported
    min_supported=$(grep -o '"minSupported"\s*:\s*"[^"]*"' "$DEPRECATIONS_FILE" 2>/dev/null | sed 's/.*:.*"\(.*\)"/\1/' || true)

    if [[ -n "$min_supported" ]] && version_lt "$version" "$min_supported"; then
        log_warn "Your version ($version) is below minimum supported ($min_supported)"
        log_warn "Please update to continue receiving support."
        return 1
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    # Read stdin (hook receives JSON) but we don't need it for version check
    cat > /dev/null

    # Skip if no local version file (not an AI Framework project)
    local local_version
    local_version=$(get_local_version)
    if [[ -z "$local_version" ]]; then
        exit 0
    fi

    # Check cache first
    local remote_version=""
    if is_cache_valid; then
        remote_version=$(read_cache)
    else
        # Fetch and cache (silently fail on network issues)
        remote_version=$(fetch_latest_version 2>/dev/null || true)
        if [[ -n "$remote_version" ]]; then
            write_cache "$remote_version"
        fi
    fi

    # Check deprecation status
    check_deprecation "$local_version" || true

    # Compare versions and notify if update available
    if [[ -n "$remote_version" ]] && version_lt "$local_version" "$remote_version"; then
        log_info "Update available: $local_version → $remote_version"
        log_info "Run: scripts/install.sh --update --target ."
    fi

    exit 0
}

main
