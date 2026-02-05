#!/usr/bin/env bash
# PreToolUse hook: Block dangerous Bash commands before execution.
#
# Reads stdin JSON to extract the command being run and rejects known
# destructive operations that can cause irreversible damage.
#
# Blocked commands:
#   - git push --force / -f to main/master
#   - rm -rf / or rm -rf /*
#   - git reset --hard on main/master
#   - git clean -fd on main/master
#   - DROP DATABASE / DROP TABLE (case insensitive)
#   - git commit when gitleaks detects secrets in staged files
#
# Exit codes:
#   0 = allow the command
#   2 = block the command (reason printed to stderr)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse stdin JSON
# ---------------------------------------------------------------------------
INPUT="$(cat)"

# Extract tool_name -- only act on Bash tool
TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ "$TOOL_NAME" != "Bash" ]]; then
    exit 0
fi

# Extract the command field from JSON
COMMAND="$(echo "$INPUT" | grep -o '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Normalize: collapse whitespace for reliable matching
CMD_NORMALIZED="$(echo "$COMMAND" | tr '\n' ' ' | sed 's/  */ /g')"

# ---------------------------------------------------------------------------
# Check for dangerous patterns
# ---------------------------------------------------------------------------

# 1. git push --force / -f to main or master
#    Catches: git push --force origin main, git push -f origin master, etc.
if echo "$CMD_NORMALIZED" | grep -qE 'git\s+push\s+.*(-f|--force).*\s+(main|master)'; then
    echo "BLOCKED: Force-pushing to main/master is prohibited. Use a feature branch." >&2
    exit 2
fi
if echo "$CMD_NORMALIZED" | grep -qE 'git\s+push\s+(-f|--force)\b'; then
    # Force push without explicit branch -- check if current branch is main/master
    CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
        echo "BLOCKED: Force-pushing on main/master is prohibited. Use a feature branch." >&2
        exit 2
    fi
fi

# 2. rm -rf / or rm -rf /*
#    Catches various flag orderings: rm -rf /, rm -fr /, rm -rf /*, etc.
if echo "$CMD_NORMALIZED" | grep -qE 'rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\s+(/\s|/\*|/$)'; then
    echo "BLOCKED: 'rm -rf /' is a catastrophic operation and is not allowed." >&2
    exit 2
fi

# 3. git reset --hard on main/master
if echo "$CMD_NORMALIZED" | grep -qE 'git\s+reset\s+--hard'; then
    CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
        echo "BLOCKED: 'git reset --hard' on main/master is prohibited. Use a feature branch." >&2
        exit 2
    fi
fi

# 4. git clean -fd on main/master
#    Catches: git clean -fd, git clean -df, git clean -f -d, etc.
if echo "$CMD_NORMALIZED" | grep -qE 'git\s+clean\s+(-[a-zA-Z]*f[a-zA-Z]*d|-[a-zA-Z]*d[a-zA-Z]*f)'; then
    CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
        echo "BLOCKED: 'git clean -fd' on main/master is prohibited. Use a feature branch." >&2
        exit 2
    fi
fi

# 5. DROP DATABASE or DROP TABLE (case insensitive)
#    Catches SQL commands in any context (psql, mysql, sqlcmd, echo, etc.)
if echo "$CMD_NORMALIZED" | grep -iqE 'drop\s+(database|table)\b'; then
    echo "BLOCKED: DROP DATABASE/TABLE commands are prohibited via CLI hooks." >&2
    exit 2
fi

# 6. Gitleaks check before git commit
#    Runs gitleaks on staged files to detect secrets before committing.
#    Uses 'gitleaks protect --staged' (gitleaks 8.x) to scan only staged content.
#    Fails open (warns) if gitleaks is not installed.
if echo "$CMD_NORMALIZED" | grep -qE 'git\s+commit\b'; then
    if command -v gitleaks &>/dev/null; then
        if ! gitleaks protect --staged --no-banner 2>/dev/null; then
            echo "BLOCKED: Secrets detected in staged files." >&2
            echo "Run 'gitleaks protect --staged --verbose' to see details." >&2
            exit 2
        fi
    else
        echo "WARNING: gitleaks not installed - skipping secret scan" >&2
    fi
fi

# ---------------------------------------------------------------------------
# Command is allowed
# ---------------------------------------------------------------------------
exit 0
